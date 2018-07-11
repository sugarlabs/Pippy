# Copyright (C) 2015, Batchu Venkat Vishal
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
# MA  02110-1301 USA

import logging

from gi.repository import Gtk

'''
The texteditor module provides a text editor widget
which can be included in any activity and then multiple
users can collaborate and edit together in the editor.
'''


class CollabTextEditor(Gtk.TextView):
    '''
    A CollabTextEditor widget is a adjustable text editor which
    can be placed on an activity screen.

    The `changed` signal is usually emitted when the text in the
    editor is changed by a user.
    The `message` signal is usually emitted when another user makes
    changes in the text editor, so they are reflected in your editor.

    The widget can be embedded in a window which can be displayed.
    Example usage:
        editorinstance = CollabTextEditor(self)
        scrolled_window.add(editorinstance)
        scrolled_window.show()

    '''

    def __init__(self, activity, editor_id, collab):
        Gtk.TextView.__init__(self)
        self.set_editable(True)
        self.set_cursor_visible(True)
        self.set_wrap_mode(Gtk.WrapMode.WORD)
        self.textbuffer = self.get_buffer()
        self._collaberizer = TextBufferCollaberizer(
            self.textbuffer, editor_id, collab)
        self.textbuffer.set_text("")
        self.show()


class TextBufferCollaberizer(object):

    def __init__(self, textbuffer, editor_id, collab):
        self._id = editor_id
        self._buffer = textbuffer
        self._callbacks_status = True
        self.has_initialized = False

        self._collab = collab
        self._collab.connect('message', self.__message_cb)
        self._collab.connect('joined', self.__joined_cb)

        self._buffer.connect('insert-text', self.__text_buffer_inserted_cb)
        self._buffer.connect('delete-range', self.__text_buffer_deleted_cb)
        self._buffer.set_text('')

        if not self._collab._leader:
            # We must be joining an activity and just made the buffer
            self._collab.post(dict(
                action='init_request',
                res_id=self._id
            ))

    '''
    The message callback is called whenever another user edits
    something in the text editor and the changes are reflected
    in the editor or when a new buddy joins and we send them the
    latest version of the text buffer.

    Args:
        buddy : another user who sent the message
        message : updates send over from other users
    '''

    def __message_cb(self, collab, buddy, message):
        action = message.get('action')
        if str(message.get('res_id')) != self._id:
            return

        if action == 'init_response' or action == 'sync_editors':
            self.has_initialized = True
            self._callbacks_status = False
            self._buffer.set_text(message.get('current_content'))
            self._callbacks_status = True
        if action == 'entry_inserted':
            start_iter = self._buffer.get_iter_at_line_offset(
                message.get('start_iter_line'),
                message.get('start_iter_offset'))
            self._callbacks_status = False
            self._buffer.insert(start_iter, message.get('new_text'))
            self._callbacks_status = True
        if action == 'entry_deleted':
            start_iter = self._buffer.get_iter_at_line_offset(
                message.get('start_iter_line'),
                message.get('start_iter_offset'))
            end_iter = self._buffer.get_iter_at_line_offset(
                message.get('end_iter_line'),
                message.get('end_iter_offset'))
            self._callbacks_status = False
            self._buffer.delete(start_iter, end_iter)
            self._callbacks_status = True
        if action == 'init_request':
            text = self._buffer.get_text(
                self._buffer.get_start_iter(),
                self._buffer.get_end_iter(),
                True)
            self._collab.post(dict(
                action='init_response',
                res_id=self._id,
                current_content=text
            ))

    def __joined_cb(self, sender):
        if self._collab._leader:
            return
        self._collab.post(dict(
            action='init_request',
            res_id=self._id
        ))

    '''
    This will send a message to all your buddies to set their editors to
    sync with the text specified as an argument.

    Args:
        text : Text to be set in all the editors
    '''
    def __set_text_synced(self, text):
        if self._callbacks_status is False:
            return
        if self.has_initialized is False:
            self.has_initialized = True
        self._callbacks_status = False
        self._buffer.set_text(text)
        self._callbacks_status = True
        self._collab.post(dict(action='sync_editors',
                               res_id=self._id,
                               current_content=text))

    '''
    The text buffer inserted callback is called whenever text is
    inserted in the editor, so that other users get updated with
    these changes.

    Args:
        textbuffer (:class:`Gtk.TextBuffer`): text storage widget
        start (:class:`Gtk.Iterator`): a pointer to the start position
    '''

    def __text_buffer_inserted_cb(self, textbuffer, start, text, length):
        if self._callbacks_status is False:
            return
        if self.has_initialized is False:
            self.has_initialized = True
        logging.debug('Text inserted is %s' % (text))
        logging.debug('Text has been updated, %s' % (textbuffer.get_text(
            textbuffer.get_start_iter(), textbuffer.get_end_iter(), True)))
        self._collab.post(dict(action='entry_inserted',
                               res_id=self._id,
                               start_iter_offset=start.get_line_offset(),
                               start_iter_line=start.get_line(),
                               new_text=text))

    '''
    The text buffer deleted callback is called whenever any text is
    removed in the editor, so that other users get updated with
    these changes.

    Args:
        textbuffer (:class:`Gtk.TextBuffer`): text storage widget
        start (:class:`Gtk.Iterator`): a pointer to the start position
        end (:class:`Gtk.Iterator`): a pointer to the end position
    '''

    def __text_buffer_deleted_cb(self, textbuffer, start, end):
        if self._callbacks_status is False:
            return
        if self.has_initialized is False:
            self.has_initialized = True
        logging.debug('Text deleted is %s' %
                      (textbuffer.get_text(start, end, True)))
        logging.debug('Text has been updated, %s' % (textbuffer.get_text(
            textbuffer.get_start_iter(), textbuffer.get_end_iter(), True)))
        self._collab.post(dict(action='entry_deleted',
                               res_id=self._id,
                               start_iter_offset=start.get_line_offset(),
                               start_iter_line=start.get_line(),
                               end_iter_offset=end.get_line_offset(),
                               end_iter_line=end.get_line()))
