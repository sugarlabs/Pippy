from gi.repository import Gtk

class PyApp(Gtk.Window): 
    def __init__(self):
        super(PyApp, self).__init__()
        self.set_size_request(300, 150)
        self.set_position(Gtk.WIN_POS_CENTER)
        self.connect("destroy", Gtk.main_quit)
        self.set_title("Haz clic en el boton")
        
        
        button = Gtk.Button("Haz clic!!!")
        button.set_size_request(80, 30)
        button.connect("clicked", self.on_clicked)
        
        fix = Gtk.Fixed()
        fix.put(button, 20, 20)
   
        self.add(fix)
        self.show_all()

    def on_clicked(self, widget):
        about = Gtk.AboutDialog()
        about.set_comments("Hola!!!")
        about.run()
        about.destroy()

PyApp()
Gtk.main()
