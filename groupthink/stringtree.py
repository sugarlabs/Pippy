import random
random.seed() #Works around some mysterious bug in the Journal or Rainbow that
              #causes the random number generator to be seeded with the same
              #constant value if a Journal entry is re-launched from the
              #Journal.
from collections import defaultdict
import dbus # We do dbus (de)serialization in this file to minimize abstraction breakage
import logging
import aatree

inf = float('inf')

class Change:
    """Each Change represents a chanage to the StringTree.
    """
    def __init__(self, unique_id, parent, edit):
        """unique_id is a unique identifier for this Change
        parent is the unique_id that is affected by this
            Change.  Parent unique_id are always associated with an Insertion edit.
        edit is an Insertion, Deletion, or Removal.  It's what is to be done to
            the parent"""
        self.unique_id = unique_id
        self.parent = parent
        self.edit = edit
    
    def __repr__(self):
        return "Change(%d, %d, %s)" % (self.unique_id, self.parent, str(self.edit))

class Insertion:
    """Represents the action of inserting a particular bit of text
    """
    def __init__(self, position, text):
        """position is the point at which to insert text, in the unmodified
            coordinates of the parent node (other insertions and deletions
            to that node do not affect these coordinates)
        text is the string to insert"""
        self.position = position
        self.text = text
    
    def __repr__(self):
        return "Insertion(%d, %s)" % (self.position, self.text)

class Deletion:
    """Represents the deletion of only those characters present in the parent in
        this range.  Characters that have been inserted into the parent by
        an Insertion are not affected.
    """
    def __init__(self, position, length):
        """position is the point, in the unmodified coordinates of the parent
            node, at which to start deletion
        length is an integer greater than 0 representing the number of
            characters to delete"""
        self.position = position
        self.length = length
    
    def __repr__(self):
        return "Deletion(%d, %d)" % (self.position, self.length)
        
class Removal:
    """Represents the deletion of all characters ever inserted in this range.
        Insertions at the endpoints are _not_ included in the Removal, and must
        be Removed separately.
    """
    def __init__(self, position, length):
        """position is the point at which to start Removal
        length is the number of points in the unmodified parent coordinate to
            the end of the Removal.  Note that many more than length characters
            can be removed if there are Insertions in this range."""
        self.position = position
        self.length = length
    
    def __repr__(self):
        return "Removal(%d, %d)" % (self.position, self.length)

class Record:
    """Each Record is used to store one Change inside the StringTree.
    The purpose of a Record is contain both the Change itself, and any cached
    information about the current effect of that Change.
    """
    def __init__(self, change, depth):
        self.change = change
        self.depth = depth
    
    def __str__(self):
        return "Record(%s, %d)" % (str(self.change), self.depth)
    
    __repr__ = __str__

def flatten(L):
    o = []
    for x in L:
        if isinstance(x,list):
            o.extend(flatten(x)) #recursive
        else:
            o.append(x)
    return o
    
def my_rand():
    return random.getrandbits(63)

def translator(c, pack):
    if pack:
        if isinstance(c.edit, Insertion):
            return dbus.Struct((dbus.Int64(c.unique_id),
                               dbus.Int64(c.parent),
                               dbus.Int16(0),
                               dbus.Int64(c.edit.position),
                               dbus.UTF8String(c.edit.text)),
                               signature='xxnxs')
        elif isinstance(c.edit, Deletion):
            return dbus.Struct((dbus.Int64(c.unique_id),
                               dbus.Int64(c.parent),
                               dbus.Int16(1),
                               dbus.Int64(c.edit.position),
                               dbus.Int64(c.edit.length)),
                               signature='xxnxx')
        elif isinstance(c.edit, Removal):
            return dbus.Struct((dbus.Int64(c.unique_id),
                               dbus.Int64(c.parent),
                               dbus.Int16(2),
                               dbus.Int64(c.edit.position),
                               dbus.Int64(c.edit.length)),
                               signature='xxnxx')
        else:
            raise Unimplemented
    else:
        if c[2] == 0:
            ed = Insertion(int(c[3]),str(c[4]))
        elif c[2] == 1:
            ed = Deletion(int(c[3]),int(c[4]))
        elif c[2] == 2:
            ed = Removal(int(c[3]),int(c[4]))
        else:
            raise "unknown type"
        return Change(int(c[0]), int(c[1]), ed)

