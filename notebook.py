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
import subprocess
import json
import os
import threading
from queue import Queue

from gi import require_version
from gi.repository import Gtk
from gi.repository import Gdk
from gi.repository import GObject
from gi.repository import Pango
require_version('GtkSource', '3.0')
from gi.repository import GtkSource
from gettext import gettext as _

from sugar3.graphics.toolbutton import ToolButton
from sugar3.graphics.alert import ConfirmationAlert

from texteditor import TextBufferCollaberizer

tab_object = list()
FONT_CHANGE_STEP = 2
DEFAULT_FONT_SIZE = 12


class PythonAutocompletion:
    """
    Provides autocompletion for Python code using Jedi directly.
    This is a simpler and more direct approach than using the Language Server Protocol.
    """
    
    def __init__(self, text_view):
        self.text_view = text_view
        self.completion_window = None
        self.completion_model = None
        self.completion_list = None
        self.current_word = ""
        self._enabled = True  # Use a private variable with property accessors
        
        try:
            import jedi
            self.jedi = jedi
            logging.debug("Jedi imported successfully for autocompletion")
        except ImportError:
            logging.error("Could not import jedi. Autocompletion disabled.")
            self.jedi = None
            self._enabled = False
    
    @property
    def enabled(self):
        return self._enabled
        
    @enabled.setter
    def enabled(self, value):
        self._enabled = value
        logging.debug(f"Autocompletion {'enabled' if value else 'disabled'}")
        # If disabled, hide the completion window if it's visible
        if not value and self.completion_window and self.completion_window.get_visible():
            self.completion_window.hide()
    
    def request_completion(self, text, position):
        """Request completion at the given position using Jedi"""
        if not self.jedi or not self._enabled:
            logging.debug("Completion request skipped - Jedi not available or disabled")
            return
            
        line = position[0] + 1  # Jedi uses 1-based line numbers
        column = position[1]
        
        logging.debug(f"Requesting completion at line {line}, column {column}")
        logging.debug(f"Current word being completed: '{self.current_word}'")
        
        try:
            script = self.jedi.Script(code=text)
            completions = script.complete(line=line, column=column)
            
            if completions:
                logging.debug(f"Found {len(completions)} completions")
                self._show_completion_window(completions)
            else:
                logging.debug("No completions found")
                if self.completion_window and self.completion_window.get_visible():
                    self.completion_window.hide()
        except Exception as e:
            logging.error(f"Error getting completions: {e}")
    
    def _show_completion_window(self, completions):
        """Display a completion window with the provided Jedi completions"""
        if not completions:
            return
            
        # Close existing window if open
        if self.completion_window and self.completion_window.get_visible():
            self.completion_window.hide()
        
        # Create a new window
        self.completion_window = Gtk.Window(type=Gtk.WindowType.POPUP)
        self.completion_window.set_property("decorated", False)
        self.completion_window.set_property("modal", False)
        self.completion_window.set_property("skip-taskbar-hint", True)
        self.completion_window.set_property("skip-pager-hint", True)
        
        # Create a frame to add a border
        frame = Gtk.Frame()
        frame.set_shadow_type(Gtk.ShadowType.OUT)
        
        # Create a scrolled window
        scrolled_window = Gtk.ScrolledWindow()
        scrolled_window.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        
        # Create a list view for completion items
        self.completion_model = Gtk.ListStore(str, str, str)  # label, detail, insert_text
        
        for completion in completions:
            label = completion.name
            detail = completion.type
            insert_text = completion.name
            
            self.completion_model.append([label, detail, insert_text])
        
        self.completion_list = Gtk.TreeView(model=self.completion_model)
        self.completion_list.set_headers_visible(False)
        self.completion_list.set_enable_search(False)
        
        # Add columns
        renderer = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn("Suggestion", renderer, text=0)
        self.completion_list.append_column(column)
        
        renderer = Gtk.CellRendererText()
        renderer.set_property("style", Pango.Style.ITALIC)
        renderer.set_property("foreground", "blue")
        column = Gtk.TreeViewColumn("Detail", renderer, text=1)
        self.completion_list.append_column(column)
        
        # Connect signals
        self.completion_list.connect("row-activated", self._on_completion_activated)
        
        # Select the first item by default
        if len(completions) > 0:
            selection = self.completion_list.get_selection()
            selection.select_path(Gtk.TreePath.new_first())
        
        # Handle keyboard navigation and Enter key
        self.completion_list.connect("key-press-event", self._on_completion_key_press)
        
        # Pack everything
        scrolled_window.add(self.completion_list)
        frame.add(scrolled_window)
        self.completion_window.add(frame)
        
        # Position the window near cursor
        buffer = self.text_view.get_buffer()
        cursor_mark = buffer.get_insert()
        cursor_iter = buffer.get_iter_at_mark(cursor_mark)
        location = self.text_view.get_iter_location(cursor_iter)
        win_x, win_y = self.text_view.buffer_to_window_coords(
            Gtk.TextWindowType.WIDGET, location.x, location.y)
        
        window = self.text_view.get_window(Gtk.TextWindowType.WIDGET)
        screen_x, screen_y = window.get_root_coords(win_x, location.y + location.height)
        
        max_height = min(300, 24 * len(completions))
        self.completion_window.set_size_request(300, max_height)
        self.completion_window.move(screen_x, screen_y)
        self.completion_window.show_all()
        
        # Set focus on the completion list to enable keyboard navigation
        self.completion_list.grab_focus()
    
    def _on_completion_activated(self, treeview, path, column):
        """Handle the selection of a completion item"""
        model = treeview.get_model()
        iter = model.get_iter(path)
        insert_text = model.get_value(iter, 2)
        
        buffer = self.text_view.get_buffer()
        cursor_mark = buffer.get_insert()
        cursor_iter = buffer.get_iter_at_mark(cursor_mark)
        
        # Handle word replacement more intelligently
        if self.current_word:
            # Find the start position of the current word
            word_start = cursor_iter.copy()
            
            if '.' in self.current_word:
                # For dot completions, only replace after the dot
                # For example, if typing "os.pa" and selecting "path", we want "os.path"
                dot_index = self.current_word.rindex('.')
                prefix = self.current_word[:dot_index+1]  # Include the dot
                suffix = self.current_word[dot_index+1:]
                
                # Move back just to the start of the suffix (after the dot)
                word_start.backward_chars(len(suffix))
                
                # Delete just the part after the dot
                buffer.delete(word_start, cursor_iter)
                
                # Insert the completion (don't prepend the module prefix)
                buffer.insert(word_start, insert_text)
            else:
                # For regular completions (no dot), replace the entire word
                word_start.backward_chars(len(self.current_word))
                buffer.delete(word_start, cursor_iter)
                buffer.insert(word_start, insert_text)
        else:
            # If no current word, just insert at cursor
            buffer.insert(cursor_iter, insert_text)
        
        # Hide the completion window
        self.completion_window.hide()
        
        # Return focus to the text view
        self.text_view.grab_focus()
    
    def _on_completion_key_press(self, widget, event):
        """Handle key press events in the completion window"""
        keyval = event.keyval
        
        if keyval == Gdk.KEY_Return or keyval == Gdk.KEY_KP_Enter:
            # Get the selected item
            selection = widget.get_selection()
            model, iter = selection.get_selected()
            if iter:
                path = model.get_path(iter)
                self._on_completion_activated(widget, path, widget.get_column(0))
            return True
            
        elif keyval == Gdk.KEY_Escape:
            self.completion_window.hide()
            self.text_view.grab_focus()
            return True
            
        return False
    
    def close(self):
        """Clean up resources"""
        if self.completion_window:
            self.completion_window.hide()


