#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright (C) 2007,2008,2009 Chris Ball, based on Collabora's
# "hellomesh" demo.
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
import pango
import vte
import re
import os
import gobject
import time

from port.style import font_zoom
from signal import SIGTERM
from gettext import gettext as _

from sugar.activity import activity
from activity import ViewSourceActivity, TARGET_TYPE_TEXT
from sugar.activity.activity import ActivityToolbox, \
     EditToolbar, get_bundle_path, get_bundle_name
from sugar.graphics import style
from sugar.graphics.toolbutton import ToolButton

import groupthink.sugar_tools
import groupthink.gtk_tools

text_buffer = None
# magic prefix to use utf-8 source encoding
PYTHON_PREFIX = """#!/usr/bin/python
# -*- coding: utf-8 -*-
"""

OLD_TOOLBAR = False
try:
    from sugar.graphics.toolbarbox import ToolbarBox, ToolbarButton
    from sugar.activity.widgets import StopButton
except ImportError:
    OLD_TOOLBAR = True

# get screen sizes
SIZE_X = gtk.gdk.screen_width()
SIZE_Y = gtk.gdk.screen_height()

groupthink_mimetype = 'pickle/groupthink-pippy'


class PippyActivity(ViewSourceActivity, groupthink.sugar_tools.GroupActivity):
    """Pippy Activity as specified in activity.info"""
    def early_setup(self):
        global text_buffer
        import gtksourceview2
        text_buffer = gtksourceview2.Buffer()

    def initialize_display(self):
        self._logger = logging.getLogger('pippy-activity')

        # Top toolbar with share and close buttons:

        if OLD_TOOLBAR:
            activity_toolbar = self.toolbox.get_activity_toolbar()
        else:
            activity_toolbar = self.activity_button.page

        # add 'make bundle' entry to 'keep' palette.
        palette = activity_toolbar.keep.get_palette()
        # XXX: should clear out old palette entries?
        from sugar.graphics.menuitem import MenuItem
        from sugar.graphics.icon import Icon
        menu_item = MenuItem(_('As Pippy Document'))
        menu_item.set_image(Icon(file=('%s/activity/activity-icon.svg' %
                                       get_bundle_path()),
                                 icon_size=gtk.ICON_SIZE_MENU))
        menu_item.connect('activate', self.keepbutton_cb)
        palette.menu.append(menu_item)
        menu_item.show()
        menu_item = MenuItem(_('As Activity Bundle'))
        menu_item.set_image(Icon(file=('%s/activity/activity-default.svg' %
                                       get_bundle_path()),
                                 icon_size=gtk.ICON_SIZE_MENU))
        menu_item.connect('activate', self.makebutton_cb)
        palette.menu.append(menu_item)
        menu_item.show()

        self._edit_toolbar = activity.EditToolbar()

        if OLD_TOOLBAR:
            activity_toolbar = gtk.Toolbar()
            self.toolbox.add_toolbar(_('Actions'), activity_toolbar)
            self.toolbox.set_current_toolbar(1)
            self.toolbox.add_toolbar(_('Edit'), self._edit_toolbar)
        else:
            edit_toolbar_button = ToolbarButton()
            edit_toolbar_button.set_page(self._edit_toolbar)
            edit_toolbar_button.props.icon_name = 'toolbar-edit'
            edit_toolbar_button.props.label = _('Edit')
            self.get_toolbar_box().toolbar.insert(edit_toolbar_button, -1)

        self._edit_toolbar.show()

        self._edit_toolbar.undo.connect('clicked', self.__undobutton_cb)
        self._edit_toolbar.redo.connect('clicked', self.__redobutton_cb)
        self._edit_toolbar.copy.connect('clicked', self.__copybutton_cb)
        self._edit_toolbar.paste.connect('clicked', self.__pastebutton_cb)

        if OLD_TOOLBAR:
            actions_toolbar = activity_toolbar
        else:
            actions_toolbar = self.get_toolbar_box().toolbar

        # The "go" button
        goicon_bw = gtk.Image()
        goicon_bw.set_from_file("%s/icons/run_bw.svg" % os.getcwd())
        goicon_color = gtk.Image()
        goicon_color.set_from_file("%s/icons/run_color.svg" % os.getcwd())
        gobutton = ToolButton(label=_("_Run!"))
        gobutton.props.accelerator = _('<alt>r')
        gobutton.set_icon_widget(goicon_bw)
        gobutton.set_tooltip("Run")
        gobutton.connect('clicked', self.flash_cb, dict({'bw': goicon_bw,
            'color': goicon_color}))
        gobutton.connect('clicked', self.gobutton_cb)
        actions_toolbar.insert(gobutton, -1)

        # The "stop" button
        stopicon_bw = gtk.Image()
        stopicon_bw.set_from_file("%s/icons/stopit_bw.svg" % os.getcwd())
        stopicon_color = gtk.Image()
        stopicon_color.set_from_file("%s/icons/stopit_color.svg" % os.getcwd())
        stopbutton = ToolButton(label=_("_Stop"))
        stopbutton.props.accelerator = _('<alt>s')
        stopbutton.set_icon_widget(stopicon_bw)
        stopbutton.connect('clicked', self.flash_cb, dict({'bw': stopicon_bw,
            'color': stopicon_color}))
        stopbutton.connect('clicked', self.stopbutton_cb)
        stopbutton.set_tooltip("Stop Running")
        actions_toolbar.insert(stopbutton, -1)

        # The "clear" button
        clearicon_bw = gtk.Image()
        clearicon_bw.set_from_file("%s/icons/eraser_bw.svg" % os.getcwd())
        clearicon_color = gtk.Image()
        clearicon_color.set_from_file("%s/icons/eraser_color.svg" %
                                      os.getcwd())
        clearbutton = ToolButton(label=_("_Clear"))
        clearbutton.props.accelerator = _('<alt>c')
        clearbutton.set_icon_widget(clearicon_bw)
        clearbutton.connect('clicked', self.clearbutton_cb)
        clearbutton.connect('clicked', self.flash_cb, dict({'bw': clearicon_bw,
            'color': clearicon_color}))
        clearbutton.set_tooltip("Clear")
        actions_toolbar.insert(clearbutton, -1)

        activity_toolbar.show()

        if not OLD_TOOLBAR:
            separator = gtk.SeparatorToolItem()
            separator.props.draw = False
            separator.set_expand(True)
            self.get_toolbar_box().toolbar.insert(separator, -1)
            separator.show()

            stop = StopButton(self)
            self.get_toolbar_box().toolbar.insert(stop, -1)

        # Main layout.
        self.hpane = gtk.HPaned()
        self.vpane = gtk.VPaned()

        # The sidebar.
        self.sidebar = gtk.VBox()
        self.model = gtk.TreeStore(gobject.TYPE_PYOBJECT, gobject.TYPE_STRING)
        treeview = gtk.TreeView(self.model)
        cellrenderer = gtk.CellRendererText()
        treecolumn = gtk.TreeViewColumn(_("Examples"), cellrenderer, text=1)
        treeview.get_selection().connect("changed", self.selection_cb)
        treeview.append_column(treecolumn)
        treeview.set_size_request(int(SIZE_X * 0.3), SIZE_Y)

        # Create scrollbars around the view.
        scrolled = gtk.ScrolledWindow()
        scrolled.add(treeview)
        self.sidebar.pack_start(scrolled)
        self.hpane.add1(self.sidebar)

        root = os.path.join(get_bundle_path(), 'data')
        for d in sorted(os.listdir(root)):
            if not os.path.isdir(os.path.join(root, d)):
                continue  # skip non-dirs
            direntry = {"name": _(d.capitalize()),
                        "path": os.path.join(root, d) + "/"}
            olditer = self.model.insert_before(None, None)
            self.model.set_value(olditer, 0, direntry)
            self.model.set_value(olditer, 1, direntry["name"])

            for _file in sorted(os.listdir(os.path.join(root, d))):
                if _file.endswith('~'):
                    continue  # skip emacs backups
                entry = {"name": _(_file.capitalize()),
                         "path": os.path.join(root, d, _file)}
                _iter = self.model.insert_before(olditer, None)
                self.model.set_value(_iter, 0, entry)
                self.model.set_value(_iter, 1, entry["name"])

        treeview.expand_all()

        # Source buffer
        import gtksourceview2
        global text_buffer
        lang_manager = gtksourceview2.language_manager_get_default()
        if hasattr(lang_manager, 'list_languages'):
            langs = lang_manager.list_languages()
        else:
            lang_ids = lang_manager.get_language_ids()
            langs = [lang_manager.get_language(lang_id)
                     for lang_id in lang_ids]
        for lang in langs:
            for m in lang.get_mime_types():
                if m == "text/x-python":
                    text_buffer.set_language(lang)

        if hasattr(text_buffer, 'set_highlight'):
            text_buffer.set_highlight(True)
        else:
            text_buffer.set_highlight_syntax(True)

        # The GTK source view window
        self.text_view = gtksourceview2.View(text_buffer)
        self.text_view.set_size_request(0, int(SIZE_Y * 0.5))
        self.text_view.set_editable(True)
        self.text_view.set_cursor_visible(True)
        self.text_view.set_show_line_numbers(True)
        self.text_view.set_wrap_mode(gtk.WRAP_CHAR)
        self.text_view.set_insert_spaces_instead_of_tabs(True)
        self.text_view.set_tab_width(2)
        self.text_view.set_auto_indent(True)
        self.text_view.modify_font(pango.FontDescription("Monospace " +
            str(font_zoom(style.FONT_SIZE))))

        # We could change the color theme here, if we want to.
        #mgr = gtksourceview2.style_manager_get_default()
        #style_scheme = mgr.get_scheme('kate')
        #self.text_buffer.set_style_scheme(style_scheme)

        codesw = gtk.ScrolledWindow()
        codesw.set_policy(gtk.POLICY_AUTOMATIC,
                      gtk.POLICY_AUTOMATIC)
        codesw.add(self.text_view)
        self.vpane.add1(codesw)

        # An hbox to hold the vte window and its scrollbar.
        outbox = gtk.HBox()

        # The vte python window
        self._vte = vte.Terminal()
        self._vte.set_encoding('utf-8')
        self._vte.set_size(30, 5)
        font = 'Monospace ' + str(font_zoom(style.FONT_SIZE))
        self._vte.set_font(pango.FontDescription(font))
        self._vte.set_colors(gtk.gdk.color_parse('#000000'),
                             gtk.gdk.color_parse('#E7E7E7'),
                             [])
        self._vte.connect('child_exited', self.child_exited_cb)
        self._child_exited_handler = None
        self._vte.drag_dest_set(gtk.DEST_DEFAULT_ALL,
                                [("text/plain", 0, TARGET_TYPE_TEXT)],
                                gtk.gdk.ACTION_COPY)
        self._vte.connect('drag_data_received', self.vte_drop_cb)
        outbox.pack_start(self._vte)

        outsb = gtk.VScrollbar(self._vte.get_adjustment())
        outsb.show()
        outbox.pack_start(outsb, False, False, 0)
        self.vpane.add2(outbox)
        self.hpane.add2(self.vpane)
        return self.hpane

    def when_shared(self):
        self.hpane.remove(self.hpane.get_child1())
        global text_buffer
        self.cloud.sharefield = \
            groupthink.gtk_tools.TextBufferSharePoint(text_buffer)
        # HACK : There are issues with undo/redoing while in shared
        # mode. So disable the 'undo' and 'redo' buttons when the activity
        # is shared.
        self._edit_toolbar.undo.set_sensitive(False)
        self._edit_toolbar.redo.set_sensitive(False)

    def vte_drop_cb(self, widget, context, x, y, selection, targetType, time):
        if targetType == TARGET_TYPE_TEXT:
            self._vte.feed_child(selection.data)

    def selection_cb(self, column):
        self.save()
        model, _iter = column.get_selected()
        value = model.get_value(_iter, 0)
        self._logger.debug("clicked! %s" % value['path'])
        _file = open(value['path'], 'r')
        lines = _file.readlines()
        global text_buffer
        text_buffer.set_text("".join(lines))
        self.metadata['title'] = value['name']
        self.stopbutton_cb(None)
        self._reset_vte()
        self.text_view.grab_focus()

    def timer_cb(self, button, icons):
        button.set_icon_widget(icons['bw'])
        button.show_all()
        return False

    def flash_cb(self, button, icons):
        button.set_icon_widget(icons['color'])
        button.show_all()
        gobject.timeout_add(400, self.timer_cb, button, icons)

    def clearbutton_cb(self, button):
        self.save()
        global text_buffer
        text_buffer.set_text("")
        self.metadata['title'] = _('%s Activity') % get_bundle_name()
        self.stopbutton_cb(None)
        self._reset_vte()
        self.text_view.grab_focus()

    def _write_text_buffer(self, filename):
        global text_buffer
        start, end = text_buffer.get_bounds()
        text = text_buffer.get_text(start, end)

        with open(filename, 'w') as f:
            # write utf-8 coding prefix if there's not already one
            if re.match(r'coding[:=]\s*([-\w.]+)',
                        '\n'.join(text.splitlines()[:2])) is None:
                f.write(PYTHON_PREFIX)
            for line in text:
                f.write(line)

    def _reset_vte(self):
        self._vte.grab_focus()
        self._vte.feed("\x1B[H\x1B[J\x1B[0;39m")

    def __undobutton_cb(self, button):
        global text_buffer
        if text_buffer.can_undo():
            text_buffer.undo()

    def __redobutton_cb(self, button):
        global text_buffer
        if text_buffer.can_redo():
            text_buffer.redo()

    def __copybutton_cb(self, button):
        global text_buffer
        text_buffer.copy_clipboard(gtk.Clipboard())

    def __pastebutton_cb(self, button):
        global text_buffer
        text_buffer.paste_clipboard(gtk.Clipboard(), None, True)

    def gobutton_cb(self, button):
        from shutil import copy2
        self.stopbutton_cb(button)  # try stopping old code first.
        self._reset_vte()

        # FIXME: We're losing an odd race here
        # gtk.main_iteration(block=False)

        pippy_app_name = '%s/tmp/pippy_app.py' % self.get_activity_root()
        self._write_text_buffer(pippy_app_name)
        # write activity.py here too, to support pippy-based activities.
        copy2('%s/activity.py' % get_bundle_path(),
              '%s/tmp/activity.py' % self.get_activity_root())

        self._pid = self._vte.fork_command(
            command="/bin/sh",
            argv=["/bin/sh", "-c",
                  "python %s; sleep 1" % pippy_app_name],
            envv=["PYTHONPATH=%s/library:%s" % (get_bundle_path(),
                                                os.getenv("PYTHONPATH", ""))],
            directory=get_bundle_path())

    def stopbutton_cb(self, button):
        try:
            os.kill(self._pid, SIGTERM)
        except:
            pass  # process must already be dead.

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
            alert.props.title = _('Save as Activity Error')
            alert.props.msg = _('Please give your activity a meaningful name '
                                'before attempting to save it as an activity.')
            ok_icon = Icon(icon_name='dialog-ok')
            alert.add_button(gtk.RESPONSE_OK, _('Ok'), ok_icon)
            alert.connect('response', self.dismiss_alert_cb)
            self.add_alert(alert)
            return
        self.stopbutton_cb(None)  # try stopping old code first.
        self._reset_vte()
        self._vte.feed(_("Creating activity bundle..."))
        self._vte.feed("\r\n")
        TMPDIR = 'instance'  # XXX: should be 'tmp', once trac #1731 is fixed.
        app_temp = mkdtemp('.activity', 'Pippy',
                           os.path.join(self.get_activity_root(), TMPDIR))
        sourcefile = os.path.join(app_temp, 'xyzzy.py')
        # invoke ourself to build the activity bundle.
        try:
            # write out application code
            self._write_text_buffer(sourcefile)
            # hook up a callback for when the bundle builder is done.
            # we can't use gobject.child_watch_add because vte will reap our
            # children before we can.
            self._child_exited_handler = \
                lambda: self.bundle_cb(title, app_temp)
            # invoke bundle builder
            self._pid = self._vte.fork_command(
                command="/usr/bin/python",
                argv=["/usr/bin/python",
                      "%s/pippy_app.py" % get_bundle_path(),
                      '-p', '%s/library' % get_bundle_path(),
                      '-d', app_temp,
                      title, sourcefile],
                directory=app_temp)
        except:
            rmtree(app_temp, ignore_errors=True)  # clean up!
            raise

    def child_exited_cb(self, *args):
        """Called whenever a child exits.  If there's a handler, run it."""
        h, self._child_exited_handler = self._child_exited_handler, None
        if h is not None:
            h()

    def bundle_cb(self, title, app_temp):
        """Called when we're done building a bundle for a source file."""
        from sugar import profile
        from shutil import rmtree
        from sugar.datastore import datastore
        try:
            # find the .xo file: were we successful?
            bundle_file = [f for f in os.listdir(app_temp) \
                           if f.endswith('.xo')]
            if len(bundle_file) != 1:
                self._logger.debug("Couldn't find bundle: %s" %
                                   str(bundle_file))
                return  # something went wrong.
            # hand off to journal
            os.chmod(app_temp, 0755)
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
                jobject.metadata[k] = v  # the dict.update method is missing =(
            jobject.file_path = os.path.join(app_temp, bundle_file[0])
            datastore.write(jobject)
            self._vte.feed("\r\n")
            self._vte.feed(_("Activity saved to journal."))
            self._vte.feed("\r\n")
            self.journal_show_object(jobject.object_id)
            jobject.destroy()
        finally:
            rmtree(app_temp, ignore_errors=True)  # clean up!

    def dismiss_alert_cb(self, alert, response_id):
        self.remove_alert(alert)

    def save_to_journal(self, file_path, cloudstring):
        _file = open(file_path, 'w')
        if not self._shared_activity:
            self.metadata['mime_type'] = 'text/x-python'
            global text_buffer
            start, end = text_buffer.get_bounds()
            text = text_buffer.get_text(start, end)
            _file.write(text)
        else:
            self.metadata['mime_type'] = groupthink_mimetype
            _file.write(cloudstring)

    def load_from_journal(self, file_path):
        if self.metadata['mime_type'] == 'text/x-python':
            text = open(file_path).read()
            # discard the '#!/usr/bin/python' and 'coding: utf-8' lines,
            # if present
            text = re.sub(r'^' + re.escape(PYTHON_PREFIX), '', text)
            global text_buffer
            text_buffer.set_text(text)
        elif self.metadata['mime_type'] == groupthink_mimetype:
            return open(file_path).read()

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
%(extra_info)s
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
"""<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<!DOCTYPE svg PUBLIC "-//W3C//DTD SVG 1.1//EN" "http://www.w3.org/Graphics/SVG/1.1/DTD/svg11.dtd" [
        <!ENTITY ns_svg "http://www.w3.org/2000/svg">
        <!ENTITY ns_xlink "http://www.w3.org/1999/xlink">
        <!ENTITY stroke_color "#000000">
        <!ENTITY fill_color "#FFFFFF">
]><!--"-->
<svg  version="1.1" id="Pippy_activity" xmlns="&ns_svg;" xmlns:xlink="&ns_xlink;" width="47.585" height="49.326"
         viewBox="0 0 47.585 49.326" overflow="visible" enable-background="new 0 0 47.585 49.326" xml:space="preserve">

<path
   fill="&fill_color;" stroke="&stroke_color;" stroke-width="2"   d="M 30.689595,16.460324 L 24.320145,12.001708 L 2.7550028,23.830689 L 23.319231,38.662412 L 45.157349,26.742438 L 36.877062,21.100925"   id="path3195" />
<path
   fill="&fill_color;" stroke="&stroke_color;" stroke-width="2"
   nodetypes="cscscssscsssssccc"
   d="M 12.201296,21.930888 C 13.063838,20.435352 17.035411,18.617621 20.372026,18.965837 C 22.109464,19.147161 24.231003,20.786115 24.317406,21.584638 C 24.401593,22.43057 25.386617,24.647417 26.88611,24.600494 C 28.114098,24.562065 28.61488,23.562481 28.992123,22.444401 C 28.992123,22.444401 28.564434,17.493894 31.897757,15.363536 C 32.836646,14.763482 35.806711,14.411448 37.249047,15.221493 C 38.691382,16.031536 37.648261,19.495598 36.785717,20.991133 C 35.923174,22.48667 32.967872,24.980813 32.967872,24.980813 C 31.242783,27.971884 29.235995,28.5001 26.338769,28.187547 C 23.859153,27.920046 22.434219,26.128159 21.837191,24.708088 C 21.323835,23.487033 20.047743,22.524906 18.388178,22.52176 C 17.218719,22.519542 14.854476,23.017137 16.212763,25.620664 C 16.687174,26.53 18.919175,28.917592 21.08204,29.521929 C 22.919903,30.035455 26.713699,31.223552 30.30027,31.418089 C 26.770532,33.262079 21.760623,32.530604 18.909599,31.658168 C 17.361253,30.887002 9.0350995,26.651992 12.201296,21.930888 z "
   id="path2209" />
<path
   fill="&fill_color;" stroke="&stroke_color;" stroke-width="1"
   d="M 37.832194,18.895786 C 36.495131,19.851587 34.017797,22.097672 32.3528,21.069911"
   id="path2211"
   transform-center-y="-3.6171625"
   transform-center-x="-0.50601649" />
<circle
   fill="&stroke_color;" stroke="none" stroke-width="0"
   cx="33.926998"
   cy="6.073"
   r="1.927"
   id="circle2213"
   transform="matrix(0.269108,-0.4665976,-0.472839,-0.2655557,26.503175,35.608682)"
   />
</svg>
"""

