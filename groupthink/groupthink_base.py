"""
Copyright 2008 Benjamin M. Schwartz

DOBject is LGPLv2+

DObject is free software: you can redistribute it and/or modify
it under the terms of the GNU Lesser General Public License as published by
the Free Software Foundation, either version 2 of the License, or
(at your option) any later version.

DObject is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU Lesser General Public License
along with DObject.  If not, see <http://www.gnu.org/licenses/>.
"""
import dbus
import dbus.service
import dbus.gobject_service
import time
import logging
import threading
import thread
import random
from listset import ListSet
import stringtree
import cPickle
import dbus_tools
"""
DObject is a library of components useful for constructing distributed
applications that need to maintain coherent state while communicating over
Telepathy.  The DObject tools are design to handle unexpected joins, leaves,
splits, and merges automatically, and always to leave each connected component
of users in a coherent state at quiescence.
"""

def PassFunction(*args,**kargs):
    logging.debug("args=%s, kargs=%s" % (str(args),str(kargs)))
    pass

def ReturnFunction(x):
    return x

class Group:
    """A Group is a simple tool for organizing DObjects.  Once it is set up
    with a tubebox, the user may simply add objects to it, e.g.
    
    self.group = Group(tb)
    ...
    self.group['mydict1'] = HighScore('No one', 0)
    
    and the group will take care of assigning a handler to the object with
    the specified name.
    For a Group g, g['a'] is equivalent in almost all ways to g.a, for
    programmer convenience.
    """
    
    tubebox = None
    _locked = False
    _d = None
    
    def __init__(self, tubebox):
        self._logger = logging.getLogger('groupthink.Group')
        self._logger.debug('new Group')
        self.tubebox = tubebox
        self._d = dict()
        self._history = dict()
        self._handlers = dict()
        self._locked = True
    
    def __setitem__(self, name, dobj):
        self._logger.debug("setitem(%s,%s)" % (name, str(dobj)))
        if name in self.__dict__ or name in self._d:
            raise #Cannot replace an existing attribute or object
        h = dobj.HANDLER_TYPE(name, self.tubebox)
        dobj.set_handler(h)
        self.add_handler(h, dobj)
    
    def add_handler(self, h, o=None):
        """This function is used to add a handler to the Group _after_ that
        handler has already been registered to completion with its object."""
        name = h.get_name()
        self._handlers[name] = h
        if name in self._history:
            h.object.add_history(self._history[name])
            del self._history[name]
        if o is not None:
            self._d[name] = o
        else:
            self._d[name] = h.object
        for hc in h.get_copies(): #Recurse through a potential tree of handlers
            self.add_handler(hc)
    
    def __setattr__(self, name, val):
        if self._locked:
            self.__setitem__(name, val)
        else:
            self.__dict__[name] = val
    
    def __getitem__(self, name):
        if name in self._d:
            return self._d[name]
        else:
            return self.__dict__[name]

    __getattr__ = __getitem__

    def __delattr__(self, name):
        raise #Deletion is not supported
    
    def dumps(self):
        d = {}
        for (name, handler) in self._handlers.iteritems():
            d[name] = dbus_tools.undbox(handler.object.get_history())
        d.update(self._history) #Include any "unclaimed history" thus far.
        return cPickle.dumps(d)
    
    def loads(self, s):
        if s:
            d = cPickle.loads(s)
            for (name,hist) in d.iteritems():
                if name in self._d:
                    handler = self._handlers[name]
                    handler.object.add_history(hist)
                else:
                    self._history[name] = hist

class TubeBox:
    """ A TubeBox is a box that either contains a Tube or does not.
    The purpose of a TubeBox is to solve this problem: Activities are not
    provided with the sharing Tube until they are shared, but DObjects should
    not have to care whether or not they have been shared.  That means that the
    DObject handler must know whether or not a Tube has been provided.  This
    could be implemented within the handlers, but then the Activity's sharing
    code would have to know a list of all DObject handlers.
    
    Instead, the sharing code just needs to create a TubeBox and pass it to the
    code that creates handlers.  Once the tube arrives, it can be added to the
    TubeBox with insert_tube.  The handlers will then be notified automatically.
    """
    def __init__(self):
        self.tube = None
        self.is_initiator = None
        self._logger = logging.getLogger()
        self._listeners = []
    
    def register_listener(self, L):
        """This method is used by the DObject handlers to add a callback
        function that will be called after insert_tube"""
        self._listeners.append(L)
        if self.tube is not None:
            L(self.tube, self.is_initiator)
    
    def insert_tube(self, tube, is_initiator=False):
        """This method is used by the sharing code to provide the tube, once it
        is ready, along with a boolean indicating whether or not this computer
        is the initiator (who may have special duties, as the first
        participant)."""
        self._logger.debug("insert_tube, notifying %s" % str(self._listeners))
        self.tube = tube
        self.is_initiator = is_initiator
        for L in self._listeners:
            L(tube, is_initiator)

class TimeHandler(dbus.gobject_service.ExportedGObject):
    """A TimeHandler provides a universal clock for a sharing instance.  It is a
    sort of cheap, decentralized synchronization system.  The TimeHandler 
    determines the offset between local time and group time by sending a
    broadcast and accepting the first response, and assuming that both transfer
    displays were equal.  The initiator's offset is 0.0, but once another group
    member has synchronized, the initiator can leave and new members will still
    be synchronized correctly.  Errors at each synchronization are typically
    between 0.1s and 2s.
    
    TimeHandler is not perfectly resilient to disappearances.  If the group
    splits, and one of the daughter groups does not contain any members that
    have had a chance to synchronize, then they will not sync to each other.  I
    am not yet aware of any sensible synchronization system that avoids this 
    problem.
    """
    IFACE = "org.dobject.TimeHandler"
    BASEPATH = "/org/dobject/TimeHandler/"

    def __init__(self, name, tube_box, offset=0.0):
        self.PATH = TimeHandler.BASEPATH + name
        dbus.gobject_service.ExportedGObject.__init__(self)
        self._logger = logging.getLogger(self.PATH)
        self._tube_box = tube_box
        self.tube = None
        self.is_initiator = None
        
        self.offset = offset
        self._know_offset = False
        self._offset_lock = threading.Lock()
        
        self._tube_box.register_listener(self.get_tube)
                
    def get_tube(self, tube, is_initiator):
        """Callback for the TubeBox"""
        self._logger.debug("get_tube")
        self._logger.debug(str(is_initiator))
        self.tube = tube
        self.add_to_connection(self.tube, self.PATH)
        self.is_initiator = is_initiator
        self._know_offset = is_initiator
        self.tube.add_signal_receiver(self.tell_time, signal_name='What_time_is_it', dbus_interface=TimeHandler.IFACE, sender_keyword='sender', path=self.PATH)

        if not self._know_offset:
            self.ask_time()

    def time(self):
        """Get the group time"""
        return time.time() + self.offset
        
    def get_offset(self):
        """Get the difference between local time and group time"""
        self._logger.debug("get_offset " + str(self.offset))
        return self.offset
    
    def set_offset(self, offset):
        """Set the difference between local time and group time, and assert that
        this is correct"""
        self._logger.debug("set_offset " + str(offset))
        self._offset_lock.acquire()
        self.offset = offset
        self._know_offset = True
        self._offset_lock.release()

    @dbus.service.signal(dbus_interface=IFACE, signature='d')
    def What_time_is_it(self, asktime):
        return
        
    def ask_time(self):
        self._logger.debug("ask_time")
        self.What_time_is_it(time.time())
    
    def tell_time(self, asktime, sender=None):
        self._logger.debug("tell_time")
        start_time = time.time()
        try:
            my_name = self.tube.get_unique_name()
            if sender == my_name:
                return
            if self._know_offset:
                self._logger.debug("telling offset")
                remote = self.tube.get_object(sender, self.PATH)
                start_time += self.offset
                remote.receive_time(asktime, start_time, time.time() + self.offset, reply_handler=PassFunction, error_handler=PassFunction)
        finally:
            return
    
    @dbus.service.method(dbus_interface=IFACE, in_signature='ddd', out_signature='')
    def receive_time(self, asktime, start_time, finish_time):
        self._logger.debug("receive_time")
        rtime = time.time()
        thread.start_new_thread(self._handle_incoming_time, (asktime, start_time, finish_time, rtime))
    
    def _handle_incoming_time(self, ask, start, finish, receive):
        self._offset_lock.acquire()
        if not self._know_offset:
            self.offset = ((start + finish)/2) - ((ask + receive)/2)
            self._know_offset = True
        self._offset_lock.release()

