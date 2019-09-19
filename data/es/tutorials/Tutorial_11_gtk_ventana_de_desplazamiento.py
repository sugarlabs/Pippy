import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk

class PyApp(Gtk.Window):

    def __init__(self):
        super(PyApp, self).__init__()

        self.set_title('Ventana de desplazamiento')
        self.set_position(Gtk.WindowPosition.CENTER_ALWAYS)
        self.set_size_request(250, 150)

        scrolled = Gtk.ScrolledWindow()

        vbox = Gtk.VBox()
        scrolled.add(vbox)

        for x in range(1, 16):
            boton = Gtk.Button(label='Boton %d' % x)
            vbox.pack_start(boton, False, False, 1)

        self.add(scrolled)
        self.show_all()

        self.connect('destroy', Gtk.main_quit)


PyApp()
Gtk.main()
