import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk

class PyApp(Gtk.Window):

    def __init__(self):
        super(PyApp, self).__init__()

        self.set_title('Visor de texto')
        self.set_position(Gtk.WindowPosition.CENTER_ALWAYS)
        self.set_size_request(250, 150)

        scrolled = Gtk.ScrolledWindow()

        textview = Gtk.TextView()
        scrolled.add(textview)

        textbuffer = textview.get_buffer()
        textbuffer.set_text('Multiples lineas\nen un mismo editor\n')

        end = textbuffer.get_end_iter()
        anchor = textbuffer.create_child_anchor(end)
        box = Gtk.HBox()
        textview.add_child_at_anchor(box, anchor)

        button = Gtk.Button('Haz click en mi')
        button.connect('clicked', self._clicked_cb, textbuffer)
        box.pack_start(button, False, False, 0)

        self.add(scrolled)
        self.show_all()

        self.connect('destroy', Gtk.main_quit)

    def _clicked_cb(self, button, textbuffer):
        end = textbuffer.get_end_iter()
        textbuffer.insert(end, 'Haz hecho click en el boton!\n')


PyApp()
Gtk.main()
