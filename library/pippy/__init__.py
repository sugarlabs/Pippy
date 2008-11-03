"""Pippy standard library."""
import pippy.console as console
import pippy.game as pygame
#import pippy.physics as physics

try:
    import pippy.sound as sound
except ImportError:
    pass # this module fails to import on non-XOs.

def wait(delay=0.1):
    """Pause briefly, for animations."""
    import time
    time.sleep(delay)
