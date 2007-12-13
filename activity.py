from sugar.activity import activity

import os, sys
import gtk, pango, vte

class VteActivity(activity.Activity):
    def __init__(self, handle):
        activity.Activity.__init__(self, handle)
        toolbox = activity.ActivityToolbox(self)
        self.set_toolbox(toolbox)
        toolbox.show()

        # XXX: NEED SHOW SOURCE BUTTON / KEYBINDING
        
        # creates vte widget
        self._vte = vte.Terminal()
        self._vte.set_size(30,5)
        self._vte.set_size_request(200, 300)
        font = 'Monospace 10'
        self._vte.set_font(pango.FontDescription(font))
        self._vte.set_colors(gtk.gdk.color_parse ('#000000'),
                             gtk.gdk.color_parse ('#E7E7E7'),
                             [])
        # ...and its scrollbar
        vtebox = gtk.HBox()
        vtebox.pack_start(self._vte)
        vtesb = gtk.VScrollbar(self._vte.get_adjustment())
        vtesb.show()
        vtebox.pack_start(vtesb, False, False, 0)
        self.set_canvas(vtebox)
        self.show_all()

        # now start subprocess.
        self._vte.grab_focus()
        bundle_path = activity.get_bundle_path()
        # the 'sleep 1' works around a bug with the command dying before
        # the vte widget manages to snarf the last bits of its output
        self._pid = self._vte.fork_command \
                    (command='/bin/sh',
                     argv=['/bin/sh','-c',
                           'python %s/pippy_app.py; sleep 1' % bundle_path],
                     envv=["PYTHONPATH=%s/library" % bundle_path],
                     directory=bundle_path)
