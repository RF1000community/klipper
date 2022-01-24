# File descriptor and timer event helper
#
# Copyright (C) 2016-2020  Kevin O'Connor <kevin@koconnor.net>
#
# This file may be distributed under the terms of the GNU GPLv3 license.
import os, gc, select, math, time, logging, queue
import greenlet
import chelper, util
import threading

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
        self.foreign_thread = False
    def test(self):
        return self.result is not self.sentinel
    def complete(self, result):
        self.result = result
        if not self.foreign_thread:
            for wait in self.waiting:
                self.reactor.update_timer(wait.timer, self.reactor.NOW)
    def wait(self, waketime=_NEVER, waketime_result=None):
        if threading.get_ident() != self.reactor.thread_id:
            self.foreign_thread = True
            while self.result is self.sentinel:
                time.sleep(0.01)
        elif self.result is self.sentinel:
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

def mp_callback(reactor, *args, **kwargs):
    reactor.register_async_callback(run_mp_callback, reactor, *args, **kwargs)

def run_mp_callback(e, reactor, callback, waketime, waiting_process, *args, **kwargs):
    res = callback(e, reactor.root, *args, **kwargs)
    if waiting_process:
        reactor.cb(reactor.mp_complete,
            (callback.__name__, waketime, reactor.process_name), res, process=waiting_process)

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
        self.event_history = [] if process == 'printer' else None
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
        self.mp_queue = None
        self.mp_queues = {}
        self._mp_callback_handler = mp_callback
        self._mp_completions = {}
        # File descriptors
        self._fds = []
        # Greenlets
        self._g_dispatch = None
        self._greenlets = []
        self._all_greenlets = []
        self.thread_id = threading.get_ident()
    def register_mp_callback_handler(self, handler):
        self._mp_callback_handler = handler
    # Start dispatching mp tasks, execute after run()
    def setup_mp_queues(self, queues):
        mp_queues = queues.copy()
        self.mp_queue = mp_queues.pop(self.process_name)
        self.mp_queues = mp_queues
        self._mp_dispatch_thread = threading.Thread(target=self._mp_dispatch_loop)
        self._mp_dispatch_thread.start()
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
    # Multiprocessing (from another process) callbacks and completions
    def cb(self, callback, *args, waketime=NOW, process='printer', wait=False, completion=False, **kwargs):
        waiting_process = None
        if wait or completion:
            waiting_process = self.process_name
            waketime = self.monotonic() # This gives unique reference to completion
            mp_completion = ReactorCompletion(self)
            self._mp_completions[(callback.__name__, waketime, process)] = mp_completion
        self.mp_queues[process].put_nowait((callback, waketime, waiting_process, args, kwargs))
        if wait:
            return mp_completion.wait()
        if completion:
            return mp_completion
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
    #             raise
    @staticmethod
    def mp_complete(e, root, reference, result):
        root.reactor.async_complete(root.reactor._mp_completions.pop(reference), result)
    # Asynchronous (from another thread) callbacks and completions
    def register_async_callback(self, callback, *args, waketime=NOW, **kwargs):
        self._async_queue.put_nowait((ReactorCallback, (self, callback, waketime, *args), kwargs))
        try:
            os.write(self._async_pipe[1], b'.')
        except os.error:
            pass
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
    def _mp_dispatch_loop(self):
        while self._process:
            cb, waketime, waiting_process, args, kwargs = self.mp_queue.get()
            self._mp_callback_handler(self, cb, waketime, waiting_process, *args, **kwargs)
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
        self.mp_queue.put_nowait((self.run_event, 0, None, ("trigger_mp_dispatch", []), {}))
        self._mp_dispatch_thread.join()
        if self._async_pipe is not None:
            os.close(self._async_pipe[0])
            os.close(self._async_pipe[1])
            self._async_pipe = None
        for g in self._all_greenlets: # Seems like this exits parallel_extras, run after other cleanup
            try:
                g.throw()
            except:
                logging.exception("reactor finalize greenlet terminate")
        self._all_greenlets = []
    def register_event_handler(self, event, callback):
        self.event_handlers.setdefault(event, []).append(callback)
    def send_event(self, event, *params):
        for process in self.mp_queues:
            self.cb(self.run_event, event, params, process=process)
        return self.run_event(None, self.root, event, params)
    def send_event_wait(self, event, *params, check_status=None):
        # Start event handlers in other processes
        completions = [self.cb(self.run_event, event, params, completion=True, process=process)
            for process in self.mp_queues]
        # Run events in printer process
        for cb in self.event_handlers.get(event, []):
            if self.root.state_message != check_status != None:
                return
            cb()
        # Wait for other processes to finish event handlers
        for completion in completions:
            completion.wait()
    @staticmethod
    def run_event(e, root, event, params):
        if root.reactor.event_history != None:
            root.reactor.event_history.append((event, params))
        return [cb(*params) for cb in root.reactor.event_handlers.get(event, [])]
    def get_event_history(self):
        event_history = self.event_history
        self.event_history = None
        return event_history
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
        if self.process_name != 'printer':
            self.finalize()

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
        if self.process_name != 'printer':
            self.finalize()

# Use the poll based reactor if it is available
try:
    select.poll
    Reactor = PollReactor
except:
    Reactor = SelectReactor
