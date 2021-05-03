# File descriptor and timer event helper
#
# Copyright (C) 2016-2020  Kevin O'Connor <kevin@koconnor.net>
#
# This file may be distributed under the terms of the GNU GPLv3 license.
import os, gc, select, math, time, queue
import greenlet
import chelper, util
import multiprocessing

_NOW = 0.
_NEVER = 9999999999999999.

class ReactorTimer:
    def __init__(self, callback, waketime):
        self.callback = callback
        self.waketime = waketime

class ReactorCompletion:
    class sentinel: pass
    def __init__(self, reactor):
        self.reactor = reactor
        self.result = self.sentinel
        self.waiting = []
    def test(self):
        return self.result is not self.sentinel
    def complete(self, result):
        self.result = result
        for wait in self.waiting:
            self.reactor.update_timer(wait.timer, self.reactor.NOW)
    def wait(self, waketime=_NEVER, waketime_result=None):
        if self.result is self.sentinel:
            wait = greenlet.getcurrent()
            self.waiting.append(wait)
            self.reactor.pause(waketime)
            self.waiting.remove(wait)
            if self.result is self.sentinel:
                return waketime_result
        return self.result

class ReactorCallback:
    def __init__(self, reactor, callback, waketime, *args, **kwargs):
        self.reactor = reactor
        self.timer = reactor.register_timer(self.invoke, waketime)
        self.callback = callback
        self.args = args
        self.kwargs = kwargs
        self.completion = ReactorCompletion(reactor)
    def invoke(self, eventtime):
        self.reactor.unregister_timer(self.timer)
        res = self.callback(eventtime, *self.args, **self.kwargs)
        self.completion.complete(res)
        return self.reactor.NEVER

class MPCallback:
    def __init__(self, reactor, eventtime):
        self.reactor = reactor
        self.timer = reactor.register_timer(self.invoke, eventtime)
    def invoke(self, eventtime):
        self.reactor.unregister_timer(self.timer)
        while 1:
            try:
                cb, waketime, waiting_process, args, kwargs = self.reactor.mp_queue.get_nowait()
            except queue.Empty:
                import logging
                logging.info("mp callback retry")
                self.reactor.pause(self.reactor.monotonic() + 0.005)
                continue
            break
        res = cb(self.reactor.monotonic(), self.reactor.root, *args, **kwargs)
        if waiting_process:
            self.reactor.cb(self.reactor.mp_complete, (cb, waketime), res, process=waiting_process)
        return self.reactor.NEVER

class ReactorFileHandler:
    def __init__(self, fd, callback):
        self.fd = fd
        self.callback = callback
    def fileno(self):
        return self.fd

class ReactorGreenlet(greenlet.greenlet):
    def __init__(self, run):
        greenlet.greenlet.__init__(self, run=run)
        self.timer = None

class ReactorMutex:
    def __init__(self, reactor, is_locked):
        self.reactor = reactor
        self.is_locked = is_locked
        self.next_pending = False
        self.queue = []
        self.lock = self.__enter__
        self.unlock = self.__exit__
    def test(self):
        return self.is_locked
    def __enter__(self):
        if not self.is_locked:
            self.is_locked = True
            return
        g = greenlet.getcurrent()
        self.queue.append(g)
        while 1:
            self.reactor.pause(self.reactor.NEVER)
            if self.next_pending and self.queue[0] is g:
                self.next_pending = False
                self.queue.pop(0)
                return
    def __exit__(self, type=None, value=None, tb=None):
        if not self.queue:
            self.is_locked = False
            return
        self.next_pending = True
        self.reactor.update_timer(self.queue[0].timer, self.reactor.NOW)

