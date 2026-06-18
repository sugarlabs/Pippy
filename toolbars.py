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

import os
from gi.repository import Gtk
from gi.repository import GObject

from gettext import gettext as _
from sugar3.graphics.toolbutton import ToolButton
from sugar3.graphics.toggletoolbutton import ToggleToolButton
from sugar3.graphics.icon import Icon
from sugar3.activity.activity import get_bundle_path

from notebook import FONT_CHANGE_STEP, DEFAULT_FONT_SIZE


class DevelopViewToolbar(Gtk.Toolbar):
    __gsignals__ = {
        'font-size-changed': (GObject.SIGNAL_RUN_FIRST, None,
                              (int,)),
        'autocomplete-toggled': (GObject.SIGNAL_RUN_FIRST, None,
                                (bool,)),
    }

    def __init__(self, _activity):
        GObject.GObject.__init__(self)

        self._activity = _activity
        self.font_size = DEFAULT_FONT_SIZE
        
        # Add autocomplete toggle button - moved to beginning for visibility
        self.autocomplete_button = ToggleToolButton('format-text-bold')  # Using a standard Sugar icon
        self.autocomplete_button.set_tooltip(_('Enable/disable code completion'))
        self.autocomplete_button.set_active(True)  # Enable by default
        self.autocomplete_button.connect('toggled', self._autocomplete_toggled)
        self.insert(self.autocomplete_button, -1)
        self.autocomplete_button.show()
        
        # Add separator
        separator = Gtk.SeparatorToolItem()
        separator.props.draw = True
        self.insert(separator, -1)
        separator.show()

        self.font_plus = ToolButton('zoom-in')
        self.font_plus.connect('clicked', self._font_size_increase)
        self.font_plus.set_tooltip(_('Zoom in'))
        self.insert(self.font_plus, -1)
        self.font_plus.show()

        self.font_minus = ToolButton('zoom-out')
        self.font_minus.connect('clicked', self._font_size_decrease)
        self.font_minus.set_tooltip(_('Zoom out'))
        self.insert(self.font_minus, -1)
        self.font_minus.show()

        self.show()

    def set_font_size(self, font_size):
        self.font_size = font_size
        self.emit('font-size-changed', self.font_size)

    def _font_size_increase(self, button):
        self.font_size += FONT_CHANGE_STEP
        self.emit('font-size-changed', self.font_size)

    def _font_size_decrease(self, button):
        self.font_size -= FONT_CHANGE_STEP
        self.emit('font-size-changed', self.font_size)
        
    def _autocomplete_toggled(self, button):
        """Emit signal when autocomplete button is toggled"""
        # Pass both the button and the active state
        is_active = button.get_active()
        self.emit('autocomplete-toggled', button, is_active)
