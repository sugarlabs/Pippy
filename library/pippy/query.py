# Copyright (C) 2007 One Laptop per Child
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA

import logging

import dbus
import gobject

from sugar.datastore import datastore

DS_DBUS_SERVICE = 'org.laptop.sugar.DataStore'
DS_DBUS_INTERFACE = 'org.laptop.sugar.DataStore'
DS_DBUS_PATH = '/org/laptop/sugar/DataStore'

# Properties the journal cares about.
PROPERTIES = ['uid', 'title', 'mtime', 'timestamp', 'keep', 'buddies',
              'icon-color', 'mime_type', 'progress', 'activity', 'mountpoint',
              'activity_id']


class _Cache(gobject.GObject):

    __gtype_name__ = 'query_Cache'

    __gsignals__ = {
        'modified': (gobject.SIGNAL_RUN_FIRST,
                     gobject.TYPE_NONE,
                     ([]))
    }

    def __init__(self, jobjects=None):
        gobject.GObject.__init__(self)

        self._array = []
        self._dict = {}
        if jobjects is not None:
            self.append_all(jobjects)

        logging.debug('_Cache.__init__: connecting signals.')
        bus = dbus.SessionBus()
        datastore = dbus.Interface(
            bus.get_object(DS_DBUS_SERVICE, DS_DBUS_PATH), DS_DBUS_INTERFACE)
        self._datastore_created_handler = \
            datastore.connect_to_signal('Created', self._datastore_created_cb)
        self._datastore_updated_handler = \
            datastore.connect_to_signal('Updated', self._datastore_updated_cb)
        self._datastore_deleted_handler = \
            datastore.connect_to_signal('Deleted', self._datastore_deleted_cb)

    def prepend_all(self, jobjects):
        for jobject in jobjects[::-1]:
            self._array.insert(0, jobject)
            self._dict[jobject.object_id] = jobject

    def append_all(self, jobjects):
        for jobject in jobjects:
            self._array.append(jobject)
            self._dict[jobject.object_id] = jobject

    def remove_all(self, jobjects):
        jobjects = jobjects[:]
        for jobject in jobjects:
            obj = self._dict[jobject.object_id]
            self._array.remove(obj)
            del self._dict[obj.object_id]
            obj.destroy()

    def __len__(self):
        return len(self._array)

    def __getitem__(self, key):
        if isinstance(key, basestring):
            return self._dict[key]
        else:
            return self._array[key]

    def destroy(self):
        logging.debug('_Cache.destroy: will disconnect signals.')
        self._datastore_created_handler.remove()
        self._datastore_updated_handler.remove()
        self._datastore_deleted_handler.remove()
        self._destroy_jobjects(self._array)
        self._array = []
        self._dict = {}

    def _invalidate(self):
        self._destroy_jobjects(self._array)
        self._array = []
        self._dict = {}
        self.emit('modified')

    def _destroy_jobjects(self, jobjects):
        for jobject in jobjects:
            jobject.destroy()

    def _datastore_created_cb(self, uid):
        logging.debug('_datastore_created_cb: %r' % uid)
        self._invalidate()

    def _datastore_updated_cb(self, uid):
        logging.debug('_datastore_updated_cb: %r' % uid)
        if uid in self._dict:
            jobject = datastore.get(uid)
            index = self._array.index(self._dict[uid])
            self._array[index].destroy()
            self._array[index] = jobject
            self._dict[uid] = jobject
            self.emit('modified')

    def _datastore_deleted_cb(self, uid):
        logging.debug('_datastore_deleted_cb: %r' % uid)
        self._invalidate()


