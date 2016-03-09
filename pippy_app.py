#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Copyright (C) 2007,2008,2009 Chris Ball, based on Collabora's
# "hellomesh" demo.
#
# Copyright (C) 2013,14 Walter Bender
# Copyright (C) 2013,14 Ignacio Rodriguez
# Copyright (C) 2013 Jorge Gomez
# Copyright (C) 2013,14 Sai Vineet
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

import re
import os
import subprocess
from random import uniform
import locale
import json
import sys
from shutil import copy2
from signal import SIGTERM
from gettext import gettext as _
import uuid

import dbus
from dbus.mainloop.glib import DBusGMainLoop

from gi import require_version
from gi.repository import Gtk
from gi.repository import Gdk
from gi.repository import GLib
from gi.repository import Pango
require_version('Vte', '2.90')
from gi.repository import Vte
from gi.repository import GObject

DBusGMainLoop(set_as_default=True)
bus = dbus.SessionBus()

from sugar3.datastore import datastore
from sugar3.activity import activity as activity
from sugar3.activity.widgets import EditToolbar
from sugar3.activity.widgets import StopButton
from sugar3.activity.activity import get_bundle_name
from sugar3.activity.activity import get_bundle_path
from sugar3.graphics.alert import Alert
from sugar3.graphics.alert import ConfirmationAlert
from sugar3.graphics.alert import NotifyAlert
from sugar3.graphics.icon import Icon
from sugar3.graphics.objectchooser import ObjectChooser
from sugar3.graphics.toggletoolbutton import ToggleToolButton
from sugar3.graphics.toolbarbox import ToolbarButton
from sugar3.graphics.toolbutton import ToolButton
from sugar3.graphics.toolbarbox import ToolbarBox
from sugar3.activity.widgets import ActivityToolbarButton

from jarabe.view.customizebundle import generate_unique_id

from activity import ViewSourceActivity
from activity import TARGET_TYPE_TEXT

from collabwrapper import CollabWrapper

from filedialog import FileDialog
from icondialog import IconDialog
from notebook import SourceNotebook, tab_object
from toolbars import DevelopViewToolbar

import sound_check
import logging

text_buffer = None
# magic prefix to use utf-8 source encoding
PYTHON_PREFIX = '''#!/usr/bin/python
# -*- coding: utf-8 -*-
'''
# Force category names into Pootle
DEFAULT_CATEGORIES = [_('graphics'), _('math'), _('python'), _('sound'),
                      _('string'), _('tutorials')]

_logger = logging.getLogger('pippy-activity')

groupthink_mimetype = 'pickle/groupthink-pippy'

DISUTILS_SETUP_SCRIPT = """#!/usr/bin/python
# -*- coding: utf-8 -*-
from distutils.core import setup
setup(name='{modulename}',
      version='1.0',
      py_modules=[
                {filenames}
                  ],
      )
"""  # This is .format()'ed with the list of the file names.

DISUTILS_SETUP_SCRIPT = """#!/usr/bin/python
# -*- coding: utf-8 -*-
from distutils.core import setup
setup(name='{modulename}',
      version='1.0',
      py_modules=[
                {filenames}
                  ],
      )
"""  # This is .format()'ed with the list of the file names.


def _has_new_vte_api():
    try:
        return (Vte.MAJOR_VERSION >= 0 and
                Vte.MINOR_VERSION >= 38)
    except:
        # Really old versions of Vte don't have VERSION
        return False


def _find_object_id(activity_id, mimetype='text/x-python'):
    ''' Round-about way of accessing self._jobject.object_id '''
    dsobjects, nobjects = datastore.find({'mime_type': [mimetype]})
    for dsobject in dsobjects:
        if 'activity_id' in dsobject.metadata and \
           dsobject.metadata['activity_id'] == activity_id:
            return dsobject.object_id
    return None


