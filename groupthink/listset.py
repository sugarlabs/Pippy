"""
Copyright 2008 Benjamin M. Schwartz

This file is LGPLv2+.

listset.py is free software: you can redistribute it and/or modify
it under the terms of the GNU Lesser General Public License as published by
the Free Software Foundation, either version 2 of the License, or
(at your option) any later version.

DObject is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU Lesser General Public License
along with DObject.  If not, see <http://www.gnu.org/licenses/>.
"""

import bisect
from collections import defaultdict

"""
dobject_helpers is a collection of functions and data structures that are useful
to DObject, but are not specific to DBus or networked applications.
"""

def merge(a, b, l=True, g=True, e=True):
    """Internal helper function for combining sets represented as sorted lists"""
    x = 0
    X = len(a)
    if X == 0:
        if g:
            return list(b)
        else:
            return []
    y = 0
    Y = len(b)
    if Y == 0:
        if l:
            return list(a)
        else:
            return []
    out = []
    p = a[x]
    q = b[y]
    while x < X and y < Y:
        if p < q:
            if l: out.append(p)
            x += 1
            if x < X: p = a[x]
        elif p > q:
            if g: out.append(q)
            y += 1
            if y < Y: q = b[y]
        else:
            if e: out.append(p)
            x += 1
            if x < X: p = a[x]
            y += 1
            if y < Y: q = b[y]       
    if x < X:
        if l: out.extend(a[x:])
    else:
        if g: out.extend(b[y:])
    return out

def merge_or(a,b):
    return merge(a,b, True, True, True)

def merge_xor(a,b):
    return merge(a, b, True, True, False)

def merge_and(a,b):
    return merge(a, b, False, False, True)

def merge_sub(a,b):
    return merge(a, b, True, False, False)

def kill_dupes(a): #assumes a is sorted
    """Internal helper function for removing duplicates in a sorted list"""
    prev = a[0]
    out = [prev]
    for item in a:
        if item != prev: #always throws out item 0, but that's ok
            out.append(item)
            prev = item
    return out

class Comparable:
    """Currently, ListSet does not provide a mechanism for specifying a
    comparator.  Users who would like to specify a comparator other than the one
    native to the item may do so by wrapping the item in a Comparable.
    """
    def __init__(self, item, comparator):
        self.item = item
        self._cmp = comparator
    
    def __cmp__(self, other):
        return self._cmp(self.item, other)

