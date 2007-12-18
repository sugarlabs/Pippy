from sugar.activity import activity

class ViewSourceActivity(activity.Activity):
    """Activity subclass which handles the 'view source' key."""
    def __init__(self, handle):
        super(ViewSourceActivity, self).__init__(handle)
        self.__source_object_id = None # XXX: persist this across invocations?
        self.connect('key-press-event', self._key_press_cb)
    def _key_press_cb(self, widget, event):
        import gtk
        if gtk.gdk.keyval_name(event.keyval) == 'XF86Start':
            self.view_source()
            return True
        return False
    def view_source(self):
        """Implement the 'view source' key by saving pippy_app.py to the
        datastore, and then telling the Journal to view it."""
        if self.__source_object_id is None:
            from sugar import profile
            from sugar.datastore import datastore
            from sugar.activity.activity import get_bundle_name, get_bundle_path
            from gettext import gettext as _
            import os.path
            jobject = datastore.create()
            metadata = {
                'title': _('%s Source') % get_bundle_name(),
                'title_set_by_user': '1',
                'suggested_filename': 'pippy_app.py',
                'icon-color': profile.get_color().to_string(),
                'mime_type': 'text/x-python',
                }
            for k,v in metadata.items():
                jobject.metadata[k] = v # dict.update method is missing =(
            jobject.file_path = os.path.join(get_bundle_path(), 'pippy_app.py')
            datastore.write(jobject)
            self.__source_object_id = jobject.object_id
            jobject.destroy()
        self.journal_show_object(self.__source_object_id)
    def journal_show_object(self, object_id):
        """Invoke parent class' journal_show_object if it exists."""
        s = super(ViewSourceActivity, self)
        if hasattr(s, 'journal_show_object'):
            s.journal_show_object(object_id)


class VteActivity(ViewSourceActivity):
    def __init__(self, handle):
        import gtk, pango, vte
        super(VteActivity, self).__init__(handle)
        toolbox = activity.ActivityToolbox(self)
        self.set_toolbox(toolbox)
        toolbox.show()

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
