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
from sugar3.graphics.toolbutton import ToolButton
from sugar3.graphics.toolbarbox import ToolbarBox
from sugar3.graphics import style
from gettext import gettext as _
import os

SUGAR_ARTWORK = [_('Actions'), _('Emblems'), _('Documents')]


def get_document_icons():
    icons = os.listdir(get_documents_path())
    icons_ = []
    for icon in icons:
        if icon.endswith('.svg'):
            icons_.append(icon[:-4])

    return icons_

SUGAR_ICONS = {
    _('Actions'): ['media-playlist-repeat-insensitive',
    'media-playlist-shuffle-insensitive',
    'format-justify-left',
    'cell-height',
    'media-playback-stop-insensitive',
    'select-all', 'format-columns-triple', 'column-insert',
    'go-right', 'cell-format', 'format-justify-right', 'row-insert',
    'entry-search', 'invite', 'format-text-underline', 'entry-stop',
    'view-return', 'transfer-from-text-uri-list', 'cell-size', 'column-remove',
    'insert-image', 'edit-clear', 'view-radial', 'view-lastedit',
    'media-seek-forward-insensitive', 'row-remove', 'zoom-home',
    'zoom-best-fit', 'media-playlist-repeat', 'media-eject-insensitive',
    'view-fullscreen', 'format-text-leading', 'transfer-from-text-x-generic',
    'select-none', 'toolbar-view', 'media-playback-pause', 'format-text-bold',
    'media-playback-start-insensitive', 'go-home', 'view-freeform', 'go-next',
    'transfer-from-image-x-generic', 'media-seek-backward', 'list-add',
    'edit-description', 'toolbar-colors', 'cell-width',
    'transfer-from-audio-x-generic', 'zoom-in', 'zoom-groups',
    'media-seek-forward', 'go-up', 'view-list', 'format-justify-center',
    'transfer-from', 'media-playback-pause-insensitive', 'media-playback-stop',
    'go-previous', 'go-left', 'transfer-from-video-x-generic',
    'media-playlist-shuffle', 'zoom-out', 'toolbar-edit', 'go-next-paired',
    'system-logout', 'view-source', 'tray-hide', 'edit-copy', 'insert-table',
    'view-size', 'format-justify-fill', 'go-down', 'format-columns-single',
    'transfer-to-text-uri-list', 'activity-stop',
    'transfer-to-audio-x-generic', 'view-box', 'zoom-original',
    'edit-undo', 'document-send', 'view-refresh',
    'document-save', 'system-shutdown', 'entry-refresh', 'dialog-cancel',
    'system-search', 'transfer-to-image-x-generic',
    'transfer-from-application-octet-stream',
    'media-seek-backward-insensitive', 'dialog-ok', 'edit-redo',
    'view-created', 'activity-start', 'format-text-size', 'view-triangle',
    'entry-cancel', 'media-eject', 'edit-paste', 'tray-show',
    'transfer-to-video-x-generic', 'transfer-to', 'view-details',
    'system-restart', 'zoom-activity', 'media-record',
    'transfer-to-text-x-generic', 'zoom-to-width', 'format-columns-double',
    'format-text-italic', 'tray-favourite', 'list-remove',
    'transfer-to-application-octet-stream', 'view-spiral',
    'media-record-insensitive', 'edit-delete', 'toolbar-help',
    'edit-duplicate', 'media-playback-start', 'zoom-neighborhood',
    'go-previous-paired'],
    _('Emblems'): ['emblem-busy', 'emblem-charging', 'emblem-downloads',
    'emblem-favorite', 'emblem-locked', 'emblem-notification',
    'emblem-outofrange', 'emblem-question', 'emblem-view-source',
    'emblem-warning'],
    _('Documents'): get_document_icons()
}



class IconDialog(Gtk.Window):
    def __init__(self):
        Gtk.Window.__init__(self)

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

        grid = Gtk.Grid()
        current = 0
        for icon in SUGAR_ARTWORK:
            expander = self.build_icons(icon)
            grid.attach(expander, 0, current, 1, 1)
            current += 1

        scroll.set_size_request(self.x, self.y)
        scroll.add_with_viewport(grid)
        return scroll

    def build_icons(self, category):
        icons = SUGAR_ICONS[category]

        if len(icons) < 1:
            return Gtk.EventBox()

        store = Gtk.ListStore(GdkPixbuf.Pixbuf, str, str)


        icon_view = Gtk.IconView.new_with_model(store)
        icon_view.set_selection_mode(Gtk.SelectionMode.SINGLE)
        icon_view.connect('selection-changed', self.set_icon, store)
        icon_view.set_pixbuf_column(0)
        icon_view.modify_bg(Gtk.StateType.NORMAL, Gdk.color_parse('#D5D5D5'))

        for icon in icons:
            info = self.theme.lookup_icon(icon, 55,
                    Gtk.IconLookupFlags.FORCE_SVG)
            if not info:
                continue
            icon_path = info.get_filename()
            if category == _('Documents'):
                icon_path = os.path.join(get_documents_path(), icon + ".svg")

            pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_size(
                        icon_path, 55, 55)
            store.insert(-1, [pixbuf, icon, icon_path])

        expand = Gtk.Expander()
        expand.set_label(category)
        expand.add(icon_view)
        return expand

    def set_icon(self, widget, model):
        try:
            iter_ = model.get_iter(widget.get_selected_items()[0])
        except:
            return

        icon_path = model.get(iter_, 2)[0]
        self._icon = icon_path
        self.destroy()

    def get_icon(self):
        return self._icon
