#!/usr/bin/python
"""
This file is part of the 'Elements' Project
Elements is a 2D Physics API for Python (supporting pybox2d)

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
__version__ = '0.11'
__contact__ = '<elements@linuxuser.at>'

# Load Box2D
try:
    import Box2D as box2d
except:
    print 'Could not load the pybox2d library (Box2D).'
    print 'Please run "setup.py install" to install the dependencies.'
    print
    print 'Or recompile pybox2d for your system and python version.'
    print "See http://code.google.com/p/pybox2d"
    exit()

# Standard Imports
from random import shuffle

# Load Elements Definitions
from .locals import *

# Load Elements Modules
from . import tools
from . import drawing
from . import add_objects
from . import callbacks
from . import camera

# Main Class


class Elements:

    """The class which handles all interaction with the box2d engine
    """
    # Settings
    run_physics = True  # Can pause the simulation
    element_count = 0  # Element Count
    renderer = None  # Drawing class (from drawing.py)
    # Default Input in Pixels! (can change to INPUT_METERS)
    input_unit = INPUT_PIXELS
    line_width = 0  # Line Width in Pixels (0 for fill)
    listener = None

    # Offset screen from world coordinate system (x, y) [meter5]
    screen_offset = (0, 0)
    # Offset screen from world coordinate system (x, y) [pixel]
    screen_offset_pixel = (0, 0)

    # The internal coordination system is y+=up, x+=right
    # But it's possible to change the input coords to something else,
    # they will then be translated on input
    inputAxis_x_left = False  # positive to the right by default
    inputAxis_y_down = True  # positive to up by default

    mouseJoint = None

    def __init__(self, screen_size, gravity=(0.0, -9.0), ppm=100.0,
                 renderer='pygame'):
        """ Init the world with boundaries and gravity, and init colors.

            Parameters:
              screen_size .. (w, h) -- screen size in pixels [int]
              gravity ...... (x, y) in m/s^2  [float] default: (0.0, -9.0)
              ppm .......... pixels per meter [float] default: 100.0
              renderer ..... which drawing method to use (str) default:
                             'pygame'

            Return: class Elements()
        """
        self.set_screenSize(screen_size)
        self.set_drawingMethod(renderer)

        # Create Subclasses
        self.add = add_objects.Add(self)
        self.callbacks = callbacks.CallbackHandler(self)
        self.camera = camera.Camera(self)

        # Gravity + Bodies will sleep on outside
        self.gravity = gravity
        self.doSleep = True
        self.PIN_MOTOR_RADIUS = 2

        # Create the World
        self.world = box2d.b2World(self.gravity, self.doSleep)
        bodyDef = box2d.b2BodyDef()
        self.world.groundBody = self.world.CreateBody(bodyDef)

        # Init Colors
        self.init_colors()

        # Set Pixels per Meter
        self.ppm = ppm

    def set_inputUnit(self, input_unit):
        """ Change the input unit to either meter or pixels

            Parameters:
              input ... INPUT_METERS or INPUT_PIXELS

            Return: -
        """
        self.input_unit = input_unit

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
            self.renderer = getattr(drawing, "draw_%s" % m)(*kw)
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
        """ Set a fixed color for all future Elements (until reset_color()
            is called)

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
        if self.fixed_color is not None:
            return self.fixed_color

        if self.cur_color == len(self.colors):
            self.cur_color = 0
            shuffle(self.colors)

        clr = self.colors[self.cur_color]
        if clr[0] == "#":
            clr = tools.hex2rgb(clr)

        self.cur_color += 1
        return clr

    def update(self, fps=50.0, vel_iterations=10, pos_iterations=8):
        """ Update the physics, if not paused (self.run_physics)

            Parameters:
              fps ............. fps with which the physics engine shall work
              vel_iterations .. velocity substeps per step for smoother
                                simulation
              pos_iterations .. position substeps per step for smoother
                                simulation

            Return: -
        """
        if self.run_physics:
            self.world.Step(1.0 / fps, vel_iterations, pos_iterations)

    def translate_coord(self, point):
        """ Flips the coordinates in another coordinate system orientation,
            if necessary (screen <> world coordinate system)
        """
        x, y = point

        if self.inputAxis_x_left:
            x = self.display_width - x

        if self.inputAxis_y_down:
            y = self.display_height - y

        return (x, y)

    def translate_coords(self, pointlist):
        """Flips the coordinates in another coordinate system orientation, if
            necessary (screen <> world coordinate system)
        """
        p_out = []
        for p in pointlist:
            p_out.append(self.translate_coord(p))
        return p_out

    def to_world(self, pos):
        """ Transfers a coordinate from the screen to the world
        coordinate system (pixels)

            - Change to the right axis orientation
            - Include the offset: screen -- world coordinate system
            - Include the scale factor (Screen coordinate system might have
              a scale factor)
        """
        dx, dy = self.screen_offset_pixel

        x = pos[0] / self.camera.scale_factor
        y = pos[1] / self.camera.scale_factor

        x, y = self.translate_coord((round(x), round(y)))
        return(x + dx, y + dy)

    def to_screen(self, pos):
        """Transfers a coordinate from the world to the screen coordinate
            system (pixels) and by the screen offset
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
        sx /= self.ppm
        sy /= self.ppm

        f = area / self.camera.scale_factor

        AABB = box2d.b2AABB()
        AABB.lowerBound = (sx - f, sy - f)
        AABB.upperBound = (sx + f, sy + f)

        query_cb = Query_CB()

        self.world.QueryAABB(query_cb, AABB)

        bodylist = []
        for s in query_cb.fixtures:
            body = s.body
            if body is None:
                continue
            if not include_static:
                if body.type == box2d.b2_staticBody or body.mass == 0.0:
                    continue

            if s.TestPoint((sx, sy)):
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
            self.camera.center(self.to_screen((p1.x * self.ppm,
                                               p1.y * self.ppm)),
                               stopTrack=False)

        # Walk through all known elements
        self.renderer.start_drawing()

        for body in self.world.bodies:
            xform = body.transform
            shape = body.fixtures
            angle = body.angle

            if shape:
                userdata = body.userData
                if 'color' in userdata:
                    clr = userdata['color']
                else:
                    clr = self.colors[0]

            for shape in body.fixtures:
                type_ = shape.type

                if type_ == box2d.b2Shape.e_circle:
                    position = box2d.b2Mul(xform, shape.shape.pos)

                    pos = self.to_screen((position.x * self.ppm,
                                          position.y * self.ppm))

                    self.renderer.draw_circle(
                        clr, pos, self.meter_to_screen(shape.shape.radius),
                        angle)

                elif type_ == box2d.b2Shape.e_polygon:
                    points = []
                    for v in shape.shape.vertices:
                        pt = box2d.b2Mul(xform, v)
                        x, y = self.to_screen((pt.x * self.ppm,
                                               pt.y * self.ppm))
                        points.append([x, y])

                    self.renderer.draw_polygon(clr, points)

                else:
                    print "unknown shape type:%d" % shape.type

        for joint in self.world.joints:
            p2 = joint.anchorA
            p2 = self.to_screen((p2.x * self.ppm, p2.y * self.ppm))

            p1 = joint.anchorB
            p1 = self.to_screen((p1.x * self.ppm, p1.y * self.ppm))

            if isinstance(joint, box2d.b2RevoluteJoint):
                self.renderer.draw_circle((255, 255, 255), p1,
                                          self.PIN_MOTOR_RADIUS, 0)
            else:
                self.renderer.draw_lines((0, 0, 0), False, [p1, p2], 3)

        self.callbacks.start(CALLBACK_DRAWING_END)
        self.renderer.after_drawing()

        return True

    def set_pin_motor_radius(self, radius):
        self.PIN_MOTOR_RADIUS = radius

    def mouse_move(self, pos):
        pos = self.to_world(pos)
        x, y = pos
        x /= self.ppm
        y /= self.ppm

        if self.mouseJoint:
            self.mouseJoint.target = (x, y)

    def pickle_save(self, fn, additional_vars={}):
        import cPickle as pickle
        self.add.remove_mouseJoint()

        if not additional_vars and hasattr(self, '_pickle_vars'):
            additional_vars = dict((var, getattr(self, var))
                                   for var in self._pickle_vars)

        save_values = [self.world, box2d.pickle_fix(self.world,
                                                    additional_vars, 'save')]

        try:
            pickle.dump(save_values, open(fn, 'wb'))
        except Exception as s:
            print 'Pickling failed: ', s
            return

        print 'Saved to %s' % fn

    def pickle_load(self, fn, set_vars=True, additional_vars=[]):
        """
        Load the pickled world in file fn.
        additional_vars is a dictionary to be populated with the
        loaded variables.
        """
        import cPickle as pickle
        try:
            world, variables = pickle.load(open(fn, 'rb'))
            world = world._pickle_finalize()
            variables = box2d.pickle_fix(world, variables, 'load')
        except Exception as s:
            print 'Error while loading world: ', s
            return

        self.world = world

        if set_vars:
            # reset the additional saved variables:
            for var, value in variables.items():
                if hasattr(self, var):
                    setattr(self, var, value)
                else:
                    print 'Unknown property %s=%s' % (var, value)

        print 'Loaded from %s' % fn

        return variables

    def json_save(self, path, additional_vars={}, serialize=False):
        import json
        worldmodel = {}

        save_id_index = 1
        self.world.groundBody.userData = {"saveid": 0}

        bodylist = []
        for body in self.world.bodies:
            if not body == self.world.groundBody:
                body.userData["saveid"] = save_id_index  # set temporary data
                save_id_index += 1
                shapelist = body.fixtures
                modelbody = {}
                modelbody['position'] = body.position.tuple
                modelbody['dynamic'] = body.type == box2d.b2_dynamicBody
                modelbody['userData'] = body.userData
                modelbody['angle'] = body.angle
                modelbody['angularVelocity'] = body.angularVelocity
                modelbody['linearVelocity'] = body.linearVelocity.tuple
                if shapelist and len(shapelist) > 0:
                    shapes = []
                    for shape in shapelist:
                        modelshape = {}
                        modelshape['density'] = shape.density
                        modelshape['restitution'] = shape.restitution
                        modelshape['friction'] = shape.friction
                        shapename = shape.shape.__class__.__name__
                        if shapename == "b2CircleShape":
                            modelshape['type'] = 'circle'
                            modelshape['radius'] = shape.shape.radius
                            modelshape['localPosition'] = shape.shape.pos.tuple
                        if shapename == "b2PolygonShape":
                            modelshape['type'] = 'polygon'
                            modelshape['vertices'] = shape.shape.vertices
                        shapes.append(modelshape)
                    modelbody['shapes'] = shapes

                bodylist.append(modelbody)

        worldmodel['bodylist'] = bodylist

        jointlist = []

        for joint in self.world.joints:
            modeljoint = {}

            if joint.__class__.__name__ == "b2RevoluteJoint":
                modeljoint['type'] = 'revolute'
                modeljoint['anchor'] = joint.anchorA.tuple
                modeljoint['enableMotor'] = joint.motorEnabled
                modeljoint['motorSpeed'] = joint.motorSpeed
                modeljoint['maxMotorTorque'] = joint.GetMaxMotorTorque()
            elif joint.__class__.__name__ == "b2DistanceJoint":
                modeljoint['type'] = 'distance'
                modeljoint['anchor1'] = joint.anchorA.tuple
                modeljoint['anchor2'] = joint.anchorB.tuple

            modeljoint['body1'] = joint.bodyA.userData['saveid']
            modeljoint['body2'] = joint.bodyB.userData['saveid']
            modeljoint['collideConnected'] = joint.collideConnected
            modeljoint['userData'] = joint.userData

            jointlist.append(modeljoint)

        worldmodel['jointlist'] = jointlist

        controllerlist = []
        worldmodel['controllerlist'] = controllerlist

        if serialize:
            addvars = additional_vars
            trackinfo = addvars['trackinfo']
            backup = trackinfo
            for key, info in backup.iteritems():
                if not info[3]:
                    try:
                        trackinfo[key][0] = info[0].userData['saveid']
                        trackinfo[key][1] = info[1].userData['saveid']
                    except AttributeError:
                        pass
                else:
                    addvars['trackinfo'][key][0] = None
                    addvars['trackinfo'][key][1] = None

            additional_vars['trackinfo'] = trackinfo

        worldmodel['additional_vars'] = additional_vars
        f = open(path, 'w')
        f.write(json.dumps(worldmodel))
        f.close()

        for body in self.world.bodies:
            del body.userData['saveid']  # remove temporary data

    def json_load(self, path, serialized=False):
        import json

        self.world.groundBody.userData = {"saveid": 0}

        f = open(path, 'r')
        worldmodel = json.loads(f.read())
        f.close()
        # clean world
        for joint in self.world.joints:
            self.world.DestroyJoint(joint)
        for body in self.world.bodies:
            if body != self.world.groundBody:
                self.world.DestroyBody(body)

        # load bodies
        for body in worldmodel['bodylist']:
            bodyDef = box2d.b2BodyDef()
            if body['dynamic']:
                bodyDef.type = box2d.b2_dynamicBody
            bodyDef.position = body['position']
            bodyDef.userData = body['userData']
            bodyDef.angle = body['angle']
            newBody = self.world.CreateBody(bodyDef)
            # _logger.debug(newBody)
            newBody.angularVelocity = body['angularVelocity']
            newBody.linearVelocity = body['linearVelocity']
            if 'shapes' in body:
                for shape in body['shapes']:
                    if shape['type'] == 'polygon':
                        polyDef = box2d.b2FixtureDef()
                        polyShape = box2d.b2PolygonShape()
                        polyShape.vertices = shape['vertices']
                        polyDef.shape = polyShape
                        polyDef.density = shape['density']
                        polyDef.restitution = shape['restitution']
                        polyDef.friction = shape['friction']
                        newBody.CreateFixture(polyDef)
                    if shape['type'] == 'circle':
                        circleDef = box2d.b2FixtureDef()
                        circleShape = box2d.b2CircleShape()
                        circleShape.radius = shape['radius']
                        circleShape.pos = shape['localPosition']
                        circleDef.shape = circleShape
                        circleDef.density = shape['density']
                        circleDef.restitution = shape['restitution']
                        circleDef.friction = shape['friction']
                        newBody.CreateFixture(circleDef)

        for joint in worldmodel['jointlist']:
            if joint['type'] == 'distance':
                jointDef = box2d.b2DistanceJointDef()
                body1 = self.getBodyWithSaveId(joint['body1'])
                anch1 = joint['anchor1']
                body2 = self.getBodyWithSaveId(joint['body2'])
                anch2 = joint['anchor2']
                jointDef.collideConnected = joint['collideConnected']
                jointDef.Initialize(body1, body2, anch1, anch2)
                jointDef.userData = joint['userData']
                self.world.CreateJoint(jointDef)
            if joint['type'] == 'revolute':
                jointDef = box2d.b2RevoluteJointDef()
                body1 = self.getBodyWithSaveId(joint['body1'])
                body2 = self.getBodyWithSaveId(joint['body2'])
                anchor = joint['anchor']
                jointDef.Initialize(body1, body2, anchor)
                jointDef.userData = joint['userData']
                jointDef.motorEnabled = joint['enableMotor']
                jointDef.motorSpeed = joint['motorSpeed']
                jointDef.maxMotorTorque = joint['maxMotorTorque']
                self.world.CreateJoint(jointDef)

        self.additional_vars = {}
        addvars = {}
        for (k, v) in worldmodel['additional_vars'].items():
            addvars[k] = v

        if serialized and 'trackinfo' in addvars:
            trackinfo = addvars['trackinfo']
            for key, info in trackinfo.iteritems():
                if not info[3]:
                    addvars['trackinfo'][key][0] = \
                        self.getBodyWithSaveId(info[0])
                    addvars['trackinfo'][key][1] = \
                        self.getBodyWithSaveId(info[1])
                else:
                    addvars['trackinfo'][key][0] = None
                    addvars['trackinfo'][key][1] = None

        self.additional_vars = addvars

        for body in self.world.bodies:
            del body.userData['saveid']  # remove temporary data

    def getBodyWithSaveId(self, saveid):
        for body in self.world.bodies:
            if body.userData['saveid'] == saveid:
                return body


class Query_CB(box2d.b2QueryCallback):

    def __init__(self):
        box2d.b2QueryCallback.__init__(self)
        self.fixtures = []

    def ReportFixture(self, fixture):
        self.fixtures.append(fixture)
        return True