class UnorderedHandler(dbus.gobject_service.ExportedGObject):
    """The UnorderedHandler serves as the interface between a local UnorderedObject
    (a pure python entity) and the d-bus/network system.  Each UnorderedObject
    is associated with a single Handler, and vice-versa.  It is the Handler that
    is actually exposed over D-Bus.  The purpose of this system is to minimize
    the amount of networking code required for each additional UnorderedObject.
    """
    IFACE = "org.dobject.Unordered"
    BASEPATH = "/org/dobject/Unordered/"

    def __init__(self, name, tube_box):
        """To construct a UO, the program must provide a name and a TubeBox.
        The name is used to identify the UO; all UO with the same name on the
        same Tube should be considered views into the same abstract distributed
        object."""
        self._myname = name
        self.PATH = UnorderedHandler.BASEPATH + name
        dbus.gobject_service.ExportedGObject.__init__(self)
        self._logger = logging.getLogger(self.PATH)
        self._tube_box = tube_box
        self.tube = None
        self._copies = []
        
        self.object = None
        self._tube_box.register_listener(self.set_tube)
        
    def set_tube(self, tube, is_initiator):
        self._logger.debug("set_tube(), is_initiator=%s" % str(is_initiator))
        """Callback for the TubeBox"""
        self.tube = tube
        self.add_to_connection(self.tube, self.PATH)
                        
        self.tube.add_signal_receiver(self.receive_message, signal_name='send', dbus_interface=UnorderedHandler.IFACE, sender_keyword='sender', path=self.PATH)
        self.tube.add_signal_receiver(self.tell_history, signal_name='ask_history', dbus_interface=UnorderedHandler.IFACE, sender_keyword='sender', path=self.PATH)
        
        # We need watch_participants because of the case in which several groups
        # all having made changes, come together and need to update each other.
        # There is no easy way to make this process more efficient without
        # changing the Unordered interface dramatically to include per-message
        # labels of some kind.
        self.tube.watch_participants(self.members_changed)

        #Alternative implementation of members_changed (not yet working)
        #self.tube.add_signal_receiver(self.members_changed, signal_name="MembersChanged", dbus_interface="org.freedesktop.Telepathy.Channel.Interface.Group")
        
        if self.object is not None:
            self.ask_history()

    def register(self, obj):
        self._logger.debug("register(%s)" % str(obj))
        """This method registers obj as the UnorderedObject being managed by
        this Handler.  It is called by obj after obj has initialized itself."""
        self.object = obj
        if self.tube is not None:
            self.ask_history()
            
    def get_path(self):
        """Returns the DBus path of this handler.  The path is the closest thing
        to a unique identifier for each abstract DObject."""
        return self.PATH
    
    def get_tube(self):
        """Returns the TubeBox used to create this handler.  This method is
        necessary if one DObject wishes to create another."""
        return self._tube_box
    
    @dbus.service.signal(dbus_interface=IFACE, signature='v')
    def send(self, message):
        self._logger.debug("send(%s)" % str(message))
        """This method broadcasts message to all other handlers for this UO"""
        return
        
    def receive_message(self, message, sender=None):
        self._logger.debug("receive_message(%s)" % str(message))
        if self.object is None:
            self._logger.error("got message before registration")
        elif sender == self.tube.get_unique_name():
            self._logger.debug("Ignoring message, because I am the sender.")
        else:
            self.object.receive_message(message)
    
    @dbus.service.signal(dbus_interface=IFACE, signature='')
    def ask_history(self):
        self._logger.debug("ask_history()")
        return
    
    def tell_history(self, sender=None):
        self._logger.debug("tell_history to " + str(sender))
        try:
            if sender == self.tube.get_unique_name():
                self._logger.debug("tell_history aborted because I am" + str(sender))
                return
            if self.object is None:
                self._logger.error("object not registered before tell_history")
                return
            self._logger.debug("getting proxy object")
            remote = self.tube.get_object(sender, self.PATH)
            self._logger.debug("got proxy object, getting history")
            h = self.object.get_history()
            self._logger.debug("got history, initiating transfer")
            remote.receive_history(h, reply_handler=PassFunction, error_handler=PassFunction)
            self._logger.debug("history transfer initiated")
        except Exception, E:
            self._logger.debug("tell_history failed: " % repr(E))
        finally:
            return
    
    @dbus.service.method(dbus_interface=IFACE, in_signature = 'v', out_signature='')
    def receive_history(self, hist):
        self._logger.debug("receive_history(%s)" % str(hist))
        if self.object is None:
            self._logger.error("object not registered before receive_history")
            return
        self.object.add_history(hist)

    #Alternative implementation of a members_changed (not yet working)
    """ 
    def members_changed(self, message, added, removed, local_pending, remote_pending, actor, reason):
        added_names = self.tube.InspectHandles(telepathy.CONNECTION_HANDLE_TYPE_LIST, added)
        for name in added_names:
            self.tell_history(name)
    """
    def members_changed(self, added, removed):
        self._logger.debug("members_changed")
        for (handle, name) in added:
            self.tell_history(sender=name)
    
    def __repr__(self):
        return 'UnorderedHandler(' + self._myname + ', ' + repr(self._tube_box) + ')'
    
    def copy(self, name):
        """A convenience function for returning a new UnorderedHandler derived
        from this one, with a new name.  This is safe as long as copy() is called
        with a different name every time."""
        h = UnorderedHandler(self._myname + "/" + name, self._tube_box)
        self._copies.append(h)
        return h
    
    def get_copies(self):
        return self._copies
    
    def get_name(self):
        return self._myname

class HandlerAcceptor:
    HANDLER_TYPE = NotImplementedError
    def set_handler(self, handler):
        raise NotImplementedError

class UnorderedHandlerAcceptor(HandlerAcceptor):
    HANDLER_TYPE = UnorderedHandler  

