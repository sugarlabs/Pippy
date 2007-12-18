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

from activity import ViewSourceActivity
from sugar.activity.activity import ActivityToolbox, \
     get_bundle_path, get_bundle_name
from sugar.presence import presenceservice


SERVICE = "org.laptop.Pippy"
IFACE = SERVICE
PATH = "/org/laptop/Pippy"

class PippyActivity(ViewSourceActivity):
    """Pippy Activity as specified in activity.info"""
    def __init__(self, handle):
        """Set up the Pippy activity."""
        super(PippyActivity, self).__init__(handle)
        self._logger = logging.getLogger('pippy-activity')

        # Top toolbar with share and close buttons:
        toolbox = ActivityToolbox(self)
        # add 'make bundle' entry to 'keep' palette.
        palette = toolbox.get_activity_toolbar().keep.get_palette()
        # XXX: should clear out old palette entries?
        from sugar.graphics.menuitem import MenuItem
        from sugar.graphics.icon import Icon
        menu_item = MenuItem(_('As Pippy Document'))
        menu_item.set_image(Icon(file=('%s/activity/activity-icon.svg' % get_bundle_path()), icon_size=gtk.ICON_SIZE_MENU))
        menu_item.connect('activate', self.keepbutton_cb)
        palette.menu.append(menu_item)
        menu_item.show()
        menu_item = MenuItem(_('As Activity Bundle'))
        menu_item.set_image(Icon(file=('%s/activity/activity-default.svg' % get_bundle_path()), icon_size=gtk.ICON_SIZE_MENU))
        menu_item.connect('activate', self.makebutton_cb)
        palette.menu.append(menu_item)
        menu_item.show()
        self.set_toolbox(toolbox)
        toolbox.show()

        # Main layout.
        hbox = gtk.HBox()
        vbox = gtk.VBox()
        
        # The sidebar.
        sidebar = gtk.VBox()
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
        sidebar.pack_start(scrolled)
        hbox.pack_start(sidebar)

        root = os.path.join(get_bundle_path(), 'data')
        for d in sorted(os.listdir(root)):
            if not os.path.isdir(os.path.join(root,d)): continue #skip non-dirs
            direntry = { "name": _(d.capitalize()),
                         "path": os.path.join(root,d) + "/" }
            olditer = self.model.insert_before(None, None)
            self.model.set_value(olditer, 0, direntry)
            self.model.set_value(olditer, 1, direntry["name"])
                
            for _file in sorted(os.listdir(os.path.join(root, d))):
                if _file.endswith('~'): continue # skip emacs backups
                entry = { "name": _(_file.capitalize()),
                          "path": os.path.join(root, d, _file) }
                _iter = self.model.insert_before(olditer, None)
                self.model.set_value(_iter, 0, entry)
                self.model.set_value(_iter, 1, entry["name"])

        treeview.expand_all()

        # Source buffer
        import gtksourceview2
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
        goicon = gtk.Image()
        goicon.set_from_stock(gtk.STOCK_YES, gtk.ICON_SIZE_BUTTON)
        gobutton = gtk.Button(label=_("Run!"))
        gobutton.set_image(goicon)
        gobutton.connect('clicked', self.gobutton_cb)
        gobutton.set_size_request(650, 2)
        buttonhbox.pack_start(gobutton)

        # The "stop" button
        stopbutton = gtk.Button(stock=gtk.STOCK_STOP)
        stopbutton.connect('clicked', self.stopbutton_cb)
        stopbutton.set_size_request(200, 2)
        buttonhbox.pack_start(stopbutton)

        # The "clear" button
        clearbutton = gtk.Button(stock=gtk.STOCK_CLEAR)
        clearbutton.connect('clicked', self.clearbutton_cb)
        clearbutton.set_size_request(150, 2)
        buttonhbox.pack_end(clearbutton)

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
        self._vte.connect('child_exited', self.child_exited_cb)
        self._child_exited_handler = None
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
        self.metadata['title'] = value['name']
        self.stopbutton_cb(None)
        self._reset_vte()
        self.text_view.grab_focus()
        
    def clearbutton_cb(self, button):
        self.save()
        self.text_buffer.set_text("")
        self.metadata['title'] = _('%s Activity') % get_bundle_name()
        self.stopbutton_cb(None)
        self._reset_vte()
        self.text_view.grab_focus()

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
        self.stopbutton_cb(button) # try stopping old code first.
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
        try:
            os.kill(self._pid, SIGTERM)
        except:
            pass # process must already be dead.

    def keepbutton_cb(self, __):
        self.copy()

    def makebutton_cb(self, __):
        from shutil import copytree, copy2, rmtree
        from tempfile import mkdtemp
        # get the name of this pippy program.
        title = self.metadata['title']
        if title == 'Pippy Activity':
            from sugar.graphics.alert import Alert
            from sugar.graphics.icon import Icon
            alert = Alert()
            alert.props.title =_ ('Save as Activity Error')
            alert.props.msg = _('Please give your activity a meaningful name before attempting to save it as an activity.')
            ok_icon = Icon(icon_name='dialog-ok')
            alert.add_button(gtk.RESPONSE_OK, _('Ok'), ok_icon)
            alert.connect('response', self.dismiss_alert_cb)
            self.add_alert(alert)
            return
        self.stopbutton_cb(None) # try stopping old code first.
        self._reset_vte()
        self._vte.feed(_("Creating activity bundle..."))
        self._vte.feed("\r\n")
        app_temp = mkdtemp('.activity', 'Pippy',
                           '%s/tmp/' % self.get_activity_root())
        sourcefile = os.path.join(app_temp, 'xyzzy.py')
        # invoke ourself to build the activity bundle.
        try:
            # write out application code
            self._write_text_buffer(sourcefile)
            # hook up a callback for when the bundle builder is done.
            # we can't use gobject.child_watch_add because vte will reap our
            # children before we can.
            self._child_exited_handler = lambda: self.bundle_cb(title, app_temp)
            # invoke bundle builder
            self._pid = self._vte.fork_command \
                    (command="/usr/bin/python",
                     argv=["/usr/bin/python",
                           "%s/pippy_app.py" % get_bundle_path(),
                           '-p', '%s/library' % get_bundle_path(),
                           '-d', app_temp,
                           title, sourcefile],
                     directory=app_temp)
        except:
            rmtree(app_temp, ignore_errors=True) # clean up!
            raise

    def child_exited_cb(self, *args):
        """Called whenever a child exits.  If there's a handler, run it."""
        h, self._child_exited_handler = self._child_exited_handler, None
        if h is not None: h()

    def bundle_cb(self, title, app_temp):
        """Called when we're done building a bundle for a source file."""
        from sugar import profile
        from shutil import rmtree
        from sugar.datastore import datastore
        try:
            # find the .xo file: were we successful?
            bundle_file=[ f for f in os.listdir(app_temp) if f.endswith('.xo') ]
            if len(bundle_file) != 1:
                self._logger.debug("Couldn't find bundle: %s"%str(bundle_file))
                return # something went wrong.
            # hand off to journal
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
            jobject.file_path = os.path.join(app_temp, bundle_file[0])
            datastore.write(jobject)
            self._vte.feed("\r\n")
            self._vte.feed(_("Activity saved to journal."))
            self._vte.feed("\r\n")
            self.journal_show_object(jobject.object_id)
            jobject.destroy()
        finally:
            rmtree(app_temp, ignore_errors=True) # clean up!

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

            from sugar.presence.tubeconn import TubeConnection
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

