#!/usr/bin/python
"""
This file is part of the 'Elements' Project
Elements is a 2D Physics API for Python (supporting Box2D2)

Copyright (C) 2008, The Elements Team, <elements@linuxuser.at>

Home:  http://elements.linuxuser.at
IRC:   #elements on irc.freenode.org

Code:  http://www.assembla.com/wiki/show/elements
       svn co http://svn2.assembla.com/svn/elements                     

License:  GPLv3 | See LICENSE for the full text
This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.              
"""
__version__=  '0.1'
__contact__ = '<elements@linuxuser.at>'

# Load Box2D
import box2d

# Standard Imports
from random import shuffle

# Load Elements Definitions
from locals import *

# Load Elements Modules
import tools
import drawing
import add_objects
import callbacks
import camera

# Main Class
class Elements:
    """The class which handles all interaction with the box2d engine
    """
    # Settings
    run_physics = True       # Can pause the simulation
    element_count = 0        # Element Count 
    renderer = None          # Drawing class (from drawing.py)
    input = INPUT_PIXELS     # Default Input in Pixels! (can change to INPUT_METERS)
    line_width = 0           # Line Width in Pixels (0 for fill)
    klistener = None
    
    screen_offset = (0, 0)   # Offset screen from world coordinate system (x, y) [meter5]
    screen_offset_pixel = (0, 0)   # Offset screen from world coordinate system (x, y) [pixel]
    
    # The internal coordination system is y+=up, x+=right
    # But it's possible to change the input coords to something else,
    # they will then be translated on input
    inputAxis_x_left = False    # positive to the right by default
    inputAxis_y_down = True     # positive to up by default

    mouseJoint = None

    def __init__(self, screen_size, gravity=(0.0,-9.0), ppm=100.0, renderer='pygame'):
        """ Init the world with boundaries and gravity, and init colors.
        
            Parameters:
              screen_size .. (w, h) -- screen size in pixels [int]
              gravity ...... (x, y) in m/s^2  [float] default: (0.0, -9.0)
              ppm .......... pixels per meter [float] default: 100.0
              renderer ..... which drawing method to use (str) default: 'pygame'

            Return: class Elements()
        """
        self.set_screenSize(screen_size)
        self.set_drawingMethod(renderer)
        
        # Create Subclasses
        self.add = add_objects.Add(self)
        self.callbacks = callbacks.CallbackHandler(self)
        self.camera = camera.Camera(self)
        
        # Set Boundaries
        self.worldAABB=box2d.b2AABB()
        self.worldAABB.lowerBound.Set(-100.0, -100.0)
        self.worldAABB.upperBound.Set(100.0, 100.0)
        
        # Gravity + Bodies will sleep on outside
        gx, gy = gravity
        self.gravity = box2d.b2Vec2(gx, gy);
        self.doSleep = True
    
        # Create the World
        self.world = box2d.b2World(self.worldAABB, self.gravity, self.doSleep)

        # Init Colors        
        self.init_colors()
        
        # Set Pixels per Meter
        self.ppm = ppm

    def set_inputUnit(self, input):
        """ Change the input unit to either meter or pixels
        
            Parameters:
              input ... INPUT_METERS or INPUT_PIXELS
          
            Return: -
        """
        self.input = input
        
    def set_inputAxisOrigin(self, left=True, top=False):
        """ Change the origin of the input coordinate system axis
        
            Parameters:
              left ... True or False -- x = 0 is at the left?
              top .... True or False -- y = 0 is at the top?
          
            Return: -
        """          
        self.inputAxis_x_left = not left
        self.inputAxis_y_down = top

    def set_drawingMethod(self, m, *kw):
        """ Set a drawing method (from drawing.py)
        
            Parameters:
              m .... 'pygame' or 'cairo'
              *kw .. keywords to pass to the initializer of the drawing method

            Return: True if ok, False if no method identifier m found
        """
        try:
            self.renderer = getattr(drawing, "draw_%s" % m) (*kw)
            return True
        except AttributeError:
            return False
            
    def set_screenSize(self, size):
        """ Set the current screen size
        
            Parameters: 
              size ... (int(width), int(height)) in pixels
              
            Return: -
        """
        self.display_width, self.display_height = size

    def init_colors(self):
        """ Init self.colors with a fix set of hex colors
        
            Return: -        
        """
        self.fixed_color = None
        self.cur_color = 0
        self.colors = [
          "#737934", "#729a55", "#040404", "#1d4e29", "#ae5004", "#615c57",
          "#6795ce", "#203d61", "#8f932b"
        ]
        shuffle(self.colors)

    def set_color(self, clr):
        """ Set a fixed color for all future Elements (until reset_color() is called) 
        
            Parameters: 
              clr ... Hex '#123123' or RGB ((r), (g), (b))
              
            Return: -
        """
        self.fixed_color = clr
    
    def reset_color(self):
        """ All Elements from now on will be drawn in random colors
           
            Return: - 
        """
        self.fixed_color = None

    def get_color(self):
        """ Get a color - either the fixed one or the next from self.colors 
        
            Return: clr = ((R), (G), (B)) 
        """
        if self.fixed_color != None:
            return self.fixed_color
            
        if self.cur_color == len(self.colors): 
            self.cur_color = 0
            shuffle(self.colors)
    
        clr = self.colors[self.cur_color]
        if clr[0] == "#":
            clr = tools.hex2rgb(clr)
        
        self.cur_color += 1
        return clr
    
    def update(self, fps=50.0, iterations=10):
        """ Update the physics, if not paused (self.run_physics)
        
            Parameters:
              fps ......... fps with which the physics engine shall work
              iterations .. substeps per step for smoother simulation
            
            Return: -
        """
        if self.run_physics:
            self.world.Step(1.0 / fps, iterations);

    def translate_coord(self, point):
        """ Flips the coordinates in another coordinate system orientation, if necessary
            (screen <> world coordinate system) 
        """
        x, y = point

        if self.inputAxis_x_left:
            x = self.display_width - x

        if self.inputAxis_y_down:
            y = self.display_height - y
            
        return (x, y)
        
    def translate_coords(self, pointlist):
        """ Flips the coordinates in another coordinate system orientation, if necessary 
            (screen <> world coordinate system) 
        """    
        p_out = []        
        for p in pointlist:
            p_out.append(self.translate_coord(p))
        return p_out

    def to_world(self, pos):
        """ Transfers a coordinate from the screen to the world coordinate system (pixels)
            - Change to the right axis orientation
            - Include the offset: screen -- world coordinate system
        """
        dx, dy = self.screen_offset_pixel
        
        x = pos[0] / self.camera.scale_factor
        y = pos[1] / self.camera.scale_factor
        
        x, y = self.translate_coord((round(x), round(y)))
        return (x+dx, y+dy) 
        
    def to_screen(self, pos):
        """ Transfers a coordinate from the world to the screen coordinate system (pixels)
            and by the screen offset
        """
        dx, dy = self.screen_offset_pixel
        x = pos[0] - dx
        y = pos[1] - dy
        
        sx, sy = self.translate_coord((x, y))
        return (sx * self.camera.scale_factor, sy * self.camera.scale_factor)
                         
    def meter_to_screen(self, i):
        return i * self.ppm * self.camera.scale_factor
        
    def get_bodies_at_pos(self, search_point, include_static=False, area=0.01):
        """ Check if given point (screen coordinates) is inside any body.
            If yes, return all found bodies, if not found return False
        """
        sx, sy = self.to_world(search_point)
        sx /= self.ppm # le sigh, screen2world returns pixels, so convert them to meters here.
        sy /= self.ppm

        f = area/self.camera.scale_factor

        AABB=box2d.b2AABB()
        AABB.lowerBound.Set(sx-f, sy-f);
        AABB.upperBound.Set(sx+f, sy+f);

        amount, shapes = self.world.Query(AABB, 2)

        if amount == 0:
            return False
        else:
            bodylist = []
            for s in shapes:
                body = s.GetBody()
                if not include_static:
                    if body.IsStatic() or body.GetMass() == 0.0:
                        continue
                        
                if s.TestPoint(body.GetXForm(), box2d.b2Vec2(sx, sy)):
                    bodylist.append(body)

            return bodylist
    
    def draw(self):
        """ If a drawing method is specified, this function passes the objects
            to the module in pixels.
            
            Return: True if the objects were successfully drawn
              False if the renderer was not set or another error occurred
        """
        self.callbacks.start(CALLBACK_DRAWING_START)
        
        # No need to run through the loop if there's no way to draw        
        if not self.renderer: 
            return False

        if self.camera.track_body:
            # Get Body Center
            p1 = self.camera.track_body.GetWorldCenter()   
            
            # Center the Camera There, False = Don't stop the tracking
            self.camera.center(self.to_screen((p1.x*self.ppm, p1.y*self.ppm)), stopTrack=False) 
            
        # Walk through all known elements
        body = self.world.GetBodyList()
        self.renderer.start_drawing()
        
        while body:            
            xform = body.GetXForm()
            shape = body.GetShapeList()
            angle = body.GetAngle()
            
            if shape:
                userdata = body.GetUserData()
                clr = userdata['color']
                                                
            while shape:                
                type = shape.GetType()
                                
                if type == box2d.e_circleShape:
                    circle = shape.asCircle()
                    position = box2d.b2Mul(xform, circle.GetLocalPosition())
                    
                    pos = self.to_screen((position.x*self.ppm, position.y*self.ppm))                    
                    self.renderer.draw_circle(clr, pos, self.meter_to_screen(circle.GetRadius()), angle)

                elif type == box2d.e_polygonShape:
                    poly = shape.asPolygon()
                    points = []
                    for i in xrange(poly.GetVertexCount()):
                        pt = box2d.b2Mul(xform, poly.getVertex(i))
                        x, y = self.to_screen((pt.x*self.ppm, pt.y*self.ppm))
                        points.append([x, y])

                    self.renderer.draw_polygon(clr, points)
                   
                else:
                    print "  unknown shape type:%d" % shape.GetType()
    
                shape = shape.GetNext()  
            body = body.GetNext()

        joint = self.world.GetJointList()
        while joint:
            p2 = joint.GetAnchor1()
            p2 = self.to_screen((p2.x*self.ppm, p2.y*self.ppm))
            
            p1 = joint.GetAnchor2()
            p1 = self.to_screen((p1.x*self.ppm, p1.y*self.ppm))
            
            if p1 == p2: # Fixation
                self.renderer.draw_circle((255,0,0), p1, 4, 0)
            else: # Object to object joint
                self.renderer.draw_lines((0,0,0), False, [p1, p2], 3)
            joint = joint.GetNext()

        self.callbacks.start(CALLBACK_DRAWING_END)
        self.renderer.after_drawing()
        
        return True


    def mouse_move(self, pos):
        pos = self.to_world(pos)
        x, y = pos
        x /= self.ppm
        y /= self.ppm
                        
        if self.mouseJoint:
            self.mouseJoint.SetTarget(box2d.b2Vec2(x,y))