class UnorderedObject(UnorderedHandlerAcceptor):
    """ The most basic DObject is the Unordered Object (UO).  A UO has the
    property that any changes to its state can be encapsulated as messages, and
    these messages have no intrinsic ordering.  Different instances of the same
    UO, after receiving the same messages in different orders, should reach the
    same state.
    
    Any UO could be implemented as a set of all messages received so far, and
    coherency could be maintained by sending all messages ever transmitted to
    each new joining member.  However, many UOs will have the property that most
    messages are obsolete, and need not be transmitted. Therefore, as an
    optimization, UOs manage their own state structures for synchronizing state
    with joining/merging users.
    
    The following code is an abstract class for UnorderedObject, serving
    primarily as documentation for the concept.
    """

    handler = None

    def set_handler(self, handler):
        """Each UO must accept an UnorderedHandler via set_handler
        Whenever an action is taken on the local UO (e.g. a method call that changes
        the object's state), the UO must call handler.send() with an appropriately
        encoded message.
        
        Subclasses may override this method if they wish to perform more actions
        when a handler is set."""
        if self.handler:
            raise
        else:
            self.handler = handler
            self.handler.register(self)
            

    def receive_message(self,msg):
        """This method accepts and processes a message sent via handler.send().
        Because objects are sent over DBus, it is advisable to DBus-ify the message
        before calling send, and de-DBus-ify it inside receive_message."""
        raise NotImplementedError
    
    def get_history(self):
        """This method returns an encoded copy of all non-obsolete state, ready to be
        sent over DBus."""
        raise NotImplementedError
    
    def add_history(self, state):
        """This method accepts and processes the state object returned by get_history()"""
        raise NotImplementedError
        

def empty_translator(x, pack):
    return x

class HighScore(UnorderedObject):
    """ A HighScore is the simplest nontrivial DObject.  A HighScore's state consists
    of a value and a score.  The user may suggest a new value and score.  If the new
    score is higher than the current score, then the value and score are updated.
    Otherwise, they are not.
    
    The value can be any object, and the score can be any comparable object.
    
    To ensure that serialization works correctly, the user may specify a
    translator function that converts values or scores to and from a format that
    can be serialized reliably by dbus-python.
    
    In the event of a tie, coherence cannot be guaranteed.  If ties are likely
    with the score of choice, the user may set break_ties=True, which appends a
    random number to each message, and thereby reduces the probability of a tie
    by a factor of 2**52.
    """
    def __init__(self, initval, initscore, value_translator=empty_translator, score_translator=empty_translator, break_ties=False):
        self._logger = logging.getLogger('stopwatch.HighScore')
        self._lock = threading.Lock()
        self._value = initval
        self._score = initscore
        
        self._break_ties = break_ties
        if self._break_ties:
            self._tiebreaker = random.random()
        else:
            self._tiebreaker = None
        
        self._val_trans = value_translator
        self._score_trans = score_translator
        
        self._listeners = []

    
    def _set_value_from_net(self, val, score, tiebreaker):
        self._logger.debug("set_value_from_net " + str(val) + " " + str(score))
        if self._actually_set_value(val, score, tiebreaker):
            self._trigger()
    
    def receive_message(self, message):
        self._logger.debug("receive_message " + str(message))
        if len(message) == 2: #Remote has break_ties=False
            self._set_value_from_net(self._val_trans(message[0], False), self._score_trans(message[1], False), None)
        elif len(message) == 3:
            self._set_value_from_net(self._val_trans(message[0], False), self._score_trans(message[1], False), float_translator(message[2], False))
            
    
    add_history = receive_message
    
    def set_value(self, val, score):
        """This method suggests a value and score for this HighScore.  If the
        suggested score is higher than the current score, then both value and
        score will be broadcast to all other participants.
        """
        self._logger.debug("set_value " + str(val) + " " + str(score))
        if self._actually_set_value(val, score, None) and self.handler:
            self.handler.send(self.get_history())
            
    def _actually_set_value(self, value, score, tiebreaker):
        self._logger.debug("_actually_set_value " + str(value)+ " " + str(score))
        if self._break_ties and (tiebreaker is None):
            tiebreaker = random.random()
        self._lock.acquire()
        if self._break_ties: 
            if (self._score < score) or ((self._score == score) and (self._tiebreaker < tiebreaker)):
                self._value = value
                self._score = score
                self._tiebreaker = tiebreaker
                self._lock.release()
                return True
            else:
                self._lock.release()
                return False
        elif self._score < score:
            self._value = value
            self._score = score
            self._lock.release()
            return True
        else:
            self._logger.debug("not changing value")
            self._lock.release()
            return False
    
    def get_value(self):
        """ Get the current winning value."""
        return self._value
    
    def get_score(self):
        """ Get the current winning score."""
        return self._score
    
    def get_pair(self):
        """ Get the current value and score, returned as a tuple (value, score)"""
        self._lock.acquire()
        pair = (self._value, self._score)
        self._lock.release()
        return pair
    
    def _get_all(self):
        if self._break_ties:
            self._lock.acquire()
            q = (self._value, self._score, self._tiebreaker)
            self._lock.release()
            return q
        else:
            return self.get_pair()
    
    def get_history(self):
        p = self._get_all()
        if self._break_ties:
            return (self._val_trans(p[0], True), self._score_trans(p[1], True), float_translator(p[2], True))
        else:
            return (self._val_trans(p[0], True), self._score_trans(p[1], True))
    
    def register_listener(self, L):
        """Register a function L that will be called whenever another user sets
        a new record.  L must have the form L(value, score)."""
        self._lock.acquire()
        self._listeners.append(L)
        self._lock.release()
        (v,s) = self.get_pair()
        L(v,s)
    
    def _trigger(self):
        (v,s) = self.get_pair()
        for L in self._listeners:
            L(v,s)

def float_translator(f, pack):
    """This translator packs and unpacks floats for dbus serialization"""
    if pack:
        return dbus.Double(f)
    else:
        return float(f)

def uint_translator(f, pack):
    """This translator packs and unpacks 64-bit uints for dbus serialization"""
    if pack:
        return dbus.UInt64(f)
    else:
        return int(f)

def int_translator(f, pack):
    """This translator packs and unpacks 32-bit ints for dbus serialization"""
    if pack:
        return dbus.Int32(f)
    else:
        return int(f)

def string_translator(s, pack):
    """This translator packs and unpacks unicode strings for dbus serialization"""
    if pack:
        return dbus.String(s)
    else:
        return str(s)

class Latest(HandlerAcceptor):
    """ Latest is a variation on HighScore, in which the score is the current
    timestamp.  Latest uses TimeHandler to provide a groupwide coherent clock.
    Because TimeHandler's guarantees about synchronization and resilience are
    weak, Latest is not as resilient to failures as a true DObject.
    
    The creator must provide  the initial value.  One may
    optionally indicate the initial time (as a float in epoch-time), a
    TimeHandler (otherwise a new one will be created), and a translator for
    serialization of the values.
    
    Note that if time_handler is not provided, the object will not be functional
    until set_handler is called.
    """
    def __init__(self, initval, inittime=float('-inf'), time_handler=None, translator=empty_translator):
        self._time_handler = time_handler
        
        self._listeners = []
        self._lock = threading.Lock()
        
        self._highscore = HighScore(initval, inittime, translator, float_translator)
        self._highscore.register_listener(self._highscore_cb)
    
    def set_handler(self, handler):
        if self.handler:
            raise
        else:
            if self._time_handler is None:
                self._time_handler = TimeHandler(handler.get_path(), handler.get_tube())
            self._highscore.set_handler(handler)
    
    def get_value(self):
        """ Returns the latest value """
        return self._highscore.get_value()
    
    def set_value(self, val):
        """ Suggest a new value """
        if self._time_handler:
            self._highscore.set_value(val, self._time_handler.time())
        else:
            raise #missing _time_handler
    
    def register_listener(self, L):
        """ Register a listener L(value), to be called whenever another user
        adds a new latest value."""
        self._lock.acquire()
        self._listeners.append(L)
        self._lock.release()
        L(self.get_value())
    
    def _highscore_cb(self, val, score):
        for L in self._listeners:
            L(val)