class ResultSet(gobject.GObject):

    __gtype_name__ = 'ResultSet'

    __gsignals__ = {
        'modified': (gobject.SIGNAL_RUN_FIRST,
                     gobject.TYPE_NONE,
                     ([]))
    }

    _CACHE_LIMIT = 80

    def __init__(self, query, sorting):
        gobject.GObject.__init__(self)
        self._total_count = -1
        self._position = -1
        self._query = query
        self._sorting = sorting

        self._offset = 0
        self._cache = _Cache()
        self._cache_modified_handler = \
            self._cache.connect('modified', self._cache_modified_cb)

    def destroy(self):
        self._cache.disconnect(self._cache_modified_handler)
        self._cache.destroy()
        del self._cache

    def get_length(self):
        if self._total_count == -1:
            jobjects, self._total_count = datastore.find(
                self._query,
                sorting=self._sorting,
                limit=ResultSet._CACHE_LIMIT,
                properties=PROPERTIES)
            self._cache.append_all(jobjects)
            self._offset = 0
        return self._total_count

    length = property(get_length)

    def seek(self, position):
        self._position = position

    def read(self, max_count):
        logging.debug('ResultSet.read position: %r' % self._position)

        if max_count * 5 > ResultSet._CACHE_LIMIT:
            raise RuntimeError(
                'max_count (%i) too big for ResultSet._CACHE_LIMIT'
                ' (%i).' % (max_count, ResultSet._CACHE_LIMIT))

        if self._position == -1:
            self.seek(0)

        if self._position < self._offset:
            remaining_forward_entries = 0
        else:
            remaining_forward_entries = \
                self._offset + len(self._cache) - self._position

        if self._position > self._offset + len(self._cache):
            remaining_backwards_entries = 0
        else:
            remaining_backwards_entries = self._position - self._offset

        last_cached_entry = self._offset + len(self._cache)

        if (remaining_forward_entries <= 0 and
            remaining_backwards_entries <= 0) or \
                max_count > ResultSet._CACHE_LIMIT:

            # Total cache miss: remake it
            offset = max(0, self._position - max_count)
            logging.debug('remaking cache, offset: %r limit: %r' %
                          (offset, max_count * 2))
            jobjects, self._total_count = datastore.find(
                self._query,
                sorting=self._sorting,
                offset=offset,
                limit=ResultSet._CACHE_LIMIT,
                properties=PROPERTIES)

            self._cache.remove_all(self._cache)
            self._cache.append_all(jobjects)
            self._offset = offset

        elif remaining_forward_entries < 2 * max_count and \
                last_cached_entry < self._total_count:

            # Add one page to the end of cache
            logging.debug('appending one more page, offset: %r' %
                          last_cached_entry)
            jobjects, self._total_count = datastore.find(
                self._query,
                sorting=self._sorting,
                offset=last_cached_entry,
                limit=max_count,
                properties=PROPERTIES)

            # update cache
            self._cache.append_all(jobjects)

            # apply the cache limit
            objects_excess = len(self._cache) - ResultSet._CACHE_LIMIT
            if objects_excess > 0:
                self._offset += objects_excess
                self._cache.remove_all(self._cache[:objects_excess])

        elif remaining_backwards_entries < 2 * max_count and self._offset > 0:

            # Add one page to the beginning of cache
            limit = min(self._offset, max_count)
            self._offset = max(0, self._offset - max_count)

            logging.debug('prepending one more page, offset: %r limit: %r' %
                          (self._offset, limit))
            jobjects, self._total_count = datastore.find(
                self._query,
                sorting=self._sorting,
                offset=self._offset,
                limit=limit,
                properties=PROPERTIES)

            # update cache
            self._cache.prepend_all(jobjects)

            # apply the cache limit
            objects_excess = len(self._cache) - ResultSet._CACHE_LIMIT
            if objects_excess > 0:
                self._cache.remove_all(self._cache[-objects_excess:])
        else:
            logging.debug('cache hit and no need to grow the cache')

        first_pos = self._position - self._offset
        last_pos = self._position - self._offset + max_count
        return self._cache[first_pos:last_pos]

    def _cache_modified_cb(self, cache):
        logging.debug('_cache_modified_cb')
        if not len(self._cache):
            self._total_count = -1
        self.emit('modified')


def find(query, sorting=['-mtime']):
    result_set = ResultSet(query, sorting)
    return result_set

if __name__ == "__main__":
    TOTAL_ITEMS = 1000
    SCREEN_SIZE = 10

    def mock_debug(string):
        print "\tDEBUG: %s" % string
    logging.debug = mock_debug

    def mock_find(query, sorting=None, limit=None, offset=None, properties=[]):
        print "mock_find %r %r" % (offset, (offset + limit))

        if limit is None or offset is None:
            raise RuntimeError("Unimplemented test.")

        result = []
        for index in range(offset, offset + limit):
            obj = datastore.DSObject(index, datastore.DSMetadata({}), '')
            result.append(obj)

        return result, TOTAL_ITEMS
    datastore.find = mock_find

    result_set = find({})

    print "Get first page"
    objects = result_set.read(SCREEN_SIZE)
    print [obj.object_id for obj in objects]
    assert range(0, SCREEN_SIZE) == [obj.object_id for obj in objects]
    print ""

    print "Scroll to 5th item"
    result_set.seek(5)
    objects = result_set.read(SCREEN_SIZE)
    print [obj.object_id for obj in objects]
    assert range(5, SCREEN_SIZE + 5) == [obj.object_id for obj in objects]
    print ""

    print "Scroll back to beginning"
    result_set.seek(0)
    objects = result_set.read(SCREEN_SIZE)
    print [obj.object_id for obj in objects]
    assert range(0, SCREEN_SIZE) == [obj.object_id for obj in objects]
    print ""

    print "Hit PgDn five times"
    for i in range(0, 5):
        result_set.seek((i + 1) * SCREEN_SIZE)
        objects = result_set.read(SCREEN_SIZE)
        print [obj.object_id for obj in objects]
        assert range((i + 1) * SCREEN_SIZE, (i + 2) * SCREEN_SIZE) == \
            [obj.object_id for obj in objects]
    print ""

    print "Hit PgUp five times"
    for i in range(0, 5)[::-1]:
        result_set.seek(i * SCREEN_SIZE)
        objects = result_set.read(SCREEN_SIZE)
        print [obj.object_id for obj in objects]
        assert range(i * SCREEN_SIZE, (i + 1) * SCREEN_SIZE) == \
            [obj.object_id for obj in objects]
    print ""
