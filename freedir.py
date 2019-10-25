#!/usr/bin/env python2
# coding: utf-8

from subprocess import Popen, PIPE, STDOUT
import sys
from os import stat, listdir, remove
from os.path import isdir, isfile, expanduser, join, getmtime


def freedir(directory, threshold=100, stop=500):
    """
    If available disk space is below a certain threshold, delete the oldest
    files in a given directory until a given amount of available space is
    reached.

    Parameters:
    directory   string/list Directory in which to delete files. If list of dirs
                            is given, delete the oldest files out of all dirs.
    threshold   int         At what amount of available space to start deleting.
                            Available partition space in MiB, defaults to 100.
    stop        int         Stop deleting as soon as this amount of space is reached.
                            Available partition space in MiB, defaults to 500.

    Return values:
    0           Deleted files and reached specified amount of space.
    1           More space left than specified threshold. Nothing deleted.
    2           Not enough files specified to reach available space set in stop.
    3           Error while deleting files (Permission denied)
    4           Argument error
    5           Directories not on same partition.
    """

    if type(directory) == str:
        dirs = [directory]
    elif type(directory) in (tuple, list):
        dirs = directory
    else:
        return 4

    for i in range(len(dirs)):
        dirs[i] = expanduser(dirs[i])
        if not isdir(dirs[i]):
            return 4

        # Compare the partitions of all directories
        if i == 0:
            device = stat(dirs[0]).st_dev
        elif not stat(dirs[i]).st_dev == device:
            return 5

    avail = get_space(dirs[0])
    print("Available space: " + str(avail) + "M")

    # Enough space left, return
    if avail > threshold:
        return 1

    files = []
    for i in dirs:
        for j in listdir(i):
            path = join(i, j)
            if isfile(path):
                files.append(path)

    # Sort to oldest files last (as of last modification time)
    files.sort(key = lambda F: getmtime(F), reverse=True)

    while get_space(dirs[0]) < stop and files:
        cur_file = files.pop()
        try:
            # Uncomment to disable safeguard
            ###remove(cur_file)
            print("Deleted " + cur_file)
        except PermissionError:
            return 3

    if get_space(dirs[0]) >= stop:
        # Everything OK
        return 0
    else:
        # Not enough files to delete
        return 2

def get_space(path):
    # Get available disk space. -BM gives output in M (1,048,576 Bytes)
    df_cmd = ['df', '-BM', '--output=avail', path]
    proc = Popen(df_cmd, stdout=PIPE, stderr=STDOUT, universal_newlines=True)
    output = proc.communicate()[0]
    if proc.returncode != 0:
        raise Exception('Error while calling df')
    output = output.splitlines()[1]
    avail = int(output.rstrip('M'))
    end = time.time()
    return avail

if __name__ == '__main__':
    args = [sys.argv[1].split(',')]
    args.extend([int(i) for i in sys.argv[2:4]])
    status = freedir(*args)
    print(status)
