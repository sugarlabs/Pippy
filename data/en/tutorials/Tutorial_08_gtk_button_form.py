from gi.repository import Gtk

class PyApp(Gtk.Window):
    def __init__(self):

        super(PyApp, self).__init__()
        
        self.set_title('Button')
        self.set_size_request(250, 200)
        self.set_position(Gtk.WindowPosition.CENTER_ALWAYS)
        
        def button_cb(widget):
            print 'click'

        button = Gtk.Button('Button')
        fixed = Gtk.Fixed()
        fixed.put(button, 20, 30)
        button.connect('clicked', button_cb)
        
        self.connect('destroy', Gtk.main_quit)
        
        self.add(fixed)
        self.show_all()


PyApp()
Gtk.main()
