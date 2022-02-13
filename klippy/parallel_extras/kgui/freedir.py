#!/usr/bin/env python3
"""
freedir() for removing files until enough space is available on the
disk.

Can be used from the command line as well as follows:

./freedir.py path1[,path2,...] [threshold] [stop]
"""

from os import stat, listdir, remove
from os.path import isdir, isfile, islink, expanduser, join, getmtime
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

    Returns a tuple (number of files deleted, space freed in MiB)
    """

    dirs = _check_input(directory)
    avail = get_space(dirs[0])

    # Enough space left, return
    if avail > threshold:
        return (0, 0)

    files = []
    for i in dirs:
        for j in listdir(i):
            path = join(i, j)
            # Ignore contained directories and symlinks
            if not(isdir(path) or islink(path)):
                files.append(path)
    # Sort to oldest files last (as of last modification time)
    files.sort(key=getmtime, reverse=True)

    fcount = 0
    while get_space(dirs[0]) < stop and files:
        cur_file = files.pop()
        remove(cur_file)
        fcount += 1

    return (fcount, get_space(dirs[0]) - avail)


def reducedir(directory, nfiles=100):
    """
    Reduce a directory to the specified amount of files.

    Parameters:
    directory   string/list Directory in which to delete files.  If
                            list of dirs is given, delete the oldest
                            files out of all dirs.
    nfiles      int         Maximum amount of files to keep.
                            Defaults to 100.

    Returns the number of files that were deleted.
    """

    dirs = _check_input(directory)
    files = []
    for i in dirs:
        for j in listdir(i):
            path = join(i, j)
            # Ignore directories, but take symlinks
            if isfile(path):
                files.append(path)
    if len(files) <= nfiles:
        return 0
    files.sort(key=getmtime)
    # How many files to delete
    ndel = len(files) - nfiles

    for i in range(ndel):
        remove(files[i])
    return ndel


def _check_input(dirs):
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


def get_space(path='.'):
    """
    Get available disk space.
    -BM gives output as an integer value in M (1,048,576 Bytes)
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