class Recentest(HandlerAcceptor):
    """ Recentest is like Latest, but without using a clock or TimeHandler.
    As a result, it can only guarantee causality, not synchrony.
    """
    def __init__(self, initval, translator=empty_translator):
        self._listeners = []
        self._lock = threading.Lock()
        
        self._highscore = HighScore(initval, 0, translator, uint_translator, break_ties=True)
        self._highscore.register_listener(self._highscore_cb)
    
    def set_handler(self, handler):
        self._highscore.set_handler(handler)
    
    def get_value(self):
        """ Returns the current value """
        return self._highscore.get_value()
    
    def set_value(self, val):
        """ Set a new value """
        self._highscore.set_value(val, self._highscore.get_score() + 1)
    
    def register_listener(self, L):
        """ Register a listener L(value), to be called whenever another user
        adds a new latest value."""
        self._lock.acquire()
        self._listeners.append(L)
        self._lock.release()
        L(self.get_value())
    
    def _highscore_cb(self, val, score):
        for L in self._listeners:
            L(val)

class AddOnlySet(UnorderedObject):
    """The AddOnlySet is the archetypal UnorderedObject.  It consists of a set,
    supporting all the normal Python set operations except those that cause an
    item to be removed from the set.  Thanks to this restriction, a AddOnlySet
    is perfectly coherent, since the order in which elements are added is not
    important.
    """
    def __init__(self, initset = (), translator=empty_translator):
        self._logger = logging.getLogger('dobject.AddOnlySet')
        self._set = set(initset)
        
        self._lock = threading.Lock()

        self._trans = translator
        self._listeners = [] 

        self.__and__ = self._set.__and__
        self.__cmp__ = self._set.__cmp__
        self.__contains__ = self._set.__contains__
        self.__eq__ = self._set.__eq__
        self.__ge__ = self._set.__ge__
        # Not implementing getattribute
        self.__gt__ = self._set.__gt__
        self.__hash__ = self._set.__hash__
        # Not implementing iand (it can remove items)
        # Special wrapper for ior to trigger events
        # Not implementing isub (it can remove items)
        self.__iter__ = self._set.__iter__
        # Not implementing ixor (it can remove items)
        self.__le__ = self._set.__le__
        self.__len__ = self._set.__len__
        self.__lt__ = self._set.__lt__
        self.__ne__ = self._set.__ne__
        self.__or__ = self._set.__or__
        self.__rand__ = self._set.__rand__
        # Special implementation of repr
        self.__ror__ = self._set.__ror__
        self.__rsub__ = self._set.__rsub__
        self.__rxor__ = self._set.__rxor__
        self.__sub__ = self._set.__sub__
        self.__xor__ = self._set.__xor__
        
        # Special implementation of add to trigger events
        # Not implementing clear
        self.copy = self._set.copy
        self.difference = self._set.difference
        # Not implementing difference_update (it removes items)
        # Not implementing discard (it removes items)
        self.intersection = self._set.intersection
        # Not implementing intersection_update (it removes items)
        self.issubset = self._set.issubset
        self.issuperset = self._set.issuperset
        # Not implementing pop
        # Not implementing remove
        self.symmetric_difference = self._set.symmetric_difference
        # Not implementing symmetric_difference_update
        self.union = self._set.union
        # Special implementation of update to trigger events
        
    def update(self, y):
        """Add all the elements of an iterable y to the current set.  If any of
        these elements were not already present, they will be broadcast to all
        other users."""
        s = set(y)
        d = s - self._set
        if len(d) > 0:
            self._set.update(d)
            self._send(d)
    
    __ior__ = update
    
    def add(self, y):
        """ Add the single element y to the current set.  If y is not already
        present, it will be broadcast to all other users."""
        if y not in self._set:
            self._set.add(y)
            self._send((y,))
    
    def _send(self, els):
        if len(els) > 0 and self.handler is not None:
            self.handler.send(dbus.Array([self._trans(el, True) for el in els]))
    
    def _net_update(self, y):
        s = set(y)
        d = s - self._set
        if len(d) > 0:
            self._set.update(d)
            self._trigger(d)
    
    def receive_message(self, msg):
        self._net_update((self._trans(el, False) for el in msg))
    
    def get_history(self):
        if len(self._set) > 0:
            return dbus.Array([self._trans(el, True) for el in self._set])
        else:
            return dbus.Array([], type=dbus.Boolean) #Prevent introspection of empty list, which fails 
    
    add_history = receive_message
    
    def register_listener(self, L):
        """Register a listener L(diffset).  Every time another user adds items
        to the set, L will be called with the set of new items."""
        self._listeners.append(L)
        L(self._set.copy())
    
    def _trigger(self, s):
        for L in self._listeners:
            L(s)
    
    def __repr__(self):
        return 'AddOnlySet(' + repr(self.handler) + ', ' + repr(self._set) + ', ' + repr(self._trans) + ')'

