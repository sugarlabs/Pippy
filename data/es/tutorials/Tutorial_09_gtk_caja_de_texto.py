from gi.repository import Gtk
from gi.repository import Gdk

class PyApp(Gtk.Window):

    def __init__(self):
        super(PyApp, self).__init__()
        self.set_title('Entrada de Texto')
        self.set_position(Gtk.WindowPosition.CENTER_ALWAYS)
        self.set_size_request(250, 150)
        
        def entry_cb(widget, event):
            if Gdk.keyval_name(event.keyval) == 'Return':
                print widget.get_text() 

        entry = Gtk.Entry()
        entry.connect('key_press_event', entry_cb)
        entry.show()

        fixed = Gtk.Fixed()
        fixed.put(entry, 20, 30)
        fixed.show()

        self.add(fixed)
        self.show()

        self.connect('destroy', Gtk.main_quit)


PyApp()
Gtk.main()
