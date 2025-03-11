#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright (C) 2007,2008,2010 One Laptop per Child Association, Inc.
# Written by C. Scott Ananian <cscott@laptop.org>
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
import logging
import os
import subprocess
import sys
import json
from gettext import gettext as _

from gi import require_version
require_version('Gdk', '3.0')
require_version('Gtk', '3.0')
from gi.repository import Gdk
from gi.repository import Gtk
from gi.repository import Pango
from gi.repository import GLib
from gi.repository import GObject

VTE_VERSION = None
try:
    require_version('Vte', '2.91')
    VTE_VERSION = '2.91'
except Exception as e:
    logging.warning(f"Vte 2.91 not found, falling back to 2.90: {e}")
    try:
        require_version('Vte', '2.90')
        VTE_VERSION = '2.90'
    except Exception as e:
        logging.error(f"No compatible VTE library found: {e}")
        sys.exit(1)
from gi.repository import Vte

from sugar3.activity import activity
from sugar3.activity.widgets import ActivityToolbarButton
from sugar3.activity.widgets import StopButton
from sugar3.graphics.toolbarbox import ToolbarBox

CONFIG_FILE = 'config.json'
try:
    with open(CONFIG_FILE, 'r') as f:
        config = json.load(f)
except FileNotFoundError:
    logging.error(f"Configuration file '{CONFIG_FILE}' not found. Using defaults.")
    config = {}

TARGET_TYPE_TEXT = 80
PIPPY_APP_FILENAME = config.get('pippy_app_filename', 'pippy_app.py')
LIBRARY_PATH = config.get('library_path', 'library')
TERMINAL_FONT = config.get('terminal_font', 'Monospace 10')
TERMINAL_COLORS = config.get('terminal_colors', {
    'foreground': '#000000',
    'background': '#E7E7E7'
})

class ViewSourceActivity(activity.Activity):
    def __init__(self, handle, **kwargs):
        super(ViewSourceActivity, self).__init__(handle, **kwargs)
        self.__source_object_id = None
        self.connect('key-press-event', self._key_press_cb)
        self._pid = None

    def _key_press_cb(self, widget, event):
        if Gdk.keyval_name(event.keyval) == 'XF86Start':
            self.view_source()
            return True
        return False

    def view_source(self):
        if self.__source_object_id is None:
            from sugar3 import profile
            from sugar3.datastore import datastore
            from sugar3.activity.activity import (get_bundle_name,
                                                  get_bundle_path)
            import os.path
            jobject = datastore.create()
            metadata = {
                'title': _('%s Source') % get_bundle_name(),
                'title_set_by_user': '1',
                'suggested_filename': PIPPY_APP_FILENAME,
                'icon-color': profile.get_color().to_string(),
                'mime_type': 'text/x-python',
            }
            for k, v in list(metadata.items()):
                jobject.metadata[k] = v
            app_path = os.path.join(get_bundle_path(), PIPPY_APP_FILENAME)
            jobject.file_path = app_path
            datastore.write(jobject)
            self.__source_object_id = jobject.object_id
            jobject.destroy()
        self.journal_show_object(self.__source_object_id)

    def journal_show_object(self, object_id):
        try:
            from sugar3.activity.activity import show_object_in_journal
            show_object_in_journal(object_id)
        except ImportError:
            logging.warning("Could not import show_object_in_journal")

    def show_error_dialog(self, message):
        dialog = Gtk.MessageDialog(
            parent=self,
            flags=0,
            message_type=Gtk.MessageType.ERROR,
            buttons=Gtk.ButtonsType.OK,
            text=message
        )
        dialog.run()
        dialog.destroy()

class BaseActivity(ViewSourceActivity):
    def __init__(self, handle, **kwargs):
        super(BaseActivity, self).__init__(handle, **kwargs)
        self.max_participants = 1
        toolbox = ToolbarBox()
        activity_button_toolbar = ActivityToolbarButton(self)
        toolbox.toolbar.insert(activity_button_toolbar, 0)
        activity_button_toolbar.show()
        self.set_toolbar_box(toolbox)
        toolbox.show()
        self.toolbar = toolbox.toolbar
        separator = Gtk.SeparatorToolItem()
        separator.props.draw = False
        separator.set_expand(True)
        toolbox.toolbar.insert(separator, -1)
        separator.show()
        stop_button = StopButton(self)
        toolbox.toolbar.insert(stop_button, -1)
        stop_button.show()
        toolbox.toolbar.show_all()

