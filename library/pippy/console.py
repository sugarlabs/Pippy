"""Console helpers for pippy."""
# Copyright (C) 2007,2008,2010 One Laptop per Child Association, Inc.
# Written by C. Scott Ananian <cscott@laptop.org>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA
import sys
import os
import tty
import termios


def clear():
    """Clear screen on console."""
    # magic escape sequence
    sys.stdout.write('\x1B[H\x1B[J')


def size():
    """Return the number of rows/columns in the current terminal widget."""
    # xterm magic! see http://rtfm.etla.org/xterm/ctlseq.html
    fd = os.open('/dev/tty', os.O_RDWR | os.O_APPEND)

    def read_to_delimit(delimit):
        buf = []
        while True:
            c = os.read(fd, 1)
            if c == delimit:
                break
            buf.append(c)
        return ''.join(buf)
    oldattr = termios.tcgetattr(fd)  # make sure we can restore tty state
    tty.setraw(fd, termios.TCSANOW)  # set to raw mode.
    os.write(fd, '\x1B[18t')         # write the 'query screen size' command
    read_to_delimit('\x1b')          # parse response.
    read_to_delimit('[')
    size = read_to_delimit('t')
    # Output can be '8;rows;cols' or 'rows;cols' depending on vte version.
    # (SL #843)
    values = size.split(';')
    if len(values) == 3:
        rows = int(values[1])
        cols = int(values[2])
    else:
        rows = int(values[0])
        cols = int(values[1])
    termios.tcsetattr(fd, termios.TCSANOW, oldattr)  # reset tty
    return cols, rows


def getpos():
    """Return the current x, y position of the cursor on the screen.

    The top-left corner is 1,1."""
    # xterm magic! see http://rtfm.etla.org/xterm/ctlseq.html
    sys.stdout.flush()  # ensure that writes to the terminal have finished
    fd = os.open('/dev/tty', os.O_RDWR | os.O_APPEND)

    def read_to_delimit(delimit):
        buf = []
        while True:
            c = os.read(fd, 1)
            if c == delimit:
                break
            buf.append(c)
        return ''.join(buf)
    oldattr = termios.tcgetattr(fd)  # make sure we can restore tty state
    tty.setraw(fd, termios.TCSANOW)  # set to raw mode.
    os.write(fd, '\x1B[6n')          # Report Cursor Position
    read_to_delimit('\x1b')          # parse response.
    read_to_delimit('[')
    row = int(read_to_delimit(';'))
    col = int(read_to_delimit('R'))
    termios.tcsetattr(fd, termios.TCSANOW, oldattr)  # reset tty
    return col, row


def setpos(column, row):
    """Move to the given position on the screen.

    The top-left corner is 1,1"""
    # xterm magic! see http://rtfm.etla.org/xterm/ctlseq.html
    sys.stdout.write('\x1B[%d;%dH' % (row, column))


def up(count=1):
    """Move the cursor up the given number of rows."""
    sys.stdout.write('\x1B[%dA' % count)


def down(count=1):
    """Move the cursor down the given number of rows."""
    sys.stdout.write('\x1B[%dB' % count)


def forward(count=1):
    """Move the cursor forward the given number of columns."""
    sys.stdout.write('\x1B[%dC' % count)


def backward(count=1):
    """Move the cursor backward the given number of columns."""
    sys.stdout.write('\x1B[%dD' % count)


def normal():
    """Switch to normal text."""
    sys.stdout.write('\x1B[0m')


def bold():
    """Switch to bold text."""
    sys.stdout.write('\x1B[1m')


def underlined():
    """Switch to underlined text."""
    sys.stdout.write('\x1B[4m')


def inverse():
    """Switch to inverse text."""
    sys.stdout.write('\x1B[7m')


def black():
    """Change text color to black."""
    # magic escape sequence.
    sys.stdout.write('\x1B[30m')


def red():
    """Change text color to red."""
    # magic escape sequence.
    sys.stdout.write('\x1B[31m')


def green():
    """Change text color to green."""
    # magic escape sequence.
    sys.stdout.write('\x1B[32m')


def yellow():
    """Change text color to yellow."""
    # magic escape sequence.
    sys.stdout.write('\x1B[33m')


def blue():
    """Change text color to blue."""
    # magic escape sequence.
    sys.stdout.write('\x1B[34m')


def magenta():
    """Change text color to magenta."""
    # magic escape sequence.
    sys.stdout.write('\x1B[35m')


def cyan():
    """Change text color to cyan."""
    # magic escape sequence.
    sys.stdout.write('\x1B[36m')


def white():
    """Change text color to white."""
    # magic escape sequence.
    sys.stdout.write('\x1B[37m')


def hide_cursor():
    """Hide the cursor."""
    sys.stdout.write('\x1B[?25l')


def show_cursor():
    """Show the cursor."""
    sys.stdout.write('\x1B[?25h')


def reset():
    """Clear screen and reset text color."""
    clear()
    show_cursor()
    sys.stdout.write('\x1B[0;39m')
