#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (C) 2013  Ignacio Rodríguez <ignacio@sugarlabs.org>
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.

import shutil
from gi.repository import Gtk
from gi.repository import Gdk
from gi.repository import GdkPixbuf
from jarabe.journal.model import get_documents_path
from sugar3.activity.activity import get_bundle_path
from sugar3.graphics.toolbutton import ToolButton
from sugar3.graphics.toolbarbox import ToolbarBox
from gettext import gettext as _
import os

DEFAULT_NAME = "default-pippy.svg"
DEFAULT_ICON = os.path.join(get_bundle_path(), 'activity',
                            'activity-default.svg')


def get_document_icons():
    icons = os.listdir(get_documents_path())
    icons_ = []
    for icon in icons:
        if icon.endswith('.svg'):
            icons_.append(icon[:-4])

    return icons_


def get_user_path():
    user = os.path.expanduser("~")
    path = os.path.join(user, ".icons")
    if not os.path.exists(path):
        os.mkdir(path)
    if os.path.exists(DEFAULT_NAME):
        os.remove(DEFAULT_NAME)
    shutil.copy(DEFAULT_ICON, os.path.join(path, DEFAULT_NAME))
    return path


def get_usericons_icons():
    path = get_user_path()
    icons = os.listdir(path)
    icons_ = []
    for icon in icons:
        if icon.endswith('.svg'):
            icons_.append(icon[:-4])

    return icons_


def get_user_icons():
    home = get_usericons_icons()
    documents = get_document_icons()
    final = []

    for x in home:
        final.append(x)

    for x in documents:
        final.append(x)

    return final


class IconDialog(Gtk.Window):
    def __init__(self):
        Gtk.Window.__init__(self)

        self.set_destroy_with_parent(True)

        self.theme = Gtk.IconTheme.get_default()
        self.theme.append_search_path(get_documents_path())

        self._icon = None
        grid = Gtk.Grid()

        self.x, self.y = (Gdk.Screen.width() / 1.5, Gdk.Screen.height() / 1.5)
        self.set_size_request(self.x, self.y)

        self.icons = None
        toolbox = self.build_toolbar()
        self.icons = self.build_scroll()

        grid.attach(toolbox, 0, 1, 1, 1)
        grid.attach(self.icons, 0, 2, 1, 1)

        self.set_decorated(False)
        self.set_skip_pager_hint(True)
        self.set_skip_taskbar_hint(True)
        self.set_position(Gtk.WindowPosition.CENTER_ALWAYS)
        self.set_resizable(False)
        self.set_modal(True)

        self.add(grid)
        self.show_all()

    def build_toolbar(self):
        toolbox = ToolbarBox()

        label = Gtk.Label("\t" + _('Select an icon'))
        label.modify_fg(Gtk.StateType.NORMAL,
                        Gdk.color_parse('white'))

        item = Gtk.ToolItem()
        item.add(label)

        close = ToolButton('entry-cancel')
        close.connect('clicked', lambda x: self.destroy())

        separator = Gtk.SeparatorToolItem()
        separator.props.draw = False
        separator.set_expand(True)

        toolbox.toolbar.insert(item, -1)
        toolbox.toolbar.insert(separator, -1)
        toolbox.toolbar.insert(close, -1)

        return toolbox

    def get_icon(self):
        return self._icon

    def build_scroll(self):
        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)

        icons = self.build_icons()

        scroll.set_size_request(self.x, self.y)
        scroll.add_with_viewport(icons)
        return scroll

    def build_icons(self):
        store = Gtk.ListStore(GdkPixbuf.Pixbuf, str, str)

        icon_view = Gtk.IconView.new_with_model(store)
        icon_view.set_selection_mode(Gtk.SelectionMode.SINGLE)
        icon_view.connect('selection-changed', self.set_icon, store)
        icon_view.set_pixbuf_column(0)
        icon_view.modify_bg(Gtk.StateType.NORMAL, Gdk.color_parse('#D5D5D5'))

        for icon in get_user_icons():
            info = self.theme.lookup_icon(icon, 55,
                                          Gtk.IconLookupFlags.FORCE_SVG)
            if not info:
                continue
            icon_path = os.path.join(get_user_path(), icon + ".svg")
            if not os.path.exists(icon_path):
                icon_path = os.path.join(get_documents_path(), icon + ".svg")

            if not os.path.exists(icon_path):
                icon_path = info.get_filename()

            pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_size(
                        icon_path, 55, 55)
            store.insert(-1, [pixbuf, icon, icon_path])

        return icon_view

    def set_icon(self, widget, model):
        try:
            iter_ = model.get_iter(widget.get_selected_items()[0])
        except:
            return

        icon_path = model.get(iter_, 2)[0]
        self._icon = icon_path
        self.destroy()
