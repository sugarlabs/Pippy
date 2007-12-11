"""pygame support for pippy."""

import pygame

def pause():
    """Display a "Paused" screen and suspend."""
    from gettext import gettext as _
    caption, icon_caption = pygame.display.get_caption()
    screen = pygame.display.get_surface()
    old_screen = screen.copy()  # save this for later.

    # dim the screen and display the 'paused' message in the center.
    BLACK = (0,0,0)
    WHITE = (255,255,255)
    dimmed = screen.copy()
    dimmed.set_alpha(128)
    screen.fill(WHITE)
    screen.blit(dimmed, (0,0))
    font = pygame.font.Font(None, 36) # 36px high
    msg = _("PAUSED")
    msg_surf = font.render(msg, True, BLACK, WHITE)
    def center(rect, screen):
        rect.center = (screen.get_width()/2, screen.get_height()/2)
    
    rect = pygame.Rect((0,0),msg_surf.get_size())
    rect.inflate_ip(rect.width, rect.height)
    center(rect, screen)
    screen.fill(WHITE, rect)
    rect = msg_surf.get_rect()
    center(rect, screen)
    screen.blit(msg_surf, rect)
    pygame.display.flip()

    # SUSPEND
    try:
        open('/sys/power/state','w').write('mem')
    except: # XXX: couldn't suspend (no permissions?)
        pygame.event.post(pygame.event.wait())

    pygame.display.set_caption(caption, icon_caption)
    screen.blit(old_screen, (0,0))
    pygame.display.flip()

_last_event_time=0
def next_frame(max_fps=20, idle_timeout=20,
               clock=pygame.time.Clock(), pause=pause):
    """Limit maximum frame rate of pygame.  Returns True.

    If idle longer than the idle_timeout (in seconds), then we'll put up a
    "paused" message and the XO will suspend.  This ensures that we don't
    burn up all of our battery running an animation!"""
    global _last_event_time
    clock.tick(max_fps)

    if pygame.event.peek(xrange(pygame.NOEVENT, pygame.USEREVENT)):
        # we're not idle anymore.
        _last_event_time = pygame.time.get_ticks()
    elif (pygame.time.get_ticks() - _last_event_time) >= idle_timeout*1000:
        # we've been idle for a long time.  Pause & suspend.
        pause()
        _last_event_time = pygame.time.get_ticks()
        
    return True