############# TEMPLATES AND INLINE FILES ##############
ACTIVITY_INFO_TEMPLATE = """
[Activity]
name = %(title)s
bundle_id = %(bundle_id)s
service_name = %(bundle_id)s
class = %(class)s
icon = activity-icon
activity_version = %(version)d
mime_types = %(mime_types)s
show_launcher = yes
"""

PIPPY_ICON = \
"""<?xml version="1.0" ?><!DOCTYPE svg  PUBLIC '-//W3C//DTD SVG 1.1//EN'  'http://www.w3.org/Graphics/SVG/1.1/DTD/svg11.dtd' [
	<!ENTITY stroke_color "#010101">
	<!ENTITY fill_color "#FFFFFF">
]><svg enable-background="new 0 0 55 55" height="55px" version="1.1" viewBox="0 0 55 55" width="55px" x="0px" xml:space="preserve" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" y="0px"><g display="block" id="activity-pippy">
	<path d="M28.497,48.507   c5.988,0,14.88-2.838,14.88-11.185c0-9.285-7.743-10.143-10.954-11.083c-3.549-0.799-5.913-1.914-6.055-3.455   c-0.243-2.642,1.158-3.671,3.946-3.671c0,0,6.632,3.664,12.266,0.74c1.588-0.823,4.432-4.668,4.432-7.32   c0-2.653-9.181-5.719-11.967-5.719c-2.788,0-5.159,3.847-5.159,3.847c-5.574,0-11.149,5.306-11.149,10.612   c0,5.305,5.333,9.455,11.707,10.612c2.963,0.469,5.441,2.22,4.878,5.438c-0.457,2.613-2.995,5.306-8.361,5.306   c-4.252,0-13.3-0.219-14.745-4.079c-0.929-2.486,0.168-5.205,1.562-5.205l-0.027-0.16c-1.42-0.158-5.548,0.16-5.548,5.465   C8.202,45.452,17.347,48.507,28.497,48.507z" fill="&fill_color;" stroke="&stroke_color;" stroke-linecap="round" stroke-linejoin="round" stroke-width="3.5"/>
	<path d="M42.579,19.854c-2.623-0.287-6.611-2-7.467-5.022" fill="none" stroke="&stroke_color;" stroke-linecap="round" stroke-width="3"/>
	<circle cx="35.805" cy="10.96" fill="&stroke_color;" r="1.676"/>
</g></svg><!-- " -->
"""

