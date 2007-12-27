from sugar.activity import activity

class ViewSourceActivity(activity.Activity):
    """Activity subclass which handles the 'view source' key."""
    def __init__(self, handle, **kwargs):
        super(ViewSourceActivity, self).__init__(handle, **kwargs)
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
        """Invoke journal_show_object from sugar.activity.activity if it
        exists."""
        try:
            from sugar.activity.activity import show_object_in_journal
            show_object_in_journal(object_id)
        except ImportError:
            pass # no love from sugar.

TARGET_TYPE_TEXT = 80
class VteActivity(ViewSourceActivity):
    def __init__(self, handle):
        import gtk, pango, vte
        from sugar.graphics.toolbutton import ToolButton
        from gettext import gettext as _
        super(VteActivity, self).__init__(handle)
        toolbox = activity.ActivityToolbox(self)
        # we don't support share/keep (yet?)
        toolbar = toolbox.get_activity_toolbar()
        toolbar.share.hide() # this should share bundle.
        toolbar.keep.hide()
        self.set_toolbox(toolbox)
        toolbox.show()

        # add 'copy' icon from standard toolbar.
        edittoolbar = activity.EditToolbar()
        edittoolbar.copy.set_tooltip(_('Copy selected text to clipboard'))
        edittoolbar.copy.connect('clicked', self._on_copy_clicked_cb)
        edittoolbar.paste.connect('clicked', self._on_paste_clicked_cb)
        # as long as nothing is selected, copy needs to be insensitive.
        edittoolbar.copy.set_sensitive(False)
        toolbox.add_toolbar(_('Edit'), edittoolbar)
        edittoolbar.show()
        self._copy_button = edittoolbar.copy

        # creates vte widget
        self._vte = vte.Terminal()
        self._vte.set_size(30,5)
        self._vte.set_size_request(200, 300)
        font = 'Monospace 10'
        self._vte.set_font(pango.FontDescription(font))
        self._vte.set_colors(gtk.gdk.color_parse ('#000000'),
                             gtk.gdk.color_parse ('#E7E7E7'),
                             [])
        self._vte.connect('selection-changed', self._on_selection_changed_cb)
        self._vte.drag_dest_set(gtk.DEST_DEFAULT_ALL,
                                [ ( "text/plain", 0, TARGET_TYPE_TEXT ) ],
                                gtk.gdk.ACTION_COPY)
        self._vte.connect('drag_data_received', self._on_drop_cb)
        # ...and its scrollbar
        vtebox = gtk.HBox()
        vtebox.pack_start(self._vte)
        vtesb = gtk.VScrollbar(self._vte.get_adjustment())
        vtesb.show()
        vtebox.pack_start(vtesb, False, False, 0)
        self.set_canvas(vtebox)
        self.show_all()
        # hide the buttons we don't use.
        edittoolbar.undo.hide()
        edittoolbar.redo.hide()
        edittoolbar.separator.hide()

        # now start subprocess.
        self._vte.connect('child-exited', self.on_child_exit)
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
    def _on_copy_clicked_cb(self, widget):
        if self._vte.get_has_selection():
            self._vte.copy_clipboard()
    def _on_paste_clicked_cb(self, widget):
        self._vte.paste_clipboard()
    def _on_selection_changed_cb(self, widget):
        self._copy_button.set_sensitive(self._vte.get_has_selection())
    def _on_drop_cb(self, widget, context, x, y, selection, targetType, time):
        if targetType == TARGET_TYPE_TEXT:
            self._vte.feed_child(selection.data)
    def on_child_exit(self, widget):
        """This method is invoked when the user's script exits."""
        pass # override in subclass