class VteActivity(BaseActivity):
    def __init__(self, handle, **kwargs):
        super(VteActivity, self).__init__(handle, **kwargs)
        self._vte = Vte.Terminal()
        self._vte.set_size(30, 5)
        self._vte.set_size_request(200, 300)
        self._vte.set_font(Pango.FontDescription(TERMINAL_FONT))
        fg = Gdk.RGBA()
        fg.parse(TERMINAL_COLORS['foreground'])
        bg = Gdk.RGBA()
        bg.parse(TERMINAL_COLORS['background'])
        self._vte.set_colors(fg, bg, [])
        vtebox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        vtebox.pack_start(self._vte, True, True, 0)
        vtesb = Gtk.Scrollbar(orientation=Gtk.Orientation.VERTICAL)
        vtesb.set_adjustment(self._vte.get_vadjustment())
        vtesb.show()
        vtebox.pack_start(vtesb, False, False, 0)
        self.set_canvas(vtebox)
        self.show_all()
        self._vte.connect('child-exited', self.on_child_exit)
        self._vte.grab_focus()
        bundle_path = activity.get_bundle_path()
        logging.debug(f"Bundle path: {bundle_path}")
        env = os.environ.copy()
        env["PYTHONPATH"] = f"{bundle_path}/{LIBRARY_PATH}"
        cmd = ['/bin/sh', '-c', f'python3 {bundle_path}/{PIPPY_APP_FILENAME}; sleep 1']
        try:
            if VTE_VERSION == '2.91':
                self._pid = self._vte.spawn_async(
                    Vte.PtyFlags.DEFAULT,
                    bundle_path,
                    cmd,
                    [f"PYTHONPATH={bundle_path}/{LIBRARY_PATH}"],
                    GLib.SpawnFlags.DO_NOT_REAP_CHILD,
                    None, None,
                    -1,
                    None, None)
            else:
                self._pid = self._vte.fork_command_full(
                    Vte.PtyFlags.DEFAULT,
                    bundle_path,
                    cmd,
                    [f"PYTHONPATH={bundle_path}/{LIBRARY_PATH}"],
                    GLib.SpawnFlags.DO_NOT_REAP_CHILD,
                    None,
                    None)
        except Exception as e:
            logging.error(f"Failed to start terminal process: {e}")
            self.show_error_dialog(f"Failed to start terminal: {e}")

    def on_child_exit(self, terminal, status=None):
        if status is not None:
            logging.debug(f"Child exited with status: {status}")
        else:
            logging.debug("Child exited")

class PyGameActivity(BaseActivity):
    def __init__(self, handle, **kwargs):
        super(PyGameActivity, self).__init__(handle, **kwargs)
        self.child_pid = self._launch_pygame()
        socket = Gtk.Socket()
        socket.set_can_focus(True)
        socket.show()
        self.set_canvas(socket)
        try:
            import pygame
            windowid = pygame.display.get_wm_info()['wmwindow']
            socket.add_id(windowid)
        except Exception as e:
            logging.error(f"Failed to add pygame window to socket: {e}")
            self.show_error_dialog(f"Failed to initialize Pygame: {e}")
        self.show_all()
        socket.grab_focus()
        GObject.child_watch_add(self.child_pid, lambda pid, cond: self.close())

    def _launch_pygame(self):
        import os
        child_pid = os.fork()
        if child_pid == 0:
            try:
                bp = activity.get_bundle_path()
                pippy_app_path = os.path.join(bp, PIPPY_APP_FILENAME)
                subprocess.run(['python3', pippy_app_path], check=True)
                sys.exit(0)
            except Exception as e:
                logging.error(f"Fatal error in pygame process: {e}")
                sys.exit(1)
        return child_pid

def _main():
    import argparse
    parser = argparse.ArgumentParser(description="Launch the Pippy activity.")
    parser.add_argument('--pygame', action='store_true', help="Launch the Pygame activity.")
    parser.add_argument('--vte', action='store_true', help="Launch the VTE activity.")
    args = parser.parse_args()
    if args.pygame:
        activity = PyGameActivity(None)
    elif args.vte:
        activity = VteActivity(None)
    else:
        print("Please specify an activity type (--pygame or --vte).")
        return
    activity.show()
    Gtk.main()

if __name__ == '__main__':
    _main()
