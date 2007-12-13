"""Console helpers for pippy."""
import sys
def clear():
    """Clear screen on console."""
    # magic escape sequence
    sys.stdout.write('\x1B[H\x1B[J')

def size():
    """Return the number of rows/columns in the current terminal widget."""
    # xterm magic! see http://rtfm.etla.org/xterm/ctlseq.html
    import os, tty, termios
    fd = os.open('/dev/tty', os.O_RDWR|os.O_APPEND)
    def read_to_delimit(delimit):
        buf = []
        while True:
            c = os.read(fd, 1)
            if c==delimit: break
            buf.append(c)
        return ''.join(buf)
    oldattr = termios.tcgetattr(fd) # make sure we can restore tty state
    tty.setraw(fd, termios.TCSANOW) # set to raw mode.
    os.write(fd, '\x1B[18t')        # write the 'query screen size' command
    read_to_delimit('\x1b')         # parse response.
    read_to_delimit('[')
    rows = int(read_to_delimit(';'))
    cols = int(read_to_delimit('t'))
    termios.tcsetattr(fd, termios.TCSANOW, oldattr) # reset tty
    return rows, cols

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
    """Switch to underlined text."""
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


def reset():
    """Clear screen and reset text color."""
    clear()
    sys.stdout.write('\x1B[0;39m')
