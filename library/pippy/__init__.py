"""Pippy standard library."""
import pippy.console as console
import pippy.game as pygame
import pippy.sound as sound

def wait(delay=0.1):
    """Pause briefly, for animations."""
    import time
    time.sleep(delay)
