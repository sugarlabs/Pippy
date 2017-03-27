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

import logging
import unicodedata
import re
import uuid

from gi.repository import Gtk
from gi.repository import Gdk
from gi.repository import GObject
from gi.repository import Pango
from gi.repository import GtkSource
from gettext import gettext as _

from sugar3.graphics.toolbutton import ToolButton

from texteditor import TextBufferCollaberizer

tab_object = list()
FONT_CHANGE_STEP = 2
DEFAULT_FONT_SIZE = 12


class TabLabel(Gtk.HBox):
    __gsignals__ = {
        'tab-close': (GObject.SignalFlags.RUN_FIRST,
                      None,
                      ([GObject.TYPE_PYOBJECT])),
    }

    def __init__(self, child, label, path, tabs, editor_id):
        GObject.GObject.__init__(self)

        self.child = child
        self.label_text = label
        self._path = path  # Hide the path in the label
        self.editor_id = editor_id
        self.tabs = tabs

        self.label_box = Gtk.EventBox()
        self._label = Gtk.Label(label=self.label_text)
        self._label.set_alignment(0, 0.5)
        self._label.show()

        self.label_box.add(self._label)
        self.label_box.connect('button-press-event', self._label_clicked)
        self.label_box.show_all()
        self.pack_start(self.label_box, True, True, 5)

        self.label_entry = Gtk.Entry()
        self.label_entry.connect('activate', self._label_entry_cb)
        self.label_entry.connect('focus-out-event', self._label_entry_cb)
        self.pack_start(self.label_entry, True, True, 0)

        button = ToolButton('close-tab')
        button.connect('clicked', self.__button_clicked_cb)
        self.pack_start(button, False, True, 0)
        button.show()
        self._close_button = button
        tab_object.append(self)

    def set_text(self, title):
        self._label.set_text(title)

    def get_text(self):
        return self._label.get_text()

    def get_path(self):
        return self._path

    def set_path(self, path):
        self._path = path

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
        if self.label_entry.get_text() != "":
            self.label_text = self.label_entry.get_text()
        self.label_box.show_all()
        self.label_entry.hide()
        self._label.set_text(self.label_text)


class AddNotebook(Gtk.Notebook):
    '''
    AddNotebook
    -----------
    This subclass has a add button which emits tab-added on clicking the
    button.
    '''
    __gsignals__ = {
        'tab-added': (GObject.SignalFlags.RUN_FIRST,
                      None,
                      ([])),
    }

    def __init__(self):
        Gtk.Notebook.__init__(self)

        self._add_tab = ToolButton('gtk-add')
        self._add_tab.connect('clicked', self._add_tab_cb)
        self._add_tab.show()
        self.set_action_widget(self._add_tab, Gtk.PackType.END)

    def _add_tab_cb(self, button):
        self.emit('tab-added')


class PippySourceView(GtkSource.View):

    def __init__(self, buffer_text, editor_id, collab):
        GtkSource.View.__init__(self)

        text_buffer = GtkSource.Buffer()
        collaberizer = TextBufferCollaberizer(
            text_buffer, editor_id, collab)

        lang_manager = GtkSource.LanguageManager.get_default()
        if hasattr(lang_manager, 'list_languages'):
            langs = lang_manager.list_languages()
        else:
            lang_ids = lang_manager.get_language_ids()
            langs = [lang_manager.get_language(lang_id)
                     for lang_id in lang_ids]
        for lang in langs:
            for m in lang.get_mime_types():
                if m == 'text/x-python':
                    text_buffer.set_language(lang)

        if hasattr(text_buffer, 'set_highlight'):
            text_buffer.set_highlight(True)
        else:
            text_buffer.set_highlight_syntax(True)
        if buffer_text:
            text_buffer.set_text(buffer_text)
            text_buffer.set_modified(False)

        self.set_buffer(text_buffer)
        self.set_size_request(0, int(Gdk.Screen.height() * 0.5))
        self.set_editable(True)
        self.set_cursor_visible(True)
        self.set_show_line_numbers(True)
        self.set_wrap_mode(Gtk.WrapMode.CHAR)
        self.set_insert_spaces_instead_of_tabs(True)
        self.set_tab_width(2)
        self.set_auto_indent(True)

        self.set_can_focus(True)

    # Notebook will call this with appropriate font size
    def set_font_size(self, font_size):
        self.modify_font(
            Pango.FontDescription(
                'Monospace {}'.format(font_size)))