class ListSet:
    """ListSet is a sorted set for comparable items.  It is inspired by the
    Java Standard Library's TreeSet.  However, it is implemented by a sorted
    list.  This implementation is much slower than a balanced binary tree, but
    has the distinct advantage that I can actually implement it.
    
    The methods of ListSet are all drawn directly from Python's set API,
    Python's list API, and Java's SortedSet API.
    """
    def __init__(self, seq=[]):
        L = list(seq)
        if len(L) > 1:
            L.sort()
            L = kill_dupes(L)
        self._list = L

    def __and__(self, someset):
        if isinstance(someset, ListSet):
            L = merge_and(self._list, someset._list)
        else:
            L = []
            for x in self._list:
                if x in someset:
                    L.append(x)
        a = ListSet()
        a._list = L
        return a
    
    def __contains__(self, item):
        if not self._list:
            return False
        if self._list[0] <= item <= self._list[-1]:
            a = bisect.bisect_left(self._list, item)
            return item == self._list[a]
        else:
            return False
    
    def __eq__(self, someset):
        if isinstance(someset, ListSet):
            return self._list == someset._list
        else:
            return len(self.symmetric_difference(someset)) == 0
    
    def __ge__(self, someset):
        if isinstance(someset, ListSet):
            return len(merge_or(self._list, someset._list)) == len(self._list)
        else:
            a = len(someset)
            k = 0
            for i in self._list:
                if i in someset:
                    k += 1
            return k == a
    
    def __gt__(self, someset):
        return (len(self) > len(someset)) and (self >= someset)

    def __iand__(self, someset):
        if isinstance(someset, ListSet):
            self._list = merge_and(self._list, someset._list)
        else:
            L = []
            for i in self._list:
                if i in someset:
                    L.append(i)
            self._list = L
        return self
    
    def __ior__(self, someset):
        if isinstance(someset, ListSet):
            self._list = merge_or(self._list, someset._list)
        else:
            self.update(someset)
        return self
    
    def __isub__(self, someset):
        if isinstance(someset, ListSet):
            self._list = merge_sub(self._list, someset._list)
        else:
            L = []
            for i in self._list:
                if i not in someset:
                    L.append(i)
            self._list = L
        return self
    
    def __iter__(self):
        return iter(self._list)
    
    def __ixor__(self, someset):
        if isinstance(someset, ListSet):
            self._list = merge_xor(self._list, someset._list)
        else:
            self.symmetric_difference_update(someset)
        return self
    
    def __le__(self, someset):
        if isinstance(someset, ListSet):
            return len(merge_or(self._list, someset._list)) == len(someset._list)
        else:
            for i in self._list:
                if i not in someset:
                   return False
            return True
    
    def __lt__(self, someset):
        return (len(self) < len(someset)) and (self <= someset)
    
    def __ne__(self, someset):
        return not (self == someset)
    
    def __len__(self):
        return len(self._list)
    
    def __nonzero__(self):
        #ugly, but faster than bool(self_list)
        return not not self._list
    
    def __or__(self, someset):
        a = ListSet()
        if isinstance(someset, ListSet):
            a._list = merge_or(self._list, someset._list)
        else:
            a._list = self._list
            a.update(someset)
        return a
    
    __rand__ = __and__
    
    def __repr__(self):
        return "ListSet(" + repr(self._list) +")"
    
    __ror__ = __or__
    
    def __rsub__(self, someset):
        if isinstance(someset, ListSet):
            a = ListSet()
            a._list = merge_sub(someset._list, self._list)
        else:
            a = ListSet(someset)
            a._list = merge_sub(a._list, self._list)
        return a
    
    def __sub__(self, someset):
        a = ListSet()
        if isinstance(someset, ListSet):
            a._list = merge_sub(self._list, someset._list)
        else:
            L = []
            for i in self._list:
                if i not in someset:
                    L.append(i)
            a._list = L
        return a
    
    def __xor__(self, someset):
        if isinstance(someset, ListSet):
            a = ListSet()
            a._list = merge_xor(self._list, someset._list)
        else:
            a = self.symmetric_difference(someset)
        return a
    
    __rxor__ = __xor__
    
    def add(self, item):
        a = bisect.bisect_left(self._list, item)
        if (a == len(self._list)) or (self._list[a] != item):
            self._list.insert(a, item)
    
    def clear(self):
        self._list = []
    
    def copy(self):
        a = ListSet()
        a._list = list(self._list) #shallow copy
        return a
    
    def difference(self, iterable):
        L = list(iterable)
        L.sort()
        a = ListSet()
        a._list = merge_sub(self._list, kill_dupes(L))
        return a
    
    def difference_update(self, iterable):
        L = list(iterable)
        L.sort()
        self._list = merge_sub(self._list, kill_dupes(L))
    
    def discard(self, item):
        if self._list and (item <= self._list[-1]):
            a = bisect.bisect_left(self._list, item)
            if self._list[a] == item:
                self._list.remove(a)
    
    def intersection(self, iterable):
        L = list(iterable)
        L.sort()
        a = ListSet()
        a._list = merge_and(self._list, kill_dupes(L))
    
    def intersection_update(self, iterable):
        L = list(iterable)
        L.sort()
        self._list = merge_and(self._list, kill_dupes(L))
    
    def issuperset(self, iterable):
        L = list(iterable)
        L.sort()
        m = merge_or(self._list, kill_dupes(L))
        return len(m) == len(self._list)
    
    def issubset(self, iterable):
        L = list(iterable)
        L.sort()
        L = kill_dupes(L)
        m = merge_or(self._list, L)
        return len(m) == len(L)
    
    def pop(self, i = None):
        if i == None:
            return self._list.pop()
        else:
            return self._list.pop(i)
        
    def remove(self, item):
        if self._list and (item <= self._list[-1]):
            a = bisect.bisect_left(self._list, item)
            if self._list[a] == item:
                self._list.remove(a)
                return
        raise KeyError("Item is not in the set")
    
    def symmetric_difference(self, iterable):
        L = list(iterable)
        L.sort()
        a = ListSet()
        a._list = merge_xor(self._list, kill_dupes(L))
        return a
    
    def symmetric_difference_update(self, iterable):
        L = list(iterable)
        L.sort()
        self._list = merge_xor(self._list, kill_dupes(L))
    
    def union(self, iterable):
        L = list(iterable)
        L.sort()
        a = ListSet()
        a._list = merge_or(self._list, kill_dupes(L))
    
    def update(self, iterable):
        L = list(iterable)
        L.sort()
        self._list = merge_or(self._list, kill_dupes(L))
    
    def __getitem__(self, key):
        if type(key) is int:
            return self._list[key]
        elif type(key) is slice:
            a = ListSet()
            L = self._list[key]
            if key.step is not None and key.step < 0:
                L.reverse()
            a._list = L
            return a
    
    def __delitem__(self, key):
        del self._list[key]
    
    def index(self, x, i=0, j=-1):
        if self._list and (x <= self._list[-1]):
            a = bisect.bisect_left(self._list, x, i, j)
            if self._list[a] == x:
                return a
        raise ValueError("Item not found")
    
    def position(self, x, i=0, j=-1):
        return bisect.bisect_left(self._list, x, i, j)
    
    def _subrange(self, x, y, includehead=True, includetail=False, i=0, j=-1):
        if includehead:
            a = bisect.bisect_left(self._list, x, i, j)
        else:
            a = bisect.bisect_right(self._list, x, i, j)
        if includetail:
            b = bisect.bisect_right(self._list, y, a, j)
        else:
            b = bisect.bisect_left(self._list, y, a, j)
        return (a, b)
    
    # From Java SortedSet
    def subset(self, x, y, includehead=True, includetail=False, i=0, j=-1):
        (a,b) = self._subrange(x, y, includehead, includetail, i, j)
        s = ListSet()
        s._list = self._list[a:b]
        return s
    
    def iterslice(self, slic):
        L = len(self._list)
        return (self._list[i] for i in xrange(*slic.indices(L)))
    
    def subiter(self, x, y, includehead=True, includetail=False, i=0, j=-1):
        (a,b) = self._subrange(x, y, includehead, includetail, i, j)
        return (self._list[i] for i in xrange(a,b))
    
    def first(self):
        return self._list[0]
    
    def last(self):
        return self._list[-1]
    
    def headset(self, x, include=False, i=0, j=-1):
        if include:
            a = bisect.bisect_right(self._list, x, i, j)
        else:
            a = bisect.bisect_left(self._list, x, i, j)
        return self[:a]
    
    def tailset(self, x, include=True, i=0, j=-1):
        if include:
            a = bisect.bisect_left(self._list, x, i, j)
        else:
            a = bisect.bisect_right(self._list, x, i, j)
        return self[a:]
    
    #From Java's NavigableSet
    def ceiling(self, x, i=0, j=-1):
        a = bisect.bisect_left(self._list, x, i, j)
        return self[a]
    
    def floor(self, x, i=0, j=-1):
        a = bisect.bisect_right(self._list, x, i, j)
        return self[a-1]
    
    def higher(self, x, i=0, j=-1):
        a = bisect.bisect_right(self._list, x, i, j)
        return self[a]
    
    def lower(self, x, i=0, j=-1):
        a = bisect.bisect_left(self._list, x, i, j)
        return self[a-1]

