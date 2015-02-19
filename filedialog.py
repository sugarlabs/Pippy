# -*- coding: utf-8 -*-
# Copyright (C) 2014 Walter Bender
# Copyright (C) 2014 Ignacio Rodríguez <ignacio@sugarlabs.org>
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

from gi.repository import Gtk, Gdk
from sugar3.graphics.toolbarbox import ToolbarBox
from sugar3.graphics.toolbutton import ToolButton
from gettext import gettext as _
import os


class FileDialog(Gtk.Dialog):
    """
    Simple file dialog:

    from filedialog import FileDialog
    dialog = FileDialog(['Graphics', '/path/of/graphics'])
    dialog.run()
    path = dialog.get_path()
    """

    def __init__(self, dirs, window=None, button=None):
        Gtk.Dialog.__init__(self, flags=Gtk.DialogFlags.DESTROY_WITH_PARENT)

        self.example_path = None
        self.expanders = []
        self.dirs = dirs
        self.button = button

        x, y = (Gdk.Screen.width() / 1.5, Gdk.Screen.height() / 1.5)
        self.set_size_request(x, y)

        toolbox = self.build_toolbar()
        expands = self.build_scroll()

        self.vbox.pack_start(toolbox, False, False, 0)

        self.vbox.pack_start(expands, True, True, 5)

        self.set_decorated(False)
        self.set_skip_pager_hint(True)
        self.set_skip_taskbar_hint(True)
        self.set_resizable(False)
        self.set_modal(True)

        self.modify_bg(Gtk.StateType.NORMAL, Gdk.color_parse('#F3EEEE'))
        self.show_all()

    def get_path(self):
        return self.example_path

    def _destroy(self, widget, sample=False):
        if sample:
            self.example_path = widget.get_tooltip_text()

        if self.button:
            self.button.set_icon_name("pippy-openoff")

        self.destroy()

    def build_toolbar(self):
        toolbox = ToolbarBox()
        toolbar = toolbox.toolbar

        label = Gtk.Label(_('Open an example bundle'))
        label.modify_fg(Gtk.StateType.NORMAL,
                        Gdk.color_parse('white'))

        item = Gtk.ToolItem()
        item.add(label)

        close = ToolButton('entry-cancel')
        close.connect('clicked', self._destroy)

        separator = Gtk.SeparatorToolItem()
        separator.props.draw = False
        separator.set_expand(True)

        toolbar.insert(item, -1)
        toolbar.insert(separator, -1)
        toolbar.insert(close, -1)

        toolbox.set_size_request(-1, 35)

        return toolbox

    def build_scroll(self):
        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.AUTOMATIC,
                          Gtk.PolicyType.AUTOMATIC)

        vbox = Gtk.VBox()
        scroll.add_with_viewport(vbox)

        dirs = self.dirs
        for dir_ in dirs:
            dir_path = dir_[1]
            dir_name = dir_[0]
            expand = self.build_expand(dir_path, dir_name)
            if not expand:
                continue
            vbox.pack_start(expand, False, False, 2)
            expand.show()
            self.expanders.append(expand)

        return scroll

    def build_expand(self, path, name):
        if not os.path.exists(path):
            return None

        expander = Gtk.Expander()
        expander.set_label(name)
        expander.modify_fg(Gtk.StateType.NORMAL,
                           Gdk.color_parse('black'))

        vbox = Gtk.VBox()
        files = sorted(os.listdir(path))

        if not files:
            return None

        for _file in files:
            if _file.endswith('~'):
                continue
            entry = {"name": _(_file.capitalize()),
                     "path": os.path.join(path, _file)}

            button = Gtk.Button(entry['name'])
            button.set_tooltip_text(entry['path'])
            button.set_has_tooltip(False)
            button.connect('clicked', self._destroy, True)
            vbox.pack_start(button, False, False, 1)

        expander.add(vbox)

        return expander
