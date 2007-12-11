"""Console helpers for pippy."""
def clear():
    """Clear screen on console."""
    # magic escape sequence
    print '\x1B[H\x1B[J' # clear screen