PIPPY_DEFAULT_ICON = \
"""<?xml version="1.0" ?><!DOCTYPE svg  PUBLIC '-//W3C//DTD SVG 1.1//EN'  'http://www.w3.org/Graphics/SVG/1.1/DTD/svg11.dtd' [
	<!ENTITY stroke_color "#010101">
	<!ENTITY fill_color "#FFFFFF">
]><svg enable-background="new 0 0 55 55" height="55px" version="1.1"
     viewBox="0 0 55 55" width="55px" x="0px" y="0px" xml:space="preserve"
     xmlns="http://www.w3.org/2000/svg"
     xmlns:xlink="http://www.w3.org/1999/xlink"
><g display="block" id="activity-icon"><path
       d="M 28.497,48.507 C 34.485,48.507 43.377,45.669 43.377,37.322 C 43.377,32.6795 41.44125,30.14375 39.104125,28.651125 C 36.767,27.1585 38.482419,26.816027 39.758087,25.662766 C 39.42248,24.275242 37.206195,22.826987 36.262179,21.037968 C 34.005473,20.582994 27.526,19.113 30.314,19.113 C 30.314,19.113 36.946,22.777 42.58,19.853 C 44.168,19.03 47.012,15.185 47.012,12.533 C 47.012,9.88 37.831,6.814 35.045,6.814 C 32.257,6.814 29.886,10.661 29.886,10.661 C 24.312,10.661 12.043878,16.258005 12.043878,21.564005 C 12.043878,24.216505 16.585399,30.069973 19.144694,33.736352 C 22.438716,38.455279 27.257,31.3065 30.444,31.885 C 33.407,32.354 35.885,34.105 35.322,37.323 C 34.865,39.936 32.327,42.629 26.961,42.629 C 22.709,42.629 13.661,42.41 12.216,38.55 C 11.287,36.064 12.384,33.345 13.778,33.345 L 13.751,33.185 C 12.331,33.027 8.203,33.345 8.203,38.65 C 8.202,45.452 17.347,48.507 28.497,48.507 z "
 fill="&fill_color;" stroke="&stroke_color;" stroke-linecap="round" stroke-linejoin="round" stroke-width="3.5" />
	<path d="M42.579,19.854c-2.623-0.287-6.611-2-7.467-5.022" fill="none" stroke="&stroke_color;" stroke-linecap="round" stroke-width="3"/>
	<circle cx="35.805" cy="10.96" fill="&stroke_color;" r="1.676"/>
</g></svg><!-- " -->
"""

############# ACTIVITY META-INFORMATION ###############
# this is used by Pippy to generate a bundle for itself.

def pippy_activity_version():
    """Returns the version number of the generated activity bundle."""
    return 14
def pippy_activity_extrafiles():
    """Returns a map of 'extra' files which should be included in the
    generated activity bundle."""
    # Cheat here and generate the map from the fs contents.
    extra = {}
    bp = get_bundle_path()
    for d in [ 'po', 'data' ]: # everybody gets library already
        for root, dirs, files in os.walk(os.path.join(bp, d)):
            for name in files:
                fn = os.path.join(root, name).replace(bp+'/', '')
                extra[fn] = open(os.path.join(root, name), 'r').read()
    extra['activity/activity-default.svg'] = PIPPY_DEFAULT_ICON
    return extra
def pippy_activity_news():
    """Return the NEWS file for this activity."""
    # Cheat again.
    return open(os.path.join(get_bundle_path(), 'NEWS')).read()
def pippy_activity_icon():
    """Return an SVG document specifying the icon for this activity."""
    return PIPPY_ICON
def pippy_activity_class():
    """Return the class which should be started to run this activity."""
    return 'pippy_app.PippyActivity'
def pippy_activity_bundle_id():
    """Return the bundle_id for the generated activity."""
    return 'org.laptop.Pippy'
def pippy_activity_mime_types():
    """Return the mime types handled by the generated activity, as a list."""
    return 'text/x-python'

################# ACTIVITY BUNDLER ################