class AddOnlySortedSet(UnorderedObject):
    """ AddOnlySortedSet is much like AddOnlySet, only backed by a ListSet, which
    provides a set for objects that are ordered under cmp().  Items are maintained
    in order.  This approach is most useful in cases where each item is a message,
    and the messages are subject to a time-like ordering.  Messages may still
    arrive out of order, but they will be stored in the same order on each
    computer.
    """
    def __init__(self, initset = (), translatohr=empty_translator):
        self._logger = logging.getLogger('dobject.AddOnlySortedSet')
        self._set = ListSet(initset)
        
        self._lock = threading.Lock()

        self._trans = translator
        self._listeners = []  
        
        self.__and__ = self._set.__and__
        self.__contains__ = self._set.__contains__
        # No self.__delitem__
        self.__eq__ = self._set.__eq__
        self.__ge__ = self._set.__ge__
        # Not implementing getattribute
        self.__getitem__ = self._set.__getitem__
        self.__gt__ = self._set.__gt__
        # Not implementing iand (it can remove items)
        # Special wrapper for ior to trigger events
        # Not implementing isub (it can remove items)
        self.__iter__ = self._set.__iter__
        # Not implementing ixor (it can remove items)
        self.__le__ = self._set.__le__
        self.__len__ = self._set.__len__
        self.__lt__ = self._set.__lt__
        self.__ne__ = self._set.__ne__
        self.__or__ = self._set.__or__
        self.__rand__ = self._set.__rand__
        # Special implementation of repr
        self.__ror__ = self._set.__ror__
        self.__rsub__ = self._set.__rsub__
        self.__rxor__ = self._set.__rxor__
        self.__sub__ = self._set.__sub__
        self.__xor__ = self._set.__xor__
        
        # Special implementation of add to trigger events
        # Not implementing clear
        self.copy = self._set.copy
        self.difference = self._set.difference
        # Not implementing difference_update (it removes items)
        # Not implementing discard (it removes items)
        self.first = self._set.first
        self.headset = self._set.headset
        self.index = self._set.index
        self.intersection = self._set.intersection
        # Not implementing intersection_update (it removes items)
        self.issubset = self._set.issubset
        self.issuperset = self._set.issuperset
        self.last = self._set.last
        # Not implementing pop
        self.position = self._set.position
        # Not implementing remove
        self.subset = self._set.subset
        self.symmetric_difference = self._set.symmetric_difference
        # Not implementing symmetric_difference_update
        self.tailset = self._set.tailset
        self.union = self._set.union
        # Special implementation of update to trigger events
        
    def update(self, y):
        """Add all the elements of an iterable y to the current set.  If any of
        these elements were not already present, they will be broadcast to all
        other users."""
        d = ListSet(y)
        d -= self._set
        if len(d) > 0:
            self._set.update(d)
            self._send(d)
    
    __ior__ = update
    
    def add(self, y):
        """ Add the single element y to the current set.  If y is not already
        present, it will be broadcast to all other users."""
        if y not in self._set:
            self._set.add(y)
            self._send((y,))
    
    def _send(self, els):
        if len(els) > 0 and self.handler is not None:
            self.handler.send(dbus.Array([self._trans(el, True) for el in els]))
    
    def _net_update(self, y):
        d = ListSet()
        d._list = y
        d -= self._set
        if len(d) > 0:
            self._set |= d
            self._trigger(d)
    
    def receive_message(self, msg):
        self._net_update([self._trans(el, False) for el in msg])
    
    def get_history(self):
        if len(self._set._list) > 0:
            return dbus.Array([self._trans(el, True) for el in self._set._list])
        else:
            return dbus.Array([], type=dbus.Boolean) #prevent introspection of empty list, which fails
    
    add_history = receive_message
    
    def register_listener(self, L):
        """Register a listener L(diffset).  Every time another user adds items
        to the set, L will be called with the set of new items as a SortedSet."""
        self._listeners.append(L)
        L(self._set.copy())
    
    def _trigger(self, s):
        for L in self._listeners:
            L(s)
    
    def __repr__(self):
        return 'AddOnlySortedSet(' + repr(self.handler) + ', ' + repr(self._set) + ', ' + repr(self._trans) + ')'
        
class CausalHandler:
    """The CausalHandler is analogous to the UnorderedHandler, in that it
    presents an interface with which to build a wide variety of objects with
    distributed state.  The CausalHandler is different from the Unordered in two
    ways:
    
    1. The send() method of an CausalHandler returns an index, which must be
    stored by the CausalObject in connection with the information that was sent.
    This index is a universal, fully-ordered, strictly causal identifier
    for each message.
    
    2. A CausalObject's receive_message method takes two arguments: the message
    and its index.
    
    As a convenience, there is also
    
    3. A get_index() method, which provides a new index on each call, always
    higher than all previous indexes.
    
    CausalObjects are responsible for including index information in the
    return value of get_history, and processing index information in add_history.
    
    It is noteworthy that CausalHandler is in fact implemented on _top_ of
    UnorderedHandler.  The imposition of ordering does not require lower-level
    access to the network.  This fact of implementation may change in the
    future, but CausalObjects will not be able to tell the difference.
    """
    
    ZERO_INDEX = (0,0)
    
    def __init__(self, name, tube_box):
        self._myname = name
        self._tube_box = tube_box
        self._unordered = UnorderedHandler(name, tube_box)
        self._counter = 0
        self._copies = []
        
        self.object = None
    
    def register(self, obj):
        self.object = obj
        self._unordered.register(self)
    
    def get_index(self):
        """get_index returns a new index, higher than all previous indexes.
        The primary reason to use get_index is if you wish two know the index
        of an item _before_ calling send()"""
        self._counter += 1
        return (self._counter, random.getrandbits(64))
    
    def index_trans(self, index, pack):
        """index_trans is a standard serialization translator for the index
        format. Thanks to this translator, a CausalObject can and should treat
        each index as an opaque, comparable object."""
        if pack:
            return dbus.Struct((dbus.UInt64(index[0]), dbus.UInt64(index[1])), signature='tt')
        else:
            return (int(index[0]), int(index[1]))
    
    def send(self, msg, index=None):
        """send() broadcasts a message to all other participants.  If called
        with one argument, send() broadcasts that message, along with a new
        index, and returns the index.  If called with two arguments, the second
        may be an index, which will be used for this message.  The index must
        have been acquired using get_index().  In this case, the index must be
        acquired immediately prior to calling send().  Otherwise, another
        message may arrive in the interim, causing a violation of causality."""
        if index is None:
            index = self.get_index()
        self._unordered.send(dbus.Struct((msg, self.index_trans(index, True))))
        return index
    
    def receive_message(self, msg):
        m = msg[0]
        index = self.index_trans(msg[1], False)
        self._counter = max(self._counter, index[0])
        self.object.receive_message(m, index)
    
    def add_history(self, hist):
        h = hist[0]
        index = self.index_trans(hist[1], False)
        self._counter = max(self._counter, index[0])
        self.object.add_history(h)
    
    def get_history(self):
        h = self.object.get_history()
        hist = dbus.Struct((h, self.index_trans(self.get_index(), True)))
        return
    
    def copy(self, name):
        """A convenience function for returning a new CausalHandler derived
        from this one, with a new name.  This is safe as long as copy() is called
        with a different name every time."""
        h = CausalHandler(self._myname + "/" + name, self._tube_box)
        self._copies.append(h)
        return h
    
    def get_copies(self):
        return self._copies
    
    def get_name(self):
        return self._myname


class CausalHandlerAcceptor(HandlerAcceptor):
    HANDLER_TYPE = CausalHandler
    def set_handler(self, handler):
        raise NotImplementedError

class CausalObject(CausalHandlerAcceptor):
    """A CausalObject is almost precisely like an UnorderedObject, except
    that whereas an UnorderedObject is completely specified by a set of messages,
    a CausalObject is completely specified by an ordered list of messages,
    sorted according to an opaque index associated with each message.
    This index must be monotonically increasing in time for new messages as they
    are created, but old messages may arrive long after they were created, and 
    are then inserted into the middle of the timestream.
    
    The following code is an abstract class for CausalObject, serving
    primarily as documentation for the concept.
    """

    handler = None

    def set_handler(self, handler):
        """Each CO must accept a CausalHandler via set_handler.

        Subclasses may override this method if they wish to perform more actions
        when a handler is set."""
        if self.handler:
            raise
        else:
            self.handler = handler
            self.handler.register(self)
            
    def receive_message(self, msg, index):
        """This method accepts and processes a message sent via handler.send().
        Because objects are sent over DBus, it is advisable to DBus-ify the message
        before calling send, and de-DBus-ify it inside receive_message.
        
        The index argument is an opaque index used for determining the ordering."""
        raise NotImplementedError
    
    def get_history(self):
        """This method returns an encoded copy of all non-obsolete state, ready to be
        sent over DBus."""
        raise NotImplementedError
    
    def add_history(self, state):
        """This method accepts and processes the state object returned by get_history()"""
        raise NotImplementedError