class ListDict:
    """ListDict is a map whose keys are comparable.  It is based on ListSet.
       Its API is drawn from python's defaultdict and Java's SortedMap."""
    def __init__(self, *args, **kwargs):
        self._dict = defaultdict(*args, **kwargs)
        self._set = ListSet(self._dict)
    
    # Dict methods
    
    def __copy__(self):
        return self.copy()
        
    def __repr__(self):
        return 'ListDict({'+', '.join(
                  (': '.join((repr(k), repr(self._dict[k])))
                   for k in self._set))+'})'
    
    def copy(self):
        D = ListDict()
        D._dict = self._dict.copy()
        D._set = self._set.copy()
        return D
    
    def __contains__(self, k):
        return k in self._dict
    
    def __delitem__(self, k):
        del self._dict[k]
        self._set.remove(k)
        
    def __eq__(self, d):
        if isinstance(d, ListDict):
            return self._dict == d._dict
        else:
            return self._dict == d
    
    def __ge__(self, d):
        if isinstance(d, ListDict):
            return self._dict >= d._dict
        else:
            return self._dict >= d
    
    def __getitem__(self, k):
        x = self._dict[k]
        if self._dict.default_factory is not None:
            self._set.add(k)
        return x
            
    def __gt__(self, d):
        if isinstance(d, ListDict):
            return self._dict > d._dict
        else:
            return self._dict > d
    
    def __hash__(self):
        return self._dict.__hash__()
    
    def __iter__():
        return self.iterkeys()
    
    def __le__(self, d):
        if isinstance(d, ListDict):
            return self._dict <= d._dict
        else:
            return self._dict <= d
    
    def __len__(self):
        return len(self._dict)
    
    def __lt__(self, d):
        if isinstance(d, ListDict):
            return self._dict < d._dict
        else:
            return self._dict < d
    
    def __ne__(self, d):
        if isinstance(d, ListDict):
            return self._dict != d._dict
        else:
            return self._dict != d
    
    def __nonzero__(self):
        return not not self._dict
    
    def __setitem__(self, k, v):
        self._dict[k] = v
        self._set.add(k)
    
    def clear(self):
        self._dict.clear()
        self._set.clear()
    
    def get(self, k, d=None):
        return self._dict.get(k, d)
    
    def has_key(self, k):
        return self._dict.has_key(k)
    
    def items(self, *args, **kwargs):
        if not (args or kwargs):
            return [(k, self._dict[k]) for k in self._set]
        else:
            return [(k, self._dict[k]) for k in self._set.subiter(*args, **kwargs)]
    
    def iteritems(self, *args, **kwargs):
        if not (args or kwargs):
            return ((k, self._dict[k]) for k in self._set)
        else:
            return ((k, self._dict[k]) for k in self._set.subiter(*args, **kwargs))
    
    def iterkeys(self, *args, **kwargs):
        if not (args or kwargs):
            return iter(self._set)
        else:
            return self._set.subiter(*args, **kwargs)
    
    def itervalues(self, *args, **kwargs):
        if not (args or kwargs):
            return (self._dict[k] for k in self._set)
        else:
            return (self._dict[k] for k in self._set.subiter(*args, **kwargs))
    
    def keys(self, *args, **kwargs):
        if not (args or kwargs):
            return self._set.copy()
        else:
            return self._set.subset(*args, **kwargs)
    
    def pop(self, *args):
        present = args[0] in self._dict
        v_or_d = self._dict.pop(*args)
        if present:
            self._set.remove(args[0])
        return v_or_d
    
    def popitem(self, i = None):
        if self._dict:
            k = self._set.pop(i)
            return (k, self._dict.pop(k))
        else:
            return self._dict.popitem() # Just to raise the appropriate KeyError
    
    def setdefault(self, k, x=None):
        self._set.add(k)
        return self._dict.setdefault(k, x)
    
    def update(self, E, **F):
        #I'm not sure how to distinguish between dict-like and non-dict-like E
        if isinstance(E, ListDict):
           self._set |= E._set
           self._dict.update(E._dict)
        else:
           try:
               keys = E.keys()
               self._set.update(keys)
               self._dict.update(E)
           except:
               self._dict.update(E,**F)
               self._set.update(self._dict)
    
    def values(self, *args, **kwargs):
        if not (args or kwargs):
            return [self._dict[k] for k in self._set]
        else:
            return [self._dict[k] for k in self._set.subiter(*args, **kwargs)]
    
    def fromkeys(*args):
        return ListDict(dict.fromkeys(*args))
    
    #SortedMap methods
    def firstkey(self):
        return self._set.first()
    
    def lastkey(self):
        return self._set.last()
    
    def headdict(self, k, include=False, i=0, j=-1):
        return self._copysubdict(self._set.headset(k, include, i, j))
    
    def taildict(self, k, include=True, i=0, j=-1):
        return self._copysubdict(self._set.tailset(k, include, i, j))
        
    def subdict(self, fromkey, tokey, 
                      includehead=True, includetail=False, i=0, j=-1):
        return self._copysubdict(self._set.subset(fromkey, tokey, includehead,
                                                   includetail, i, j))

    def _copysubdict(self, s):
        L = ListDict()
        L._set = s
        L._dict.default_factory = self._dict.default_factory
        for k in s:
            L._dict[k] = self._dict[k]
        return L
    
    #NavigableMap methods
    def ceilingkey(self, k):
        return self._set.ceiling(k)
    
    def floorkey(self, k):
        return self._set.floor(k)
    
    def higherkey(self, k):
        return self._set.higher(k)
    
    def lowerkey(self, k):
        return self._set.lower(k)
    
    #ListSet methods
    def index(self, k, i=0, j=-1):
        return self._set.index(k, i, j)
        
    def position(self, k, i=0, j=-1):
        return self._set.position(k, i, j)
    
    def nthkey(self, ind):
        #ind can be an int or a slice
        return self._set[ind]
    
    def nthvalue(self, ind):
        if type(ind) is int:
            return self._dict[self._set[ind]]
        else:
            return [self._dict[k] for k in self._set[ind]]
    
    def nthdict(self, ind):
        s = self._set[ind]
        if type(s) is not ListSet:
            try:
                s = ListSet(s)
            except:
                s = ListSet((s,))
        return self._copysubdict(s)
                