def main():
    """Create a bundle from a pippy-style source file"""
    from optparse import OptionParser
    from pyclbr import readmodule_ex
    from tempfile import mkdtemp
    from shutil import copytree, copy2, rmtree
    from sugar import profile
    from sugar.activity import bundlebuilder
    import sys
    parser = OptionParser(usage='%prog [options] [title] [sourcefile]')
    parser.add_option('-d', '--dir', dest='dir',default='.',metavar='DIR',
                      help='Put generated bundle in the specified directory.')
    parser.add_option('-p', '--pythonpath', dest='path', action='append',
                      default=[], metavar='DIR',
                      help='Append directory to python search path.')
    (options, args) = parser.parse_args()
    if len(args) != 2:
        parser.error('The title and sourcefile arguments are required.')
    title = args[0]
    sourcefile = args[1]
    pytitle = re.sub(r'[^A-Za-z0-9_]', '', title)
    if re.match(r'[0-9]', pytitle) is not None:
        pytitle = '_' + pytitle # first character cannot be numeric
    # first take a gander at the source file and see if it's got extra info
    # for us.
    sourcedir, basename = os.path.split(sourcefile)
    if not sourcedir: sourcedir = '.'
    module, ext = os.path.splitext(basename)
    # things we look for:
    bundle_info = {
        'version': 1,
        'extrafiles': {},
        'news': 'No news.',
        'icon': PIPPY_DEFAULT_ICON,
        'class': 'activity.VteActivity',
        'bundle_id': ('org.laptop.pippy.%s' % pytitle),
        'mime_types': '',
        }
    # are any of these things in the module?
    try_import = False
    info = readmodule_ex(module, [ sourcedir ] + options.path)
    for func in bundle_info.keys():
        p_a_func = 'pippy_activity_%s' % func
        if p_a_func in info: try_import = True
    if try_import:
        # yes, let's try to execute them to get better info about our bundle
        oldpath = list(sys.path)
        sys.path[0:0] = [ sourcedir ] + options.path
        modobj = __import__(module)
        for func in bundle_info.keys():
            p_a_func = 'pippy_activity_%s' % func
            if p_a_func in modobj.__dict__:
                bundle_info[func] = modobj.__dict__[p_a_func]()
        sys.path = oldpath

    # okay!  We've done the hard part.  Now let's build a bundle.
    # create a new temp dir in which to create the bundle.
    app_temp = mkdtemp('.activity', 'Pippy') # hope TMPDIR is set correctly!
    bundle = get_bundle_path()
    try:
        copytree('%s/library' % bundle, '%s/library' % app_temp)
        copy2('%s/activity.py' % bundle, '%s/activity.py' % app_temp)
        # create activity.info file.
        bundle_info['title'] = title
        bundle_info['pytitle'] = pytitle
        # put 'extra' files in place.
        extrafiles = {
            'activity/activity.info': ACTIVITY_INFO_TEMPLATE % bundle_info,
            'activity/activity-icon.svg': bundle_info['icon'],
            'NEWS': bundle_info['news'],
            }
        extrafiles.update(bundle_info['extrafiles'])
        for path, contents in extrafiles.items():
            # safety first!
            assert '..' not in path
            dirname, filename = os.path.split(path)
            dirname = os.path.join(app_temp, dirname)
            if not os.path.exists(dirname): os.makedirs(dirname)
            with open(os.path.join(dirname, filename), 'w') as f:
                f.write(contents)
        # put script into $app_temp/pippy_app.py
        copy2(sourcefile, '%s/pippy_app.py' % app_temp)
        # write MANIFEST file.
        with open('%s/MANIFEST' % app_temp, 'w') as f:
            for dirpath, dirnames, filenames in os.walk(app_temp):
                for name in filenames:
                    fn = os.path.join(dirpath, name).replace(app_temp+'/', '')
                    if fn=='MANIFEST': continue
                    f.write('%s\n' % fn)
        # invoke bundle builder
        olddir = os.getcwd()
        oldargv = sys.argv
        os.chdir(app_temp)
        sys.argv = [ 'setup.py', 'dist' ]
        bundlebuilder.start(pytitle)
        sys.argv = oldargv
        os.chdir(olddir)
        # move to destination directory.
        copy2('%s/%s-%d.xo' % (app_temp, pytitle, bundle_info['version']),
              '%s/%s-%d.xo' % (options.dir, pytitle, bundle_info['version']))
    finally:
        rmtree(app_temp, ignore_errors=True)

if __name__ == '__main__':
    from gettext import gettext as _
    import sys
    if False: # change this to True to test within Pippy
        sys.argv = sys.argv + [ '-d','/tmp','Pippy', '/home/olpc/pippy_app.py' ]
    #print _("Working..."),
    #sys.stdout.flush()
    main()
    #print _("done!")
    sys.exit(0)