# XXX: Why do we use ViewSourceActivity?  Sugar already has view source
# Note:  the structure is very weird, because this was migrated from groupthink
class PippyActivity(ViewSourceActivity):
    '''Pippy Activity as specified in activity.info'''
    def __init__(self, handle):
        self._pippy_instance = self
        self.session_data = []  # Used to manage saving
        self._loaded_session = []  # Used to manage tabs
        self._py_file_loaded_from_journal = False
        self._py_object_id = None
        self._dialog = None

        sys.path.append(os.path.join(self.get_activity_root(), 'Library'))

        ViewSourceActivity.__init__(self, handle)
        self._collab = CollabWrapper(self)
        self._collab.message.connect(self.__message_cb)
        self.set_canvas(self.initialize_display())
        self.after_init()
        self.connect("notify::active", self.__active_cb)
        self._collab.setup()

    def initialize_display(self):
        '''Build activity toolbar with title input, share button and export
        buttons
        '''
        toolbar_box = ToolbarBox()
        activity_button = ActivityToolbarButton(self)
        toolbar_box.toolbar.insert(activity_button, 0)
        self.set_toolbar_box(toolbar_box)
        activity_button.show()
        toolbar_box.show()
        activity_toolbar = activity_button.page

        separator = Gtk.SeparatorToolItem()
        activity_toolbar.insert(separator, -1)
        separator.show()

        button = ToolButton('pippy-import-doc')
        button.set_tooltip(_('Import Python file to new tab'))
        button.connect('clicked', self._import_py_cb)
        activity_toolbar.insert(button, -1)
        button.show()

        button = ToolButton('pippy-export-doc')
        button.set_tooltip(_('Export as Pippy document'))
        button.connect('clicked', self._export_document_cb)
        activity_toolbar.insert(button, -1)
        button.show()

        button = ToolButton('pippy-export-library')
        button.set_tooltip(_('Save this file to the Pippy library'))
        button.connect('clicked', self._save_as_library)
        activity_toolbar.insert(button, -1)
        button.show()

        button = ToolButton('pippy-export-example')
        button.set_tooltip(_('Export as new Pippy example'))
        button.connect('clicked', self._export_example_cb)
        activity_toolbar.insert(button, -1)
        button.show()

        button = ToolButton('pippy-create-bundle')
        button.set_tooltip(_('Create a Sugar activity bundle'))
        button.connect('clicked', self._create_bundle_cb)
        activity_toolbar.insert(button, -1)
        button.show()

        button = ToolButton('pippy-create-disutils')
        # TRANS: A distutils package is used to distribute Python modules
        button.set_tooltip(_('Export as a disutils package'))
        button.connect('clicked', self._export_disutils_cb)
        activity_toolbar.insert(button, -1)
        button.show()

        self._edit_toolbar = EditToolbar()

        button = ToolbarButton()
        button.set_page(self._edit_toolbar)
        button.props.icon_name = 'toolbar-edit'
        button.props.label = _('Edit')
        self.get_toolbar_box().toolbar.insert(button, -1)
        button.show()
        self._edit_toolbar.show()

        self._edit_toolbar.undo.connect('clicked', self.__undobutton_cb)
        self._edit_toolbar.redo.connect('clicked', self.__redobutton_cb)
        self._edit_toolbar.copy.connect('clicked', self.__copybutton_cb)
        self._edit_toolbar.paste.connect('clicked', self.__pastebutton_cb)

        view_btn = ToolbarButton()
        view_toolbar = DevelopViewToolbar(self)
        view_btn.props.page = view_toolbar
        view_btn.props.icon_name = 'toolbar-view'
        view_btn.props.label = _('View')
        view_toolbar.connect('font-size-changed',
                             self._font_size_changed_cb)
        self.get_toolbar_box().toolbar.insert(view_btn, -1)
        self.view_toolbar = view_toolbar
        view_toolbar.show()

        actions_toolbar = self.get_toolbar_box().toolbar

        self._toggle_output = ToggleToolButton('tray-show')
        self._toggle_output.set_tooltip(_('Show output panel'))
        self._toggle_output.connect('toggled', self._toggle_output_cb)
        actions_toolbar.insert(self._toggle_output, -1)
        self._toggle_output.show()

        icons_path = os.path.join(get_bundle_path(), 'icons')

        icon_bw = Gtk.Image()
        icon_bw.set_from_file(os.path.join(icons_path, 'run_bw.svg'))
        icon_color = Gtk.Image()
        icon_color.set_from_file(os.path.join(icons_path, 'run_color.svg'))
        button = ToolButton(label=_('Run!'))
        button.props.accelerator = _('<alt>r')
        button.set_icon_widget(icon_bw)
        button.set_tooltip(_('Run!'))
        button.connect('clicked', self._flash_cb,
                       dict({'bw': icon_bw, 'color': icon_color}))
        button.connect('clicked', self._go_button_cb)
        actions_toolbar.insert(button, -1)
        button.show()

        icon_bw = Gtk.Image()
        icon_bw.set_from_file(os.path.join(icons_path, 'stopit_bw.svg'))
        icon_color = Gtk.Image()
        icon_color.set_from_file(os.path.join(icons_path, 'stopit_color.svg'))
        button = ToolButton(label=_('Stop'))
        button.props.accelerator = _('<alt>s')
        button.set_icon_widget(icon_bw)
        button.connect('clicked', self._flash_cb,
                       dict({'bw': icon_bw, 'color': icon_color}))
        button.connect('clicked', self._stop_button_cb)
        button.set_tooltip(_('Stop'))
        actions_toolbar.insert(button, -1)
        button.show()

        icon_bw = Gtk.Image()
        icon_bw.set_from_file(os.path.join(icons_path, 'eraser_bw.svg'))
        icon_color = Gtk.Image()
        icon_color.set_from_file(os.path.join(icons_path, 'eraser_color.svg'))
        button = ToolButton(label=_('Clear'))
        button.props.accelerator = _('<alt>c')
        button.set_icon_widget(icon_bw)
        button.connect('clicked', self._clear_button_cb)
        button.connect('clicked', self._flash_cb,
                       dict({'bw': icon_bw, 'color': icon_color}))
        button.set_tooltip(_('Clear'))
        actions_toolbar.insert(button, -1)
        button.show()

        activity_toolbar.show()

        separator = Gtk.SeparatorToolItem()
        self.get_toolbar_box().toolbar.insert(separator, -1)
        separator.show()

        button = ToolButton('pippy-openoff')
        button.set_tooltip(_('Load example'))
        button.connect('clicked', self._load_example_cb)
        self.get_toolbar_box().toolbar.insert(button, -1)
        button.show()

        separator = Gtk.SeparatorToolItem()
        separator.props.draw = False
        separator.set_expand(True)
        self.get_toolbar_box().toolbar.insert(separator, -1)
        separator.show()

        stop = StopButton(self)
        self.get_toolbar_box().toolbar.insert(stop, -1)
        stop.show()

        vpane = Gtk.Paned.new(orientation=Gtk.Orientation.VERTICAL)
        vpane.set_position(400)  # setting initial position

        self.paths = []

        try:
            if sound_check.finddir():
                TAMTAM_AVAILABLE = True
            else:
                TAMTAM_AVAILABLE = False
        except sound_check.SoundLibraryNotFoundError:
            TAMTAM_AVAILABLE = False

        data_path = os.path.join(get_bundle_path(), 'data')

        # get default language from locale
        locale_lang = locale.getdefaultlocale()[0]
        if locale_lang is None:
            lang = 'en'
        else:
            lang = locale_lang.split('_')[0]
        _logger.debug(locale.getdefaultlocale())
        _logger.debug(lang)

        # construct the path for both
        lang_path = os.path.join(data_path, lang)
        en_lang_path = os.path.join(data_path, 'en')

        # get all folders in lang examples
        all_folders = []
        if os.path.exists(lang_path):
            for d in sorted(os.listdir(lang_path)):
                all_folders.append(d)

        # get all folders in English examples
        for d in sorted(os.listdir(en_lang_path)):
            # check if folder isn't already in list
            if d not in all_folders:
                all_folders.append(d)

        for folder in all_folders:
            # Skip sound folders if TAMTAM is not installed
            if folder == 'sound' and not TAMTAM_AVAILABLE:
                continue

            direntry = {}
            # check if dir exists in pref language, if exists, add it
            if os.path.exists(os.path.join(lang_path, folder)):
                direntry = {
                    'name': _(folder.capitalize()),
                    'path': os.path.join(lang_path, folder) + '/'}
            # if not try to see if it's in default English path
            elif os.path.exists(os.path.join(en_lang_path, folder)):
                direntry = {
                    'name': _(folder.capitalize()),
                    'path': os.path.join(en_lang_path, folder) + '/'}
            self.paths.append([direntry['name'], direntry['path']])

        # Adding local examples
        data_path = os.path.join(get_bundle_path(), 'data')
        self.paths.append([_('My examples'), data_path])

        self._source_tabs = SourceNotebook(self, self._collab)
        self._source_tabs.connect('tab-added', self._add_source_cb)
        if self._loaded_session:
            for name, content, path in self._loaded_session:
                self._source_tabs.add_tab(name, content, path)
        else:
            self.session_data.append(None)
            self._source_tabs.add_tab()  # New instance, ergo empty tab

        vpane.add1(self._source_tabs)
        self._source_tabs.show()

        self._outbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)

        self._vte = Vte.Terminal()
        self._vte.set_encoding('utf-8')
        self._vte.set_size(30, 5)
        self._vte.set_scrollback_lines(-1)

        # XXX support both Vte APIs
        if _has_new_vte_api():
            foreground = Gdk.RGBA()
            foreground.parse('#000000')
            background = Gdk.RGBA()
            background.parse('#E7E7E7')
        else:
            foreground = Gdk.color_parse('#000000')
            background = Gdk.color_parse('#E7E7E7')

        self._vte.set_colors(foreground, background, [])

        self._child_exited_handler = None
        self._vte.connect('child_exited', self._child_exited_cb)
        self._vte.connect('drag_data_received', self._vte_drop_cb)
        self._outbox.pack_start(self._vte, True, True, 0)

        outsb = Gtk.Scrollbar(orientation=Gtk.Orientation.VERTICAL)
        outsb.set_adjustment(self._vte.get_vadjustment())
        outsb.show()
        self._outbox.pack_start(outsb, False, False, 0)

        self._load_config()

        vpane.add2(self._outbox)
        self._outbox.show()
        vpane.show()
        return vpane

    def after_init(self):
        self._outbox.hide()

    def _font_size_changed_cb(self, widget, size):
        self._source_tabs.set_font_size(size)
        self._vte.set_font(
            Pango.FontDescription('Monospace {}'.format(size)))

    def _store_config(self):
        font_size = self._source_tabs.get_font_size()

        _config_file_path = os.path.join(
            activity.get_activity_root(), 'data',
            'config.json')
        with open(_config_file_path, "w") as f:
            f.write(json.dumps(font_size))

    def _load_config(self):
        _config_file_path = os.path.join(
            activity.get_activity_root(), 'data',
            'config.json')

        if not os.path.isfile(_config_file_path):
            return

        with open(_config_file_path, "r") as f:
            font_size = json.loads(f.read())
            self.view_toolbar.set_font_size(font_size)
            self._vte.set_font(
                Pango.FontDescription('Monospace {}'.format(font_size)))

    def __active_cb(self, widget, event):
        logging.debug('__active_cb %r', self.props.active)
        if self.props.active:
            self.resume()
        else:
            self.pause()

    def do_visibility_notify_event(self, event):
        logging.debug('do_visibility_notify_event %r', event.get_state())
        if event.get_state() == Gdk.VisibilityState.FULLY_OBSCURED:
            self.pause()
        else:
            self.resume()

    def pause(self):
        # FIXME: We had resume, but no pause?
        pass

    def resume(self):
        if self._dialog is not None:
            self._dialog.set_keep_above(True)

    def _toggle_output_cb(self, button):
        shown = button.get_active()
        if shown:
            self._outbox.show_all()
            self._toggle_output.set_tooltip(_('Hide output panel'))
            self._toggle_output.set_icon_name('tray-hide')
        else:
            self._outbox.hide()
            self._toggle_output.set_tooltip(_('Show output panel'))
            self._toggle_output.set_icon_name('tray-show')

    def _load_example_cb(self, widget):
        widget.set_icon_name('pippy-openon')
        self._dialog = FileDialog(self.paths, self, widget)
        self._dialog.show()
        self._dialog.run()
        path = self._dialog.get_path()
        if path:
            self._select_func_cb(path)

    def _add_source_cb(self, button, force=False, editor_id=None):
        if self._collab.props.leader or force:
            if editor_id is None:
                editor_id = str(uuid.uuid1())
            self._source_tabs.add_tab(editor_id=editor_id)
            self.session_data.append(None)
            self._source_tabs.get_nth_page(-1).show_all()
            self._source_tabs.get_text_view().grab_focus()
            if self._collab.props.leader:
                self._collab.post(dict(
                    action='add-source',
                    editor_id=editor_id))
        else:
            # The leader must do it first so that they can set
            # up the text buffer
            self._collab.post(dict(action='add-source-request'))

    def __message_cb(self, collab, buddy, msg):
        action = msg.get('action')
        if action == 'add-source-request' and self._collab.props.leader:
            self._add_source_cb(None, force=True)
        elif action == 'add-source':
            self._add_source_cb(
                None, force=True, editor_id=msg.get('editor_id'))

    def _vte_drop_cb(self, widget, context, x, y, selection, targetType, time):
        if targetType == TARGET_TYPE_TEXT:
            self._vte.feed_child(selection.data)

    def get_data(self):
        return self._source_tabs.get_all_data()

    def set_data(self, data):
        # Remove initial new/blank thing
        self.session_data = []
        self._loaded_session = []
        try:
            self._source_tabs.remove_page(0)
            tab_object.pop(0)
        except IndexError:
            pass

        list_ = zip(*data)
        for name, code, path, modified, editor_id in list_:
            self._source_tabs.add_tab(
                label=name, editor_id=editor_id)
            self.session_data.append(None)  # maybe?

    def _selection_cb(self, value):
        self.save()
        _logger.debug('clicked! %s' % value['path'])
        _file = open(value['path'], 'r')
        lines = _file.readlines()
        text_buffer = self._source_tabs.get_text_buffer()
        current_content = text_buffer.get_text(
            *text_buffer.get_bounds(),
            include_hidden_chars=True)
        if current_content != "":
            # Add a new page to the notebook with the example
            self._add_source_cb(None)
        if text_buffer.get_modified():
            self._source_tabs.add_tab()
            self.session_data.append(None)
            text_buffer = self._source_tabs.get_text_buffer()
        text_buffer.set_text(''.join(lines))
        text_buffer.set_modified(False)
        self._pippy_instance.metadata['title'] = value['name']
        self._stop_button_cb(None)
        self._reset_vte()
        self._source_tabs.set_current_label(value['name'])
        self._source_tabs.set_current_path(value['path'])
        self._source_tabs.get_text_view().grab_focus()

    def _select_func_cb(self, path):
        values = {}
        values['name'] = os.path.basename(path)
        values['path'] = path
        self._selection_cb(values)

    def _timer_cb(self, button, icons):
        button.set_icon_widget(icons['bw'])
        button.show_all()
        return False

    def _flash_cb(self, button, icons):
        button.set_icon_widget(icons['color'])
        button.show_all()
        GObject.timeout_add(400, self._timer_cb, button, icons)

    def _clear_button_cb(self, button):
        self.save()
        text_buffer = self._source_tabs.get_text_buffer()
        text_buffer.set_text('')
        text_buffer.set_modified(False)
        self._pippy_instance.metadata['title'] = \
            _('%s Activity') % get_bundle_name()
        self._stop_button_cb(None)
        self._reset_vte()
        self._source_tabs.get_text_view().grab_focus()

    def _write_all_buffers(self, tmp_dir):
        data = self._source_tabs.get_all_data()
        zipdata = zip(data[0], data[1])
        for name, content in zipdata:
            with open(os.path.join(tmp_dir, name), 'w') as f:
                # Write utf-8 coding prefix if there's not one already
                if re.match(r'coding[:=]\s*([-\w.]+)',
                            '\n'.join(content.splitlines()[:2])) is None:
                    f.write(PYTHON_PREFIX)
                f.write(content)

    def _reset_vte(self):
        self._vte.grab_focus()
        self._vte.feed('\x1B[H\x1B[J\x1B[0;39m')

    def __undobutton_cb(self, butston):
        text_buffer = self._source_tabs.get_text_buffer()
        if text_buffer.can_undo():
            text_buffer.undo()

    def __redobutton_cb(self, button):
        text_buffer = self._source_tabs.get_text_buffer()
        if text_buffer.can_redo():
            text_buffer.redo()

    def __copybutton_cb(self, button):
        text_buffer = self._source_tabs.get_text_buffer()
        clipboard = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
        text_buffer.copy_clipboard(clipboard)

    def __pastebutton_cb(self, button):
        text_buffer = self._source_tabs.get_text_buffer()
        clipboard = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
        text_buffer.paste_clipboard(clipboard, None, True)

    def _go_button_cb(self, button):
        self._stop_button_cb(button)  # Try stopping old code first.
        self._reset_vte()

        # FIXME: We're losing an odd race here
        # Gtk.main_iteration(block=False)

        if self._toggle_output.get_active() is False:
            self._outbox.show_all()
            self._toggle_output.set_active(True)

        pippy_tmp_dir = '%s/tmp/' % self.get_activity_root()
        self._write_all_buffers(pippy_tmp_dir)

        current_file = os.path.join(
            pippy_tmp_dir,
            self._source_tabs.get_current_file_name())

        # Write activity.py here too, to support pippy-based activities.
        copy2('%s/activity.py' % get_bundle_path(),
              '%s/tmp/activity.py' % self.get_activity_root())

        # XXX Support both Vte APIs
        if _has_new_vte_api():
            vte_run = self._vte.spawn_sync
        else:
            vte_run = self._vte.fork_command_full

        self._pid = vte_run(
            Vte.PtyFlags.DEFAULT,
            get_bundle_path(),
            ['/bin/sh', '-c', 'python %s; sleep 1' % current_file,
             'PYTHONPATH=%s/library:%s' % (get_bundle_path(),
                                           os.getenv('PYTHONPATH', ''))],
            ['PYTHONPATH=%s/library:%s' % (get_bundle_path(),
                                           os.getenv('PYTHONPATH', ''))],
            GLib.SpawnFlags.DO_NOT_REAP_CHILD,
            None,
            None,)

    def _stop_button_cb(self, button):
        try:
            if self._pid is not None:
                os.kill(self._pid[1], SIGTERM)
        except:
            pass  # Process must already be dead.

    def _save_as_library(self, button):
        library_dir = os.path.join(get_bundle_path(), 'library')
        file_name = self._source_tabs.get_current_file_name()
        text_buffer = self._source_tabs.get_text_buffer()
        content = text_buffer.get_text(
            *text_buffer.get_bounds(),
            include_hidden_chars=True)

        if not os.path.isdir(library_dir):
            os.mkdir(library_dir)

        with open(os.path.join(library_dir, file_name), 'w') as f:
            f.write(content)
            success = True

        if success:
            alert = NotifyAlert(5)
            alert.props.title = _('Python File added to Library')
            IMPORT_MESSAGE = _('The file you selected has been added'
                               ' to the library. Use "import {importname}"'
                               ' to import the library for using.')
            alert.props.msg = IMPORT_MESSAGE.format(importname=file_name[:-3])
            alert.connect('response', self._remove_alert_cb)
            self.add_alert(alert)

    def _export_document_cb(self, __):
        self.copy()
        alert = NotifyAlert()
        alert.props.title = _('Saved')
        alert.props.msg = _('The document has been saved to journal.')
        alert.connect('response', lambda x, i: self.remove_alert(x))
        self.add_alert(alert)

    def _remove_alert_cb(self, alert, response_id):
        self.remove_alert(alert)

    def _import_py_cb(self, button):
        chooser = ObjectChooser()
        result = chooser.run()
        if result is Gtk.ResponseType.ACCEPT:
            dsitem = chooser.get_selected_object()
            if dsitem.metadata['mime_type'] != 'text/x-python':
                alert = NotifyAlert(5)
                alert.props.title = _('Error importing Python file')
                alert.props.msg = _('The file you selected is not a '
                                    'Python file.')
                alert.connect('response', self._remove_alert_cb)
                self.add_alert(alert)
            elif dsitem.object_id in self.session_data:
                alert = NotifyAlert(5)
                alert.props.title = _('Error importing Python file')
                alert.props.msg = _('The file you selected is already '
                                    'open')
                alert.connect('response', self._remove_alert_cb)
                self.add_alert(alert)
            else:
                name = dsitem.metadata['title']
                file_path = dsitem.get_file_path()
                content = open(file_path, 'r').read()

                self._source_tabs.add_tab(name, content, None)
                self._source_tabs.set_current_label(name)
                self.session_data.append(dsitem.object_id)
                _logger.debug('after import py: %r' % self.session_data)

        chooser.destroy()

    def _create_bundle_cb(self, button):
        from shutil import rmtree
        from tempfile import mkdtemp

        # Get the name of this pippy program.
        title = self._pippy_instance.metadata['title'].replace('.py', '')
        title = title.replace('-', '')
        if title == 'Pippy Activity':
            alert = Alert()
            alert.props.title = _('Save as Activity Error')
            alert.props.msg = _('Please give your activity a meaningful name '
                                'before attempting to save it as an activity.')
            ok_icon = Icon(icon_name='dialog-ok')
            alert.add_button(Gtk.ResponseType.OK, _('Ok'), ok_icon)
            alert.connect('response', self._dismiss_alert_cb)
            self.add_alert(alert)
            return

        alert_icon = Alert()
        ok_icon = Icon(icon_name='dialog-ok')
        alert_icon.add_button(Gtk.ResponseType.OK, _('Ok'), ok_icon)
        alert_icon.props.title = _('Activity icon')
        alert_icon.props.msg = _('Please select an activity icon.')

        self._stop_button_cb(None)  # try stopping old code first.
        self._reset_vte()
        self._outbox.show_all()
        self._vte.feed(_("Creating activity bundle..."))
        self._vte.feed("\r\n")
        TMPDIR = 'instance'
        app_temp = mkdtemp('.activity', 'Pippy',
                           os.path.join(self.get_activity_root(), TMPDIR))
        sourcefile = os.path.join(app_temp, 'xyzzy.py')
        # invoke ourself to build the activity bundle.
        _logger.debug('writing out source file: %s' % sourcefile)

        def internal_callback(window=None, event=None):
            icon = '%s/activity/activity-default.svg' % (get_bundle_path())
            if window:
                icon = window.get_icon()
            self._stop_button_cb(None)  # Try stopping old code first.
            self._reset_vte()
            self._vte.feed(_('Creating activity bundle...'))
            self._vte.feed('\r\n')

            TMPDIR = 'instance'
            app_temp = mkdtemp('.activity', 'Pippy',
                               os.path.join(self.get_activity_root(), TMPDIR))
            sourcefile = os.path.join(app_temp, 'xyzzy.py')
            # Invoke ourself to build the activity bundle.
            _logger.debug('writing out source file: %s' % sourcefile)

            # Write out application code
            self._write_text_buffer(sourcefile)

            try:
                # FIXME: vte invocation was raising errors.
                # Switched to subprocss
                output = subprocess.check_output(
                    ['/usr/bin/python2',
                     '%s/pippy_app.py' % get_bundle_path(),
                     '-p', '%s/library' % get_bundle_path(),
                     '-d', app_temp, title, sourcefile, icon])
                self._vte.feed(output)
                self._vte.feed('\r\n')
                self._bundle_cb(title, app_temp)
            except subprocess.CalledProcessError:
                rmtree(app_temp, ignore_errors=True)  # clean up!
                self._vte.feed(_('Save as Activity Error'))
                self._vte.feed('\r\n')
                raise

        def _alert_response(alert, response_id):
            self.remove_alert(alert)

            def _dialog():
                dialog = IconDialog()
                dialog.connect('destroy', internal_callback)

            GObject.idle_add(_dialog)

        alert_icon.connect('response', _alert_response)
        self.add_alert(alert_icon)

    def _write_text_buffer(self, filename):
        text_buffer = self._source_tabs.get_text_buffer()
        start, end = text_buffer.get_bounds()
        text = text_buffer.get_text(start, end, True)

        with open(filename, 'w') as f:
            # Write utf-8 coding prefix if there's not one already
            if re.match(r'coding[:=]\s*([-\w.]+)',
                        '\n'.join(text.splitlines()[:2])) is None:
                f.write(PYTHON_PREFIX)
            for line in text:
                f.write(line)

    def _export_disutils_cb(self, button):
        app_temp = os.path.join(self.get_activity_root(), 'instance')
        data = self._source_tabs.get_all_data()
        for filename, content in zip(data[0], data[1]):
            fileobj = open(os.path.join(app_temp, filename), 'w')
            fileobj.write(content)
            fileobj.close()

        filenames = ','.join([("'"+name[:-3]+"'") for name in data[0]])

        title = self._pippy_instance.metadata['title']
        if title is _('Pippy Activity'):
            alert = Alert()
            alert.props.title = _('Save as disutils package error')
            alert.props.msg = _('Please give your activity a meaningful '
                                'name before attempting to save it '
                                'as an disutils package.')
            ok_icon = Icon(icon_name='dialog-ok')
            alert.add_button(Gtk.ResponseType.OK, _('Ok'), ok_icon)
            alert.connect('response', self._dismiss_alert_cb)
            self.add_alert(alert)
            return

        setup_script = DISUTILS_SETUP_SCRIPT.format(modulename=title,
                                                    filenames=filenames)
        setupfile = open(os.path.join(app_temp, 'setup.py'), 'w')
        setupfile.write(setup_script)
        setupfile.close()

        os.chdir(app_temp)

        subprocess.check_output(
            ['/usr/bin/python', os.path.join(app_temp, 'setup.py'), 'sdist',
             '-v'])

        # Hand off to journal
        os.chmod(app_temp, 0777)
        jobject = datastore.create()
        metadata = {
            'title': '%s disutils bundle' % title,
            'title_set_by_user': '1',
            'mime_type': 'application/x-gzip',
        }
        for k, v in metadata.items():
            # The dict.update method is missing =(
            jobject.metadata[k] = v
        tarname = 'dist/{modulename}-1.0.tar.gz'.format(modulename=title)
        jobject.file_path = os.path.join(app_temp, tarname)
        datastore.write(jobject)

    def _export_example_cb(self, button):
        # Get the name of this pippy program.
        title = self._pippy_instance.metadata['title']
        if title == _('Pippy Activity'):
            alert = Alert()
            alert.props.title = _('Save as Example Error')
            alert.props.msg = \
                _('Please give your activity a meaningful '
                  'name before attempting to save it as an example.')
            ok_icon = Icon(icon_name='dialog-ok')
            alert.add_button(Gtk.ResponseType.OK, _('Ok'), ok_icon)
            alert.connect('response', self._dismiss_alert_cb)
            self.add_alert(alert)
            return
        self._stop_button_cb(None)  # Try stopping old code first.
        self._reset_vte()
        self._vte.feed(_('Creating example...'))
        self._vte.feed('\r\n')
        local_data = os.path.join(os.environ['SUGAR_ACTIVITY_ROOT'], 'data')
        local_file = os.path.join(local_data, title)
        if os.path.exists(local_file):
            alert = ConfirmationAlert()
            alert.props.title = _('Save as Example Warning')
            alert.props.msg = _('This example already exists. '
                                'Do you want to overwrite it?')
            alert.connect('response', self._confirmation_alert_cb, local_file)
            self.add_alert(alert)
        else:
            self.write_file(local_file)
            self._reset_vte()
            self._vte.feed(_('Saved as example.'))
            self._vte.feed('\r\n')
            self._add_to_example_list(local_file)

    def _child_exited_cb(self, *args):
        '''Called whenever a child exits.  If there's a handler, run it.'''
        h, self._child_exited_handler = self._child_exited_handler, None
        if h is not None:
            h()

    def _bundle_cb(self, title, app_temp):
        '''Called when we're done building a bundle for a source file.'''
        from sugar3 import profile
        from shutil import rmtree
        try:
            # Find the .xo file: were we successful?
            bundle_file = [f for f in os.listdir(app_temp)
                           if f.endswith('.xo')]
            if len(bundle_file) != 1:
                _logger.debug("Couldn't find bundle: %s" %
                              str(bundle_file))
                self._vte.feed('\r\n')
                self._vte.feed(_('Error saving activity to journal.'))
                self._vte.feed('\r\n')
                return  # Something went wrong.
            # Hand off to journal
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
                # The dict.update method is missing =(
                jobject.metadata[k] = v
            jobject.file_path = os.path.join(app_temp, bundle_file[0])
            datastore.write(jobject)
            self._vte.feed('\r\n')
            self._vte.feed(_('Activity saved to journal.'))
            self._vte.feed('\r\n')
            self.journal_show_object(jobject.object_id)
            jobject.destroy()
        finally:
            rmtree(app_temp, ignore_errors=True)  # clean up!

    def _dismiss_alert_cb(self, alert, response_id):
        self.remove_alert(alert)

    def _confirmation_alert_cb(self, alert, response_id, local_file):
        # Callback for conf alert
        self.remove_alert(alert)
        if response_id is Gtk.ResponseType.OK:
            self.write_file(local_file)
            self._reset_vte()
            self._vte.feed(_('Saved as example.'))
            self._vte.feed('\r\n')
        else:
            self._reset_vte()

    def _add_to_example_list(self, local_file):
        entry = {'name': _(os.path.basename(local_file)),
                 'path': local_file}
        _iter = self.model.insert_before(self.example_iter, None)
        self.model.set_value(_iter, 0, entry)
        self.model.set_value(_iter, 1, entry['name'])

    def _get_pippy_object_id(self):
        ''' We need the object_id of this pippy instance to save in the .py
            file metadata'''
        if self._pippy_instance == self:
            return _find_object_id(self.metadata['activity_id'],
                                   mimetype='application/json')
        else:
            return self._pippy_instance.get_object_id()

    def write_file(self, file_path):
        pippy_id = self._get_pippy_object_id()
        data = self._source_tabs.get_all_data()
        zipped_data = zip(*data)
        session_list = []
        app_temp = os.path.join(self.get_activity_root(), 'instance')
        tmpfile = os.path.join(app_temp, 'pippy-tempfile-storing.py')
        for zipdata, content in zip(zipped_data, self.session_data):
            logging.error('Session data %r', content)
            name, python_code, path, modified, editor_id = zipdata
            if content is not None and content == self._py_object_id:
                _logger.debug('saving to self')
                self.metadata['title'] = name
                self.metadata['mime_type'] = 'text/x-python'
                if pippy_id is not None:
                    self.metadata['pippy_instance'] = pippy_id
                __file = open(file_path, 'w')
                __file.write(python_code)
                __file.close()
                session_list.append([name, content])
            elif content is not None and content[0] != '/':
                _logger.debug('Saving an existing dsobject')
                dsobject = datastore.get(content)
                dsobject.metadata['title'] = name
                dsobject.metadata['mime_type'] = 'text/x-python'
                if pippy_id is not None:
                    dsobject.metadata['pippy_instance'] = pippy_id
                __file = open(tmpfile, 'w')
                __file.write(python_code)
                __file.close()
                dsobject.set_file_path(tmpfile)
                datastore.write(dsobject)
                session_list.append([name, dsobject.object_id])
            elif modified:
                _logger.debug('Creating new dsobj for modified code')
                if len(python_code) > 0:
                    dsobject = datastore.create()
                    dsobject.metadata['title'] = name
                    dsobject.metadata['mime_type'] = 'text/x-python'
                    if pippy_id is not None:
                        dsobject.metadata['pippy_instance'] = pippy_id
                    __file = open(tmpfile, 'w')
                    __file.write(python_code)
                    __file.close()
                    dsobject.set_file_path(tmpfile)
                    datastore.write(dsobject)
                    session_list.append([name, dsobject.object_id])
                    # If there are multiple Nones, we need to find
                    # the correct one.
                    if content is None and \
                       self.session_data.count(None) > 1:
                        i = zipped_data.index(zipdata)
                    else:
                        i = self.session_data.index(content)
                    self.session_data[i] = dsobject.object_id
            elif content is not None or path is not None:
                _logger.debug('Saving reference to sample file')
                if path is None:  # Should not happen, but just in case...
                    _logger.error('path is None.')
                    session_list.append([name, content])
                else:
                    session_list.append([name, path])
            else:  # Should not happen, but just in case...
                _logger.error('Nothing to save in tab? %s %s %s %s' %
                              (str(name), str(python_code), str(path),
                               str(content)))

        self._pippy_instance.metadata['mime_type'] = 'application/json'
        pippy_data = json.dumps(session_list)

        # Override file path if we created a new Pippy instance
        if self._py_file_loaded_from_journal:
            file_path = os.path.join(app_temp, 'pippy-temp-instance-data')
        _file = open(file_path, 'w')
        _file.write(pippy_data)
        _file.close()
        if self._py_file_loaded_from_journal:
            _logger.debug('setting pippy instance file_path to %s' %
                          file_path)
            self._pippy_instance.set_file_path(file_path)
            datastore.write(self._pippy_instance)

        self._store_config()

    def read_file(self, file_path):
        # Either we are opening Python code or a list of objects
        # stored (json-encoded) in a Pippy instance, or a shared
        # session.

        # Remove initial new/blank thing
        self.session_data = []
        self._loaded_session = []
        try:
            self._source_tabs.remove_page(0)
            tab_object.pop(0)
        except IndexError:
            pass

        if self.metadata['mime_type'] == 'text/x-python':
            _logger.debug('Loading Python code')
            # Opening some Python code directly
            try:
                text = open(file_path).read()
            except:
                alert = NotifyAlert(10)
                alert.props.title = _('Error')
                alert.props.msg = _('Error reading data.')

                def _remove_alert(alert, response_id):
                    self.remove_alert(alert)

                alert.connect("response", _remove_alert)
                self.add_alert(alert)
                return

            self._py_file_loaded_from_journal = True

            # Discard the '#!/usr/bin/python' and 'coding: utf-8' lines,
            # if present
            python_code = re.sub(r'^' + re.escape(PYTHON_PREFIX), '', text)
            name = self.metadata['title']
            self._loaded_session.append([name, python_code, None])

            # Since we loaded Python code, we need to create (or
            # restore) a Pippy instance
            if 'pippy_instance' in self.metadata:
                _logger.debug('found a pippy instance: %s' %
                              self.metadata['pippy_instance'])
                try:
                    self._pippy_instance = datastore.get(
                        self.metadata['pippy_instance'])
                except:
                    _logger.debug('Cannot find old Pippy instance: %s')
                    self._pippy_instance = None
            if self._pippy_instance in [self, None]:
                self._pippy_instance = datastore.create()
                self._pippy_instance.metadata['title'] = self.metadata['title']
                self._pippy_instance.metadata['mime_type'] = 'application/json'
                self._pippy_instance.metadata['activity'] = 'org.laptop.Pippy'
                datastore.write(self._pippy_instance)
                self.metadata['pippy_instance'] = \
                    self._pippy_instance.get_object_id()
                _logger.debug('get_object_id %s' %
                              self.metadata['pippy_instance'])

            # We need the Pippy file path so we can read the session data
            file_path = self._pippy_instance.get_file_path()

            # Finally, add this Python object to the session data
            self._py_object_id = _find_object_id(self.metadata['activity_id'])
            self.session_data.append(self._py_object_id)
            _logger.debug('session_data: %s' % self.session_data)

        if self.metadata['mime_type'] == 'application/json' or \
           self._pippy_instance != self:
            # Reading file list from Pippy instance
            _logger.debug('Loading Pippy instance')
            if len(file_path) == 0:
                return
            data = json.loads(open(file_path).read())
            for name, content in data:
                # content is either a datastore id or the path to some
                # sample code
                if content is not None and content[0] == '/':  # a path
                    try:
                        python_code = open(content).read()
                    except:
                        _logger.error('Could not open %s; skipping' % content)
                    path = content
                elif content != self._py_object_id:
                    try:
                        dsobject = datastore.get(content)
                        if 'mime_type' not in dsobject.metadata:
                            _logger.error(
                                'Warning: %s missing mime_type' % content)
                        elif dsobject.metadata['mime_type'] != 'text/python':
                            _logger.error(
                                'Warning: %s has unexpected mime_type %s' %
                                (content, dsobject.metadata['mime_type']))
                    except:
                        # Could be that the item has subsequently been
                        # deleted from the datastore, so we skip it.
                        _logger.error('Could not open %s; skipping' % content)
                        continue
                    try:
                        python_code = open(dsobject.get_file_path()).read()
                    except:
                        # Malformed bundle?
                        _logger.error('Could not open %s; skipping' %
                                      dsobject.get_file_path())
                        continue
                    path = None

                # Queue up the creation of the tabs...
                # And add this content to the session data
                if content not in self.session_data:
                    self.session_data.append(content)
                    self._loaded_session.append([name, python_code, path])
        elif self.metadata['mime_type'] == groupthink_mimetype:
            # AAAAAAAAAAAAARRRRRRRRRRRRRGGGGGGGGGHHHHHHHHHH
            # TODO:  Find what groupthink data actually is under the layers
            #        an layers of abstraction
            pass

        for name, content, path in self._loaded_session:
            self._source_tabs.add_tab(name, content, path)

