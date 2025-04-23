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
from gi.repository import GObject

from gettext import gettext as _
from sugar3.graphics.toolbutton import ToolButton

from notebook import FONT_CHANGE_STEP, DEFAULT_FONT_SIZE


class DevelopViewToolbar(Gtk.Toolbar):
    __gsignals__ = {
        'font-size-changed': (GObject.SIGNAL_RUN_FIRST, None,
                              (int,)),
    }

    def __init__(self, _activity):
        GObject.GObject.__init__(self)

        self._activity = _activity
        self.font_size = DEFAULT_FONT_SIZE

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
        
    def add_buttons_to_toolbar(self, toolbar):
        """Move font resize buttons from view toolbar to the main toolbar"""
        # Remove buttons from view toolbar
        self.remove(self.font_plus)
        self.remove(self.font_minus)
        
        # Update tooltips for main toolbar context
        self.font_plus.set_tooltip(_('Increase font size'))
        self.font_plus.set_accelerator('<Ctrl>equal')
        toolbar.insert(self.font_plus, -1)
        self.font_plus.show()
        
        # Add additional hidden button for Ctrl+plus shortcut
        font_plus_alt = ToolButton('zoom-in')
        font_plus_alt.connect('clicked', self._font_size_increase)
        font_plus_alt.set_accelerator('<Ctrl>plus')
        toolbar.insert(font_plus_alt, -1)
        # Don't show this button, just use it for the accelerator
        
        self.font_minus.set_tooltip(_('Decrease font size'))
        self.font_minus.set_accelerator('<Ctrl>minus')
        toolbar.insert(self.font_minus, -1)
        self.font_minus.show()
        
        return self.font_plus, self.font_minus

    def set_font_size(self, font_size):
        # Apply limits
        font_size = max(8, min(36, font_size))
        if self.font_size != font_size:
            self.font_size = font_size
            self.emit('font-size-changed', self.font_size)

    def _font_size_increase(self, button):
        self.font_size += FONT_CHANGE_STEP
        # Apply maximum limit
        self.font_size = min(36, self.font_size)
        self.emit('font-size-changed', self.font_size)

    def _font_size_decrease(self, button):
        self.font_size -= FONT_CHANGE_STEP
        # Apply minimum limit
        self.font_size = max(8, self.font_size)
        self.emit('font-size-changed', self.font_size)
