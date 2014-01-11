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
import logging
import re
import os
import subprocess
from random import uniform
import locale
import json
import sys

import dbus
from dbus.mainloop.glib import DBusGMainLoop

DBusGMainLoop(set_as_default=True)
bus = dbus.SessionBus()

from gi.repository import Gtk
from gi.repository import Gdk
from gi.repository import GLib
from gi.repository import Pango
from gi.repository import Vte
from gi.repository import GObject

from port.style import font_zoom
from signal import SIGTERM
from gettext import gettext as _

from sugar3.datastore import datastore
from sugar3.activity.widgets import EditToolbar
from sugar3.activity.widgets import StopButton
from sugar3.activity.activity import get_bundle_path
from sugar3.activity.activity import get_bundle_name
from sugar3.graphics.alert import NotifyAlert
from sugar3.graphics.alert import ConfirmationAlert
from sugar3.graphics.alert import Alert
from sugar3.graphics import style
from sugar3.graphics.icon import Icon
from sugar3.graphics.objectchooser import ObjectChooser
from sugar3.graphics.toggletoolbutton import ToggleToolButton

from jarabe.view.customizebundle import generate_unique_id

from activity import ViewSourceActivity
from activity import TARGET_TYPE_TEXT

import groupthink.sugar_tools
import groupthink.gtk_tools

from FileDialog import FileDialog
from IconDialog import IconDialog