# TEMPLATES AND INLINE FILES
ACTIVITY_INFO_TEMPLATE = '''
[Activity]
name = %(title)s
bundle_id = %(bundle_id)s
exec = sugar-activity %(class)s
icon = activity-icon
activity_version = %(version)d
mime_types = %(mime_types)s
show_launcher = yes
%(extra_info)s
'''

PIPPY_ICON = """<?xml version="1.0" ?><!DOCTYPE svg PUBLIC '-//W3C//DTD SVG
1.1//EN' 'http://www.w3.org/Graphics/SVG/1.1/DTD/svg11.dtd' [
    <!ENTITY stroke_color "#010101">
    <!ENTITY fill_color "#FFFFFF">
]>
<svg enable-background="new 0 0 55 55" height="55px" version="1.1"
viewBox="0 0 55 55" width="55px" x="0px" xml:space="preserve"
xmlns="http://www.w3.org/2000/svg"
xmlns:xlink="http://www.w3.org/1999/xlink" y="0px"><g display="block"
id="activity-pippy">
<path d="M28.497,48.507
c5.988,0,14.88-2.838,14.88-11.185
c0-9.285-7.743-10.143-10.954-11.083
c-3.549-0.799-5.913-1.914-6.055-3.455
c-0.243-2.642,1.158-3.671,3.946-3.671
c0,0,6.632,3.664,12.266,0.74
c1.588-0.823,4.432-4.668,4.432-7.32
c0-2.653-9.181-5.719-11.967-5.719
c-2.788,0-5.159,3.847-5.159,3.847
c-5.574,0-11.149,5.306-11.149,10.612
c0,5.305,5.333,9.455,11.707,10.612
c2.963,0.469,5.441,2.22,4.878,5.438
c-0.457,2.613-2.995,5.306-8.361,5.306
c-4.252,0-13.3-0.219-14.745-4.079
c-0.929-2.486,0.168-5.205,1.562-5.205l-0.027-0.16
c-1.42-0.158-5.548,0.16-5.548,5.465
C8.202,45.452,17.347,48.507,28.497,48.507z"
fill="&fill_color;" stroke="&stroke_color;"
stroke-linecap="round" stroke-linejoin="round" stroke-width="3.5"/>
    <path d="M42.579,19.854c-2.623-0.287-6.611-2-7.467-5.022" fill="none"
stroke="&stroke_color;" stroke-linecap="round" stroke-width="3"/>
    <circle cx="35.805" cy="10.96" fill="&stroke_color;" r="1.676"/>
</g></svg><!-- " -->

"""


