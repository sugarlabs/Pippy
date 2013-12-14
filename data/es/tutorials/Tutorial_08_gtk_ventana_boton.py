from gi.repository import Gtk

class PyApp(Gtk.Window):
    def __init__(self):
        super(PyApp, self).__init__()
        
        self.set_title("Boton")
        self.set_size_request(250, 200)
        self.set_position(Gtk.WIN_POS_CENTER)
        
        btn1 = Gtk.Button("Boton")
        fixed = Gtk.Fixed()
        fixed.put(btn1, 20, 30)
        
        self.connect("destroy", Gtk.main_quit)
        
        self.add(fixed)
        self.show_all()


PyApp()
Gtk.main()