text_buffer = None
# magic prefix to use utf-8 source encoding
PYTHON_PREFIX = """#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
default_categoties = [_('graphics'), _('math'), _('pyhton'), _('sound'),
                      _('string'), _('tutorials')]

from sugar3.graphics.toolbarbox import ToolbarButton
from sugar3.graphics.toolbutton import ToolButton

# get screen sizes
SIZE_X = Gdk.Screen.width()
SIZE_Y = Gdk.Screen.height()

groupthink_mimetype = 'pickle/groupthink-pippy'

from Notebook import SourceNotebook

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


class PippyActivity(ViewSourceActivity, groupthink.sugar_tools.GroupActivity):
    """Pippy Activity as specified in activity.info"""
    def early_setup(self):
        from gi.repository import GtkSource
        self.initial_text_buffer = GtkSource.Buffer()
        self.loaded_from_journal = False
        self.py_file = False
        self.loaded_session = []
        self.session_data = []

        sys.path.append(os.path.join(self.get_activity_root(), "Library"))

    def initialize_display(self):
        self._logger = logging.getLogger('pippy-activity')

        # Activity toolbar with title input, share button and export buttons:

        activity_toolbar = self.activity_button.page

        separator = Gtk.SeparatorToolItem()
        separator.show()
        activity_toolbar.insert(separator, -1)

        import_py_button = ToolButton("pippy-import-doc")
        import_py_button.set_tooltip(_("Import Python file to new tab"))
        import_py_button.connect("clicked", self._import_py_cb)
        import_py_button.show()
        activity_toolbar.insert(import_py_button, -1)

        export_doc_button = ToolButton('pippy-export-doc')
        export_doc_button.set_tooltip(_("Export as Pippy document"))
        export_doc_button.connect('clicked', self._export_document_cb)
        export_doc_button.show()
        activity_toolbar.insert(export_doc_button, -1)

        save_as_library = ToolButton("pippy-export-library")
        save_as_library.set_tooltip(_("Save this file to the Pippy library"))
        save_as_library.connect("clicked", self._save_as_library)
        save_as_library.show()
        activity_toolbar.insert(save_as_library, -1)

        export_example_button = ToolButton('pippy-export-example')
        export_example_button.set_tooltip(_("Export as new Pippy example"))
        export_example_button.connect('clicked', self._export_example_cb)
        export_example_button.show()
        activity_toolbar.insert(export_example_button, -1)

        create_bundle_button = ToolButton('pippy-create-bundle')
        create_bundle_button.set_tooltip(_("Create a Sugar activity bundle"))
        create_bundle_button.connect('clicked', self._create_bundle_cb)
        create_bundle_button.show()
        activity_toolbar.insert(create_bundle_button, -1)

        export_disutils = ToolButton("pippy-create-disutils")
        export_disutils.set_tooltip(_("Export as a disutils package"))
        export_disutils.connect("clicked", self.__export_disutils_cb)
        export_disutils.show()
        activity_toolbar.insert(export_disutils, -1)

        self._edit_toolbar = EditToolbar()

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

        actions_toolbar = self.get_toolbar_box().toolbar

        self.toggle_output = ToggleToolButton("tray-show")
        self.toggle_output.set_tooltip(_("Show output panel"))
        self.toggle_output.connect("toggled", self._toggle_output_cb)
        actions_toolbar.insert(self.toggle_output, -1)

        # The "go" button
        goicon_bw = Gtk.Image()
        goicon_bw.set_from_file("%s/icons/run_bw.svg" % os.getcwd())
        goicon_color = Gtk.Image()
        goicon_color.set_from_file("%s/icons/run_color.svg" % os.getcwd())
        gobutton = ToolButton(label=_("Run!"))
        gobutton.props.accelerator = _('<alt>r')
        gobutton.set_icon_widget(goicon_bw)
        gobutton.set_tooltip(_("Run!"))
        gobutton.connect('clicked', self.flash_cb,
                         dict({'bw': goicon_bw, 'color': goicon_color}))
        gobutton.connect('clicked', self.gobutton_cb)
        actions_toolbar.insert(gobutton, -1)

        # The "stop" button
        stopicon_bw = Gtk.Image()
        stopicon_bw.set_from_file("%s/icons/stopit_bw.svg" % os.getcwd())
        stopicon_color = Gtk.Image()
        stopicon_color.set_from_file("%s/icons/stopit_color.svg" % os.getcwd())
        stopbutton = ToolButton(label=_("Stop"))
        stopbutton.props.accelerator = _('<alt>s')
        stopbutton.set_icon_widget(stopicon_bw)
        stopbutton.connect('clicked', self.flash_cb,
                           dict({'bw': stopicon_bw,
                                 'color': stopicon_color}))
        stopbutton.connect('clicked', self.stopbutton_cb)
        stopbutton.set_tooltip(_("Stop"))
        actions_toolbar.insert(stopbutton, -1)

        # The "clear" button
        clearicon_bw = Gtk.Image()
        clearicon_bw.set_from_file("%s/icons/eraser_bw.svg" % os.getcwd())
        clearicon_color = Gtk.Image()
        clearicon_color.set_from_file("%s/icons/eraser_color.svg" %
                                      os.getcwd())
        clearbutton = ToolButton(label=_("Clear"))
        clearbutton.props.accelerator = _('<alt>c')
        clearbutton.set_icon_widget(clearicon_bw)
        clearbutton.connect('clicked', self.clearbutton_cb)
        clearbutton.connect('clicked', self.flash_cb,
                            dict({'bw': clearicon_bw,
                                  'color': clearicon_color}))
        clearbutton.set_tooltip(_("Clear"))
        actions_toolbar.insert(clearbutton, -1)

        activity_toolbar.show()

        examples = ToolButton("pippy-openoff")
        examples.set_tooltip(_("Load example"))
        examples.connect("clicked", self.load_example)

        self.get_toolbar_box().toolbar.insert(Gtk.SeparatorToolItem(), -1)
        self.get_toolbar_box().toolbar.insert(examples, -1)

        separator = Gtk.SeparatorToolItem()
        separator.props.draw = False
        separator.set_expand(True)
        self.get_toolbar_box().toolbar.insert(separator, -1)
        separator.show()

        stop = StopButton(self)
        self.get_toolbar_box().toolbar.insert(stop, -1)

        self.paths = []

        vpane = Gtk.Paned.new(orientation=Gtk.Orientation.VERTICAL)
        vpane.set_position(400)  # setting initial position

        self.paths = []

        data_path = os.path.join(get_bundle_path(), 'data')

        # get default language from locale
        locale_lang = locale.getdefaultlocale()[0]
        if locale_lang is None:
            lang = 'en'
        else:
            lang = locale_lang.split('_')[0]
        logging.debug(locale.getdefaultlocale())
        logging.debug(lang)

        # construct the path for both
        lang_path = os.path.join(data_path, lang)
        en_lang_path = os.path.join(data_path, 'en')

        # get all folders in lang examples
        self.all_folders = []
        if os.path.exists(lang_path):
            for d in sorted(os.listdir(lang_path)):
                self.all_folders.append(d)

        # get all folders in English examples
        for d in sorted(os.listdir(en_lang_path)):
            # check if folder isn't already in list
            if d not in self.all_folders:
                self.all_folders.append(d)

        for folder in self.all_folders:
            direntry = {}
            # check if dir exists in pref language, if exists, add it
            if os.path.exists(os.path.join(lang_path, folder)):
                direntry = {
                    "name": _(folder.capitalize()),
                    "path": os.path.join(lang_path, folder) + "/"}
            # if not try to see if it's in default English path
            elif os.path.exists(os.path.join(en_lang_path, folder)):
                direntry = {
                    "name": _(folder.capitalize()),
                    "path": os.path.join(en_lang_path, folder) + "/"}
            self.paths.append([direntry['name'], direntry['path']])

        # Adding local examples
        root = os.path.join(os.environ['SUGAR_ACTIVITY_ROOT'], 'data')
        self.paths.append([_('My examples'), root])

        self.source_tabs = SourceNotebook(self)
        self.source_tabs.connect("tab-added", self._add_source_cb)
        if self.loaded_from_journal and self.py_file:
            self.source_tabs.add_tab(
                self.initial_title,
                self.initial_text_buffer)
        elif self.loaded_session:
            for name, content in self.loaded_session:
                self.source_tabs.add_tab(name, content)
        else:
            self.source_tabs.add_tab()

        vpane.add1(self.source_tabs)

        outbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        self._vte = Vte.Terminal()
        self._vte.set_encoding('utf-8')
        self._vte.set_size(30, 5)
        font = 'Monospace ' + str(font_zoom(style.FONT_SIZE))
        self._vte.set_font(Pango.FontDescription(font))
        self._vte.set_colors(Gdk.color_parse('#000000'),
                             Gdk.color_parse('#E7E7E7'),
                             [])
        self._vte.connect('child_exited', self.child_exited_cb)

        self._child_exited_handler = None
        self._vte.connect('drag_data_received', self.vte_drop_cb)
        outbox.pack_start(self._vte, True, True, 0)

        outsb = Gtk.Scrollbar(orientation=Gtk.Orientation.VERTICAL)
        outsb.set_adjustment(self._vte.get_vadjustment())
        outsb.show()
        outbox.pack_start(outsb, False, False, 0)
        vpane.add2(outbox)
        self.outbox = outbox

        return vpane

    def after_init(self):
        self.outbox.hide()

    def _toggle_output_cb(self, button):
        shown = button.get_active()
        if shown:
            self.outbox.show_all()
            self.toggle_output.set_tooltip(_("Hide output panel"))
            self.toggle_output.set_icon_name("tray-hide")
        else:
            self.outbox.hide()
            self.toggle_output.set_tooltip(_("Show output panel"))
            self.toggle_output.set_icon_name("tray-show")

    def load_example(self, widget):
        widget.set_icon_name("pippy-openon")
        dialog = FileDialog(self.paths, self, widget)
        dialog.run()
        path = dialog.get_path()
        if path:
            self._select_func_cb(path)

    def when_shared(self):
        text_buffer = self.source_tabs.get_text_buffer()
        self.cloud.sharefield = \
            groupthink.gtk_tools.TextBufferSharePoint(text_buffer)
        # HACK : There are issues with undo/redoing while in shared
        # mode. So disable the 'undo' and 'redo' buttons when the activity
        # is shared.
        self._edit_toolbar.undo.set_sensitive(False)
        self._edit_toolbar.redo.set_sensitive(False)

    def _add_source_cb(self, button):
        self.source_tabs.add_tab()
        self.source_tabs.get_nth_page(-1).show_all()

    def vte_drop_cb(self, widget, context, x, y, selection, targetType, time):
        if targetType == TARGET_TYPE_TEXT:
            self._vte.feed_child(selection.data)

    def selection_cb(self, value):
        self.save()
        self._logger.debug("clicked! %s" % value['path'])
        _file = open(value['path'], 'r')
        lines = _file.readlines()
        text_buffer = self.source_tabs.get_text_buffer()
        text_buffer.set_text("".join(lines))
        text_buffer.set_modified(False)
        self.metadata['title'] = value['name']
        self.stopbutton_cb(None)
        self._reset_vte()
        self.text_view.grab_focus()

    def _select_func_cb(self, path):
        text_buffer = self.source_tabs.get_text_buffer()
        if text_buffer.get_modified():
            alert = ConfirmationAlert()
            alert.props.title = _('Example selection Warning')
            alert.props.msg = _('You have modified the currently selected file. \
                                Discard changes?')
            alert.connect('response', self._discard_changes_cb, path)
            self.add_alert(alert)
            return False
        else:
            values = {}
            values['name'] = os.path.basename(path)
            values['path'] = path
            self.selection_cb(values)

        return False

    def _discard_changes_cb(self, alert, response_id, path):
        self.remove_alert(alert)
        if response_id is Gtk.ResponseType.OK:
            values = {}
            values['name'] = os.path.basename(path)
            values['path'] = path
            self.selection_cb(values)
            text_buffer = self.source_tabs.get_text_buffer()
            text_buffer.set_modified(False)

    def timer_cb(self, button, icons):
        button.set_icon_widget(icons['bw'])
        button.show_all()
        return False

    def flash_cb(self, button, icons):
        button.set_icon_widget(icons['color'])
        button.show_all()
        GObject.timeout_add(400, self.timer_cb, button, icons)

    def clearbutton_cb(self, button):
        self.save()
        text_buffer = self.source_tabs.get_text_buffer()
        text_buffer.set_text("")
        text_buffer.set_modified(False)
        self.metadata['title'] = _('%s Activity') % get_bundle_name()
        self.stopbutton_cb(None)
        self._reset_vte()
        self.source_tabs.get_text_view().grab_focus()

    def _write_all_buffers(self, tmp_dir):
        data = self.source_tabs.get_all_data()
        zipdata = zip(data[0], data[1])
        for name, content in zipdata:
            with open(os.path.join(tmp_dir, name), 'w') as f:
                # write utf-8 coding prefix if there's not already one
                if re.match(r'coding[:=]\s*([-\w.]+)',
                            '\n'.join(content.splitlines()[:2])) is None:
                    f.write(PYTHON_PREFIX)
                f.write(content)

    def _reset_vte(self):
        self._vte.grab_focus()
        self._vte.feed("\x1B[H\x1B[J\x1B[0;39m")

    def __undobutton_cb(self, butston):
        text_buffer = self.source_tabs.get_text_buffer()
        if text_buffer.can_undo():
            text_buffer.undo()

    def __redobutton_cb(self, button):
        text_buffer = self.source_tabs.get_text_buffer()
        if text_buffer.can_redo():
            text_buffer.redo()

    def __copybutton_cb(self, button):
        text_buffer = self.source_tabs.get_text_buffer()
        text_buffer.copy_clipboard(Gtk.Clipboard())

    def __pastebutton_cb(self, button):
        text_buffer = self.source_tabs.get_text_buffer()
        text_buffer.paste_clipboard(Gtk.Clipboard(), None, True)

    def gobutton_cb(self, button):
        from shutil import copy2
        self.stopbutton_cb(button)  # try stopping old code first.
        self._reset_vte()

        # FIXME: We're losing an odd race here
        # Gtk.main_iteration(block=False)

        if self.toggle_output.get_active() is False:
            self.outbox.show_all()
            self.toggle_output.set_active(True)

        pippy_tmp_dir = '%s/tmp/' % self.get_activity_root()
        self._write_all_buffers(pippy_tmp_dir)

        current_file = os.path.join(
            pippy_tmp_dir,
            self.source_tabs.get_current_file_name())

        # write activity.py here too, to support pippy-based activities.
        copy2('%s/activity.py' % get_bundle_path(),
              '%s/tmp/activity.py' % self.get_activity_root())

        self._pid = self._vte.fork_command_full(
            Vte.PtyFlags.DEFAULT,
            get_bundle_path(),
            ["/bin/sh", "-c", "python %s; sleep 1" % current_file,
             "PYTHONPATH=%s/library:%s" % (get_bundle_path(),
                                           os.getenv("PYTHONPATH", ""))],
            ["PYTHONPATH=%s/library:%s" % (get_bundle_path(),
                                           os.getenv("PYTHONPATH", ""))],
            GLib.SpawnFlags.DO_NOT_REAP_CHILD,
            None,
            None,)

    def stopbutton_cb(self, button):
        try:
            if self._pid is not None:
                os.kill(self._pid[1], SIGTERM)
        except:
            pass  # process must already be dead.

    def _save_as_library(self, button):
        library_dir = os.path.join(get_bundle_path(), "library")
        file_name = self.source_tabs.get_current_file_name()
        text_buffer = self.source_tabs.get_text_buffer()
        content = text_buffer.get_text(
            *text_buffer.get_bounds(),
            include_hidden_chars=True)

        if not os.path.isdir(library_dir):
            os.mkdir(library_dir)

        with open(os.path.join(library_dir, file_name), "w") as f:
            f.write(content)
            success = True

        if success:
            alert = NotifyAlert(5)
            alert.props.title = _('Python File added to Library')
            IMPORT_MESSAGE = _('The file you selected has been added'
                               ' to the library. Use "import {importname}"'
                               ' to import the library for using.')
            alert.props.msg = IMPORT_MESSAGE.format(importname=file_name[:-3])
            alert.connect('response', self.remove_alert_cb)
            self.add_alert(alert)

    def _export_document_cb(self, __):
        self.copy()

    def remove_alert_cb(self, alert, response_id):
        self.remove_alert(alert)

    def _import_py_cb(self, button):
        chooser = ObjectChooser()
        result = chooser.run()
        if result is Gtk.ResponseType.ACCEPT:
            dsitem = chooser.get_selected_object()
            if dsitem.metadata['mime_type'] != "text/x-python":
                alert = NotifyAlert(5)
                alert.props.title = _('Error importing Python file')
                alert.props.msg = _('The file you selected is not a '
                                    'Python file.')
                alert.connect('response', self.remove_alert_cb)
                self.add_alert(alert)
            elif dsitem.object_id in self.session_data:
                alert = NotifyAlert(5)
                alert.props.title = _('Error importing Python file')
                alert.props.msg = _('The file you selected is already '
                                    'open')
                alert.connect('response', self.remove_alert_cb)
                self.add_alert(alert)
            else:
                name = dsitem.metadata['title']
                file_path = dsitem.get_file_path()
                content = open(file_path, "r").read()

                self.source_tabs.add_tab(name, content)
                self.session_data.append(dsitem.object_id)

        chooser.destroy()

    def _create_bundle_cb(self, __):
        from shutil import rmtree
        from tempfile import mkdtemp

        # get the name of this pippy program.
        title = self.metadata['title'].replace('.py', '')
        title = title.replace('-', '')
        if title == 'Pippy Activity':
            alert = Alert()
            alert.props.title = _('Save as Activity Error')
            alert.props.msg = _('Please give your activity a meaningful name '
                                'before attempting to save it as an activity.')
            ok_icon = Icon(icon_name='dialog-ok')
            alert.add_button(Gtk.ResponseType.OK, _('Ok'), ok_icon)
            alert.connect('response', self.dismiss_alert_cb)
            self.add_alert(alert)
            return

        alert_icon = Alert()
        ok_icon = Icon(icon_name='dialog-ok')
        alert_icon.add_button(Gtk.ResponseType.OK, _('Ok'), ok_icon)
        alert_icon.props.title = _('Activity icon')
        alert_icon.props.msg = _('Please select an activity icon.')

        def internal_callback(window=None, event=None):
            icon = "%s/activity/activity-default.svg" % (get_bundle_path())
            if window:
                icon = window.get_icon()
            self.stopbutton_cb(None)  # try stopping old code first.
            self._reset_vte()
            self._vte.feed(_("Creating activity bundle..."))
            self._vte.feed("\r\n")

            TMPDIR = 'instance'
            app_temp = mkdtemp('.activity', 'Pippy',
                               os.path.join(self.get_activity_root(), TMPDIR))
            sourcefile = os.path.join(app_temp, 'xyzzy.py')
            # invoke ourself to build the activity bundle.
            self._logger.debug('writing out source file: %s' % sourcefile)

            # write out application code
            self._write_text_buffer(sourcefile)

            try:
                # FIXME: vte invocation was raising errors.
                # Switched to subprocss
                output = subprocess.check_output(
                    ["/usr/bin/python",
                     "%s/pippy_app.py" % get_bundle_path(),
                     '-p', '%s/library' % get_bundle_path(),
                     '-d', app_temp, title, sourcefile, icon])
                self._vte.feed(output)
                self._vte.feed("\r\n")
                self.bundle_cb(title, app_temp)
            except subprocess.CalledProcessError:
                rmtree(app_temp, ignore_errors=True)  # clean up!
                self._vte.feed(_('Save as Activity Error'))
                self._vte.feed("\r\n")
                raise

        def alert_response(alert, response_id):
            self.remove_alert(alert)

            def dialog():
                dialog = IconDialog()
                dialog.connect('destroy', internal_callback)

            GObject.idle_add(dialog)

        alert_icon.connect('response', alert_response)
        self.add_alert(alert_icon)

    def _write_text_buffer(self, filename):
        text_buffer = self.source_tabs.get_text_buffer()
        start, end = text_buffer.get_bounds()
        text = text_buffer.get_text(start, end, True)

        with open(filename, 'w') as f:
            # write utf-8 coding prefix if there's not already one
            if re.match(r'coding[:=]\s*([-\w.]+)',
                        '\n'.join(text.splitlines()[:2])) is None:
                f.write(PYTHON_PREFIX)
            for line in text:
                f.write(line)

    def __export_disutils_cb(self, button):
        app_temp = os.path.join(self.get_activity_root(), "instance")
        data = self.source_tabs.get_all_data()
        for filename, content in zip(data[0], data[1]):
            fileobj = open(os.path.join(app_temp, filename), "w")
            fileobj.write(content)
            fileobj.close()

        filenames = ",".join([("'"+name[:-3]+"'") for name in data[0]])

        title = self.metadata['title']
        if title is _('Pippy Activity'):
            from sugar3.graphics.alert import Alert
            from sugar3.graphics.icon import Icon
            alert = Alert()
            alert.props.title = _('Save as disutils package error')
            alert.props.msg = _('Please give your activity a meaningful'
                                'name before attempting to save it '
                                'as an disutils package.')
            ok_icon = Icon(icon_name='dialog-ok')
            alert.add_button(Gtk.ResponseType.OK, _('Ok'), ok_icon)
            alert.connect('response', self.dismiss_alert_cb)
            self.add_alert(alert)
            return

        setup_script = DISUTILS_SETUP_SCRIPT.format(modulename=title,
                                                    filenames=filenames)
        setupfile = open(os.path.join(app_temp, "setup.py"), "w")
        setupfile.write(setup_script)
        setupfile.close()

        os.chdir(app_temp)

        subprocess.check_output(
            [
                "/usr/bin/python",
                os.path.join(app_temp, "setup.py"),
                "sdist", "-v"
            ])

        # hand off to journal
        os.chmod(app_temp, 0777)
        jobject = datastore.create()
        metadata = {
            'title': '%s disutils bundle' % title,
            'title_set_by_user': '1',
            'mime_type': 'application/x-gzip',
        }
        for k, v in metadata.items():
            # the dict.update method is missing =(
            jobject.metadata[k] = v
        tarname = "dist/{modulename}-1.0.tar.gz".format(modulename=title)
        jobject.file_path = os.path.join(app_temp, tarname)
        datastore.write(jobject)

    def _export_example_cb(self, __):
        # get the name of this pippy program.
        title = self.metadata['title']
        if title == _('Pippy Activity'):
            from sugar3.graphics.alert import Alert
            from sugar3.graphics.icon import Icon
            alert = Alert()
            alert.props.title = _('Save as Example Error')
            alert.props.msg = _('Please give your activity a meaningful \
name before attempting to save it as an example.')
            ok_icon = Icon(icon_name='dialog-ok')
            alert.add_button(Gtk.ResponseType.OK, _('Ok'), ok_icon)
            alert.connect('response', self.dismiss_alert_cb)
            self.add_alert(alert)
            return
        self.stopbutton_cb(None)  # try stopping old code first.
        self._reset_vte()
        self._vte.feed(_("Creating example..."))
        self._vte.feed("\r\n")
        local_data = os.path.join(os.environ['SUGAR_ACTIVITY_ROOT'], 'data')
        local_file = os.path.join(local_data, title)
        if os.path.exists(local_file):
            alert = ConfirmationAlert()
            alert.props.title = _('Save as Example Warning')
            alert.props.msg = _('This example already exists. \
Do you want to overwrite it?')
            alert.connect('response', self.confirmation_alert_cb, local_file)
            self.add_alert(alert)
        else:
            self.write_file(local_file)
            self._reset_vte()
            self._vte.feed(_("Saved as example."))
            self._vte.feed("\r\n")
            self.add_to_example_list(local_file)

    def child_exited_cb(self, *args):
        """Called whenever a child exits.  If there's a handler, run it."""
        h, self._child_exited_handler = self._child_exited_handler, None
        if h is not None:
            h()

    def bundle_cb(self, title, app_temp):
        """Called when we're done building a bundle for a source file."""
        from sugar3 import profile
        from shutil import rmtree
        try:
            # find the .xo file: were we successful?
            bundle_file = [f for f in os.listdir(app_temp)
                           if f.endswith('.xo')]
            if len(bundle_file) != 1:
                self._logger.debug("Couldn't find bundle: %s" %
                                   str(bundle_file))
                self._vte.feed("\r\n")
                self._vte.feed(_("Error saving activity to journal."))
                self._vte.feed("\r\n")
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
                # the dict.update method is missing =(
                jobject.metadata[k] = v
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

    def confirmation_alert_cb(self, alert, response_id, local_file):
        # callback for conf alert
        self.remove_alert(alert)
        if response_id is Gtk.ResponseType.OK:
            self.write_file(local_file)
            self._reset_vte()
            self._vte.feed(_("Saved as example."))
            self._vte.feed("\r\n")
        else:
            self._reset_vte()

    def add_to_example_list(self, local_file):  # def for add example
        entry = {"name": _(os.path.basename(local_file)),
                 "path": local_file}
        _iter = self.model.insert_before(self.example_iter, None)
        self.model.set_value(_iter, 0, entry)
        self.model.set_value(_iter, 1, entry["name"])

    def save_to_journal(self, file_path, cloudstring):
        _file = open(file_path, 'w')
        if not self.shared_activity:
            data = self.source_tabs.get_all_data()
            zipped_data = zip(data[0], data[1])
            sessionlist = []
            app_temp = os.path.join(self.get_activity_root(), "instance")
            tmpfile = os.path.join(app_temp,
                                   "pippy-tempfile-storing.py")
            for zipdata, dsid in map(None, zipped_data, self.session_data):
                name, content = zipdata

                if dsid is not None:
                    dsitem = datastore.get(dsid)
                    __file = open(tmpfile, "w")
                    __file.write(content)
                    __file.close()
                    dsitem.set_file_path(tmpfile)
                    dsitem.metadata['title'] = name
                    datastore.write(dsitem)
                else:
                    dsobject = datastore.create()
                    dsobject.metadata['mime_type'] = 'text/x-python'
                    dsobject.metadata['title'] = name
                    __file = open(tmpfile, "w")
                    __file.write(content)
                    __file.close()
                    dsobject.set_file_path(tmpfile)
                    datastore.write(dsobject)
                    dsitem = None

                if dsitem is not None:
                    sessionlist.append([name, dsitem.object_id])
                else:
                    sessionlist.append([name, dsobject.object_id])

            self.metadata['mime_type'] = 'application/json'
            _file.write(json.dumps(sessionlist))
        else:
            self.metadata['mime_type'] = groupthink_mimetype
            _file.write(cloudstring)

    def load_from_journal(self, file_path):
        if self.metadata['mime_type'] == 'text/x-python':
            text = open(file_path).read()
            # discard the '#!/usr/bin/python' and 'coding: utf-8' lines,
            # if present
            text = re.sub(r'^' + re.escape(PYTHON_PREFIX), '', text)

            self.initial_text_buffer = text
            self.initial_title = self.metadata['title']
            self.loaded_from_journal = self.py_file = True

        elif self.metadata['mime_type'] == "application/json":
            data = json.loads(open(file_path).read())
            for name, dsid in data:
                dsitem = datastore.get(dsid)
                content = open(dsitem.get_file_path()).read()
                self.loaded_session.append([name, content])
                self.session_data.append(dsitem.object_id)

        elif self.metadata['mime_type'] == groupthink_mimetype:
            return open(file_path).read()

