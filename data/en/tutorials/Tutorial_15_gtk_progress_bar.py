import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk
from gi.repository import GObject


class PyApp(Gtk.Window):

    def __init__(self):
        super(PyApp, self).__init__()

        self.set_title('Barras de progreso')
        self.set_position(Gtk.WindowPosition.CENTER_ALWAYS)
        self.set_border_width(20)

        self.fraction = 0

        grid = Gtk.Grid()
        grid.set_row_spacing(10)

        self.bar1 = Gtk.ProgressBar()
        self.bar1.set_hexpand(True)
        self.bar1.set_vexpand(True)
        grid.attach(self.bar1, 1, 0, 3, 1)

        label = Gtk.Label(label="Una barra de progreso simple")
        label.set_hexpand(True)
        grid.attach(label, 1, 1, 1, 1)

        self.bar2 = Gtk.ProgressBar()
        self.bar2.set_hexpand(True)
        self.bar2.set_vexpand(True)
        grid.attach(self.bar2, 1, 2, 3, 1)

        label = Gtk.Label(label="Una barra de progreso con pulsos")
        grid.attach(label, 1, 3, 1, 1)

        GObject.timeout_add(200, self._update)

        self.add(grid)
        self.show_all()

        self.connect('destroy', Gtk.main_quit)

    def _update(self):
        self.fraction += 0.01
        if self.fraction >= 1:
            self.fraction = 0

        self.bar1.set_fraction(self.fraction)
        self.bar2.pulse()

        return True


PyApp()
Gtk.main()