class SelectReactor:
    NOW = _NOW
    NEVER = _NEVER
    def __init__(self, gc_checking=False, process='printer'):
        # Main code
        self.event_handlers = {}
        self.root = None
        self._process = False
        self.monotonic = chelper.get_ffi()[1].get_monotonic
        self.process_name = process
        # Python garbage collection
        self._check_gc = gc_checking
        self._last_gc_times = [0., 0., 0.]
        # Timers
        self._timers = []
        self._next_timer = self.NEVER
        # Callbacks
        self._async_pipe = None
        self._async_queue = queue.Queue()
        # Multiprocessing
        self.mp_queue = multiprocessing.Queue()
        self._mp_queues = {}
        self._mp_pipes_read = {}
        self._mp_pipes_write = {}
        self._mp_callback_handler = MPCallback
        self._mp_completions = {}
        # File descriptors
        self._fds = []
        # Greenlets
        self._g_dispatch = None
        self._greenlets = []
        self._all_greenlets = []
    def register_mp_callback_handler(self, handler):
        self._mp_callback_handler = handler
    @staticmethod
    def connect_mp(reactor_1, reactor_2):
        pipe_1_2 = os.pipe()
        pipe_2_1 = os.pipe()
        reactor_1.register_mp(reactor_2.process_name, reactor_2.mp_queue, pipe_1_2, pipe_2_1)
        reactor_2.register_mp(reactor_1.process_name, reactor_1.mp_queue, pipe_2_1, pipe_1_2)
    def register_mp(self, process, queue, write_pipe, read_pipe):
        self._mp_queues[process] = queue
        self._mp_pipes_write[process] = write_pipe[1]
        self._mp_pipes_read[process] = read_pipe[0]
        self.register_fd(read_pipe[0], self._got_mp_pipe_signal)
    def get_gc_stats(self):
        return tuple(self._last_gc_times)
    # Timers
    def update_timer(self, timer_handler, waketime):
        timer_handler.waketime = waketime
        self._next_timer = min(self._next_timer, waketime)
    def register_timer(self, callback, waketime=NEVER):
        timer_handler = ReactorTimer(callback, waketime)
        self._timers.append(timer_handler)
        self._next_timer = min(self._next_timer, waketime)
        return timer_handler
    def unregister_timer(self, timer_handler):
        timer_handler.waketime = self.NEVER
        timers = list(self._timers)
        timers.pop(timers.index(timer_handler))
        self._timers = timers
    def _check_timers(self, eventtime, busy):
        if eventtime < self._next_timer:
            if busy:
                return 0.
            if self._check_gc:
                gi = gc.get_count()
                if gi[0] >= 700:
                    # Reactor looks idle and gc is due - run it
                    gc_level = 0
                    if gi[1] >= 10:
                        gc_level = 1
                        if gi[2] >= 10:
                            gc_level = 2
                    self._last_gc_times[gc_level] = eventtime
                    gc.collect(gc_level)
                    return 0.
            return min(1., max(.001, self._next_timer - eventtime))
        self._next_timer = self.NEVER
        g_dispatch = self._g_dispatch
        for t in self._timers:
            waketime = t.waketime
            if eventtime >= waketime:
                t.waketime = self.NEVER
                t.waketime = waketime = t.callback(eventtime)
                if g_dispatch is not self._g_dispatch:
                    self._next_timer = min(self._next_timer, waketime)
                    self._end_greenlet(g_dispatch)
                    return 0.
            self._next_timer = min(self._next_timer, waketime)
        return 0.
    # Callbacks and Completions
    def completion(self):
        return ReactorCompletion(self)
    def register_callback(self, callback, waketime=NOW):
        rcb = ReactorCallback(self, callback, waketime)
        return rcb.completion
    # Asynchronous (from another thread) callbacks and completions
    def cb(self, callback, *args, waketime=NOW, process='printer', wait=False, **kwargs):
        if process is None or process == self.process_name:
            self._async_queue.put_nowait((ReactorCallback, (self, callback, waketime, *args), kwargs))
            try:
                os.write(self._async_pipe[1], b'.')
            except os.error:
                pass
        else:
            waiting_process = self.process_name if wait else None
            self._mp_queues[process].put_nowait((callback, waketime, waiting_process, args, kwargs))
            os.write(self._mp_pipes_write[process], b'.')
            if wait:
                completion = ReactorCompletion(self)
                self._mp_completions[(callback, waketime)] = completion
                return completion.wait()
    def register_async_callback(self, *args, **kwargs):
        self.cb(*args, process=self.process_name, **kwargs)
    @staticmethod
    def mp_complete(e, root, reference, result):
        root.reactor._mp_completions.pop(reference).complete(result)
    def async_complete(self, completion, result):
        self._async_queue.put_nowait((completion.complete, (result,), {}))
        try:
            os.write(self._async_pipe[1], b'.')
        except os.error:
            pass
    def _got_pipe_signal(self, eventtime):
        try:
            os.read(self._async_pipe[0], 4096)
        except os.error:
            pass
        while 1:
            try:
                func, args, kwargs = self._async_queue.get_nowait()
            except queue.Empty:
                break
            func(*args, **kwargs)
    def _got_mp_pipe_signal(self, eventtime):
        signal = b''
        for pipe in self._mp_pipes_read.values():
            signal += os.read(pipe, 4096)
        for i in range(signal.count(b'.')):
            self._mp_callback_handler(self, eventtime)
    # helper function to identify unpickleable arguments during development
    # def check_pickleable(self, args):
    #     import pickle
    #     is_kwarg = bool(type(args) is dict)
    #     if is_kwarg:
    #         items = args.items()
    #     else:
    #         args = list(args)
    #         items = enumerate(args)
    #     for key, value in items:
    #         try:
    #             pickle.dumps(value)
    #         except:
    #             import logging
    #             logging.warning(f"couldn't pickle arg {key}, {value}")
    #             args[key] = None
    #             raise
    #     if not is_kwarg:
    #         args = tuple(args)
    #     return args
    def _setup_async_callbacks(self):
        self._async_pipe = os.pipe()
        util.set_nonblock(self._async_pipe[0])
        util.set_nonblock(self._async_pipe[1])
        self.register_fd(self._async_pipe[0], self._got_pipe_signal)
    # Greenlets
    def _sys_pause(self, waketime):
        # Pause using system sleep for when reactor not running
        delay = waketime - self.monotonic()
        if delay > 0.:
            time.sleep(delay)
        return self.monotonic()
    def pause(self, waketime):
        g = greenlet.getcurrent()
        if g is not self._g_dispatch:
            if self._g_dispatch is None:
                return self._sys_pause(waketime)
            # Switch to _check_timers (via g.timer.callback return)
            return self._g_dispatch.switch(waketime)
        # Pausing the dispatch greenlet - prepare a new greenlet to do dispatch
        if self._greenlets:
            g_next = self._greenlets.pop()
        else:
            g_next = ReactorGreenlet(run=self._dispatch_loop)
            self._all_greenlets.append(g_next)
        g_next.parent = g.parent
        g.timer = self.register_timer(g.switch, waketime)
        self._next_timer = self.NOW
        # Switch to _dispatch_loop (via _end_greenlet or direct)
        eventtime = g_next.switch()
        # This greenlet activated from g.timer.callback (via _check_timers)
        return eventtime
    def _end_greenlet(self, g_old):
        # Cache this greenlet for later use
        self._greenlets.append(g_old)
        self.unregister_timer(g_old.timer)
        g_old.timer = None
        # Switch to _check_timers (via g_old.timer.callback return)
        self._g_dispatch.switch(self.NEVER)
        # This greenlet reactivated from pause() - return to main dispatch loop
        self._g_dispatch = g_old
    # Mutexes
    def mutex(self, is_locked=False):
        return ReactorMutex(self, is_locked)
    # File descriptors
    def register_fd(self, fd, callback):
        file_handler = ReactorFileHandler(fd, callback)
        self._fds.append(file_handler)
        return file_handler
    def unregister_fd(self, file_handler):
        self._fds.pop(self._fds.index(file_handler))
    # Main loop
    def _dispatch_loop(self):
        self._g_dispatch = g_dispatch = greenlet.getcurrent()
        busy = True
        eventtime = self.monotonic()
        while self._process:
            timeout = self._check_timers(eventtime, busy)
            busy = False
            res = select.select(self._fds, [], [], timeout)
            eventtime = self.monotonic()
            for fd in res[0]:
                busy = True
                fd.callback(eventtime)
                if g_dispatch is not self._g_dispatch:
                    self._end_greenlet(g_dispatch)
                    eventtime = self.monotonic()
                    break
        self._g_dispatch = None
        if self.process_name != 'printer':
            self.finalize()
    def run(self):
        if self._async_pipe is None:
            self._setup_async_callbacks()
        self._process = True
        g_next = ReactorGreenlet(run=self._dispatch_loop)
        self._all_greenlets.append(g_next)
        g_next.switch()
    def end(self, e=None):
        self._process = False
    def finalize(self):
        self._g_dispatch = None
        self._greenlets = []
        for g in self._all_greenlets:
            try:
                g.throw()
            except:
                import logging
                logging.exception("reactor finalize greenlet terminate")
        self._all_greenlets = []
        if self._async_pipe is not None:
            for pipe in (self._async_pipe
                + tuple(self._mp_pipes_read.values())
                + tuple(self._mp_pipes_write.values())):
                os.close(pipe)
            self._async_pipe = None
    def register_event_handler(self, event, callback):
        self.event_handlers.setdefault(event, []).append(callback)
    def send_event(self, event, *params):
        for process in self._mp_queues.keys():
            self.cb(self.run_event, event, params, process=process)
        return self.run_event(None, self.root, event, params)
    def send_event_wait_check_status(self, event, *params, status=None):
        # Start event handlers in all processes
        self._pending_event_handlers = {}
        for process in self._mp_queues.keys():
            self._pending_event_handlers[process] = True
            self.cb(self.send_event_wait, event, params, process=process)
        for cb in self.event_handlers.get(event, []):
            if self.root.state_message is not status:
                return
            cb()
        # Wait for all processes to finish event handlers
        while True in self._pending_event_handlers.values():
            self.pause(self.monotonic() + 0.01)
    @staticmethod
    def run_event(e, root, event, params):
        return [cb(*params) for cb in root.reactor.event_handlers.get(event, [])]
    @staticmethod
    def send_event_wait(e, root, event, params):
        root.reactor.run_event(e, root, event, params)
        root.reactor.cb(root.reactor.note_event_handlers_done, root.reactor.process_name, process='printer')
    @staticmethod
    def note_event_handlers_done(e, printer, done_process):
        printer.reactor._pending_event_handlers[done_process] = False

