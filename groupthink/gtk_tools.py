from gi.repository import Gtk
import groupthink_base as groupthink
import logging
import stringtree

class RecentEntry(groupthink.UnorderedHandlerAcceptor, Gtk.Entry):
    """RecentEntry is an extension of Gtk.Entry that, when attached to a group,
    creates a unified Entry field for all participants"""
    def __init__(self, *args, **kargs):
        GObject.GObject.__init__(self, *args, **kargs)
        self.logger = logging.getLogger('RecentEntry')
        self.add_events(Gdk.EventMask.PROPERTY_CHANGE_MASK)
        self._text_changed_handler = self.connect('changed', self._local_change_cb)
        self._recent = groupthink.Recentest(self.get_text(), groupthink.string_translator)
        self._recent.register_listener(self._remote_change_cb)
        
    def _local_change_cb(self, widget):
        self.logger.debug("_local_change_cb()")
        self._recent.set_value(self.get_text())
    
    def set_handler(self, handler):
        self.logger.debug("set_handler")
        self._recent.set_handler(handler)
    
    def _remote_change_cb(self, text):
        self.logger.debug("_remote_change_cb(%s)" % text)
        if self.get_text() != text:
            #The following code will break if running in any thread other than
            #the main thread.  I do not know how to make code that works with
            #both multithreaded gtk _and_ single-threaded Gtk.
            self.handler_block(self._text_changed_handler)
            self.set_text(text)
            self.handler_unblock(self._text_changed_handler)
            
class SharedTreeStore(groupthink.CausalHandlerAcceptor, Gtk.TreeStore):
    def __init__(self, columntypes=(), translators=()):
        self._columntypes = columntypes
        self._causaltree = groupthink.CausalTree()
        if len(translators) != 0 and len(translators) != len(columntypes):
            raise #Error: translators must be empty or match columntypes in length
        if len(translators) == len(self._columntypes):
            self._columndicts = [groupthink.CausalDict(
                                key_translator = self._causaltree.node_trans,
                                value_translator = translators[i])
                                for i in xrange(len(translators))]
        else:
            self._columndicts = [groupthink.CausalDict(
                                key_translator = self._causaltree.node_trans)
                                for i in xrange(len(translators))]
        self._causaltree.register_listener(self._tree_listener)
        for i in xrange(len(self._columndicts)):
            self._columndicts[i].register_listener(self._generate_dictlistener(i))
                                
    def set_handler(self, handler):
        self._causaltree.set_handler(handler)
        for i in xrange(len(self._columndicts)):
            #Make a new handler for each columndict
            #Not very future-proof: how do we serialize out and reconstitute
            #objects that GroupActivity.cloud is not even aware of?
            h = handler.copy(str(i))
            self._columndicts[i].set_handler(h)

    ### Methods necessary to implement Gtk.GenericTreeModel ###

    def on_get_flags(self):
        return Gtk.TREE_MODEL_ITERS_PERSIST

    def on_get_n_columns(self):
        return len(self._columntypes)
        
    def on_get_column_type(self, index):
        return self._columntypes[index]
        
    def on_get_iter(self, path):
        node = self._causaltree.ROOT
        for k in path:
            c = list(self._causaltree.get_children(node))
            if len(c) <= k:
                return None #Invalid path
            else:
                c.sort()
                node = c[k]
        return node
        
    def on_get_path(self, rowref):
        revpath = []
        node = rowref
        if rowref in self._causaltree:
            while node != self._causaltree.ROOT:
                p = self._causaltree.get_parent(node)
                c = list(self._causaltree.get_children(p))
                c.sort()
                revpath.append(c.index(node)) # could be done "faster" using bisect
                node = p
            return tuple(revpath[::-1])
        else:
            return None
                        
    def on_get_value(self, rowref, column):
        return self._columndicts[column][rowref]
    
    def on_iter_next(self, rowref):
        p = self._causaltree.get_parent(rowref)
        c = list(self._causaltree.get_children(p))
        c.sort()
        i = c.index(rowref) + 1
        if i < len(c):
            return c[i]
        else:
            return None
            
    def on_iter_children(self, parent):
        if parent is None:
            parent = self._causaltree.ROOT
        c = self._causaltree.get_children(parent)
        if len(c) > 0:
            return min(c)
        else:
            return None
            
    def on_iter_has_child(self, rowref):
        return len(self._causaltree.get_children(rowref)) > 0
        
    def on_iter_n_children(self, rowref):
        return len(self._causaltree.get_children(rowref))
        
    def on_iter_nth_child(self, parent, n):
        if parent is None:
            parent = self._causaltree.ROOT
        c = self._causaltree.get_children(parent)
        if len(c) > n:
            c = list(c)
            c.sort()
            return c[n]
        else:
            return None
             
    def on_iter_parent(self, child):
        p = self._causaltree.get_parent(child)
        if p == self._causaltree.ROOT:
            return None
        else:
            return p
    
    ### Methods for passing changes from remote users ###
    
    def _dict_listener(self, i, added, removed):
        s = set()
        s.update(added.keys())
        s.update(removed.keys())
        for node in s:
            path = self.on_get_path(node)
            if path is not None:
                it = self.create_tree_iter(node)
                self.row_changed(path, it)
        self.emit('changed')
    
    def _generate_dict_listener(self, i):
        def temp(added,removed):
            self._dict_listener(i,added,removed)
        return temp
    
    def _tree_listener(self, forward, reverse):
        #forward is the list of commands representing the change, and
        #reverse is the list representing their inverse.  Together, these
        #lists represent a total description of the change.  However, deriving
        #sufficient information to fill in the signals would require replicating
        #the entire CausalTree state machine.  Therefore, for the moment, we make only a modest
        #attempt, and if it fails, throw up an "unknown-change" flag
        deleted = set() #unused, since we can only safely handle a single deletion with this method
        haschild = set() #All signals may be sent spuriously, but this one especially so
        inserted = set()
        unknown_change = False
        # no reordered, since there is no ordering choice
        
        for cmd in forward:
            if cmd[0] == self._causaltree.SET_PARENT:
                if cmd[2] in self._causaltree:
                    haschild.add(cmd[2])
                else:
                    unknown_change = True
                if cmd[1] in self._causaltree:
                    inserted.add(cmd[1])
                else:
                    unknown_change = True
        for cmd in reverse:
            clean = True
            if cmd[0] == self._causaltree.SET_PARENT:
                if (clean and
                    cmd[2] in self._causaltree and
                    (cmd[1] not in self._causaltree or
                    cmd[2] != self._causaltree.get_parent(cmd[1]))):
                    
                    clean = False
                    haschild.add((cmd[2], cmd[1]))
                    c = self._causaltree.get_children(cmd[2])
                    c = list(c)
                    c.append(cmd[1])
                    c.sort()
                    i = c.index(cmd[1])
                    p = self.on_get_path(cmd[2])
                    p = list(p)
                    p.append(i)
                    p = tuple(p)
                    self.row_deleted(p)
                else:
                    unknown_change = True
        if unknown_change:
            self.emit('unknown-change')
        for node in inserted:
            path = self.on_get_path(node)
            if path is not None:
                it = self.create_tree_iter(node)
                self.row_inserted(path, it)
        for node in haschild:
            path = self.on_get_path(node)
            if path is not None:
                it = self.create_tree_iter(node)
                self.row_has_child_toggled(path, it)
        self.emit('changed')
            
    ### Methods for resembling Gtk.TreeStore ###
    
    def set_value(self, it, column, value):
        node = self.get_user_data(it)
        self._columndicts[i][node] = value
    
    def set(self, it, *args):
        for i in xrange(0,len(args),2):
            self.set_value(it,args[i],args[i+1])
    
    def remove(self, it):
        node = self.get_user_data(it)
        self._causaltree.delete(node)
        for d in self._columndicts:
            if node in d:
                del d[node]
    
    def append(self, parent, row=None):
        if parent is not None:
            node = self.get_user_data(it)
        else:
            node = self._causaltree.ROOT
        node = self._causaltree.new_child(node)
        if row is not None:
            if len(row) != len(columndicts):
                raise IndexError("row had the wrong length")
            else:
                for i in xrange(len(row)):
                    self._columndicts[i][node] = row[i]
        return self.create_tree_iter(node)
    
    def is_ancestor(self, it, descendant):
        node = self.get_user_data(it)
        d = self.get_user_data(descendant)
        d = self._causaltree.get_parent(d)
        while d != self._causaltree.ROOT:
            if d == node:
                return True
            else:
                d = self._causaltree.get_parent(d)
        return False
    
    def iter_depth(self, it):
        node = self.get_user_data(it)
        i = 0
        node = self._causaltree.get_parent(node)
        while node != self._causaltree.ROOT:
            i = i + 1
            node = self._causaltree.get_parent(node)
        return i
    
    def clear(self):
        self._causaltree.clear()
        for d in self._columndicts:
            d.clear()
    
    def iter_is_valid(self, it):
        node = self.get_user_data(it)
        return node in self._causaltree
    
    ### Additional Methods ###
    def move(self, it, newparent):
        node = self.get_user_data(row)
        p = self.get_user_data(newparent)
        self._causaltree.change_parent(node,p)

