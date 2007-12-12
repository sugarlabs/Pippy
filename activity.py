# Copyright 2007 Chris Ball, based on Collabora's "hellomesh" demo.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 2 of the License, or
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

"""Pippy Activity: A simple Python programming activity ."""
from __future__ import with_statement
import gtksourceview2
import gtk
import logging
import telepathy
import telepathy.client
import pango
import vte
import re, os, os.path
import gobject

from signal import SIGTERM
from gettext import gettext as _
from dbus.service import method, signal
from dbus.gobject_service import ExportedGObject

from sugar.activity.activity import Activity, ActivityToolbox, get_bundle_path
from sugar.presence import presenceservice

from sugar.presence.tubeconn import TubeConnection
from sugar.graphics.toolbutton import ToolButton


SERVICE = "org.laptop.Pippy"
IFACE = SERVICE
PATH = "/org/laptop/Pippy"

ACTIVITY_INFO_TEMPLATE = """
[Activity]
name = %s
bundle_id = org.laptop.pippy.%s
class = activity.VteActivity
icon = activity-icon
activity_version = %d
show_launcher = yes
"""

class PippyActivity(Activity):
    """Pippy Activity as specified in activity.info"""
    def __init__(self, handle):
        """Set up the Pippy activity."""
        Activity.__init__(self, handle)
        self._logger = logging.getLogger('pippy-activity')

        # Top toolbar with share and close buttons:
        toolbox = ActivityToolbox(self)
        # add 'make bundle' button.
        at = toolbox.get_activity_toolbar()
        # XXX: shouldn't reuse document-save; we need a distinctive icon.
        self._make = ToolButton('document-save')
        self._make.set_tooltip(_('Save as Activity'))
        self._make.connect('clicked', self.makebutton_cb)
        toolbox.get_activity_toolbar().insert(self._make, 4)
        self._make.show()
        self.set_toolbox(toolbox)
        toolbox.show()

        # Main layout.
        hbox = gtk.HBox()
        vbox = gtk.VBox()
        
        # The sidebar.
        self.model = gtk.TreeStore(gobject.TYPE_PYOBJECT, gobject.TYPE_STRING)
        treeview = gtk.TreeView(self.model)
        cellrenderer = gtk.CellRendererText()
        treecolumn = gtk.TreeViewColumn(_("Examples"), cellrenderer, text=1)
        treeview.get_selection().connect("changed", self.selection_cb)
        treeview.append_column(treecolumn)
        treeview.set_size_request(220, 900)

        # Create scrollbars around the view.
        scrolled = gtk.ScrolledWindow()
        scrolled.add(treeview)
        hbox.pack_start(scrolled)

        for root, dirs, files in os.walk(get_bundle_path() + '/data/', topdown=True):
            for i in dirs:
                self._logger.debug("dir %s" % i)
                direntry = { "name": _(i), "path": root + i + "/" }
                olditer = self.model.insert_before(None, None)
                self.model.set_value(olditer, 0, direntry)
                self.model.set_value(olditer, 1, direntry["name"])
                
                listdir = os.listdir(root + i)
                listdir.sort()
                for _file in listdir:
                    self._logger.debug("file %s" % _file)
                    entry = { "name": _(_file), "path": root + i + "/" + _file }
                    _iter = self.model.insert_before(olditer, None)
                    self.model.set_value(_iter, 0, entry)
                    self.model.set_value(_iter, 1, entry["name"])

        treeview.expand_all()

        # Source buffer
        self.text_buffer = gtksourceview2.Buffer()
        lang_manager = gtksourceview2.language_manager_get_default()
        langs = lang_manager.list_languages()
        for lang in langs:
            for m in lang.get_mime_types():
                if m == "text/x-python":
                    self.text_buffer.set_language(lang)

        self.text_buffer.set_highlight(True)

        # The GTK source view window
        self.text_view = gtksourceview2.View(self.text_buffer)
        self.text_view.set_size_request(900, 350)
        self.text_view.set_editable(True)
        self.text_view.set_cursor_visible(True)
        self.text_view.set_show_line_numbers(True)
        self.text_view.set_wrap_mode(gtk.WRAP_CHAR)
        self.text_view.modify_font(pango.FontDescription("Monospace 10"))

        # We could change the color theme here, if we want to.
        #mgr = gtksourceview2.style_manager_get_default()
        #style_scheme = mgr.get_scheme('kate')
        #self.text_buffer.set_style_scheme(style_scheme)

        codesw = gtk.ScrolledWindow()
        codesw.set_policy(gtk.POLICY_AUTOMATIC,
                      gtk.POLICY_AUTOMATIC)
        codesw.add(self.text_view)
        vbox.pack_start(codesw)

        # An hbox for the buttons
        buttonhbox = gtk.HBox()

        # The "go" button
        gobutton = gtk.Button(label=_("Run!"))
        gobutton.connect('clicked', self.gobutton_cb)
        gobutton.set_size_request(800, 2)
        buttonhbox.pack_start(gobutton)

        # The "stop" button
        stopbutton = gtk.Button(label=_("Stop!"))
        stopbutton.connect('clicked', self.stopbutton_cb)
        stopbutton.set_size_request(200, 2)
        buttonhbox.pack_end(stopbutton)

        vbox.pack_start(buttonhbox)

        # An hbox to hold the vte window and its scrollbar.
        outbox = gtk.HBox()
        
        # The vte python window
        self._vte = vte.Terminal()
        self._vte.set_size(30, 5)
        self._vte.set_size_request(200, 300)
        font = 'Monospace 10'
        self._vte.set_font(pango.FontDescription(font))
        self._vte.set_colors(gtk.gdk.color_parse ('#000000'),
                             gtk.gdk.color_parse ('#E7E7E7'),
                             [])
        outbox.pack_start(self._vte)
        
        outsb = gtk.VScrollbar(self._vte.get_adjustment())
        outsb.show()
        outbox.pack_start(outsb, False, False, 0)
        vbox.pack_end(outbox)
        hbox.pack_end(vbox)
        self.set_canvas(hbox)
        self.show_all()

        
        self.hellotube = None

        # get the Presence Service
        self.pservice = presenceservice.get_instance()
        name, path = self.pservice.get_preferred_connection()
        self.tp_conn_name = name
        self.tp_conn_path = path
        self.conn = telepathy.client.Connection(name, path)
        self.initiating = None
        
        self.connect('shared', self._shared_cb)

        # Buddy object for you
        owner = self.pservice.get_owner()
        self.owner = owner

        if self._shared_activity:
            # we are joining the activity
            self.connect('joined', self._joined_cb)
            self._shared_activity.connect('buddy-joined',
                                          self._buddy_joined_cb)
            self._shared_activity.connect('buddy-left',
                                          self._buddy_left_cb)
            if self.get_shared():
                # we've already joined
                self._joined_cb()

    def selection_cb(self, column):
        self.save()
        model, _iter = column.get_selected()
        value = model.get_value(_iter,0)
        self._logger.debug("clicked! %s" % value['path'])
        _file = open(value['path'], 'r')
        lines = _file.readlines()
        self.text_buffer.set_text("".join(lines))

    def _write_text_buffer(self, filename):
        start, end = self.text_buffer.get_bounds()
        text = self.text_buffer.get_text(start, end)

        with open(filename, 'w') as f:
            for line in text:
                f.write(line)
    def _reset_vte(self):
        self._vte.grab_focus()
        self._vte.feed("\x1B[H\x1B[J\x1B[0;39m")

    def gobutton_cb(self, button):
        self._reset_vte()
        
        # FIXME: We're losing an odd race here
        # gtk.main_iteration(block=False)
        
        pippy_app_name = '%s/tmp/pippy_app.py' % self.get_activity_root()
        self._write_text_buffer(pippy_app_name)

        self._pid = self._vte.fork_command \
                    (command="/bin/sh",
                     argv=["/bin/sh", "-c",
                           "python %s; sleep 1" % pippy_app_name],
                     envv=["PYTHONPATH=%s/library" % get_bundle_path()],
                     directory=get_bundle_path())

    def stopbutton_cb(self, button):
        os.kill(self._pid, SIGTERM)	

    def makebutton_cb(self, button):
        from shutil import copytree, copy2, rmtree
        from tempfile import mkdtemp
        from sugar import profile
        from sugar.datastore import datastore
        # get the name of this pippy program.
        title = self.metadata['title']
        if title == 'Pippy Activity':
            from sugar.graphics.alert import Alert
            from sugar.graphics.icon import Icon
            alert = Alert()
            alert.props.title =_ ('Save as Activity Error')
            alert.props.msg = _('Please give your activity a meaningful name before attempting to save it as an activity.')
            cancel_icon = Icon(icon_name='dialog-cancel')
            alert.add_button(gtk.RESPONSE_CANCEL, _('Stop'), cancel_icon)
            alert.connect('response', self.dismiss_alert_cb)
            self.add_alert(alert)
            return
        self._reset_vte()
        # turn the activity title into a python identifier.
        pytitle = re.sub(r'[^A-Za-z0-9_]', '', title)
        if re.match(r'[0-9]', pytitle) is not None:
            pytitle = '_' + pytitle # first character cannot be numeric
        # create a new temp dir in which to create the bundle.
        app_temp = mkdtemp('.activity', 'Pippy',
                           '%s/tmp/' % self.get_activity_root())
        bundle = get_bundle_path()
        try:
            for f in os.listdir('%s/skel' % bundle):
                if os.path.isdir(f):
                    cp = copytree
                else:
                    cp = copy2
                cp('%s/skel/%s' % (bundle, f), '%s/%s' % (app_temp, f))
            copytree('%s/library' % bundle, '%s/library' % app_temp)
            # create activity.info file.
            version = 1
            with open('%s/activity/activity.info' % app_temp, 'w') as f:
                f.write(ACTIVITY_INFO_TEMPLATE % (title, pytitle, version))
            # put script into $app_temp/pippy_app.py
            self._write_text_buffer('%s/pippy_app.py' % app_temp)
            # write MANIFEST file.
            with open('%s/MANIFEST' % app_temp, 'w') as f:
                for dirpath, dirnames, filenames in os.walk(app_temp):
                    for name in filenames:
                        fn = os.path.join(dirpath, name).replace(app_temp+'/', '')
                        if fn=='MANIFEST': continue
                        f.write('%s\n' % fn)
            # invoke bundle builder
            pid = self._vte.fork_command \
                    (command="/bin/sh",
                     argv=["/bin/sh", "-c",
                           "python %s/setup.py dist || sleep 1" % app_temp],
                     directory=app_temp)
            # hand off to journal?
            jobject = datastore.create()
            metadata = {
                'title': '%s Bundle' % title,
                'title_set_by_user': '1',
                'buddies': '',
                'preview': '',
                'icon-color': profile.get_color().to_string(),
                'mime_type': 'application/vnd.olpc-sugar',
            }
            for k, v in metadata.items():
                jobject.metadata[k] = v # the dict.update method is missing =(
            jobject.file_path = '%s/%s-%d.xo' % (app_temp, pytitle, version)
            os.waitpid(pid, 0)
            datastore.write(jobject)
            jobject.destroy()
            self._vte.feed("\r\n")
            self._vte.feed(_("Activity saved to journal."))
            self._vte.feed("\r\n")
        finally:
            rmtree(app_temp, ignore_errors=True)

    def dismiss_alert_cb(self, alert, response_id):
        self.remove_alert(alert)

    def write_file(self, file_path):
        self.metadata['mime_type'] = 'text/x-python'
        start, end = self.text_buffer.get_bounds()
        text = self.text_buffer.get_text(start, end)
        _file = open(file_path, 'w')
        _file.write(text)
    
    def read_file(self, file_path):
        text = open(file_path).read()
        self.text_buffer.set_text(text)
        
    def _shared_cb(self, activity):
        self._logger.debug('My activity was shared')
        self.initiating = True
        self._setup()

        for buddy in self._shared_activity.get_joined_buddies():
            self._logger.debug('Buddy %s is already in the activity' %
                buddy.props.nick)

        self._shared_activity.connect('buddy-joined', self._buddy_joined_cb)
        self._shared_activity.connect('buddy-left', self._buddy_left_cb)

        self._logger.debug('This is my activity: making a tube...')
        _id = self.tubes_chan[telepathy.CHANNEL_TYPE_TUBES].OfferDBusTube(
            SERVICE, {})

    # presence service should be tubes-aware and give us more help
    # with this
    def _setup(self):
        if self._shared_activity is None:
            self._logger.error('Failed to share or join activity')
            return

        bus_name, conn_path, channel_paths =\
            self._shared_activity.get_channels()

        # Work out what our room is called and whether we have Tubes already
        room = None
        tubes_chan = None
        text_chan = None
        for channel_path in channel_paths:
            channel = telepathy.client.Channel(bus_name, channel_path)
            htype, handle = channel.GetHandle()
            if htype == telepathy.HANDLE_TYPE_ROOM:
                self._logger.debug('Found our room: it has handle#%d "%s"',
                    handle, self.conn.InspectHandles(htype, [handle])[0])
                room = handle
                ctype = channel.GetChannelType()
                if ctype == telepathy.CHANNEL_TYPE_TUBES:
                    self._logger.debug('Found our Tubes channel at %s', channel_path)
                    tubes_chan = channel
                elif ctype == telepathy.CHANNEL_TYPE_TEXT:
                    self._logger.debug('Found our Text channel at %s', channel_path)
                    text_chan = channel

        if room is None:
            self._logger.error("Presence service didn't create a room")
            return
        if text_chan is None:
            self._logger.error("Presence service didn't create a text channel")
            return

        # Make sure we have a Tubes channel - PS doesn't yet provide one
        if tubes_chan is None:
            self._logger.debug("Didn't find our Tubes channel, requesting one...")
            tubes_chan = self.conn.request_channel(telepathy.CHANNEL_TYPE_TUBES,
                telepathy.HANDLE_TYPE_ROOM, room, True)

        self.tubes_chan = tubes_chan
        self.text_chan = text_chan

        tubes_chan[telepathy.CHANNEL_TYPE_TUBES].connect_to_signal('NewTube',
            self._new_tube_cb)

    def _list_tubes_reply_cb(self, tubes):
        for tube_info in tubes:
            self._new_tube_cb(*tube_info)

    def _list_tubes_error_cb(self, e):
        self._logger.error('ListTubes() failed: %s', e)

    def _joined_cb(self, activity):
        if not self._shared_activity:
            return

        # Find out who's already in the shared activity:
        for buddy in self._shared_activity.get_joined_buddies():
            self._logger.debug('Buddy %s is already in the activity' % buddy.props.nick)

        self._logger.debug('Joined an existing shared activity')
        self.initiating = False
        self._setup()

        self._logger.debug('This is not my activity: waiting for a tube...')
        self.tubes_chan[telepathy.CHANNEL_TYPE_TUBES].ListTubes(
            reply_handler=self._list_tubes_reply_cb,
            error_handler=self._list_tubes_error_cb)

    def _new_tube_cb(self, _id, initiator, type, service, params, state):
        self._logger.debug('New tube: ID=%d initator=%d type=%d service=%s '
                     'params=%r state=%d', _id, initiator, type, service,
                     params, state)

        if (type == telepathy.TUBE_TYPE_DBUS and
            service == SERVICE):
            if state == telepathy.TUBE_STATE_LOCAL_PENDING:
                self.tubes_chan[telepathy.CHANNEL_TYPE_TUBES].AcceptDBusTube(_id)

            tube_conn = TubeConnection(self.conn,
                self.tubes_chan[telepathy.CHANNEL_TYPE_TUBES],
                _id, group_iface=self.text_chan[telepathy.CHANNEL_INTERFACE_GROUP])
            self.hellotube = HelloTube(tube_conn, self.initiating, self._get_buddy)

    def _buddy_joined_cb (self, activity, buddy):
        self._logger.debug('Buddy %s joined' % buddy.props.nick)

    def _buddy_left_cb (self, activity, buddy):
        self._logger.debug('Buddy %s left' % buddy.props.nick)

    def _get_buddy(self, cs_handle):
        """Get a Buddy from a channel specific handle."""
        self._logger.debug('Trying to find owner of handle %u...', cs_handle)
        group = self.text_chan[telepathy.CHANNEL_INTERFACE_GROUP]
        my_csh = group.GetSelfHandle()
        self._logger.debug('My handle in that group is %u', my_csh)
        if my_csh == cs_handle:
            handle = self.conn.GetSelfHandle()
            self._logger.debug('CS handle %u belongs to me, %u', cs_handle, handle)
        elif group.GetGroupFlags() & telepathy.CHANNEL_GROUP_FLAG_CHANNEL_SPECIFIC_HANDLES:
            handle = group.GetHandleOwners([cs_handle])[0]
            self._logger.debug('CS handle %u belongs to %u', cs_handle, handle)
        else:
            handle = cs_handle
            self._logger.debug('non-CS handle %u belongs to itself', handle)

            # XXX: deal with failure to get the handle owner
            assert handle != 0

        # XXX: we're assuming that we have Buddy objects for all contacts -
        # this might break when the server becomes scalable.
        return self.pservice.get_buddy_by_telepathy_handle(self.tp_conn_name,
                self.tp_conn_path, handle)