class CausalDict(CausalObject):
    """NOTE: CausalDict is UNTESTED.  Other things may be buggy, but CausalDict
    PROBABLY DOES NOT WORK. A CausalDict WILL NOT WORK UNTIL set_handler IS CALLED.
    
    CausalDict is a distributed version of a Dict (hash table).  All users keep
    a copy of the entire table, so this is not a "Distributed Hash Table"
    according to the terminology of the field.
    
    CausalDict permits all Dict operations, including removing keys and
    modifying the value of existing keys.  This would not be possible using an
    Unordered approach, because two value assignments to the same key could
    arrive in different orders for different users, leaving them in different
    states at quiescence.
    
    To solve this problem, every assignment and removal is given a monotonically
    increasing unique index, and whenever there is a conflict, the higher-index
    operation wins.
    
    One side effect of this design is that deleted keys cannot be forgotten. If
    an assignment operation is received whose index is lower than
    the deletion's, then that assignment is considered obsolete and must not be
    executed.
    
    To provide a mechanism for reducing memory usage, the clear() method has
    been interpreted to remove not only all entries received so far, but also
    all entries that will ever be received with index less than the current
    index.
    """
    ADD = 0
    DELETE = 1
    CLEAR = 2

    def __init__(self, initdict=(), key_translator=empty_translator, value_translator=empty_translator):
        self._dict = dict(initdict)
        self._listeners = []
        
        self._key_trans = key_translator
        self._val_trans = value_translator
        
        self.__contains__ = self._dict.__contains__
        #Special __delitem__
        self.__eq__ = self._dict.__eq__
        self.__ge__ = self._dict.__ge__
        self.__getitem__ = self._dict.__getitem__
        self.__gt__ = self._dict.__gt__
        self.__le__ = self._dict.__le__
        self.__len__ = self._dict.__len__
        self.__lt__ = self._dict.__lt__
        self.__ne__ = self._dict.__ne__
        # special __setitem__
        
        #Special clear
        self.copy = self._dict.copy
        self.get = self._dict.get
        self.has_key = self._dict.has_key
        self.items = self._dict.items
        self.iteritems = self._dict.iteritems
        self.iterkeys = self._dict.iterkeys
        self.itervalues = self._dict.itervalues
        self.keys = self._dict.keys
        #Special pop
        #Special popitem
        #special setdefault
        #special update
        self.values = self._dict.values

    def set_handler(self, handler):
        if self.handler is not None:
            raise
        else:    
            self.handler = handler
            self._clear = self.handler.get_index() #this must happen before index_dict initialization, so that self._clear is less than any index in index_dict
            self._index_dict = dict(((k, self.handler.get_index()) for k in self._dict))
            
            self.handler.register(self)
    
    def __delitem__(self, key):
        """Same as for dict"""
        del self._dict[key]
        n = self.handler.send(((dbus.Int32(CausalDict.DELETE), self._key_trans(key, True))))
        self._index_dict[key] = n
    
    def __setitem__(self, key, value):
        """Same as for dict"""
        self._dict[key] = value
        n = self.handler.send(dbus.Array([(dbus.Int32(CausalDict.ADD), self._key_trans(key, True), self._val_trans(value, True))]))
        self._index_dict[key] = n
    
    def clear(self):
        """Same as for dict"""
        self._dict.clear()
        self._index_dict.clear()
        n = self.handler.send(dbus.Array([(dbus.Int32(CausalDict.CLEAR))]))
        self._clear = n
    
    def pop(self, key, x=None):
        """Same as for dict"""
        t = (key in self._dict)
        if x is None:
            r = self._dict.pop(key)
        else:
            r = self._dict.pop(key, x)
        
        if t:
            n = self.handler.send(dbus.Array([(dbus.Int32(CausalDict.DELETE), self._key_trans(key, True))]))
            self._index_dict[key] = n
        
        return r
    
    def popitem(self):
        """Same as for dict"""
        p = self._dict.popitem()
        key = p[0]
        n = self.handler.send(dbus.Array([(dbus.Int32(CausalDict.DELETE), self._key_trans(key, True))]))
        self._index_dict[key] = n
        return p
    
    def setdefault(self, key, x):
        """Same as for dict"""
        if key not in self._dict:
            self._dict[key] = x
            n = self.handler.send(dbus.Array([(dbus.Int32(CausalDict.ADD), self._key_trans(key, True), self._val_trans(value, True))]))
        self._index_dict[key] = n
    
    def update(*args,**kargs):
        """Same as for dict"""
        d = dict()
        d.update(*args,**kargs)
        newpairs = []
        for p in d.items():
            if (p[0] not in self._dict) or (self._dict[p[0]] != p[1]):
                newpairs.append(p)
                self._dict[p[0]] = p[1]
        n = self.handler.send(dbus.Array([(dbus.Int32(CausalDict.ADD), self._key_trans(p[0], True), self._val_trans(p[1], True)) for p in newpairs]))
        
        for p in newpairs:
            self._index_dict[p[0]] = n
    
    def receive_message(self, msg, n):
        if n > self._clear:
            a = dict()
            r = dict()
            for m in msg:
                flag = int(m[0]) #don't know length of m without checking flag
                if flag == CausalDict.ADD:
                    key = self._key_trans(m[1], False)
                    if (key not in self._index_dict) or (self._index_dict[key] < n):
                        val = self._val_trans(m[2], False)
                        if key in self._dict:
                            r[key] = self._dict[key]
                        self._dict[key] = val
                        a[key] = val
                        self._index_dict[key] = n
                elif flag == CausalDict.DELETE:
                    key = self._key_trans(m[1], False)
                    if key not in self._index_dict:
                        self._index_dict[key] = n
                    elif (self._index_dict[key] < n):
                        self._index_dict[key] = n
                        if key in self._dict:
                            r[key] = self._dict[key]
                            del self._dict[key]
                elif flag == CausalDict.CLEAR:
                    self._clear = n
                    for (k, ind) in self._index_dict.items():
                        if ind < self._clear:
                            del self._index_dict[k]
                            if k in self._dict:
                                r[k] = self._dict[k]
                                del self._dict[k]
            if (len(a) > 0) or (len(r) > 0):
                self._trigger(a,r)

    def get_history(self):
        c = self.handler.index_trans(self._clear, True)
        d = dbus.Array([(self._key_trans(p[0], True), self._val_trans(p[1], True)) for p in self._dict.items()])
        i = dbus.Array([(self._key_trans(p[0], True), self.handler.index_trans(p[1], True)) for p in self._index_dict.items()])
        return dbus.Struct((c,d,i),signature='itt')
    
    def add_history(self, hist):
        c = self.handler.index_trans(hist[0], False)
        d = dict(((self._key_trans(p[0], False), self._val_trans(p[1], False)) for p in hist[1]))
        i = [(self._key_trans(p[0], False), self.handler.index_trans(p[1], False)) for p in hist[2]]
        
        a = dict()
        r = dict()
        
        if c > self._clear:
            self._clear = c
            for (k, n) in self._index_dict.items():
                if n < self._clear:
                    del self._index_dict[k]
                    if k in self._dict:
                        r[k] = self._dict[k]
                        del self._dict[k]
        
        k_changed = []
        for (k, n) in i:
            if (((k not in self._index_dict) and (n > self._clear)) or
                ((k in self._index_dict) and (n > self._index_dict[k]))):
                k_changed.append(k)
                self._index_dict[k] = n
        
        for k in k_changed:
            if k in d:
                if (k in self._dict) and (self._dict[k] != d[k]):
                    r[k] = self._dict[k]
                    a[k] = d[k]
                elif k not in self._dict:
                    a[k] = d[k]
                self._dict[k] = d[k]
            else:
                if k in self._dict:
                    r[k] = self._dict[k]
                    del self._dict[k]
        
        if (len(a) > 0) or (len(r) > 0):
            self._trigger(a,r)
        
    def register_listener(self, L):
        """Register a change-listener L.  Whenever another user makes a change
        to this dict, L will be called with L(dict_added, dict_removed).  The
        two arguments are the dict of new entries, and the dict of entries that
        have been deleted or overwritten."""
        self._listeners.append(L)
        L(self._dict.copy(), dict())
    
    def _trigger(self, added, removed):
        for L in self._listeners:
            L(added, removed)

