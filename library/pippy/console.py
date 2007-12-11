"""Console helpers for pippy."""
import sys
def clear():
    """Clear screen on console."""
    # magic escape sequence
    sys.stdout.write('\x1B[H\x1B[J')

def red():
    """Change text color to red."""
    # magic escape sequence.
    sys.stdout.write('\x1B[0;31m')

def green():
    """Change text color to green."""
    # magic escape sequence.
    sys.stdout.write('\x1B[0;32m')

def orange():
    """Change text color to orange."""
    # magic escape sequence.
    sys.stdout.write('\x1B[0;33m')

def blue():
    """Change text color to blue."""
    # magic escape sequence.
    sys.stdout.write('\x1B[0;34m')

def purple():
    """Change text color to purple."""
    # magic escape sequence.
    sys.stdout.write('\x1B[0;35m')

def cyan():
    """Change text color to cyan."""
    # magic escape sequence.
    sys.stdout.write('\x1B[0;36m')

def grey():
    """Change text color to grey."""
    # magic escape sequence.
    sys.stdout.write('\x1B[0;37m')
gray=grey

def black():
    """Change text color to blue."""
    # magic escape sequence.
    # ;38m seems to be identical to this one.
    sys.stdout.write('\x1B[0;39m')

def reset():
    """Clear screen and reset text color to black."""
    clear()
    black()
