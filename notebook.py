# -*- coding: utf-8 -*-
# Copyright (C) 2014 Walter Bender
# Copyright (C) 2014 Sai Vineet
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

from gi.repository import Gtk
from gi.repository import Gdk
from gi.repository import GObject
from gi.repository import Vte
from gi.repository import Pango
from gi.repository import GtkSource
from gettext import gettext as _
from sugar3.graphics.icon import Icon
from port.style import font_zoom
from sugar3.graphics import style

from sugar3.graphics.toolbutton import ToolButton


SIZE_X = Gdk.Screen.width()
SIZE_Y = Gdk.Screen.height()


class TabLabel(Gtk.HBox):
    __gsignals__ = {
        'tab-close': (GObject.SignalFlags.RUN_FIRST,
                      None,
                      ([GObject.TYPE_PYOBJECT])),
    }

    def __init__(self, child, label, tabs):
        GObject.GObject.__init__(self)

        self.child = child
        self.label_text = label
        self.tabs = tabs

        self.label_box = Gtk.EventBox()
        self._label = Gtk.Label(label=self.label_text)
        self._label.set_alignment(0, 0.5)
        self._label.show()

        self.label_box.add(self._label)
        self.label_box.connect("button-press-event", self._label_clicked)
        self.label_box.show_all()
        self.pack_start(self.label_box, True, True, 5)

        self.label_entry = Gtk.Entry()
        self.label_entry.connect("activate", self._label_entry_cb)
        self.label_entry.connect("focus-out-event", self._label_entry_cb)
        self.pack_start(self.label_entry, True, True, 0)

        button = ToolButton("close-tab")
        button.connect('clicked', self.__button_clicked_cb)
        self.pack_start(button, False, True, 0)
        button.show()
        self._close_button = button

    def set_text(self, title):
        self._label.set_text(title)

    def get_text(self):
        return self._label.get_text()

    def update_size(self, size):
        self.set_size_request(size, -1)

    def hide_close_button(self):
        self._close_button.hide()

    def show_close_button(self):
        self._close_button.show()

    def __button_clicked_cb(self, button):
        self.emit('tab-close', self.child)

    def _label_clicked(self, eventbox, data):
        if self.tabs.page_num(self.child) is not self.tabs.get_current_page():
            self.child.grab_focus()
        else:
            self.label_entry.set_text(self.label_text)
            eventbox.hide()
            self.label_entry.grab_focus()
            self.label_entry.show()

    def _label_entry_cb(self, entry, focus=None):
        self.label_text = self.label_entry.get_text()
        self.label_box.show_all()
        self.label_entry.hide()
        self._label.set_text(self.label_text)


"""
    AddNotebook
    -----------
    This subclass has a add button which emits tab-added on clicking the
    button.
"""


class AddNotebook(Gtk.Notebook):
    __gsignals__ = {
        'tab-added': (GObject.SignalFlags.RUN_FIRST,
                      None,
                      ([])),
    }

    def __init__(self):
        Gtk.Notebook.__init__(self)

        self._add_tab = ToolButton("gtk-add")
        self._add_tab.connect("clicked", self._add_tab_cb)
        self._add_tab.show()
        self.set_action_widget(self._add_tab, Gtk.PackType.END)

    def _add_tab_cb(self, button):
        self.emit("tab-added")


class SourceNotebook(AddNotebook):
    def __init__(self, activity):
        AddNotebook.__init__(self)
        self.activity = activity
        self.set_scrollable(True)

    def add_tab(self, label=None, buffer_text=None):

        # Set text_buffer
        text_buffer = GtkSource.Buffer()
        lang_manager = GtkSource.LanguageManager.get_default()
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

        if buffer_text:
            text_buffer.set_text(buffer_text)

        # Set up SourceView
        text_view = GtkSource.View()
        text_view.set_buffer(text_buffer)
        text_view.set_size_request(0, int(SIZE_Y * 0.5))
        text_view.set_editable(True)
        text_view.set_cursor_visible(True)
        text_view.set_show_line_numbers(True)
        text_view.set_wrap_mode(Gtk.WrapMode.CHAR)
        text_view.set_insert_spaces_instead_of_tabs(True)
        text_view.set_tab_width(2)
        text_view.set_auto_indent(True)
        text_view.modify_font(
            Pango.FontDescription("Monospace " +
                                  str(font_zoom(style.FONT_SIZE))))

        codesw = Gtk.ScrolledWindow()
        codesw.set_policy(Gtk.PolicyType.AUTOMATIC,
                          Gtk.PolicyType.AUTOMATIC)
        codesw.add(text_view)

        tabdex = self.get_n_pages() + 1
        if label:
            tablabel = TabLabel(codesw, label, self)
        else:
            tablabel = TabLabel(codesw,
                                _("New Source File %d" % tabdex),
                                self)
        tablabel.connect("tab-close", self._tab_closed_cb)
        codesw.show_all()
        index = self.append_page(codesw, tablabel)
        self.props.page = index  # Set new page as active tab

    def set_current_label(self, label):
        child = self.get_nth_page(self.get_current_page())
        widget = self.get_tab_label(child)
        widget.set_text(self._purify_file(label))

    def get_text_buffer(self):
        tab = self.get_nth_page(self.get_current_page()).get_children()
        text_buffer = tab[0].get_buffer()
        return text_buffer

    def get_text_view(self):
        tab = self.get_nth_page(self.get_current_page()).get_children()
        text_view = tab[0]
        return text_view

    def _purify_file(self, label):
        import unicodedata

        if not label.endswith(".py"):
            label = label + ".py"

        label = label.replace(" ", "_")
        if isinstance(label, unicode):
            label = \
                unicodedata.normalize('NFKD', label).encode('ascii', 'ignore')

        return label

    def get_all_data(self):
        # Returns all the names of files and the buffer contents too.
        names = []
        contents = []
        for i in range(0, self.get_n_pages()):
            child = self.get_nth_page(i)
            text_buffer = child.get_children()[0].get_buffer()
            text = text_buffer.get_text(*text_buffer.get_bounds(),
                                        include_hidden_chars=True)
            contents.append(text)

            label = self._purify_file(self.get_tab_label(child).get_text())

            names.append(label)

        return (names, contents)

    def get_current_file_name(self):
        child = self.get_nth_page(self.get_current_page())
        label = self.get_tab_label(child).get_text()
        label = self._purify_file(label)

        return label

    def child_exited_cb(self, *args):
        """Called whenever a child exits.  If there's a handler, runadd it."""
        h, self.activity._child_exited_handler = \
            self.activity._child_exited_handler, None
        if h is not None:
            h()

    def _tab_closed_cb(self, notebook, child):
        index = self.page_num(child)
        self.remove_page(index)
        try:
            del self.activity.session_data[index]
        except IndexError:
            pass