class UserDict(dbus.gobject_service.ExportedGObject):
    IFACE = "org.dobject.UserDict"
    BASEPATH = "/org/dobject/UserDict/"
    
    def __init__(self, name, tubebox, myval, translator = empty_translator):
        self._myname = name
        self.PATH = UserDict.BASEPATH + name
        dbus.gobject_service.ExportedGObject.__init__(self)
        self._logger = logging.getLogger(self.PATH)
        self._tube_box = tube_box
        self.tube = None
        
        self._dict = dict()
        self._myval = myval
        self._trans = translator
        
        self._tube_box.register_listener(self.set_tube)
        
        self.__contains__ = self._dict.__contains__
        #No __delitem__
        self.__eq__ = self._dict.__eq__
        self.__ge__ = self._dict.__ge__
        self.__getitem__ = self._dict.__getitem__
        self.__gt__ = self._dict.__gt__
        self.__le__ = self._dict.__le__
        self.__len__ = self._dict.__len__
        self.__lt__ = self._dict.__lt__
        self.__ne__ = self._dict.__ne__
        #No __setitem__
        
        #No clear
        self.copy = self._dict.copy
        self.get = self._dict.get
        self.has_key = self._dict.has_key
        self.items = self._dict.items
        self.iteritems = self._dict.iteritems
        self.iterkeys = self._dict.iterkeys
        self.itervalues = self._dict.itervalues
        self.keys = self._dict.keys
        #No pop
        #No popitem
        #No setdefault
        #No update
        self.values = self._dict.values

    def set_tube(self, tube, is_initiator):
        """Callback for the TubeBox"""
        self.tube = tube
        self.add_to_connection(self.tube, self.PATH)
                        
        self.tube.add_signal_receiver(self.receive_value, signal_name='send_value', dbus_interface=UserDict.IFACE, sender_keyword='sender', path=self.PATH)
        self.tube.add_signal_receiver(self.tell_value, signal_name='ask_values', dbus_interface=UserDict.IFACE, sender_keyword='sender', path=self.PATH)
        self.tube.watch_participants(self.members_changed)

        #Alternative implementation of members_changed (not yet working)
        #self.tube.add_signal_receiver(self.members_changed, signal_name="MembersChanged", dbus_interface="org.freedesktop.Telepathy.Channel.Interface.Group")

        self.ask_values()
            
    def get_path(self):
        """Returns the DBus path of this handler.  The path is the closest thing
        to a unique identifier for each abstract DObject."""
        return self.PATH
    
    def get_tube(self):
        """Returns the TubeBox used to create this handler.  This method is
        necessary if one DObject wishes to create another."""
        return self._tube_box
    
    @dbus.service.signal(dbus_interface=IFACE, signature='v')
    def send_value(self, value):
        """This method broadcasts message to all other handlers for this UO"""
        return
        
    @dbus.service.signal(dbus_interface=IFACE, signature='')
    def ask_values(self):
        return
    
    def tell_value(self, sender=None):
        self._logger.debug("tell_history to " + str(sender))
        try:
            if sender == self.tube.get_unique_name():
                return
            remote = self.tube.get_object(sender, self.PATH)
            remote.receive_value(self._myval, sender_keyword='sender', reply_handler=PassFunction, error_handler=PassFunction)
        finally:
            return
    
    @dbus.service.method(dbus_interface=IFACE, in_signature = 'v', out_signature='', sender_keyword = 'sender')
    def receive_value(self, value, sender=None):
        self._dict[sender] = self._trans(value, False)

    #Alternative implementation of a members_changed (not yet working)
    """ 
    def members_changed(self, message, added, removed, local_pending, remote_pending, actor, reason):
        added_names = self.tube.InspectHandles(telepathy.CONNECTION_HANDLE_TYPE_LIST, added)
        for name in added_names:
            self.tell_history(name)
    """
    def members_changed(self, added, removed):
        self._logger.debug("members_changed")
        for (handle, name) in removed:
            if name in self._dict:
                del self._dict[name]
        for (handle, name) in added:
            self.tell_value(sender=name)

class UnorderedString(UnorderedObject):
    
    def __init__(self,initstring=''):
        self._tree = stringtree.SimpleStringTree()
        self._listeners = []
        self._newbuffer = []
        if initstring:
            self.insert(initstring, 0)
    
    def insert(self, text, pos):
        x = self._tree.insert(text,pos)
        if self.handler is not None:
            self.handler.send(dbus.Array(stringtree.translator(i,True) for i in x))
    
    def delete(self, k, n):
        x = self._tree.delete(k,n)
        if self.handler is not None:
            self.handler.send(dbus.Array(stringtree.translator(i,True) for i in x))
    
    def _net_update(self, L):
        transformed_list = []
        self._newbuffer.append(L)
        for li in self._newbuffer[::-1]:
            if self._tree.is_ready(li[0]): #each update from the net is required to
                #obey the rule that if the tree is ready for the first Change,
                #then it is ready for all the changes.  This may be a sort of
                #violation of the Unordered abstraction...
                for c in li:
                    transformed_list.extend(self._tree.add_change(c))
                self._newbuffer.pop() #Having handled the contents of li, we
                #should make sure it doesn't come up for consideration again
        self._trigger(transformed_list)
            
    def get_history(self):
        return dbus.Array((stringtree.translator(c, True) 
                                   for c in self._tree.get_changes()),
                                   signature = 'v')
    
    def add_history(self, msg):
        L = []
        for el in msg:
            change = stringtree.translator(el, False)
            if change.unique_id not in self._tree._id2rec:
                L.append(change)
        if L:
            self._net_update(L)
    
    receive_message = add_history
    
    def register_listener(self, L):
        """Register a listener L(editlist).  Every time another user modifies
        the string, L will be called with a set of edits that represent those
        changes on the local version of the string.  Note that the edits must
        be performed in order."""
        self._listeners.append(L)
    
    def _trigger(self, editlist):
        for L in self._listeners:
            L(editlist)

