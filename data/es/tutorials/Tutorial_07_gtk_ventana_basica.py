from gi.repository import Gtk

class PyApp(Gtk.Window):

    def __init__(self):
        super(PyApp, self).__init__()
        self.set_title("Hola mundo!!")
        self.set_position(Gtk.WindowPosition.CENTER_ALWAYS)
        self.set_size_request(250, 150)

        self.connect("destroy", Gtk.main_quit)

        self.show()

PyApp()
Gtk.main()