class PollReactor(SelectReactor):
    def __init__(self, gc_checking=False, process='printer'):
        SelectReactor.__init__(self, gc_checking, process)
        self._poll = select.poll()
        self._fds = {}
    # File descriptors
    def register_fd(self, fd, callback):
        file_handler = ReactorFileHandler(fd, callback)
        fds = self._fds.copy()
        fds[fd] = callback
        self._fds = fds
        self._poll.register(file_handler, select.POLLIN | select.POLLHUP)
        return file_handler
    def unregister_fd(self, file_handler):
        self._poll.unregister(file_handler)
        fds = self._fds.copy()
        del fds[file_handler.fd]
        self._fds = fds
    # Main loop
    def _dispatch_loop(self):
        self._g_dispatch = g_dispatch = greenlet.getcurrent()
        busy = True
        eventtime = self.monotonic()
        while self._process:
            timeout = self._check_timers(eventtime, busy)
            busy = False
            res = self._poll.poll(int(math.ceil(timeout * 1000.)))
            eventtime = self.monotonic()
            for fd, event in res:
                busy = True
                self._fds[fd](eventtime)
                if g_dispatch is not self._g_dispatch:
                    self._end_greenlet(g_dispatch)
                    eventtime = self.monotonic()
                    break
        self._g_dispatch = None