class CausalTree(CausalObject):
    #SET_PARENT and DELETE_NODE are opcodes to be sent over the wire, and also
    #to the trigger.  MAJOR_CHANGE is sent only to the trigger, and it is not
    #an opcode. It represents a significant but undefined changed in the tree.
    SET_PARENT = 0
    DELETE_NODE = 1
    CLEAR = 2
    MAJOR_CHANGE = -1
    
    ROOT = 0
    
    def __init__(self):
        self._timeline = ListSet()
        self._reverse = {}
        self._listeners = []
        self._reset()
    
    def _reset(self):
        self._parent = {}
        self._children = {self.ROOT:set()}
        
    def __contains__(self, node):
        return node in self._children
    
    def get_parent(self,node):
        if node == self.ROOT:
            return self.ROOT
        else:
            return self._parent[node]
    
    def get_children(self, node):
        return frozenset(self._children[node])
    
    def _process_local_cmd(self,cmd):
        i = self.handler.get_index()
        self._timeline.add((i,cmd))
        rev = self._step(cmd)
        self._reverse[(i,cmd)] = rev
        self.handler.send(self._cmd_trans(cmd,True),i)
    
    def change_parent(self,node,newparent):
        if (node in self._parent) and (newparent in self._children):
            if self._parent[node] != newparent:
                cmd = (self.SET_PARENT, node, newparent)
                self._process_local_cmd(cmd)
        else:
            raise KeyError("One or both nodes is not present")
        
    def new_child(self,parent):
        node = random.getrandbits(64)
        cmd = (self.SET_PARENT, node, parent)
        self._process_local_cmd(cmd)
        return node
    
    def delete(self,node):
        if node == self.ROOT:
            raise KeyError("You cannot delete the root node.")
        if node not in self._children:
            raise KeyError("No such node.")
        cmd = (self.DELETE_NODE, node)
        self._process_local_cmd(cmd)
        
    def clear(self):
        cmd = (self.CLEAR,)
        self._process_local_cmd(cmd)
    
    def _step(self, cmd):
        # Returns () if the command failed or had no effect
        # If the command succeeded, returns an iterable of the commands necessary
        # to undo this command
        if cmd[0] == self.SET_PARENT:
            if cmd[2] in self._children: #if newparent is known
                if cmd[1] in self._parent: #if node is known
                    if self._parent[cmd[1]] == cmd[2]:
                        return () #No change necessary.  This SET_PARENT is redundant
                    if cmd[1] in self._allparents(cmd[2]): #if node is above newparent
                        #This command would create a loop.  It is therefore illegal
                        #and should be ignored
                        return ()
                    else:
                        #remove node from under its current parent
                        oldp = self._parent[cmd[1]]
                        self._children[oldp].remove(cmd[1])
                        self._children[cmd[2]].add(cmd[1])
                        self._parent[cmd[1]] = cmd[2]
                        return ((self.SET_PARENT, cmd[1], oldp),)
                else:
                    #Node is unknown, so it must be added
                    self._children[cmd[1]] = set()
                    self._children[cmd[2]].add(cmd[1])
                    self._parent[cmd[1]] = cmd[2]
                    return ((self.DELETE_NODE, cmd[1]),)  #the command executed successfully
            else:
                #The new parent is unknown, so the command is illegal and should
                #be ignored.
                return ()
        elif cmd[0] == self.DELETE_NODE:
            if cmd[1] == self.ROOT:
                #Deleting the root node is not allowed, so this command is illegal and should be ignored
                return ()
            if cmd[1] in self._children:
                p = self._parent[cmd[1]]
                self._children[p].remove(cmd[1])
                cmds = [(self.SET_PARENT, cmd[1], p)]
                for c in self._children[cmd[1]]:
                    self._children[p].add(c)
                    self._parent[c] = p
                    cmds.append((self.SET_PARENT,c,cmd[1]))
                del self._children[cmd[1]]
                del self._parent[cmd[1]]
                return cmds #The command completed successfully
            else:
                #cmd[1] is an unknown node, so this command should be ignored
                return ()
        elif cmd[0] == self.CLEAR:
            deleted = self._parent.keys() #relies on self.ROOT not being in _parent
            cmds = []
            stack = [self.ROOT]
            while len(stack) > 0:
                n = stack.pop()
                for c in self._children[n]:
                    cmds.append((self.SET_PARENT, c, n))
                    stack.append(c)
            self._reset()
            return cmds
    
    def _allparents(self, node):
        s = set()
        while node != self.ROOT:
            s.add(node)
            node = self._parent[node]
        s.add(self.ROOT)
        return s
    
    def _cmd_trans(self,cmd,pack):
        #This code does not completely specify the dbus typing because it avoids
        #calling dbus.Struct.  The tuple will be introspected.
        if len(cmd) == 1: #CLEAR
            return (self._instruction_trans(cmd[0],pack),)
        if len(cmd) == 2: #DELETE_NODE
            return (self._instruction_trans(cmd[0],pack), self.node_trans(cmd[1],pack))
        elif len(cmd) == 3: #SET_PARENT
            return (self._instruction_trans(cmd[0],pack), 
                                self.node_trans(cmd[1],pack),
                                self.node_trans(cmd[2],pack))
    
    def _instruction_trans(self,ins,pack):
        return int_translator(ins,pack)
    
    def node_trans(self,node,pack):
        return uint_translator(node,pack)
    
    def register_listener(self, L):
        self._listeners.append(L)
    
    def receive_message(self, cmd, i):
        cmd = self._cmd_trans(cmd,False)
        elt = (i, cmd)
        if elt > self._timeline.last():
            self._timeline.add(elt)
            s = self._step(cmd)
            self._reverse[elt] = s
            if s:
                self._trigger((cmd,),s)
        else:
            (forward, reverse) = self._antestep((elt,))
            if forward:
                self._trigger(forward, reverse)
    
    def _antestep(self, elts):
        #_antestep accepts an iterable of (i, cmd)s that may have
        # occurred at previous times.  It incorporates these changes into the
        # timeline and state.  It also returns a two-element tuple:
        # a list of cmds that would have the same effect as the inclusion of elts, and a
        # list of cmds that would reverse this effect.
        newelts = [e for e in elts if e not in self._timeline]
        if len(newelts) == 0:
            return (False, False)
        affected = [e for e in self._timeline.tailset(newelts[0]) if self._reverse[e]]
        rollback = []
        for l in affected[::-1]:
            rollback.extend(self._reverse[l])
        for cmd in rollback:
            self._step(cmd)
        # We have now rolled back to the point where newelts[0] is inserted
        self._timeline.update(newelts)
        new_effective = []
        reversers = []
        for (i,cmd) in self._timeline.tailset(newelts[0]):
            rev = self._step(cmd)
            self._reverse[(i,cmd)] = rev
            if rev: #If the command had any effect
                reversers.append(rev)
                new_effective.append(cmd)
        reversers.reverse()
        reversenew = []
        for l in reversers:
            reversenew.extend(l)
        forward = rollback
        forward.extend(new_effective)
        reverse = reversenew
        reverse.extend(affected)
        return (forward, reverse)
        #This implementation is extremely suboptimal. An ideal implementation
        #would use some knowledge about the commutativity of different commands
        #to shorten forward and reverse substantially.  As is, they will likely
        #contain mostly redundant undo-and-then-redo.
        
    def get_history(self):
        return dbus.Array(
            (self.handler.index_trans(i,True), self._cmd_trans(cmd,True)) 
                for (i,cmd) in self._timeline)
    
    def add_history(self,h):
        elts = ((self.handler.index_trans(i,False), self._cmd_trans(cmd,False))
                    for (i,cmd) in h)
        (forward, reverse) = self._antestep(elts)
        if forward:
            self._trigger(forward, reverse)
    
    def _trigger(self, info):
        # info is either (added, removed, affected) if that info is available,
        # or False if there has been a change but no info is available
        for L in self._listeners:
            L(info)
