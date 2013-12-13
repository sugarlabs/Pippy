# pong: hit the ball with the paddle
#
# use the escape key to exit
#
# on the XO, the escape key is the top lefthand key,
# circle with an x in it.

import pippy
import pygame
import sys
from pygame.locals import *
from random import *

# always need to init first thing
pygame.init()

# create the window and keep track of the surface
# for drawing into
screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)

# ask for screen's width and height
size = width, height = screen.get_size()

# turn off the cursor
pygame.mouse.set_visible(False)

# turn on key repeating (repeat 40 times per second)
pygame.key.set_repeat(25, 25)

# start the screen all black
bgcolor = (0, 0, 0)
screen.fill(bgcolor)

# paddle constants
paddle_width = 20
paddle_length = 100
paddle_radius = paddle_length / 2
paddle_color = (250, 250, 250)
step = 6  # paddle moves 3 pixels at a go

# ball constants
ball_color = (250, 250, 250)
ball_radius = 25

# game constants
fsize = 48
msg = 'Press \'g\' to start game'

font = pygame.font.Font(None, fsize)
text = font.render(msg, True, (250, 250, 250))
textRect = text.get_rect()
textRect.centerx = screen.get_rect().centerx
textRect.centery = screen.get_rect().centery

while pippy.pygame.next_frame():

    # display msg
    screen.fill(bgcolor)
    screen.blit(text, textRect)
    pygame.display.flip()

    # chill until a key is pressed
    for idle_event in pygame.event.get():
        if idle_event.type == QUIT:
            sys.exit()

        if idle_event.type == KEYDOWN:
            if idle_event.key == K_ESCAPE:
                sys.exit()

            if idle_event.key == 103:  # g key

                # play a game!

                # start the paddle in the center
                paddle_location = height / 2

                # number of balls to a game
                balls = 4

                while balls > 0:

                    ball_position = [ball_radius, ball_radius]
                    ball_mvect = [randint(3, 5), randint(3, 5)]
                    ball_limit = size
                    balls = balls - 1

                    while ball_position[0] + ball_radius < ball_limit[0]:  # in play

                        for event in pygame.event.get():
                            if event.type == QUIT:
                                sys.exit()

                            elif event.type == KEYDOWN:
                                if event.key == K_ESCAPE:
                                    sys.exit()
                                elif event.key == 273 \
                                    or event.key == 265 \
                                    or event.key == 264:  # up
                                    paddle_location = paddle_location - step
                                elif event.key == 274 \
                                    or event.key == 259 \
                                    or event.key == 258:  # down
                                    paddle_location = paddle_location + step

                        # make sure the paddle is in-bounds
                        if paddle_location - paddle_radius < 0:
                            paddle_location = paddle_radius
                        elif paddle_location + paddle_radius >= height:
                            paddle_location = height - 1 - paddle_radius

                        # clear the screen
                        screen.fill(bgcolor)

                        # draw the paddle on the right side of the screen
                        pygame.draw.line(screen,
                                        paddle_color,
                                        (width - paddle_width, paddle_location -
                                        paddle_radius),
                                        (width - paddle_width,
                                        paddle_location + paddle_radius),
                                        paddle_width)

                        # draw the ball
                        pygame.draw.circle(screen, ball_color, ball_position, ball_radius)

                        # draw the unused balls
                        for i in range(balls):
                            pygame.draw.circle(screen, ball_color,
                                 (int(round(30 + i * ball_radius * 2.4)), 30),
                                 ball_radius)

                        # update the display
                        pygame.display.flip()

                        # update the ball
                        for i in range(2):
                            ball_position[i] = ball_position[i] + ball_mvect[i]

                            # bounce on top and left
                            if ball_position[i] < ball_radius:
                                ball_position[i] = ball_radius
                                ball_mvect[i] = -1 * ball_mvect[i]
                            # bounce on bottom
                            elif i == 1 \
                                and ball_position[i] >= ball_limit[i] - ball_radius:
                                ball_position[i] = ball_limit[i] - ball_radius - 1
                                ball_mvect[i] = -1 * ball_mvect[i]
                            elif i == 0 \
                                and ball_position[i] >= ball_limit[i] - ball_radius - paddle_width \
                                and ball_position[1] > paddle_location - paddle_radius \
                                and ball_position[1] < paddle_location + paddle_radius:
                                ball_position[i] = ball_limit[i] - ball_radius - paddle_width - 1
                                ball_mvect[i] = (-1) * ball_mvect[i]