class EPollReactor(SelectReactor):
    def __init__(self, gc_checking=False, process='printer'):
        SelectReactor.__init__(self, gc_checking, process)
        self._epoll = select.epoll()
        self._fds = {}
    # File descriptors
    def register_fd(self, fd, callback):
        file_handler = ReactorFileHandler(fd, callback)
        fds = self._fds.copy()
        fds[fd] = callback
        self._fds = fds
        self._epoll.register(fd, select.EPOLLIN | select.EPOLLHUP)
        return file_handler
    def unregister_fd(self, file_handler):
        self._epoll.unregister(file_handler.fd)
        fds = self._fds.copy()
        del fds[file_handler.fd]
        self._fds = fds
    # Main loop
    def _dispatch_loop(self):
        self._g_dispatch = g_dispatch = greenlet.getcurrent()
        busy = True
        eventtime = self.monotonic()
        while self._process:
            timeout = self._check_timers(eventtime, busy)
            busy = False
            res = self._epoll.poll(timeout)
            eventtime = self.monotonic()
            for fd, event in res:
                busy = True
                self._fds[fd](eventtime)
                if g_dispatch is not self._g_dispatch:
                    self._end_greenlet(g_dispatch)
                    eventtime = self.monotonic()
                    break
        self._g_dispatch = None

# Use the poll based reactor if it is available
try:
    select.poll
    Reactor = PollReactor
except:
    Reactor = SelectReactor
