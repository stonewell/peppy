# -*- coding: UTF-8 -*-
# Copyright (C) 2004-2007 Juan David Ibáñez Palomar <jdavid@itaapy.com>
# Copyright (C) 2006 Hervé Cauwelier <herve@itaapy.com>
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
This module aims to implement the URI standard as specified by RFC2396,
see http://www.ietf.org/rfc/rfc2396.txt


Other related RFCs include:

 - The URN scheme, http://www.ietf.org/rfc/rfc2141.txt

 - List of URI schemes: http://www.iana.org/assignments/uri-schemes

 - Registration of new schemes, http://www.ietf.org/rfc/rfc2717.txt
"""

# FIXME Latest URI RFC is 3986: http://www.faqs.org/rfcs/rfc3986.html
# Check agains it.
# Consider a C library, for instance: http://uriparser.sourceforge.net/

# XXX A resource should be an inmutable object, at least its components
# (scheme, authority, path, query and fragment). Then we could get rid
# of the copy method. And this change woule easy the way to a datetime
# like API.

# Import from the Standard Library
import sys
from copy import copy
from urlparse import urlsplit, urlunsplit
import urllib


##########################################################################
# Authority
##########################################################################

class Authority(object):
    """
    There are two types of authorities: registry based and server-based;
    right now only server-based are supported (XXX).

    The userinfo component could be further processed.
    """

    __slots__ = ['userinfo', 'host', 'port']


    def __init__(self, auth):
        # The userinfo
        if '@' in auth:
            self.userinfo, auth = auth.split('@', 1)
        else:
            self.userinfo = None
        # host:port
        if ':' in auth:
            self.host, self.port = auth.split(':', 1)
        else:
            self.host = auth
            self.port = None


    def __str__(self):
        # userinfo@host
        if self.userinfo is not None:
            auth = '%s@%s' % (self.userinfo, self.host)
        else:
            auth = self.host
        # The port
        if self.port is not None:
            return auth + ':' + self.port
        return auth


    def __eq__(self, other):
        return unicode(self) == unicode(other)


    def __hash__(self):
        return hash(unicode(self))


    def __nonzero__(self):
        return bool(unicode(self))



#########################################################################
# Path
##########################################################################

def normalize_path(path):
    """
    Normalize the path (we don't use os.path because on Windows it
    converts forward slashes to back slashes).

    Examples:

      'a//b/c'     -> 'a/b/c'
      'a/./b/c'    -> 'a/b/c'
      'a/b/c/../d' -> 'a/b/d'
      '/../a/b/c ' -> '/a/b/c'
      '.'          -> ''
    """
    if not isinstance(path, (str, unicode)):
        raise TypeError, 'path must be an string, not a %s' % type(path)

    # Does the path start by an slash? i.e.: is it absolute?
    startswith_slash = path.startswith('/')

    # Does the path end by an slash? (relevant to resolve URLs)
    endswith_slash = path.endswith('/') or path.endswith('/.')

    # Split the path http://a//
    path = path.split('/')

    # Transform '//' and '/./' to '/'
    path = [ x for x in path if x not in ('', '.') ]

    # Transform 'a/..' to ''
    stack = []
    for name in path:
        if name == '..' and stack and stack[-1] != '..':
            stack.pop()
        else:
            stack.append(name)
    path = stack

    # Absolute or Relative
    if startswith_slash:
        # Absolute path, remove '..' at the beginning
        while path and path[0] == '..':
            path = path[1:]

    path = '/'.join(path)
    if path:
        if startswith_slash:
            path = '/' + path
        if endswith_slash:
            path = path + '/'
        return path
    else:
        if startswith_slash:
            return '/'
        return ''



class Segment(str):

    __slots__ = []

    def get_name(self):
        return self.split(';', 1)[0]

    name = property(get_name, None, None, '')


    def get_params(self):
        if ';' in self:
            return self.split(';')[1:]
        return []

    params = property(get_params, None, None, '')



class USegment(unicode):

    __slots__ = []

    def get_name(self):
        return self.split(';', 1)[0]

    name = property(get_name, None, None, '')


    def get_params(self):
        if ';' in self:
            return self.split(';')[1:]
        return []

    params = property(get_params, None, None, '')



class Path(list):
    """
    A path is a sequence of segments. A segment is has a name and,
    optionally one or more parameters.

    A path may start and/or end by an slash. This information is only
    useful when resolving paths. When a path starts by an slash it is
    called an absolute path, otherwise it is called a relative path.
    """

    __slots__ = ['startswith_slash', 'endswith_slash', 'dospath']


    def __init__(self, path):
        if isinstance(path, tuple) or isinstance(path, list):
            path = '/'.join([ unicode(x) for x in path ])

        path = normalize_path(path)

        self.dospath = False
        if len(path) > 1:
            doschar = path[0].lower()
            if doschar >= 'a' and doschar <= 'z' and path[1] == ':':
                self.dospath = True
        
        # Absolute or relative
        self.startswith_slash = path.startswith('/')
        if self.startswith_slash:
            path = path[1:]
        self.endswith_slash = path.endswith('/')
        if self.endswith_slash:
            path = path[:-1]

        if isinstance(path, unicode):
            segment = USegment
        else:
            segment = Segment
        if path != '':
            path = [ segment(x) for x in path.split('/') ]
            list.__init__(self, path)


    def __getslice__(self, a, b):
         slice = Path(list.__getslice__(self, a, b))
         slice.startswith_slash = self.startswith_slash
         return slice


    def __add__(self, path):
        raise NotImplementedError, \
              'paths can not be added, use resolve2 instead'


    ##########################################################################
    # API
    def __repr__(self):
        return '<itools.uri.Path at %s>' % hex(id(self))


    def __str__(self):
        path = ''
        if self.startswith_slash:
            path = '/'
        path += '/'.join([ str(x) for x in self ])
        if self.endswith_slash:
            path += '/'
        if len(path) == 0:
            return '.'
        return path

    def __unicode__(self):
        path = u''
        if self.startswith_slash:
            path = u'/'
        #for x in self:
        #    print(repr(x))
        path += u'/'.join([ unicode(x) for x in self ])
        if self.endswith_slash:
            path += u'/'
        if len(path) == 0:
            return u'.'
        return path


    def __ne__(self, other):
        if isinstance(other, str) or isinstance(other, unicode):
            other = Path(other)

        return unicode(self) != unicode(other)


    def __eq__(self, other):
        if isinstance(other, str) or isinstance(other, unicode):
            other = Path(other)

        return unicode(self) == unicode(other)


    def __hash__(self):
        return hash(unicode(self))


    def is_absolute(self):
        return self.startswith_slash or self.dospath


    def is_relative(self):
        return not self.dospath and not self.startswith_slash


    def get_name(self):
        if len(self) > 0:
            return self[-1].name
        return ''


    def resolve(self, path):
        """
        Resolve the path following the standard (RFC2396). This is to say,
        it takes into account the trailing slash, so:

          Path('/a/b').resolve('c') => Path('/a/c')
          Path('/a/b/').resolve('c') => Path('/a/b/c')
        """
        if not isinstance(path, Path):
            path = Path(path)

        if path.is_absolute():
            return path

        if self.endswith_slash:
            if len(self) > 0 and isinstance(self[0], unicode):
                template = u'%s/%s'
            else:
                template = '%s/%s'
            return Path(template % (self, path))

        if len(self) > 0 and isinstance(self[0], unicode):
            template = u'%s/../%s'
        else:
            template = '%s/../%s'
        return Path(template % (self, path))


    def resolve2(self, path):
        """
        This method provides an alternative to the standards resolution
        algorithm. The difference is that it not takes into account the
        trailing slash (it behaves like if always there was a trailing
        slash):

          Path('/a/b').resolve('c') => Path('/a/b/c')
          Path('/a/b/').resolve('c') => Path('/a/b/c')

        Very, very practical.
        """
        if not isinstance(path, Path):
            path = Path(path)

        if path.is_absolute():
            return path

        if len(self) > 0 and isinstance(self[0], unicode):
            try:
                path = unicode(path)
            except UnicodeDecodeError:
                #for comp in path:
                #    print("components: %s" % repr(comp))
                path = str(path)
                #print("path: %s, encoding=%s" % (repr(path), sys.getfilesystemencoding()))
                #path = str(path).encode(sys.getfilesystemencoding())
                path = str(path).decode('utf-8')
            return Path(u'%s/%s' % (self, path))
        return Path('%s/%s' % (self, path))


    def get_prefix(self, path):
        """
        Returns the common prefix of two paths, for example:

          >>> print Path('a/b/c').get_prefix(Path('a/b/d/e'))
          a/b

        XXX When there are parameters (e.g. a/b;lang=es/c) it is undefined.
        """
        if not isinstance(path, Path):
            path = Path(path)

        i = 0
        while i < len(self) and i < len(path) and self[i] == path[i]:
            i = i + 1
        return self[:i]


    def get_pathto(self, path):
        """
        Returns the relative path from 'self' to 'path'. This operation is
        the complement of 'resolve2'. So, if 'x = a.get_pathto(b)', then
        'b = a.resolve2(x)'.
        """
        if not isinstance(path, Path):
            path = Path(path)

        prefix = self.get_prefix(path)
        i = len(prefix)
        return Path(((['..'] * len(self[i:])) + path[i:]) or ['.'])


    def get_pathtoroot(self):
        """
        Returns the path from the tail to the head, for example: '../../..'
        """
        return Path('../' * (len(self) - 1))



#########################################################################
# Query
##########################################################################

# Implements the 'application/x-www-form-urlencoded' content type (see
# http://www.w3.org/TR/REC-html40/interact/forms.html#h-17.13.4.1). The
# information decode as a dictionary.

# XXX This is not specified by RFC2396, so maybe we should not parse the
# query for the generic case.

# XXX The Python functions 'cgi.parse_qs' and 'urllib.urlencode' provide
# similar functionality, maybe we should just be a thin wrapper around
# them.

def decode_query(data):
    """
    Decodes a query as defined by the "application/x-www-form-urlencoded"
    content type.

    The value expected is a byte string like "a=1&b=2"; the value returned
    is a dictonary like {'a': 1, 'b': 2}.

    See http://www.w3.org/TR/REC-html40/interact/forms.html#h-17.13.4.1
    for details.
    """
    query = {}
    if data:
        for x in data.split('&'):
            if x:
                if '=' in x:
                    key, value = x.split('=', 1)
                    value = urllib.unquote_plus(value)
                else:
                    key, value = x, None

                key = urllib.unquote_plus(key)
                if key in query:
                    old_value = query[key]
                    if isinstance(old_value, list):
                        old_value.append(value)
                    else:
                        value = [old_value, value]
                        query[key] = value
                else:
                    query[key] = value
    return query


def encode_query(query):
    """
    This method encodes a query as defined by the
    "application/x-www-form-urlencoded" content type (see
    http://www.w3.org/TR/REC-html40/interact/forms.html#h-17.13.4.1 for
    details)

    The value expected is a dictonary like {'a': 1, 'b': 2}.
    The value returned is a byte string like "a=1&b=2".
    """
    # Special case: the empty reference sets query to None, so this case must
    # be considered
    if not query:
        return ""
    
    line = []
    for key, value in query.items():
        key = urllib.quote_plus(key)
        if value is None:
            # XXX As of the application/x-www-form-urlencoded content type,
            # it has not sense to have a parameter without a value, so
            # "?a&b=1" should be the same as "?b=1" (check the spec).
            # But for the tests defined by RFC2396 to pass, we must preserve
            # these empty parameters.
            line.append(key)
        elif isinstance(value, list):
            for x in value:
                if isinstance(x, unicode):
                    x = x.encode('UTF-8')
                line.append('%s=%s' % (key, urllib.quote_plus(x)))
        else:
            if isinstance(value, unicode):
                value = value.encode('UTF-8')
            line.append('%s=%s' % (key, urllib.quote_plus(value)))
    return '&'.join(line)



##########################################################################
# Generic references
##########################################################################

class Reference(object):
    """
    A common URI reference is made of five components:

    - the scheme
    - the authority
    - the path
    - the query
    - the fragment

    Its syntax is:

      <scheme>://<authority><path>?<query>#<fragment>

    Not all the components must be present, examples of possible references
    include:

    http://www.example.com
    http://www.ietf.org/rfc/rfc2616.txt
    /rfc/rfc2616.txt
    XXX
    """

    __slots__ = ['scheme', 'authority', 'path', 'query', 'fragment']


    def __init__(self, scheme, authority, path, query, fragment=None):
        self.scheme = scheme
        self.authority = authority
        self.path = path
        self.query = query
        self.fragment = fragment


##    def get_netpath(self):
##        return NetPath('//%s/%s' % (self.authority, self.path))
##
##    netpath = property(get_netpath, None, None, '')


    def __getstate__(self):
        return unicode(self)


    def __setstate__(self, data):
        ref = GenericDataType.decode(data)
        for attr in self.__slots__:
            setattr(self, attr, getattr(ref, attr))


    def __str__(self):
        path = str(self.path)
        if path == '.':
            path = ''
        query = encode_query(self.query)
        reference = urlunsplit((self.scheme, str(self.authority), path, query,
                                self.fragment))
        if reference == '':
            if self.fragment is not None:
                return '#'
            return '.'
        return reference


    def __unicode__(self):
        path = unicode(self.path)
        if path == u'.':
            path = u''
        query = encode_query(self.query)
        reference = urlunsplit((self.scheme, str(self.authority), path, query,
                                self.fragment))
        if reference == '':
            if self.fragment is not None:
                return u'#'
            return u'.'
        return reference


    def __eq__(self, other):
        return unicode(self) == unicode(other)


    def __hash__(self):
        return hash(unicode(self))


    def resolve(self, reference):
        """
        Resolve the given relative URI, this URI (self) is considered to be
        the base.

        If the given uri is not relative, it is returned. If 'self' is not
        absolute, the result is undefined.
        """
        if not isinstance(reference, Reference):
            reference = GenericDataType.decode(reference)

        # Absolute URI
        if reference.scheme:
            return reference

        # Network path
        if reference.authority:
            return Reference(self.scheme,
                             copy(reference.authority),
                             copy(reference.path),
                             copy(reference.query),
                             reference.fragment)

        # Absolute path
        if reference.path.is_absolute():
            return Reference(self.scheme,
                             copy(self.authority),
                             copy(reference.path),
                             copy(reference.query),
                             reference.fragment)

        # Internal references
        if isinstance(reference, EmptyReference):
            return Reference(self.scheme,
                             copy(self.authority),
                             copy(self.path),
                             self.query.copy(),
                             None)

        if reference.fragment and not reference.path and not reference.query:
            return Reference(self.scheme,
                             copy(self.authority),
                             copy(self.path),
                             copy(self.query),
                             reference.fragment)

        # Relative path
        return Reference(self.scheme,
                         copy(self.authority),
                         self.path.resolve(reference.path),
                         copy(reference.query),
                         reference.fragment)


    def resolve2(self, reference):
        """
        This is much like 'resolv', but uses 'Path.resolve2' method instead.

        XXX Too much code is duplicated, the only difference beween 'resolve'
        and 'resolve2' is one character. Refactor!
        """
        if not isinstance(reference, Reference):
            reference = GenericDataType.decode(reference)

        # Absolute URI
        if reference.scheme:
            return reference

        # Network path
        if reference.authority:
            return Reference(self.scheme,
                             copy(reference.authority),
                             copy(reference.path),
                             copy(reference.query),
                             reference.fragment)

        # Absolute path
        if reference.path.is_absolute():
            return Reference(self.scheme,
                             copy(self.authority),
                             copy(reference.path),
                             copy(reference.query),
                             reference.fragment)

        # Internal references
        if isinstance(reference, EmptyReference):
            return Reference(self.scheme,
                             copy(self.authority),
                             copy(self.path),
                             copy(self.query),
                             None)

        if reference.fragment and not reference.path and not reference.query:
            return Reference(self.scheme,
                             copy(self.authority),
                             copy(self.path),
                             copy(self.query),
                             reference.fragment)

        # Relative path
        return Reference(self.scheme,
                         copy(self.authority),
                         self.path.resolve2(reference.path),
                         copy(reference.query),
                         reference.fragment)


    def replace(self, **kw):
        """
        This method returns a new uri reference, equal to this one, but
        with the given keyword parameters set in the query.
        """
        query = copy(self.query)
        for key in kw:
            value = kw[key]
            if value is None:
                if key in query:
                    del query[key]
            else:
                query[key] = value
        return Reference(self.scheme, self.authority, self.path, query,
                         self.fragment)


    def copy(self):
        """Make a new object containing the same information as the current
        reference.
        """
        return Reference(self.scheme, self.authority, self.path, self.query,
                         self.fragment)



class EmptyReference(Reference):

    scheme = None
    authority = None
    path = Path('')
    query = None
    fragment = None


    def __init__(self):
        pass


    def __str__(self):
        return ''


##########################################################################
# Factory
##########################################################################

class GenericDataType(object):

    @staticmethod
    def decode(data):
        if isinstance(data, Path):
            return Reference('', Authority(''), data, {}, None)

        if not isinstance(data, (str, unicode)):
            raise TypeError, 'unexpected %s' % type(data)

        # Special case, the empty reference
        if data == '':
            return EmptyReference()

        # Special case, the empty fragment
        if data == '#':
            return Reference('', Authority(''), Path(''), {}, '')

        # All other cases, split the reference in its components
        scheme, authority, path, query, fragment = urlsplit(data)
        
        # Convenience function to break out the fragment from a file URL.  This
        # assumes that the only allowed fragments are digits, specifying line
        # numbers.
        def find_fragment(path, fragment):
            if "#" in path:
                # the fragment is improperly placed in the path
                path1, fragment1 = path.rsplit("#", 1)
                if fragment1.isdigit():
                    return path1, fragment1
            return path, fragment
            
        # Some special cases for Windows paths c:/a/b#4 and file:///c:/a/b#4.
        # urlsplit has problems with the scheme, leading slashes in the path,
        # and doesn't split out the fragment properly.  Also, replace windows-
        # style backslash separators with forward slashes
        if len(scheme) == 1:
            # found a windows drive name instead of path, because urlsplit
            # thinks the scheme is "c" for Windows paths like "c:/a/b"
            path, fragment = find_fragment(path, fragment)
            # Also replace backslash characters if present
            path = "%s:%s" % (scheme, path.replace('\\', '/'))
            scheme = "file"
        elif len(path) > 3 and path[0] == '/' and path[2] == ':':
            # urlsplit also doesn't correctly handle windows path in url form
            # like "file:///c:/a/b" -- it thinks the path is "/c:/a/b", which
            # to be correct requires removing the leading slash.
            drive = path[1].lower()
            path = path[3:]
            path, fragment = find_fragment(path, fragment)
            path = "%s:%s" % (drive, path.replace('\\', '/'))
        
        # The path
        if path:
            path = urllib.unquote(path)
        elif authority:
            # Force path to be empty instead of "/" because we need to
            # recognize the difference between http://www.example.com and
            # http://www.example.com/.  Note that an empty Path object gets
            # converted to "." when printed.
            path = ""
        # The authority
        authority = urllib.unquote(authority)
        authority = Authority(authority)
        # The query
        try:
            query = decode_query(query)
        except ValueError:
            pass
        # The fragment
        if fragment == '':
            fragment = None

        return Reference(scheme, authority, Path(path), query, fragment)