# ACTIVITY META-INFORMATION
# this is used by Pippy to generate a bundle for itself.


def pippy_activity_version():
    '''Returns the version number of the generated activity bundle.'''
    return 39


def pippy_activity_extra_files():
    '''Returns a map of 'extra' files which should be included in the
    generated activity bundle.'''
    # Cheat here and generate the map from the fs contents.
    extra = {}
    bp = get_bundle_path()
    for d in ['po', 'data', 'groupthink', 'post']:  # everybody gets library
        for root, dirs, files in os.walk(os.path.join(bp, d)):
            for name in files:
                fn = os.path.join(root, name).replace(bp + '/', '')
                extra[fn] = open(os.path.join(root, name), 'r').read()
    return extra


def pippy_activity_news():
    '''Return the NEWS file for this activity.'''
    # Cheat again.
    return open(os.path.join(get_bundle_path(), 'NEWS')).read()


def pippy_activity_icon():
    '''Return an SVG document specifying the icon for this activity.'''
    return PIPPY_ICON


def pippy_activity_class():
    '''Return the class which should be started to run this activity.'''
    return 'pippy_app.PippyActivity'


def pippy_activity_bundle_id():
    '''Return the bundle_id for the generated activity.'''
    return 'org.laptop.Pippy'


def pippy_activity_mime_types():
    '''Return the mime types handled by the generated activity, as a list.'''
    return ['text/x-python', groupthink_mimetype]