class EagerHideList:
    """EagerHideList provides a list with hidden elements.  The standard index
    considers only the visible elements, but the 'all' index considers all
    elements.  The standard index of an invisible element is considered to be
    the index of the next visible element."""
    def __init__(self):
        self._sourcelist = []
        self._poslist = []
        self._posmap = {}
    def __len__(self):
        return len(self._sourcelist)
    def __iter__(self):
        return self._sourcelist.__iter__()
    def __getitem__(self, s):
        return self._sourcelist[s]
    def index(self, item):
        x = self._poslist[self._posmap[item]]
        return x[2]
    def hide(self, position, length):
        """Given the position in _sourcelist, and the length of the deletion,
        perform the deletion in the lists"""
        pfirst = self._sourcelist[position]
        plast = self._sourcelist[position+length-1]
        ifirst = self._posmap[pfirst]
        ilast = self._posmap[plast]
        for i in xrange(ifirst, ilast+1):
            L = self._poslist[i]
            L[1] = False #No longer visible, if it was visible before
            L[2] = position #collapse positions
        for L in self._poslist[ilast+1:]:
            L[2] -= length #move all subsequent character up by length
            
        del self._sourcelist[position:(position+length)]
        #self._check_invariants()
    def getitem_all(self, s):
        if isinstance(s, int):
            return self._poslist[s][0]
        else:
            return [x[0] for x in self._poslist[s]]
    def index_all(self, item):
        return self._posmap[item]
    def is_visible(self, i):
        return self._poslist[i][1]
    def is_visible_item(self, item):
        return self._poslist[self._posmap[item]][1]
    def insert_sequence_all(self, position, sequence, visibility):
        """Insert sequence with visibility into the all-coordinates at position"""
        if position > 0:
            psource = self._poslist[position][2]
        else:
            psource = 0
        length = len(sequence)
        newlist = []
        newlistsource = []
        i = psource
        for elt, viz in zip(sequence, visibility):
            newlist.append([elt, viz, i])
            if viz:
                newlistsource.append(elt)
                i += 1
        self._poslist[position:position] = newlist
        for i in xrange(position,position+length):
            L = self._poslist[i]
            self._posmap[L[0]] = i
        num_viz = len(newlistsource)
        for i in xrange(position+length,len(self._poslist)):
            L = self._poslist[i]
            L[2] += num_viz
            self._posmap[L[0]] = i
        self._sourcelist[psource:psource] = newlistsource
        #self._check_invariants()
    def insert_sequence_leftof(self, target, sequence, visibility):
        self.insert_sequence_all(self._posmap[target], sequence, visibility)
        
    def _check_invariants(self):
        assert len(self._posmap) == len(self._poslist)
        for i in xrange(len(self._poslist)):
            assert self._posmap[self._poslist[i][0]] == i
            if self._poslist[i][1]:
                assert self._sourcelist[self._poslist[i][2]] == self._poslist[i][0]
            if i > 0:
                if self._poslist[i-1][1]:
                    assert self._poslist[i-1][2] + 1 == self._poslist[i][2]
                else:
                    assert self._poslist[i-1][2] == self._poslist[i][2]

