import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk


class PyApp(Gtk.Window):

    def __init__(self):
        super(PyApp, self).__init__()

        self.set_title('Cuadricula')
        self.set_position(Gtk.WindowPosition.CENTER_ALWAYS)

        grid = Gtk.Grid()
        grid.set_column_homogeneous(True)
        grid.set_row_homogeneous(True)

        button = Gtk.Button('Boton 1')
        grid.attach(button, 0, 0, 1, 1)

        button = Gtk.Button('Boton 2')
        grid.attach(button, 0, 2, 1, 2)

        button = Gtk.Button('Boton 3')
        grid.attach(button, 1, 1, 2, 2)

        button = Gtk.Button('Boton 4')
        grid.attach(button, 2, 0, 2, 1)

        button = Gtk.Button('Boton 5')
        grid.attach(button, 3, 3, 3, 3)

        self.add(grid)
        self.show_all()

        self.connect('destroy', Gtk.main_quit)


PyApp()
Gtk.main()
