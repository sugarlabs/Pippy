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

    def set_font_size(self, font_size):
        self.font_size = font_size
        self.emit('font-size-changed', self.font_size)

    def _font_size_increase(self, button):
        self.font_size += FONT_CHANGE_STEP
        self.emit('font-size-changed', self.font_size)

    def _font_size_decrease(self, button):
        self.font_size -= FONT_CHANGE_STEP
        self.emit('font-size-changed', self.font_size)