class SimpleStringTree:
    """SimpleStringTree is a StringTree that supports only Insertions and
    Deletions.  Handling References, while valuable, has proven quite difficult,
    and so will not be addressed by this data structure.
    
    Code for handling Removals will be left in for the moment, since it is
    easy enough, even though it is not presently used."""

    def __init__(self, initstring=""):
        self.ROOT = Record(Change(-1, -1, Insertion(0, "")), 0)
        self._id2rec = dict() #unique_id: Record(change) | change.unique_id = unique_id
        self._id2rec[-1] = self.ROOT
        self._parent2children = defaultdict(set) # unique_id: {Record(change) | change.parent == unique_id}
        self._cursor = 0
        self._listing = aatree.AATreeHideList()
        self._listing.insert_sequence_all(0,[(-1,0)],[False])
        if initstring:
            self.insert(initstring, 0)
    
    def __repr__(self):
        return "\n".join((str(v) for v in self._id2rec.values()))
    
    def getvalue(self, r = None):
        if r is None:
            r = self.ROOT
        s = "".join(self._id2rec[x[0]].change.edit.text[x[1]] for x in self._listing)
        return s
    
    def next(self):
        raise
    
    def flush(self):
        # This could be used to implement lazy evaluation of input by not
        # re-evaluating the string until flush (or read?)
        pass
    
    def close(self):
        raise
    
    def read(self, size=float('inf')):
        #Efficiency: This method should use size to avoid calling getvalue and rendering the entire string
        s = self.getvalue()
        outpoint = min(len(s), self._cursor + size)
        inpoint = self._cursor
        self._cursor = outpoint
        return s[inpoint:outpoint]
        
    def readline(self, size=float('inf')):
        #Efficiency: This method should use size to avoid rendering the whole string
        s = self.getvalue()
        outpoint = min(len(s), self._cursor + size)
        inpoint = self._cursor
        i = s.find("\n", inpoint, outpoint)
        if i == -1 or i >= outpoint:
            self._cursor = outpoint
            return s[inpoint:outpoint]
        else:
            self._cursor = i + 1
            return s[inpoint:(i+1)]
    
    def readlines(self, sizehint=None):
        #Efficiency: use sizehint
        s = self.getvalue()
        t = s[self._cursor:]
        self._cursor = len(s)
        return t.splitlines(True)
    
    def seek(self, offset, whence=0):
        if whence == 0:
            self._cursor = offset
        elif whence == 1:
            self._cursor += offset
        elif whence == 2:
            self._cursor = len(self._listing) + offset
    
    def tell(self):
        return self._cursor
        
    def truncate(self, size=None):
        if size is None:
            size = self._cursor
        return self.delete(size, len(self._listing) - size)
        
    def write(self, text):
        L = min(len(self._listing) - self._cursor, len(text))
        changelist = []
        if L > 0:
            changelist.extend(self.delete(self._cursor, L))
        changelist.extend(self.insert(text))
        return changelist
    
    def writelines(self, sequence):
        s = "".join(sequence)
        return self.write(s)
    
    # Non-filelike text editing methods

    def insert(self, text, k=None):
        if k is None:
            k = self._cursor

        if len(self._listing) == 0:
            r = self.ROOT
            uid = -1
            inspoint = 0
        elif k == 0:
            (uid, inspoint) = self._listing[k]
            r = self._id2rec[uid]
        elif k < len(self._listing):
            # When not inserting at the endpoints, we have to be sure to
            # check if we are at the boundary between a parent and one of its
            # descendants.  If so, we must make our insertion in the descendant,
            # not the parent, because the insertions would "conflict" (occur at
            # the same location) in the parent, which would produce an ordering
            # ambiguity, which will resolve in our favor only 50% of the time.
            pL, pR = self._listing[(k-1):(k+1)]
            (uidL, inspointL) = pL
            (uidR, inspointR) = pR
            rR = self._id2rec[uidR]
            if uidL == uidR: #There's no boundary here at all (at least not one
                # of any importance to us.  Therefore, we have to insert to the
                # left of the character at k, as usual.
                r = rR
                uid = uidR
                inspoint = inspointR
            else: #There's a boundary of some sort here.  We always choose to
                # insert at the deeper node (breaking left in case of a tie).
                # (In the case that neither node is the ancestor of the other,
                # either choice would be acceptable, regardless of depth.  This
                # logic is therefore acceptable, and has the advantage of being
                # simple and fast.)
                rL = self._id2rec[uidL]
                if rR.depth > rL.depth:
                    r = rR
                    uid = uidR
                    inspoint = inspointR
                else:
                    r = rL
                    uid = uidL
                    inspoint = inspointL + 1
        elif k == len(self._listing):
            (uid,i) = self._listing[k-1]
            r = self._id2rec[uid]
            inspoint = i + 1
        else:
            raise
        
        e = Insertion(inspoint, text)
        c = Change(my_rand(), r.change.unique_id, e)
        self._add_change_treeonly(c)
        target = (uid, inspoint)
        self._insert_listonly(c.unique_id, target, len(text))
        self._cursor = k + len(text)
        return [c]
    
    def delete(self, k, n):
        """Starting at a point k (0-indexed), delete n characters"""
        if k + n > len(self._listing):
            raise
        p = self._listing[k]
        contigs = [[p[0],p[1],p[1]]]
        for (uid, index) in self._listing[(k+1):(k+n)]:
            #This logic produces deletions that span any missing chunks.  This
            #produces a smaller number of deletions than making sure that they
            #are actually "contiguous", but it might interact badly with a 
            #hypothetical undo system.
            if contigs[-1][0] == uid:
                contigs[-1][2] = index
            else:
                contigs.append([uid,index,index])
        changelist = [Change(my_rand(), c[0], Deletion(c[1],1 + c[2]-c[1])) for c in contigs]
        for c in changelist:
            self._add_change_treeonly(c)
        self._delete_listonly(k,n)
        return changelist

    def get_range(self, rec, point, m):
        todo = [(rec, point, m, None)] # None is a dummy value since p is unused
        ranges = []
        while len(todo) > 0:
            (rec, point, m, p) = todo[0]
            h = self._range_helper(point, m)
            self._step(h, rec)
            if h.outpoint is not None:
                ranges.append((rec, h.point_parent, h.outpoint - h.point_parent))
                #print rec, h.point_parent, h.outpoint - h.point_parent
            todo.extend(h.todo)
            #print todo
            del todo[0]
        return ranges
    
    def move(self, rempoint, n, inspoint):
        """In StringTree, move() should coherently copy a section of text,
        such that any conflicting edits appear in the new location, not the old.
        In SimpleStringTree, this is not possible, so move() just falls back to
        Deletion and Insertion."""
        self.seek(rempoint)
        t = self.read(n)
        
        if rempoint > inspoint:
            L = self.delete(rempoint,n)
            L.extend(self.insert(t, inspoint))
        else:
            L = self.insert(t, inspoint)
            L.extend(self.delete(rempoint,n))
        return L
                        
    # Patch management methods
    
    def add_change(self, c):
        if c.unique_id in self._id2rec:
            return []
        if isinstance(c.edit, Insertion):
            p = self._effective_parent(c.unique_id, c.parent, c.edit.position)
            i = self._listing.index(p)
            d = len(c.edit.text)
            self._insert_listonly(c.unique_id, p, d)
            flist = [Insertion(i, c.edit.text)]
        elif isinstance(c.edit, Deletion):
            flist = []
            start = None
            end = None
            for i in xrange(c.edit.position,c.edit.position + c.edit.length):
                p = (c.parent, i)
                if self._listing.is_visible_item(p):
                    q = self._listing.index(p)
                    if end == q:
                        end += 1
                    else:
                        if end is not None:
                            n = end - start
                            flist.append(Deletion(start,n))
                            self._delete_listonly(start,n)
                        start = q
                        end = start + 1
            if end is not None: # the last contig won't be handled by the loop
                n = end - start
                flist.append(Deletion(start,n))
                self._delete_listonly(start,n)                
        else:
            raise
        self._add_change_treeonly(c)
        return flist
    
    def _effective_parent(self, uid, parentid, position):
        """The effective parent of an insertion is defined as the (uid, loc) pair
        that causes it to be inserted in the right location in the string.  This
        is only relevant in the event of a conflict, in which case the conflict
        edits are required to be ordered from least uid to greatest uid.  The
        effective parent of a conflicted edit, then, is either the original pair,
        or (u_next, 0), where u_next is the uid of the sibling directly to the right
        of the input uid.  That is to say, it is the least u greater than uid
        that has the same position."""
        if parentid in self._parent2children:
            u_next = None
            for r in self._parent2children[parentid]:
                u = r.change.unique_id
                p = r.change.edit.position
                if (p == position) and isinstance(r.change.edit, Insertion) and (u > uid):
                    if (u_next is None) or (u < u_next):
                        u_next = u
            if u_next is not None:
                return (u_next, 0)
        return (parentid, position)
        
    def _delete_listonly(self, position, length):
        """Given the position in _sourcelist, and the length of the deletion,
        perform the deletion in the lists"""
        self._listing.hide(position,length)
        
    def _insert_listonly(self, uid, target, length):
        """Make a new insertion into the lists with uid and length at position
        in _poslist"""
        elts = [(uid,i) for i in xrange(length+1)]
        visibility = [True] * length
        visibility.append(False)
        self._listing.insert_sequence_leftof(target, elts, visibility)
    
    def _add_change_treeonly(self, c):
        if c.unique_id in self._id2rec:
            return
        d = self._id2rec[c.parent].depth + 1
        r = Record(c,d)
        self._id2rec[c.unique_id] = r
        if c.parent not in self._parent2children:
            self._parent2children[c.parent] = set()
        self._parent2children[c.parent].add(r)

    def get_insert(self, k, n = 0, parent=None):
        #FIXME: This method could be useful, but it no longer works
        """get_insert finds and returns the youngest insertion containing positions
        k to k + n in the total coordinates of parent.  If parent is unspecified,
        then it is taken to be the root, meaning the coordinates in question
        are the current document coordinates.
        
        The return value is a tuple (rec, k_unmodified, k_modified), meaning
        the record containing k and k + n, the position of k in rec's
        unmodified coordinates, and the position of k in rec's
        modified coordinates.
        
        "containing" is defined so that a record with n characters
        (labeled 0...n-1) can still be returned as containing k...k+n.  In
        other words, each Insertion contains both endpoints.  However, an
        Insertion that has been totally deleted is ignored entirely."""
        if parent is None:
            parent = self.ROOT
        
        h = self._get_insert_helper(k, n)
        self._step(h, parent)
        while h.child is not None:
            parent = h.child
            h = self._get_insert_helper(h.child_k, n)
            self._step(h, parent)
                
        return (parent, h.k_in_parent, h.k)

    def get_changes(self): #TODO: add arguments to get only changes in a certain range
        """get_changes provides a depth-first topologically sorted list of all
        Changes in this Tree"""
        L = []
        stack = [-1]
        while stack:
            x = self._id2rec[stack.pop()].change
            L.append(x)
            if x.unique_id in self._parent2children:
                stack.extend(r.change.unique_id 
                                   for r in self._parent2children[x.unique_id])
        return L
    
    def is_ready(self, c):
        """Returns a boolean indicating whether a Change c may safely be added
        to the Tree.  Specifically, it checks whether c.parent is already known."""
        return c.parent in self._id2rec