class SourceNotebook(AddNotebook):
    def __init__(self, activity, collab):
        AddNotebook.__init__(self)
        self.activity = activity
        self._collab = collab
        self.set_scrollable(True)
        self.last_tab = 0
        self._font_size = DEFAULT_FONT_SIZE

    def add_tab(self, label=None, buffer_text=None, path=None, editor_id=None):
        self.last_tab += 1
        codesw = Gtk.ScrolledWindow()
        codesw.set_policy(Gtk.PolicyType.AUTOMATIC,
                          Gtk.PolicyType.AUTOMATIC)
        if editor_id is None:
            editor_id = str(uuid.uuid1())
        text_view = PippySourceView(
            buffer_text, editor_id, self._collab)
        text_view.set_font_size(self._font_size)
        codesw.add(text_view)
        text_view.show()
        text_view.grab_focus()
        tabdex = self.get_n_pages() + 1
        if label:
            self.tablabel = TabLabel(codesw, label, path, self, editor_id)
        else:
            self.tablabel = TabLabel(codesw,
                                     _('New Source File %d' % self.last_tab),
                                     path, self, editor_id)
        self.tablabel.connect('tab-close', self._tab_closed_cb)
        self.connect('key-press-event', self._key_press_cb)

        codesw.show_all()

        index = self.append_page(codesw, self.tablabel)
        self.props.page = index  # Set new page as active tab

        # Show close only when tabs > 1
        only_widget = self.get_nth_page(0)
        if self.get_n_pages() == 1:
            self.get_tab_label(only_widget).hide_close_button()
        else:
            self.get_tab_label(only_widget).show_close_button()

    def _key_press_cb(self, widget, event):
        key_name = Gdk.keyval_name(event.keyval)

        if event.get_state() & Gdk.ModifierType.CONTROL_MASK:
            if key_name == 'w':
                if self.get_n_pages() > 1:
                    index = self.get_current_page()
                    self.remove_page(index)
                    tab_object.pop(index)
                    try:
                        logging.debug('deleting session_data %s' %
                                      str(self.activity.session_data[index]))
                        del self.activity.session_data[index]
                    except IndexError:
                        pass
                    # Show close only when tabs > 1
                    only_widget = self.get_nth_page(0)
                    if self.get_n_pages() == 1:
                        self.get_tab_label(only_widget).hide_close_button()
                    else:
                        self.get_tab_label(only_widget).show_close_button()
            elif key_name in ['1', '2', '3', '4', '5', '6', '7', '8', '9']:
                if int(key_name) <= self.get_n_pages():
                    self.set_current_page(int(key_name) - 1)
            elif key_name == 't':
                self.emit('tab-added')
            elif key_name == 'Tab':
                if self.get_current_page() == self.get_n_pages() - 1:
                    self.set_current_page(0)
                else:
                    self.next_page()
            elif event.get_state() & Gdk.ModifierType.SHIFT_MASK:
                if key_name == 'ISO_Left_Tab':
                    if self.get_current_page() == 0:
                        self.set_current_page(self.get_n_pages() - 1)
                    else:
                        self.prev_page()
                else:
                    return False
            else:
                return False
            return True
        return False

    def set_current_label(self, label):
        child = self.get_nth_page(self.get_current_page())
        widget = self.get_tab_label(child)
        widget.set_text(self._purify_file(label))

    def set_current_path(self, path):
        child = self.get_nth_page(self.get_current_page())
        widget = self.get_tab_label(child)
        widget.set_path(path)

    def get_text_buffer(self):
        tab = self.get_nth_page(self.get_current_page()).get_children()
        text_buffer = tab[0].get_buffer()
        return text_buffer

    def get_text_view(self):
        tab = self.get_nth_page(self.get_current_page()).get_children()
        text_view = tab[0]
        return text_view

    def _purify_file(self, label):
        if not label.endswith('.py'):
            label = label + '.py'

        label = label.replace(' ', '_')
        if isinstance(label, unicode):
            label = \
                unicodedata.normalize('NFKD', label).encode('ascii', 'ignore')

        return label

    def get_all_data(self):
        # Returns all the names of files and the buffer contents too.
        names = []
        python_codes = []
        paths = []
        modifieds = []
        editor_ids = []
        for i in range(0, self.get_n_pages()):
            child = self.get_nth_page(i)

            label = self._purify_file(self.get_tab_label(child).get_text())
            names.append(label)

            path = self.get_tab_label(child).get_path()
            paths.append(path)

            text_buffer = child.get_children()[0].get_buffer()
            text = text_buffer.get_text(*text_buffer.get_bounds(),
                                        include_hidden_chars=True)
            python_codes.append(text)

            modifieds.append(text_buffer.get_modified())

            editor_ids.append(self.get_tab_label(child).editor_id)

        return (names, python_codes, paths, modifieds, editor_ids)

    def get_current_file_name(self):
        child = self.get_nth_page(self.get_current_page())
        label = self.get_tab_label(child).get_text()
        label = self._purify_file(label)

        return label

    def set_font_size(self, font_size):
        self._font_size = font_size

        for i in xrange(self.get_n_pages()):
            page = self.get_nth_page(i)
            children = page.get_children()
            children[0].set_font_size(self._font_size)

    def get_font_size(self):
        return self._font_size

    def child_exited_cb(self, *args):
        '''Called whenever a child exits.  If there's a handler, runadd it.'''
        h, self.activity._child_exited_handler = \
            self.activity._child_exited_handler, None
        if h is not None:
            h()

    def _tab_closed_cb(self, notebook, child):
        index = self.page_num(child)
        self.remove_page(index)
        tab_object.pop(index)
        # Hide close button if only one tab present
        if self.get_n_pages() == 1:
            only_widget = self.get_nth_page(0)
            self.get_tab_label(only_widget).hide_close_button()

        try:
            logging.debug('deleting session_data %s' %
                          str(self.activity.session_data[index]))
            del self.activity.session_data[index]
        except IndexError:
            pass

    def rename_tab(self, iterator1):
        for i in range(iterator1, self.get_n_pages()):
            if re.match('New Source File ', tab_object[i].get_text()) != None:
                tab_object[i].label_text = 'New Source File ' + str(self.last_tab+1)
            else:
                tab_object[i].label_text = tab_object[i].get_text()
            tab_object[i]._label.set_text(tab_object[i].label_text)