############# ACTIVITY META-INFORMATION ###############
# this is used by Pippy to generate a bundle for itself.


def pippy_activity_version():
    """Returns the version number of the generated activity bundle."""
    return 39


def pippy_activity_extra_files():
    """Returns a map of 'extra' files which should be included in the
    generated activity bundle."""
    # Cheat here and generate the map from the fs contents.
    extra = {}
    bp = get_bundle_path()
    for d in ['po', 'data', 'groupthink', 'post']:  # everybody gets library
        for root, dirs, files in os.walk(os.path.join(bp, d)):
            for name in files:
                fn = os.path.join(root, name).replace(bp + '/', '')
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
    return ['text/x-python', groupthink_mimetype]


def pippy_activity_extra_info():
    return """
license = GPLv2+
update_url = http://activities.sugarlabs.org """

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
    parser.add_option('-d', '--dir', dest='dir', default='.', metavar='DIR',
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
        pytitle = '_' + pytitle  # first character cannot be numeric
    # first take a gander at the source file and see if it's got extra info
    # for us.
    sourcedir, basename = os.path.split(sourcefile)
    if not sourcedir:
        sourcedir = '.'
    module, ext = os.path.splitext(basename)
    # things we look for:
    bundle_info = {
        'version': 1,
        'extra_files': {},
        'news': 'No news.',
        'icon': PIPPY_DEFAULT_ICON,
        'class': 'activity.VteActivity',
        'bundle_id': ('org.laptop.pippy.%s' % pytitle),
        'mime_types': '',
        'extra_info': '',
        }
    # are any of these things in the module?
    try_import = False
    info = readmodule_ex(module, [sourcedir] + options.path)
    for func in bundle_info.keys():
        p_a_func = 'pippy_activity_%s' % func
        if p_a_func in info:
            try_import = True
    if try_import:
        # yes, let's try to execute them to get better info about our bundle
        oldpath = list(sys.path)
        sys.path[0:0] = [sourcedir] + options.path
        modobj = __import__(module)
        for func in bundle_info.keys():
            p_a_func = 'pippy_activity_%s' % func
            if p_a_func in modobj.__dict__:
                bundle_info[func] = modobj.__dict__[p_a_func]()
        sys.path = oldpath

    # okay!  We've done the hard part.  Now let's build a bundle.
    # create a new temp dir in which to create the bundle.
    app_temp = mkdtemp('.activity', 'Pippy')  # hope TMPDIR is set correctly!
    bundle = get_bundle_path()
    try:
        copytree('%s/library' % bundle, '%s/library' % app_temp)
        copy2('%s/activity.py' % bundle, '%s/activity.py' % app_temp)
        # create activity.info file.
        bundle_info['title'] = title
        bundle_info['pytitle'] = pytitle
        # put 'extra' files in place.
        extra_files = {
            'activity/activity.info': ACTIVITY_INFO_TEMPLATE % bundle_info,
            'activity/activity-icon.svg': bundle_info['icon'],
            'NEWS': bundle_info['news'],
            }
        extra_files.update(bundle_info['extra_files'])
        for path, contents in extra_files.items():
            # safety first!
            assert '..' not in path
            dirname, filename = os.path.split(path)
            dirname = os.path.join(app_temp, dirname)
            if not os.path.exists(dirname):
                os.makedirs(dirname)
            with open(os.path.join(dirname, filename), 'w') as f:
                f.write(contents)
        # put script into $app_temp/pippy_app.py
        copy2(sourcefile, '%s/pippy_app.py' % app_temp)
        # write MANIFEST file.
        with open('%s/MANIFEST' % app_temp, 'w') as f:
            for dirpath, dirnames, filenames in sorted(os.walk(app_temp)):
                for name in sorted(filenames):
                    fn = os.path.join(dirpath, name)
                    fn = fn.replace(app_temp + '/', '')
                    if fn == 'MANIFEST':
                        continue
                    f.write('%s\n' % fn)
        # invoke bundle builder
        olddir = os.getcwd()
        oldargv = sys.argv
        os.chdir(app_temp)
        sys.argv = ['setup.py', 'dist_xo']
        bundlebuilder.start()
        sys.argv = oldargv
        os.chdir(olddir)
        # move to destination directory.
        copy2('%s/dist/%s-%d.xo' % (app_temp, pytitle, bundle_info['version']),
              '%s/%s-%d.xo' % (options.dir, pytitle, bundle_info['version']))
    finally:
        rmtree(app_temp, ignore_errors=True)

if __name__ == '__main__':
    from gettext import gettext as _
    import sys
    if False:  # change this to True to test within Pippy
        sys.argv = sys.argv + ['-d', '/tmp', 'Pippy',
                               '/home/olpc/pippy_app.py']
    #print _("Working..."),
    #sys.stdout.flush()
    main()
    #print _("done!")
    sys.exit(0)
