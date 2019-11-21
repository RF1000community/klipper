#!/usr/bin/env python2
# coding: utf-8

"""
freedir() for removing files until enough space is available on the
disk.
"""

from os import stat, listdir, remove
from os.path import isdir, isfile, expanduser, join, getmtime
from subprocess import Popen, PIPE, STDOUT
import sys


def freedir(directory, threshold=100, stop=500):
    """
    If available disk space is below a certain threshold, delete the
    oldest files in a given directory until a given amount of available
    space is reached.

    Parameters:
    directory   string/list Directory in which to delete files.  If
                            list of dirs is given, delete the oldest
                            files out of all dirs.
    threshold   int         At what amount of available space to start
                            deleting.  Available partition space in MiB,
                            defaults to 100.
    stop        int         Stop deleting as soon as this amount of
                            space is reached.  Available partition space
                            in MiB, defaults to 500.

    Return values:
    0           Deleted files and reached specified amount of space.
    1           More space left than specified threshold.
                Nothing deleted.
    2           Not enough files specified to reach space set in stop.
    3           Error while deleting files (Permission denied)
    """

    dirs = check_input(directory)
    avail = get_space(dirs[0])
    print("Available space: " + str(avail) + "M")

    # Enough space left, return
    if avail > threshold:
        return 1

    files = []
    for i in dirs:
        for j in listdir(i):
            path = join(i, j)
            # Ignore contained directories
            if isfile(path):
                files.append(path)
    # Sort to oldest files last (as of last modification time)
    files.sort(key=getmtime, reverse=True)

    while get_space(dirs[0]) < stop and files:
        cur_file = files.pop()
        # Uncomment to disable safeguard
        ###remove(cur_file)
        print("Deleted " + cur_file)

    if get_space(dirs[0]) < stop:
        # Not enough files to delete
        return 2
    return 0


def check_input(dirs):
    """
    Parses the specified str/list of directories and checks for wrong
    arguments.
    """
    if isinstance(dirs, str):
        dirs = [dirs]
    elif not isinstance(dirs, (list, tuple)):
        raise TypeError(
            "directory argument must be either a list, tuple or string")

    for i, _ in enumerate(dirs):
        dirs[i] = expanduser(dirs[i])
        if not isdir(dirs[i]):
            raise ValueError("Not a directory: " + dirs[i])
        # All directorie must be in the same partition
        if i == 0:
            device = stat(dirs[0]).st_dev
        elif not stat(dirs[i]).st_dev == device:
            raise ValueError("All directories must lie on the same partition")
    return dirs


def get_space(path):
    """
    Get available disk space. -BM gives output in M (1,048,576 Bytes)
    """
    df_cmd = ['df', '-BM', '--output=avail', path]
    proc = Popen(df_cmd, stdout=PIPE, stderr=STDOUT, universal_newlines=True)
    output = proc.communicate()[0]
    if proc.returncode != 0:
        raise Exception('df failed with returncode ' + proc.returncode)
    output = output.splitlines()[1]
    avail = int(output.rstrip('M'))
    return avail


if __name__ == '__main__':
    args = [sys.argv[1].split(',')]
    args.extend([int(i) for i in sys.argv[2:4]])
    status = freedir(*args)
    print(status)
