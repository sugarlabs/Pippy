from gi.repository import Gtk

class PyApp(Gtk.Window):
    def __init__(self):
        super(PyApp, self).__init__()
        self.set_title("Hello World!!")
        self.connect("destroy", Gtk.main_quit)
        self.set_size_request(250, 150)
        self.set_position(Gtk.WIN_POS_CENTER)
        
        entry = Gtk.Entry()
        fixed = Gtk.Fixed()
        fixed.put(entry, 20, 30)
        self.connect("destroy", Gtk.main_quit)
        self.add(fixed)
        self.show()

PyApp()
Gtk.main()