class Overlap1D:
    """Overlap1D is a structure for determining quickly whether two intervals
    overlap."""
    
    def __init__(self):
        # _present is a dict of (position,set(objects)) pairs.  Each key is
        # the leftmost point of an object, and each value is the
        # set of all objects present at that point
        self._present = ListDict()
        # _rightend is a dict of (position,set(objects)).  Each key is the
        # rightmost point of one or more objects, and each value is a set of
        # only those objects that end at this point.
        self._rightend = ListDict(set)
        # _objects is a dict of (object, (left, right)).  It remembers where
        # objects start and stop.
        self._objects = dict()
    
    def add(self, obj, left, right):
        if (not self._present) or left < self._present.firstkey():
            self._present[left] = set((obj,))
        elif left not in self._present:
            # We are adding a new marker to _present.  Start with the nearest
            # marker to the left of the new one.
            prev = self._present[self._present.lowerkey(left)]
            # and keep only the objects that are still present at the new
            # location, i.e. whose rightmost point is further right than
            # the leftmost point of this new object.  We take a closed-left,
            # open-right convention.
            newsetgen = (o for o in prev if self._objects[o][1] > left)
            self._present[left] = set(newsetgen)
        
        intermediates = self._present.itervalues(left, right)
        for s in intermediates:
            # add the object to each set that is inside its interval
            s.add(obj)
        self._objects[obj] = (left,right)
        self._rightend[right].add(obj)
    
    def remove(self, obj):
        (left, right) = self._objects.pop(obj)
        intermediates = self._present.itervalues(left, right)
        for s in intermediates:
            s.remove(obj)
        #boolean tests whether self._present[left] is an empty set()
        if ((not self._present[left]) or
           (self._present[left] <= self._present[self._present.lowerkey(left)])):
            del self._present[left]
        self._rightend[right].remove(obj)
        if not self._rightend[right]:
            del self._rightend[right]
            
    def overlaps(self, left, right, closed = False):
        intermediates = self._present.itervalues(left, right)
        outset = set()
        for s in intermediates:
            outset |= s
            
        if ((left not in self._present) and self._present and
                                             (left > self._present.firstkey())):
            preleft = self._present.floorkey(left)
            prev = self._present[preleft]
            newsetgen = (o for o in prev if self._objects[o][1] > left)
            outset.update(newsetgen)
        if closed:
            if left in self._rightend:
                outset |= self._rightend[left]
            if right in self._present:
                outset |= self.present[right]
        return outset
    
    def collides(self, obj, closed=False):
        (left, right) = self._objects[obj]
        return self.overlaps(left, right, closed)
    
    def get_interval(self, obj):
        return self._objects[obj]

class Overlap2D:
    def __init__(self):
        self._x = Overlap1D()
        self._y = Overlap1D()
    
    def add(self, obj, x1, x2, y1, y2):
        self._x.add(obj, x1, x2)
        self._y.add(obj, y1, y2)
    
    def remove(self, obj):
        self._x.remove(obj)
        self._y.remove(obj)
   
    def overlaps(self, x1, x2, y1, y2, closed = False):
        xset = self._x.overlaps(x1,x2,closed)
        yset = self._y.overlaps(y1,y2,closed)
        return xset & yset
    
    def collides(self, obj, closed = False):
        xset = self._x.collides(obj, closed)
        yset = self._y.collides(obj, closed)
        return xset & yset
    
    def get_rectangle(self, obj):
        (x1, x2) = self._x.get_interval(obj)
        (y1, y2) = self._y.get_interval(obj)
        return (x1, x2, y1, y2)
