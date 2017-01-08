import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk

from sugar3.graphics.toolbarbox import ToolbarBox
from sugar3.graphics.toolbutton import ToolButton
from sugar3.graphics.palettemenu import PaletteMenuBox
from sugar3.graphics.palettemenu import PaletteMenuItem
from sugar3.graphics.colorbutton import ColorToolButton


class PyApp(Gtk.Window):

    def __init__(self):
        super(PyApp, self).__init__()

        self.set_title('Palettes')
        self.set_position(Gtk.WindowPosition.CENTER_ALWAYS)

        vbox = Gtk.VBox()

        toolbarbox = ToolbarBox()
        vbox.add(toolbarbox)

        toolbar = toolbarbox.toolbar

        color_button = ColorToolButton()
        toolbar.insert(color_button, -1)

        button = ToolButton('list-add')
        button.set_tooltip('Palette with widgets')
        toolbar.insert(button, -1)

        palette = button.get_palette()
        palette_box = Gtk.VBox()
        palette.set_content(palette_box)

        checkbutton1 = Gtk.CheckButton('Option 1')
        palette_box.pack_start(checkbutton1, False, False, 0)

        checkbutton2 = Gtk.CheckButton('Option 2')
        palette_box.pack_start(checkbutton2, False, False, 0)

        checkbutton3 = Gtk.CheckButton('Option 3')
        palette_box.pack_start(checkbutton3, False, False, 0)

        separator = Gtk.VSeparator()
        palette_box.pack_start(separator, False, False, 0)

        radio_button1 = Gtk.RadioButton('Option 1')
        palette_box.pack_start(radio_button1, False, False, 0)

        radio_button2 = Gtk.RadioButton('Option 2', group=radio_button1)
        palette_box.pack_start(radio_button2, False, False, 0)

        radio_button3 = Gtk.RadioButton('Option 3', group=radio_button1)
        palette_box.pack_start(radio_button3, False, False, 0)

        palette_box.show_all()

        button = ToolButton(icon_name='format-justify-fill')
        button.props.tooltip = 'Select list'
        button.props.hide_tooltip_on_click = False
        button.palette_invoker.props.toggle_palette = True
        toolbar.insert(button, -1)

        menu_box = PaletteMenuBox()
        button.props.palette.set_content(menu_box)
        menu_box.show()

        menu_item = PaletteMenuItem('Item 1', icon_name='format-justify-fill')
        menu_box.append_item(menu_item)

        menu_item = PaletteMenuItem('Item 1', icon_name='format-justify-center')
        menu_box.append_item(menu_item)

        menu_item = PaletteMenuItem('Item 1', icon_name='format-justify-left')
        menu_box.append_item(menu_item)

        menu_item = PaletteMenuItem('Item 1', icon_name='format-justify-right')
        menu_box.append_item(menu_item)

        self.add(vbox)
        self.show_all()

        self.connect('destroy', Gtk.main_quit)


PyApp()
Gtk.main()
