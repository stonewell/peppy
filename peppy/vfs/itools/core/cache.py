# -*- coding: UTF-8 -*-
# Copyright (C) 2009 Juan David Ibáñez Palomar <jdavid@itaapy.com>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""
This module implements a LRU (Least Recently Used) Cache.
http://en.wikipedia.org/wiki/Cache_algorithms
"""


class DNode(object):
    """This class makes the nodes of a doubly-linked list.
    """

    __slots__ = ['prev', 'next', 'key']


    def __init__(self, key):
        self.key = key



class LRUCache(dict):
    """LRU stands for Least-Recently-Used.

    The LRUCache is a mapping from key to value, it is implemented as a dict
    with some differences:

    - The elemens within the cache are ordered by the access time, starting
      from the least-recently used value.  All iteration methods ('items',
      'iteritems', 'keys', etc.) return the objects sorted by this criteria,
      and so does 'popitem' too.

    - The constructor is different from that of a dict, it expects first a
      'size_min' argument, and optionally a 'size_max' argument, they are
      used to control the dict size.

      Optionally it can take an 'automatic' boolean argument, which defaults
      to 'True'.

    - When the size of the cache surpasses the defined maximum size, then
      the least-recently used values from the cache will be removed, until its
      size reaches the defined minimum.

      This happens unless the 'automatic' parameter is set to 'False'.  Then
      it will be the responsability of external code to explicitly remove the
      least-recently used values.

    Some of the dict methods have been de-activated on purpose: 'copy',
    'fromkeys', 'setdefault' and 'update'.

    There are other new methods too:

    - touch(key): defines the value identified by the given key as to be
      accessed, hence it will be at the end of the list.
    """

    def __init__(self, size_min, size_max=None, automatic=True):
        # Check arguments type
        if type(size_min) is not int:
            error = "the 'size_min' argument must be an int, not '%s'"
            raise TypeError, error % type(size_min)
        if type(automatic) is not bool:
            error = "the 'automatic' argument must be an int, not '%s'"
            raise TypeError, error % type(automatic)

        if size_max is None:
            size_max = size_min
        elif type(size_max) is not int:
            error = "the 'size_max' argument must be an int, not '%s'"
            raise TypeError, error % type(size_max)
        elif size_max < size_min:
            raise ValueError, "the 'size_max' is smaller than 'size_min'"

        # Initialize the dict
        dict.__init__(self)
        # The doubly-linked list
        self.first = None
        self.last = None
        # Map from key-to-node
        self.key2node = {}
        # The cache size
        self.size_min = size_min
        self.size_max = size_max
        # Whether to free memory automatically or not (boolean)
        self.automatic = automatic


    def _check_integrity(self):
        """This method is for testing purposes, it checks the internal
        data structures are consistent.
        """
        keys = self.keys()
        keys.sort()
        # Check the key-to-node mapping
        keys2 = self.key2node.keys()
        keys2.sort()
        assert keys == keys2
        # Check the key-to-node against the doubly-linked list
        for key, node in self.key2node.iteritems():
            assert type(key) is type(node.key)
            assert key == node.key
        # Check the doubly-linked list against the cache
        keys = set(keys)
        node = self.first
        while node is not None:
            assert node.key in keys
            keys.discard(node.key)
            node = node.next
        assert len(keys) == 0


    def _append(self, key):
        node = DNode(key)

        # (1) Insert into the key-to-node map
        self.key2node[key] = node

        # (2) Append to the doubly-linked list
        node.prev = self.last
        node.next = None
        if self.first is None:
            self.first = node
        else:
            self.last.next = node
        self.last = node

        # Free memory if needed
        if self.automatic is True and len(self) > self.size_max:
            while len(self) > self.size_min:
                self.popitem()


    def _remove(self, key):
        # (1) Pop the node from the key-to-node map
        node = self.key2node.pop(key)

        # (2) Remove from the doubly-linked list
        if node.prev is None:
            self.first = node.next
        else:
            node.prev.next = node.next

        if node.next is None:
            self.last = node.prev
        else:
            node.next.prev = node.prev


    ######################################################################
    # Override dict API
    def __iter__(self):
        node = self.first
        while node is not None:
            yield node.key
            node = node.next


    def __setitem__(self, key, value):
        dict.__setitem__(self, key, value)
        self._append(key)


    def __delitem__(self, key):
        self._remove(key)
        dict.__delitem__(self, key)


    def clear(self):
        dict.clear(self)
        self.key2node.clear()
        self.first = self.last = None


    def copy(self):
        raise NotImplementedError, "use 'copy.deepcopy' to copy a cache"


    def fromkeys(self, seq, value=None):
        raise NotImplementedError, "the 'fromkeys' method is not supported"


    def items(self):
        return list(self.iteritems())


    def iteritems(self):
        node = self.first
        while node is not None:
            yield node.key, self[node.key]
            node = node.next


    def iterkeys(self):
        node = self.first
        while node is not None:
            yield node.key
            node = node.next


    def itervalues(self):
        node = self.first
        while node is not None:
            yield self[node.key]
            node = node.next


    def keys(self):
        return list(self.iterkeys())


    def pop(self, key):
        self._remove(key)
        return dict.pop(self, key)


    def popitem(self):
        if self.first is None:
            raise KeyError, 'popitem(): cache is empty'
        key = self.first.key
        value = self[key]
        del self[key]
        return (key, value)


    def setdefault(self, key, default=None):
        raise NotImplementedError, "the 'setdefault' method is not supported"


    def update(self, value=None, **kw):
        raise NotImplementedError, "the 'update' method is not supported"


    def values(self):
        return list(self.itervalues())


    ######################################################################
    # Specific public API
    def touch(self, key):
        # (1) Get the node from the key-to-node map
        node = self.key2node[key]

        # (2) Touch in the doubly-linked list
        # Already the last one
        if node.next is None:
            return

        # Unlink
        if node.prev is None:
            self.first = node.next
        else:
            node.prev.next = node.next
        node.next.prev = node.prev

        # Link
        node.prev = self.last
        node.next = None
        self.last.next = node
        self.last = node

