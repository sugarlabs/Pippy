import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk

class PyApp(Gtk.Window):

    def __init__(self):
        super(PyApp, self).__init__()

        self.set_title('Menu')
        self.set_position(Gtk.WindowPosition.CENTER_ALWAYS)
        self.set_size_request(250, 150)

        accel_group = Gtk.AccelGroup()
        self.add_accel_group(accel_group)

        vbox = Gtk.VBox()

        menubar = Gtk.MenuBar()
        vbox.pack_start(menubar, False, False, 0)

        self.label = Gtk.Label('Activate a menu item')
        vbox.pack_start(self.label, True, True, 0)

        menu_file = Gtk.Menu()

        item_file = Gtk.MenuItem.new_with_mnemonic('_File')
        item_file.set_submenu(menu_file)
        menubar.append(item_file)

        item_new = Gtk.MenuItem.new_with_mnemonic('_New')
        key, mod = Gtk.accelerator_parse('<Ctrl>N')
        item_new.add_accelerator('activate', accel_group, key, mod, Gtk.AccelFlags.VISIBLE)
        item_new.connect('activate', self._activate_cb, 'New')
        menu_file.append(item_new)

        item_open = Gtk.MenuItem.new_with_mnemonic('_Open')
        key, mod = Gtk.accelerator_parse('<Ctrl>O')
        item_open.add_accelerator('activate', accel_group, key, mod, Gtk.AccelFlags.VISIBLE)
        item_open.connect('activate', self._activate_cb, 'Open')
        menu_file.append(item_open)

        menu_recents = Gtk.Menu()

        item_recents = Gtk.MenuItem.new_with_mnemonic('Open _recents')
        item_recents.set_submenu(menu_recents)
        menu_file.append(item_recents)

        for recent_file in range(1, 6):
            item_recent = Gtk.MenuItem.new_with_mnemonic('_%d: Recent file %d' % (recent_file, recent_file))
            item_recent.connect('activate', self._activate_cb, 'Recent file %d' % recent_file)
            menu_recents.append(item_recent)

        separator = Gtk.SeparatorMenuItem()
        menu_file.append(separator)

        item_exit = Gtk.MenuItem.new_with_mnemonic('_Quit')
        key, mod = Gtk.accelerator_parse('<Ctrl>Q')
        item_exit.add_accelerator('activate', accel_group, key, mod, Gtk.AccelFlags.VISIBLE)
        item_exit.connect('activate', self._activate_cb, 'Quit')
        menu_file.append(item_exit)

        menu_edit = Gtk.Menu()

        item_edit = Gtk.MenuItem.new_with_mnemonic('_Edit')
        item_edit.set_submenu(menu_edit)
        menubar.append(item_edit)

        item_undo = Gtk.ImageMenuItem.new_from_stock(Gtk.STOCK_UNDO, None)
        key, mod = Gtk.accelerator_parse('<Ctrl>Z')
        item_undo.add_accelerator('activate', accel_group, key, mod, Gtk.AccelFlags.VISIBLE)
        item_undo.connect('activate', self._activate_cb, 'Undo')
        menu_edit.append(item_undo)

        item_redo = Gtk.ImageMenuItem.new_from_stock(Gtk.STOCK_REDO, None)
        key, mod = Gtk.accelerator_parse('<Ctrl><Shift>Z')
        item_redo.add_accelerator('activate', accel_group, key, mod, Gtk.AccelFlags.VISIBLE)
        item_redo.connect('activate', self._activate_cb, 'Redo')
        menu_edit.append(item_redo)

        separator = Gtk.SeparatorMenuItem()
        menu_edit.append(separator)

        item_copy = Gtk.ImageMenuItem.new_from_stock(Gtk.STOCK_COPY, None)
        key, mod = Gtk.accelerator_parse('<Ctrl>C')
        item_copy.add_accelerator('activate', accel_group, key, mod, Gtk.AccelFlags.VISIBLE)
        item_copy.connect('activate', self._activate_cb, 'Copy')
        menu_edit.append(item_copy)

        item_cut = Gtk.ImageMenuItem.new_from_stock(Gtk.STOCK_CUT, None)
        key, mod = Gtk.accelerator_parse('<Ctrl>X')
        item_cut.add_accelerator('activate', accel_group, key, mod, Gtk.AccelFlags.VISIBLE)
        item_cut.connect('activate', self._activate_cb, 'Cut')
        menu_edit.append(item_cut)

        item_paste = Gtk.ImageMenuItem.new_from_stock(Gtk.STOCK_PASTE, None)
        key, mod = Gtk.accelerator_parse('<Ctrl>V')
        item_paste.add_accelerator('activate', accel_group, key, mod, Gtk.AccelFlags.VISIBLE)
        item_paste.connect('activate', self._activate_cb, 'Paste')
        menu_edit.append(item_paste)

        separator = Gtk.SeparatorMenuItem()
        menu_edit.append(separator)

        label = 'Vertical page'
        item_vertical = Gtk.RadioMenuItem(label)
        item_vertical.set_active(True)
        item_vertical.connect('toggled', self._toggled_cb, label)
        menu_edit.append(item_vertical)

        label = 'Horizontal page'
        item_horizontal = Gtk.RadioMenuItem.new_with_label((item_vertical,), label)
        item_horizontal.connect('toggled', self._toggled_cb, label)
        menu_edit.append(item_horizontal)

        menu_view = Gtk.Menu()

        item_view = Gtk.MenuItem.new_with_mnemonic('_View')
        item_view.set_submenu(menu_view)
        menubar.append(item_view)

        item_hides = Gtk.CheckMenuItem.new_with_mnemonic('_Hidden files')
        key, mod = Gtk.accelerator_parse('<Ctrl>H')
        item_hides.add_accelerator('activate', accel_group, key, mod, Gtk.AccelFlags.VISIBLE)
        item_hides.connect('toggled', self._toggled_cb, 'Hidden files', True)
        menu_view.append(item_hides)

        menu_help = Gtk.Menu()

        item_help = Gtk.MenuItem('Ayuda')
        item_help.set_submenu(menu_help)
        menubar.append(item_help)

        item_about = Gtk.ImageMenuItem.new_from_stock(Gtk.STOCK_ABOUT, None)
        item_about.add_accelerator('activate', accel_group, key, mod, Gtk.AccelFlags.VISIBLE)
        item_about.connect('activate', self._activate_cb, 'About')
        menu_help.append(item_about)

        self.add(vbox)
        self.show_all()

        self.connect('destroy', Gtk.main_quit)

    def _activate_cb(self, item, label):
        self.label.set_text('You activated %s item' % label)

    def _toggled_cb(self, item, label, no_active=False):
        if item.get_active():
            self.label.set_text('You activated %s item' % label)

        elif not item.get_active() and no_active:
            self.label.set_text('You deactivate %s item' % label)


PyApp()
Gtk.main()