class TextBufferUnorderedStringLinker:
    def __init__(self,tb,us):
        self._tb = tb
        self._us = us
        self._us.register_listener(self._netupdate_cb)
        self._insert_handler = tb.connect('insert-text', self._insert_cb)
        self._delete_handler = tb.connect('delete-range', self._delete_cb)
        self._logger = logging.getLogger('the Linker')
    
    def _insert_cb(self, tb, itr, text, length):
        self._logger.debug('user insert: %s' % text)
        pos = itr.get_offset()
        self._us.insert(text,pos)
    
    def _delete_cb(self, tb, start_itr, end_itr):
        self._logger.debug('user delete')
        k = start_itr.get_offset()
        n = end_itr.get_offset()-k
        self._us.delete(k,n)
    
    def _netupdate_cb(self, edits):
        self._logger.debug('update from network: %s' % str(edits))
        self._tb.handler_block(self._insert_handler)
        self._tb.handler_block(self._delete_handler)
        for e in edits:
            if isinstance(e, stringtree.Insertion):
                itr = self._tb.get_iter_at_offset(e.position)
                self._tb.insert(itr, e.text)
            elif isinstance(e, stringtree.Deletion):
                itr1 = self._tb.get_iter_at_offset(e.position)
                itr2 = self._tb.get_iter_at_offset(e.position + e.length)
                self._tb.delete(itr1,itr2)
        self._tb.handler_unblock(self._insert_handler)
        self._tb.handler_unblock(self._delete_handler)


class TextBufferSharePoint(groupthink.UnorderedHandlerAcceptor):
    def __init__(self, buff):
        self._us = groupthink.UnorderedString(buff.get_text(buff.get_start_iter(), buff.get_end_iter(), True))
        self._linker = TextBufferUnorderedStringLinker(buff, self._us)
        
    def set_handler(self, handler):
        self._us.set_handler(handler)

class SharedTextView(groupthink.UnorderedHandlerAcceptor, Gtk.TextView):
    def __init__(self, *args, **kargs):
        GObject.GObject.__init__(self, *args, **kargs)
        self._link = TextBufferSharePoint(self.get_buffer())
        
    def set_handler(self, handler):
        self._link.set_handler(handler)