############# TEMPLATES AND INLINE FILES ##############
ACTIVITY_INFO_TEMPLATE = """
[Activity]
name = %(title)s
bundle_id = %(bundle_id)s
exec = sugar-activity %(class)s
icon = activity-icon
activity_version = %(version)d
mime_types = %(mime_types)s
show_launcher = yes
%(extra_info)s
"""

PIPPY_ICON = \
"""<?xml version="1.0" ?><!DOCTYPE svg PUBLIC '-//W3C//DTD SVG
1.1//EN' 'http://www.w3.org/Graphics/SVG/1.1/DTD/svg11.dtd' [
    <!ENTITY stroke_color "#010101">
    <!ENTITY fill_color "#FFFFFF">
]>
<svg enable-background="new 0 0 55 55" height="55px" version="1.1"
viewBox="0 0 55 55" width="55px" x="0px" xml:space="preserve"
xmlns="http://www.w3.org/2000/svg"
xmlns:xlink="http://www.w3.org/1999/xlink" y="0px"><g display="block"
id="activity-pippy">
    <path d="M28.497,48.507   c5.988,0,14.88-2.838,14.88-11.185c0-9.285-7.743-10.143-10.954-11.083c-3.549-0.799-5.913-1.914-6.055-3.455   c-0.243-2.642,1.158-3.671,3.946-3.671c0,0,6.632,3.664,12.266,0.74c1.588-0.823,4.432-4.668,4.432-7.32   c0-2.653-9.181-5.719-11.967-5.719c-2.788,0-5.159,3.847-5.159,3.847c-5.574,0-11.149,5.306-11.149,10.612   c0,5.305,5.333,9.455,11.707,10.612c2.963,0.469,5.441,2.22,4.878,5.438c-0.457,2.613-2.995,5.306-8.361,5.306   c-4.252,0-13.3-0.219-14.745-4.079c-0.929-2.486,0.168-5.205,1.562-5.205l-0.027-0.16c-1.42-0.158-5.548,0.16-5.548,5.465   C8.202,45.452,17.347,48.507,28.497,48.507z" fill="&fill_color;" stroke="&stroke_color;" stroke-linecap="round" stroke-linejoin="round" stroke-width="3.5"/>
    <path d="M42.579,19.854c-2.623-0.287-6.611-2-7.467-5.022" fill="none"
stroke="&stroke_color;" stroke-linecap="round" stroke-width="3"/>
    <circle cx="35.805" cy="10.96" fill="&stroke_color;" r="1.676"/>
</g></svg><!-- " -->

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

    # first take a gander at the source file and see if it's got extra info
    # for us.
    sourcedir, basename = os.path.split(sourcefile)
    if not sourcedir:
        sourcedir = '.'
    module, ext = os.path.splitext(basename)
    f = open(icon_path, 'r')
    icon = f.read()
    f.close()
    # things we look for:
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
        # invoke bundle builder
        olddir = os.getcwd()
        oldargv = sys.argv
        os.chdir(app_temp)
        sys.argv = ['setup.py', 'dist_xo']
        print('\r\nStarting bundlebuilder\r\n')
        bundlebuilder.start()
        sys.argv = oldargv
        os.chdir(olddir)
        # move to destination directory.
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
    import sys
    from gettext import gettext as _
    if False:  # change this to True to test within Pippy
        sys.argv = sys.argv + ['-d', '/tmp', 'Pippy',
                               '/home/olpc/pippy_app.py']
    print(_("Working..."))
    sys.stdout.flush()
    main()
    print(_("done!"))
    sys.exit(0)