def pippy_activity_extra_info():
    return '''
license = GPLv2+
update_url = http://activities.sugarlabs.org '''

# ACTIVITY BUNDLER


def main():
    '''Create a bundle from a pippy-style source file'''
    from optparse import OptionParser
    from pyclbr import readmodule_ex
    from tempfile import mkdtemp
    from shutil import copytree, copy2, rmtree
    from sugar3.activity import bundlebuilder

    parser = OptionParser(usage='%prog [options] [title] [sourcefile] [icon]')
    parser.add_option('-d', '--dir', dest='dir', default='.', metavar='DIR',
                      help='Put generated bundle in the specified directory.')
    parser.add_option('-p', '--pythonpath', dest='path', action='append',
                      default=[], metavar='DIR',
                      help='Append directory to python search path.')

    (options, args) = parser.parse_args()
    if len(args) < 3:
        parser.error('The title, sourcefile and icon arguments are required.')

    title = args[0]
    sourcefile = args[1]
    icon_path = args[2]
    pytitle = re.sub(r'[^A-Za-z0-9_]', '', title)
    if re.match(r'[0-9]', pytitle) is not None:
        pytitle = '_' + pytitle  # first character cannot be numeric

    # First take a gander at the source file and see if it's got extra info
    # for us.
    sourcedir, basename = os.path.split(sourcefile)
    if not sourcedir:
        sourcedir = '.'
    module, ext = os.path.splitext(basename)
    f = open(icon_path, 'r')
    icon = f.read()
    f.close()
    # Things we look for:
    bundle_info = {
        'version': 1,
        'extra_files': {},
        'news': 'No news.',
        'icon': icon,
        'class': 'activity.VteActivity',
        'bundle_id': ('org.sugarlabs.pippy.%s%d' %
                      (generate_unique_id(),
                       int(round(uniform(1000, 9999), 0)))),
        'mime_types': '',
        'extra_info': '',
        }
    # Are any of these things in the module?
    try_import = False

    info = readmodule_ex(module, [sourcedir] + options.path)
    for func in bundle_info.keys():
        p_a_func = 'pippy_activity_%s' % func
        if p_a_func in info:
            try_import = True
    if try_import:
        # Yes, let's try to execute them to get better info about our bundle
        oldpath = list(sys.path)
        sys.path[0:0] = [sourcedir] + options.path
        modobj = __import__(module)
        for func in bundle_info.keys():
            p_a_func = 'pippy_activity_%s' % func
            if p_a_func in modobj.__dict__:
                bundle_info[func] = modobj.__dict__[p_a_func]()
        sys.path = oldpath

    # Okay!  We've done the hard part.  Now let's build a bundle.
    # Create a new temp dir in which to create the bundle.
    app_temp = mkdtemp('.activity', 'Pippy')  # Hope TMPDIR is set correctly!
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
        # Put script into $app_temp/pippy_app.py
        copy2(sourcefile, '%s/pippy_app.py' % app_temp)
        # Invoke bundle builder
        olddir = os.getcwd()
        oldargv = sys.argv
        os.chdir(app_temp)
        sys.argv = ['setup.py', 'dist_xo']
        print('\r\nStarting bundlebuilder\r\n')
        bundlebuilder.start()
        sys.argv = oldargv
        os.chdir(olddir)
        # Move to destination directory.
        src = '%s/dist/%s-%d.xo' % (app_temp, pytitle, bundle_info['version'])
        dst = '%s/%s-%d.xo' % (options.dir, pytitle, bundle_info['version'])
        if not os.path.exists(src):
            print('Cannot find %s\r\n' % (src))
        else:
            copy2(src, dst)
    finally:
        rmtree(app_temp, ignore_errors=True)
        print('Finally\r\n')

if __name__ == '__main__':
    from gettext import gettext as _
    if False:  # Change this to True to test within Pippy
        sys.argv = sys.argv + ['-d', '/tmp', 'Pippy',
                               '/home/olpc/pippy_app.py']
    print(_('Working...'))
    sys.stdout.flush()
    main()
    print(_('done!'))
    sys.exit(0)
