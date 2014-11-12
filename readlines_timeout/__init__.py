#!/usr/bin/env python
"""
The MIT License (MIT)

Copyright (c) 2014 Stanislaw Pitucha

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.
"""

import fcntl
import os
import select


class Timeout(object):
    """Marker for timeout value. If it's returned, there
    was not enough data to return a full line.
    """
    pass

TIMEOUT = Timeout()


def readlines(open_file, timeout, callback=None, read_size=8*1024,
              keepends=False):
    """
    Iterate over lines from a given file object, additionally notifying
    about timeouts while waiting for another line. Timeout is reset after
    any successful read, not only complete new line.

    If callback is provided, it will be called on each timeout with the
    current buffer as a parameter. Otherwise the TIMEOUT object will be
    returned.

    Any exception raised by open_file.read() may be raised here.
    """

    empty_buffer = b"" if "b" in open_file.mode else ""
    line_end = b"\n"[0] if "b" in open_file.mode else "\n"
    buffer = empty_buffer

    # put fd in nonblocking mode
    orig_mode = fcntl.fcntl(open_file, fcntl.F_GETFL)
    fcntl.fcntl(open_file, fcntl.F_SETFL, orig_mode | os.O_NONBLOCK)

    # prepare polling
    ms_timeout = int(timeout * 1000)
    poll = select.poll()
    poll.register(open_file, select.POLLIN)

    while True:
        res = poll.poll(ms_timeout)
        if res:
            # file is ready for reading
            new_data = open_file.read(read_size)

            if new_data == empty_buffer:
                # end of file
                if buffer:
                    yield buffer
                break

            buffer += new_data

            # yield all lines we've got so far (may be multiple)
            while True:
                line, sep, tail = buffer.partition(line_end)
                if not sep:
                    break

                if keepends:
                    yield line + sep
                else:
                    yield line

                buffer = tail

        else:
            # no new data is available, notify about the timeout
            if callback is None:
                yield TIMEOUT
            else:
                callback(buffer)

    # restore original blocking behaviour if it's been removed
    fcntl.fcntl(open_file, fcntl.F_SETFL, orig_mode)

if __name__ == "__main__":
    import sys

    def print_timeout(buffer):
        print("Timeout (buffer so far: %s)" % buffer)

    for line in readlines(sys.stdin, 1, print_timeout):
        print("Line: %s" % line)
