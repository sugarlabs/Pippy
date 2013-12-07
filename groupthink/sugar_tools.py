# Copyright 2007 Collabora Ltd.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA

import logging
import telepathy

from sugar3.activity.activity import Activity
from sugar3.presence import presenceservice

from sugar3.presence.tubeconn import TubeConnection
from sugar3.graphics.window import Window

from gi.repository import Gtk
from gi.repository import Gdk
from gi.repository import GObject

import groupthink_base as groupthink

from sugar3.graphics.toolbarbox import ToolbarBox
from sugar3.activity.widgets import ActivityToolbarButton

def exhaust_event_loop():
    while Gtk.events_pending():
        Gtk.main_iteration()

class GroupActivity(Activity):

    message_preparing = "Preparing user interface"
    message_loading = "Loading object from Journal"
    message_joining = "Joining shared activity"
    
    """Abstract Class for Activities using Groupthink"""
    def __init__(self, handle):
        # self.initiating indicates whether this instance has initiated sharing
        # it always starts false, but will be set to true if this activity
        # initiates sharing. In particular, if Activity.__init__ calls
        # self.share(), self.initiating will be set to True.
        self.initiating = False
        # self._processed_share indicates whether when_shared() has been called
        self._processed_share = False
        # self.initialized tracks whether the Activity's display is up and running
        self.initialized = False
        
        self.early_setup()
        
        super(GroupActivity, self).__init__(handle)
        self.dbus_name = self.get_bundle_id()
        self.logger = logging.getLogger(self.dbus_name)
        
        self._handle = handle

        ##GObject.threads_init()

        self._sharing_completed = not self.shared_activity
        self._readfile_completed = not handle.object_id

        if self.shared_activity:
            self.message = self.message_joining
        elif handle.object_id:
            self.message = self.message_loading
        else:
            self.message = self.message_preparing

        toolbar_box = ToolbarBox()
        self.activity_button = ActivityToolbarButton(self)
        toolbar_box.toolbar.insert(self.activity_button, 0)
        self.set_toolbar_box(toolbar_box)

        v = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.startup_label = Gtk.Label(label=self.message)
        v.pack_start(self.startup_label, True, True, 0)
        Window.set_canvas(self,v)
        self.show_all()
        
        # The show_all method queues up draw events, but they aren't executed
        # until the mainloop has a chance to process them.  We want to process
        # them immediately, because we need to show the waiting screen
        # before the waiting starts, not after.
        exhaust_event_loop()
        # exhaust_event_loop() provides the possibility that write_file could
        # be called at this time, so write_file is designed to trigger read_file
        # itself if that path occurs.
        
        self.tubebox = groupthink.TubeBox()
        self.timer = groupthink.TimeHandler("main", self.tubebox)
        self.cloud = groupthink.Group(self.tubebox)
        # self.cloud is extremely important.  It is the unified reference point
        # that contains all state in the system.  Everything else is stateless.
        # self.cloud has to be defined before the call to self.set_canvas, because
        # set_canvas can trigger almost anything, including pending calls to read_file,
        # which relies on self.cloud.
        
        # get the Presence Service
        self.pservice = presenceservice.get_instance()
        # Buddy object for you
        owner = self.pservice.get_owner()
        self.owner = owner

        self.connect('shared', self._shared_cb)
        self.connect('joined', self._joined_cb)
        if self.get_shared():
            if self.initiating:
                self._shared_cb(self)
            else:
                self._joined_cb(self)
        
        self.add_events(Gdk.EventMask.VISIBILITY_NOTIFY_MASK)
        self.connect("visibility-notify-event", self._visible_cb)
        self.connect("notify::active", self._active_cb)
        
        if not self._readfile_completed:
            self.read_file(self._jobject.file_path)
        elif not self.shared_activity:
            GObject.idle_add(self._initialize_cleanstart)
    
    def _initialize_cleanstart(self):
        self.initialize_cleanstart()
        self._initialize_display()
        return False
    
    def initialize_cleanstart(self):
        """Any subclass that needs to take any extra action in the case where
        the activity is launched locally without a sharing context or input
        file should override this method"""
        pass
    
    def early_setup(self):
        """Any subclass that needs to take an action before any external interaction
        (e.g. read_file, write_file) occurs should place that code in early_setup"""
        pass
    
    def _initialize_display(self):
        main_widget = self.initialize_display()
        Window.set_canvas(self, main_widget)
        self.initialized = True

        if self.shared_activity and not self._processed_share:
            # We are joining a shared activity, but when_shared has not yet
            # been called
            self.when_shared()
            self._processed_share = True
        self.show_all()
        self.after_init()

    def after_init(self):
        """Callback after init. Override to use"""
        pass
    
    def initialize_display(self):
        """All subclasses must override this method, in order to display
        their GUI using self.set_canvas()"""
        raise NotImplementedError
        
    def share(self, private=False):
        """The purpose of this function is solely to permit us to determine
        whether share() has been called.  This is necessary because share() may
        be called during Activity.__init__, and thus emit the 'shared' signal
        before we have a chance to connect any signal handlers."""
        self.initiating = True
        super(GroupActivity, self).share(private)
        if self.initialized and not self._processed_share:
            self.when_shared()
            self._processed_share = True
    
    def when_shared(self):
        """Inheritors should override this method to perform any special
        operations when the user shares the session"""
        pass

    def _shared_cb(self, activity):
        self.logger.debug('My activity was shared')
        self.initiating = True
        self._sharing_setup()

        self.logger.debug('This is my activity: making a tube...')
        id = self.tubes_chan[telepathy.CHANNEL_TYPE_TUBES].OfferDBusTube(
            self.dbus_name, {})

    def _sharing_setup(self):
        if self.shared_activity is None:
            self.logger.error('Failed to share or join activity')
            return

        self.conn = self.shared_activity.telepathy_conn
        self.tubes_chan = self.shared_activity.telepathy_tubes_chan
        self.text_chan = self.shared_activity.telepathy_text_chan

        self.tubes_chan[telepathy.CHANNEL_TYPE_TUBES].connect_to_signal('NewTube',
            self._new_tube_cb)

    def _list_tubes_reply_cb(self, tubes):
        self.logger.debug('Got %d tubes from ListTubes' % len(tubes))
        for tube_info in tubes:
            self._new_tube_cb(*tube_info)

    def _list_tubes_error_cb(self, e):
        self.logger.error('ListTubes() failed: %s', e)

    def _joined_cb(self, activity):
        if not self.shared_activity:
            return

        self.logger.debug('Joined an existing shared activity')
        self.initiating = False
        self._sharing_setup()

        self.logger.debug('This is not my activity: waiting for a tube...')
        self.tubes_chan[telepathy.CHANNEL_TYPE_TUBES].ListTubes(
            reply_handler=self._list_tubes_reply_cb,
            error_handler=self._list_tubes_error_cb)

    def _new_tube_cb(self, id, initiator, type, service, params, state):
        self.logger.debug('New tube: ID=%d initator=%d type=%d service=%s '
                     'params=%r state=%d', id, initiator, type, service,
                     params, state)
        if (type == telepathy.TUBE_TYPE_DBUS and
            service == self.dbus_name):
            if state == telepathy.TUBE_STATE_LOCAL_PENDING:
                self.tubes_chan[telepathy.CHANNEL_TYPE_TUBES].AcceptDBusTube(id)
            tube_conn = TubeConnection(self.conn,
                self.tubes_chan[telepathy.CHANNEL_TYPE_TUBES],
                id, group_iface=self.text_chan[telepathy.CHANNEL_INTERFACE_GROUP])
            self.tubebox.insert_tube(tube_conn, self.initiating)
            self._sharing_completed = True
            if self._readfile_completed and not self.initialized:
                self._initialize_display()

    def read_file(self, file_path):
        self.cloud.loads(self.load_from_journal(file_path))
        self._readfile_completed = True
        if self._sharing_completed and not self.initialized:
            self._initialize_display()
        
    def load_from_journal(self, file_path):
        """This implementation of load_from_journal simply returns the contents
        of the file.  Any inheritor overriding this method must return the
        string provided to save_to_journal as cloudstring."""
        if file_path:
            f = file(file_path,'rb')
            s = f.read()
            f.close()
            return s
    
    def write_file(self, file_path):
        # There is a possibility that the user could trigger a write_file
        # action before read_file has occurred.  This could be dangerous,
        # potentially overwriting the journal entry with blank state.  To avoid
        # this, we ensure that read_file has been called (if there is a file to
        # read) before writing.
        if not self._readfile_completed:
            self.read_file(self._jobject.file_path)
        self.save_to_journal(file_path, self.cloud.dumps())

    def save_to_journal(self, file_path, cloudstring):
        """This implementation of save_to_journal simply dumps the output of
        self.cloud.dumps() to disk.  Any inheritor who wishes to control file
        output should override this method, and must
        be sure to include cloudstring in its write_file."""
        f = file(file_path, 'wb')
        f.write(cloudstring)
        f.close()
        
    def _active_cb(self, widget, event):
        self.logger.debug("_active_cb")
        if self.props.active:
            self.resume()
        else:
            self.pause()
            
    def _visible_cb(self, widget, event):
        self.logger.debug("_visible_cb")
        if event.get_state() == Gdk.VisibilityState.FULLY_OBSCURED:
            self.pause()
        else:
            self.resume()
    
    def pause(self):
        """Subclasses should override this function to stop updating the display
        since it is not visible."""
        pass
    
    def resume(self):
        """Subclasses should override this function to resume updating the
        display, since it is now visible"""
        pass