class TabLabel(Gtk.HBox):
    __gsignals__ = {
        'tab-close': (GObject.SignalFlags.RUN_FIRST,
                      None,
                      ([GObject.TYPE_PYOBJECT])),
        'tab-rename': (GObject.SignalFlags.RUN_FIRST,
                      None,
                      ([GObject.TYPE_PYOBJECT, GObject.TYPE_PYOBJECT, ])),
        'tab-switch': (GObject.SignalFlags.RUN_FIRST,
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

    def set_text(self, label):
        self.label_text = label
        self._label.set_text(self.label_text)

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
            self.emit('tab-switch', self.child)
        else:
            self.label_entry.set_text(self.label_text)
            eventbox.hide()
            self.label_entry.grab_focus()
            self.label_entry.show()

    def _label_entry_cb(self, entry, focus=None):
        label = self.label_entry.get_text()
        if label != "":
            if label != self.label_text:
                self.label_text = label
                self.emit('tab-rename', self.child, label)
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
        'tab-renamed': (GObject.SignalFlags.RUN_FIRST,
                      None,
                      ([GObject.TYPE_PYOBJECT, GObject.TYPE_PYOBJECT, ])),
        'tab-closed': (GObject.SignalFlags.RUN_FIRST,
                      None,
                      ([GObject.TYPE_PYOBJECT, ])),
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

        self._css_provider = Gtk.CssProvider()
        self.set_light()
        self.get_style_context().add_provider(
            self._css_provider, Gtk.STYLE_PROVIDER_PRIORITY_USER)

        text_buffer = GtkSource.Buffer()
        TextBufferCollaberizer(text_buffer, editor_id, collab)

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
        
        # Initialize autocompletion
        self.completion = PythonAutocompletion(self)
        self.connect("key-press-event", self._on_key_press)
        self.current_word = ""

        self.set_can_focus(True)

    def _on_key_press(self, widget, event):
        """Handle key press events for autocompletion"""
        keyval = event.keyval
        state = event.state
        
        key_name = Gdk.keyval_name(keyval)
        logging.debug(f"Key press: {key_name}, state: {state}")
        
        # If autocompletion is disabled, don't handle special keys
        if not hasattr(self, 'completion') or not self.completion.enabled:
            logging.debug("Autocompletion disabled or not initialized")
            return False
        
        # Handle Ctrl+Space for manual completion
        if keyval == Gdk.KEY_space and state & Gdk.ModifierType.CONTROL_MASK:
            logging.debug("Ctrl+Space pressed, manually triggering completion")
            self._trigger_completion()
            return True
            
        # Automatically trigger on alphanumeric keys, dot, underscore
        if (Gdk.KEY_a <= keyval <= Gdk.KEY_z or 
            Gdk.KEY_A <= keyval <= Gdk.KEY_Z or
            Gdk.KEY_0 <= keyval <= Gdk.KEY_9 or
            keyval == Gdk.KEY_period or
            keyval == Gdk.KEY_underscore):
            
            logging.debug(f"Detected trigger key: {key_name}")
            # Let the default handler add the character first
            GObject.timeout_add(50, self._trigger_completion)
            return False
            
        # Escape key should hide completion window if visible
        if keyval == Gdk.KEY_Escape and self.completion.completion_window:
            if self.completion.completion_window.get_visible():
                logging.debug("Escape pressed, hiding completion window")
                self.completion.completion_window.hide()
                return True
                
        return False
        
    def _trigger_completion(self):
        """Trigger autocompletion at the current cursor position"""
        # Check if autocompletion is enabled
        if not hasattr(self, 'completion') or not self.completion.enabled:
            logging.debug("Autocompletion disabled or not available")
            return False
            
        logging.debug("Triggering autocompletion")
        buffer = self.get_buffer()
        cursor_mark = buffer.get_insert()
        cursor_iter = buffer.get_iter_at_mark(cursor_mark)
        
        # Get the start of the current line
        line_start = cursor_iter.copy()
        line_start.set_line_offset(0)
        
        # Get line and column of cursor position (0-based)
        line = cursor_iter.get_line()
        column = cursor_iter.get_line_offset()
        logging.debug(f"Cursor position: line {line}, column {column}")
        
        # Get the current line text up to the cursor
        line_text = buffer.get_text(line_start, cursor_iter, False)
        logging.debug(f"Current line text up to cursor: '{line_text}'")
        
        # Extract the current word being typed
        match = re.search(r'[A-Za-z0-9_\.]+$', line_text)
        self.current_word = match.group(0) if match else ""
        self.completion.current_word = self.current_word
        logging.debug(f"Current word: '{self.current_word}'")
        
        # Always trigger for period/dot (object attribute access)
        trigger_for_dot = self.current_word.endswith('.')
        
        # If the word is too short and not ending with a dot, don't trigger
        if len(self.current_word) < 1 and not trigger_for_dot:
            logging.debug(f"Word too short ('{self.current_word}'), not triggering completion")
            if self.completion.completion_window:
                self.completion.completion_window.hide()
            return False
        
        # Get the full buffer text
        start_iter = buffer.get_start_iter()
        end_iter = buffer.get_end_iter()
        text = buffer.get_text(start_iter, end_iter, False)
        logging.debug(f"Sending request with buffer of length {len(text)}")
        
        # Request completion from Jedi
        self.completion.request_completion(text, (line, column))
        return False

    # Notebook will call this with appropriate font size
    def set_font_size(self, font_size):
        self.modify_font(
            Pango.FontDescription(
                'Monospace {}'.format(font_size)))

    def set_dark(self):
        theme = b"""
            textview text {
                background: @black;
                color: @white;
            }"""
        self._css_provider.load_from_data(theme)

    def set_light(self):
        theme = b"""
            textview text {
                background: @white;
                color: @black;
            }"""
        self._css_provider.load_from_data(theme)
        
    def close(self):
        """Clean up resources when the view is closed"""
        if hasattr(self, 'completion'):
            self.completion.close()


class SourceNotebook(AddNotebook):
    def __init__(self, activity, collab, edit_toolbar=None):
        AddNotebook.__init__(self)
        self.activity = activity
        self._collab = collab
        self._edit_toolbar = edit_toolbar
        self.set_scrollable(True)
        self.last_tab = 0
        self._font_size = DEFAULT_FONT_SIZE
        self._autocomplete_enabled = True

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
        
        # Set initial autocomplete state based on notebook setting
        text_view.completion.enabled = self._autocomplete_enabled
        
        if label:
            tablabel = TabLabel(codesw, label, path, self, editor_id)
        else:
            tablabel = TabLabel(codesw,
                                     _('New Source File %d' % self.last_tab),
                                     path, self, editor_id)
        tablabel.connect('tab-close', self._tab_closed_cb)
        tablabel.connect('tab-rename', self._tab_renamed_cb)
        tablabel.connect('tab-switch', self._tab_switched_cb)
        self.connect('key-press-event', self._key_press_cb)
        self.connect('key-release-event', self._key_release_cb)

        codesw.show_all()

        index = self.append_page(codesw, tablabel)
        self.props.page = index  # Set new page as active tab

        # Show close only when tabs > 1
        only_widget = self.get_nth_page(0)
        if self.get_n_pages() == 1:
            self.get_tab_label(only_widget).hide_close_button()
        else:
            self.get_tab_label(only_widget).show_close_button()
            
    def set_autocomplete_enabled(self, enabled):
        """Enable or disable autocompletion for all source views"""
        self._autocomplete_enabled = enabled
        
        if enabled:
            logging.debug("Autocompletion enabled")
        else:
            logging.debug("Autocompletion disabled")
            
            # Hide any visible completion windows when disabled
            for i in range(self.get_n_pages()):
                page = self.get_nth_page(i)
                children = page.get_children()
                text_view = children[0]
                if (hasattr(text_view, 'completion') and 
                    text_view.completion.completion_window and 
                    text_view.completion.completion_window.get_visible()):
                    text_view.completion.completion_window.hide()
        
        # Update all existing source views
        for i in range(self.get_n_pages()):
            page = self.get_nth_page(i)
            children = page.get_children()
            text_view = children[0]
            if hasattr(text_view, 'completion'):
                text_view.completion.enabled = enabled

    def _key_press_cb(self, widget, event):
        key_name = Gdk.keyval_name(event.keyval)

        if event.get_state() & Gdk.ModifierType.CONTROL_MASK:
            if key_name == 'w':
                if self.get_n_pages() > 1:
                    self._tab_closed_cb(
                        None, self.get_nth_page(self.get_current_page()))
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

    def update_edit_toolbar(self, text_buffer=None):
        if self._edit_toolbar is None:
            return
        if text_buffer is None:
            text_buffer = self.get_text_buffer()
        self._edit_toolbar.undo.set_sensitive(text_buffer.can_undo())
        self._edit_toolbar.redo.set_sensitive(text_buffer.can_redo())
    
    def _key_release_cb(self, widget, event):
        self.update_edit_toolbar()

    def set_current_label(self, label):
        child = self.get_nth_page(self.get_current_page())
        widget = self.get_tab_label(child)
        widget.set_text(self.purify_name(label))

    def set_current_path(self, path):
        child = self.get_nth_page(self.get_current_page())
        widget = self.get_tab_label(child)
        widget.set_path(path)

    def get_text_buffer(self):
        tab = self.get_nth_page(self.get_current_page()).get_children()
        text_buffer = tab[0].get_buffer()
        return text_buffer

    def get_text_view(self):
        page = self.get_current_page()
        if page == -1:
            return None
        tab = self.get_nth_page(page).get_children()
        text_view = tab[0]
        return text_view

    def purify_name(self, label):
        if not label.endswith('.py'):
            label = label + '.py'

        label = label.replace(' ', '_')
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

            label = self.get_tab_label(child).get_text()
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
        label = self.purify_name(label)

        return label

    def set_font_size(self, font_size):
        self._font_size = font_size

        for i in range(self.get_n_pages()):
            page = self.get_nth_page(i)
            children = page.get_children()
            children[0].set_font_size(self._font_size)

    def get_font_size(self):
        return self._font_size

    def set_light(self):
        for i in range(self.get_n_pages()):
            page = self.get_nth_page(i)
            children = page.get_children()
            children[0].set_light()

    def set_dark(self):
        for i in range(self.get_n_pages()):
            page = self.get_nth_page(i)
            children = page.get_children()
            children[0].set_dark()

    def child_exited_cb(self, *args):
        '''Called whenever a child exits.  If there's a handler, runadd it.'''
        h, self.activity._child_exited_handler = \
            self.activity._child_exited_handler, None
        if h is not None:
            h()

    def __tab_close(self, index):
        page = self.get_nth_page(index)
        if page:
            # Close and clean up the source view
            text_view = page.get_children()[0]
            if hasattr(text_view, 'close'):
                text_view.close()
                
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

    def _tab_closed_cb(self, notebook, child):
        index = self.page_num(child)

        page = self.get_nth_page(index)

        text_buffer = page.get_children()[0].get_buffer()
        empty = text_buffer.get_char_count() == 0

        if empty:
            self.__tab_close(index)
            self.emit('tab-closed', index)
            return

        tablabel = self.get_tab_label(page)
        path = tablabel.get_path()
        example = self.activity.is_example(path)
        pristine = not text_buffer.get_modified()

        if example and pristine:
            self.__tab_close(index)
            self.emit('tab-closed', index)
            return

        alert = ConfirmationAlert()
        alert.props.title = _('Erase')
        alert.props.msg = _('Do you want to permanently erase \"%s\"?') \
                          % tablabel.get_text()
        alert.connect('response', self._tab_close_alert_response_cb, index)
        self.activity.add_alert(alert)

    def _tab_close_alert_response_cb(self, alert, response_id, index):
        self.activity.remove_alert(alert)

        if response_id is not Gtk.ResponseType.OK:
            return

        logging.debug(
            'SourceNotebook._tab_close_alert_response_cb %r' % (index))
        self.__tab_close(index)
        self.emit('tab-closed', index)

    def close_tab(self, index):
        logging.debug('SourceNotebook.close_tab %r' % (index))
        self.__tab_close(index)

    def _tab_renamed_cb(self, tablabel, child, name):
        index = self.page_num(child)
        logging.debug('SourceNotebook._tab_renamed_cb %r %r' % (index, name))
        self.emit('tab-renamed', index, name)

    def _tab_switched_cb(self, notebook, child):
        index = self.page_num(child)
        page = self.get_nth_page(index)
        text_buffer = page.get_children()[0].get_buffer()
        self.update_edit_toolbar(text_buffer)

    def rename_tab(self, index, name):
        logging.debug('SourceNotebook.rename_tab %r %r' % (index, name))
        page = self.get_nth_page(index)
        tablabel = self.get_tab_label(page)
        tablabel.set_text(name)
