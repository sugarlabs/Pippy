import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk

class PyApp(Gtk.Window):

    def __init__(self):
        super(PyApp, self).__init__()

        self.set_title('Botones de radio')
        self.set_position(Gtk.WindowPosition.CENTER_ALWAYS)
        self.set_size_request(250, 150)

        vbox = Gtk.VBox()

        button1 = Gtk.RadioButton(group=None, label='Boton 1')
        button1.connect('toggled', self._activate_cb, 1)
        vbox.pack_start(button1, True, True, 2)

        button2 = Gtk.RadioButton(group=button1, label='Boton 2')
        button2.connect('toggled', self._activate_cb, 2)
        vbox.pack_start(button2, True, True, 2)

        button3 = Gtk.RadioButton(group=button1, label='Boton 3')
        button3.connect('toggled', self._activate_cb, 3)
        vbox.pack_start(button3, True, True, 2)

        self.add(vbox)
        self.show_all()

        self.connect('destroy', Gtk.main_quit)

    def _activate_cb(self, button, button_index):
        if button.get_active():
            print 'Has seleccionado el boton %d' % button_index


PyApp()
Gtk.main()