class HelloTube(ExportedGObject):
    """The bit that talks over the TUBES!!!"""

    def __init__(self, tube, is_initiator, get_buddy):
        super(HelloTube, self).__init__(tube, PATH)
        self._logger = logging.getLogger('pippy-activity.HelloTube')
        self.tube = tube
        self.is_initiator = is_initiator
        self.entered = False  # Have we set up the tube?
        self.helloworld = False  # Have we said Hello and received World?
        self._get_buddy = get_buddy  # Converts handle to Buddy object

        self.ordered_bus_names = []

        self.tube.watch_participants(self.participant_change_cb)

    def participant_change_cb(self, added, removed):
        self._logger.debug('Adding participants: %r' % added)
        self._logger.debug('Removing participants: %r' % type(removed))

        for handle, bus_name in added:
            buddy = self._get_buddy(handle)
            if buddy is not None:
                self._logger.debug('Buddy %s was added' % buddy.props.nick)

        for handle in removed:
            buddy = self._get_buddy(handle)
            if buddy is not None:
                self._logger.debug('Buddy %s was removed' % buddy.props.nick)
            try:
                self.ordered_bus_names.remove(self.tube.participants[handle])
            except ValueError:
                # already absent
                pass

        if not self.entered:
            #self.tube.add_signal_receiver(self.insert_cb, 'Insert', IFACE,
            #    path=PATH, sender_keyword='sender')
            if self.is_initiator:
                self._logger.debug("I'm initiating the tube, will "
                    "watch for hellos.")
                self.add_hello_handler()
                self.ordered_bus_names = [self.tube.get_unique_name()]
            else:
                self._logger.debug('Hello, everyone! What did I miss?')
                self.Hello()
        self.entered = True

    @signal(dbus_interface=IFACE, signature='')
    def Hello(self):
        """Say Hello to whoever else is in the tube."""
        self._logger.debug('I said Hello.')

    @method(dbus_interface=IFACE, in_signature='as', out_signature='')
    def World(self, bus_names):
        """To be called on the incoming XO after they Hello."""
        if not 1 or self.helloworld:  # XXX remove 1
            self._logger.debug('Somebody said World.')
            self.ordered_bus_names = bus_names
            # now I can World others
            self.add_hello_handler()

            #buddy = self._get_buddy(self.tube.bus_name_to_handle[bus_names[0]])
        else:
            self._logger.debug("I've already been welcomed, doing nothing")

    def add_hello_handler(self):
        self._logger.debug('Adding hello handler.')
        self.tube.add_signal_receiver(self.hello_cb, 'Hello', IFACE,
            path=PATH, sender_keyword='sender')

    def hello_cb(self, sender=None):
        """Somebody Helloed me. World them."""
        self._logger.debug('Newcomer %s has joined', sender)
        self.ordered_bus_names.append(sender)
        self._logger.debug('Bus names are now: %r', self.ordered_bus_names)
        self._logger.debug('Welcoming newcomer and sending them the game state')
        self.tube.get_object(sender, PATH).World(self.ordered_bus_names,
                                                 dbus_interface=IFACE)


