import os, sys
import copy as pycopy

from peppy.vfs.itools.datatypes import FileName
from peppy.vfs.itools.vfs import *
from peppy.vfs.itools.vfs.registry import get_file_system, deregister_file_system, _file_systems
from peppy.vfs.itools.uri import get_reference, Reference, Path
from peppy.vfs.itools.uri.generic import Authority
from peppy.vfs.itools.vfs.base import BaseFS

from peppy.debug import *

def normalize(ref, base=None):
    """Normalize a url string into a reference and fix windows shenanigans"""
    if not isinstance(ref, Reference):
        if ref.startswith('file:'):
            # URLs always use /, so change windows path separators to forward
            # slashes
            try:
                ref = unicode(ref)
            except UnicodeDecodeError:
                try:
                    ref = str(ref).decode(sys.getfilesystemencoding())
                except UnicodeDecodeError:
                    ref = str(ref).decode('utf-8')
            #dprint(repr(ref))
            if os.path.sep == '\\':
                ref = ref.replace(os.path.sep, '/')
        ref = get_reference(ref)
    # If the reference is absolute (i.e.  contains a scheme), we return;
    # otherwise we assume it's a file:// URI
    #dprint(str(ref))
    if ref.scheme:
        return ref

    # Default to the current working directory
    if base is None:
        try:
            base = os.getcwd().decode(sys.getfilesystemencoding())
        except UnicodeDecodeError:
            base = os.getcwd().decode('utf-8')

    # URLs always use /
    if os.path.sep == '\\':
        base = base.replace(os.path.sep, '/')
    #dprint(base)
    # Check windows drive letters and add extra slash for correct URL syntax
    if len(base) > 1 and base[1] == ':':
        base = "/%s:%s" % (base[0].lower(), base[2:])
    baseref = get_reference(u'file://%s/' % base)
    try:
        path = unicode(ref.path)
    except UnicodeDecodeError:
        try:
            path = str(ref.path).decode(sys.getfilesystemencoding())
        except UnicodeDecodeError:
            path = str(ref.path).decode('utf-8')
    #dprint(repr(path))
    
    # Add the query string and fragment if they exist
    newref = baseref.resolve(path)
    newref.query = ref.query
    newref.fragment = ref.fragment
    #dprint(newref)
    return newref

def canonical_reference(ref):
    """Normalize a uri but remove any query string or fragments."""
    # get a copy of the reference
    if not isinstance(ref, Reference):
        ref = normalize(unicode(ref))
        ref.query = {}
        ref.fragment = ''
    else:
        from copy import copy
        ref = Reference(ref.scheme, copy(ref.authority), copy(ref.path), {}, '')
    
    # make sure that any path that points to a folder ends with a slash
    if is_folder(ref):
        ref.path.endswith_slash = True
    return ref

def get_file_system_schemes():
    """Return a list of all filesystem scheme names"""
    return _file_systems.keys()

def get_dirname(ref):
    if not isinstance(ref, Reference):
        ref = get_reference(ref)
    return Reference(ref.scheme,
                     pycopy.copy(ref.authority),
                     ref.path.resolve2('../'),
                     pycopy.copy(ref.query),
                     ref.fragment)

def get_filename(ref):
    if not isinstance(ref, Reference):
        ref = get_reference(ref)
    """Convenience method to return the filename component of the URL"""
    return ref.path[-1]

def get_file_reference(path):
    """Get a relative filename reference based on the path, ignoring # or ?
    characters special meaning in URLs.
    
    Because filesystem files aren't required to obey the URL character rules
    about # or ?, force the passed in path into a URL L{Reference} object
    without being interpreted as a query string or fragment.
    """
    import urllib
    return get_reference(urllib.quote(path))

def reference_with_new_extension(ref, ext):
    """Returns copy of reference with new extension
    
    If the URL has a extension, it is replaced by the new extension.  If
    it doesn't have an extension, the new extension is appended.  The new
    extension may be specified with or without the leading "." character.
    """
    if not isinstance(ref, Reference):
        ref = get_reference(ref)
    path = pycopy.copy(ref.path)
    last = path.pop()
    if "." in last:
        prefix, oldext = os.path.splitext(last)
    else:
        prefix = last
    while ext.startswith("."):
        ext = ext[1:]
    last = "%s.%s" % (prefix, ext)
    return Reference(ref.scheme,
                     pycopy.copy(ref.authority),
                     ref.path.resolve2('../%s' % last),
                     pycopy.copy(ref.query),
                     pycopy.copy(ref.fragment))


# Simple cache of wrappers around local filesystem objects.
cache = {}
max_cache = 5
def remove_from_cache(fstype, path):
    if fstype in cache:
        subcache = cache[fstype]
        newlist = []
        for saved_path, saved_mtime, obj in subcache:
            if path != saved_path:
                newlist.append((saved_path, saved_mtime, obj))
        cache[fstype] = newlist

def find_local_cached(fstype, path):
    if fstype in cache:
        subcache = cache[fstype]
        for i in range(len(subcache)):
            saved_path, saved_mtime, obj = subcache[i]
            #dprint("path=%s: checking %s: mtime=%s" % (path, saved_path, saved_mtime))
            if path == saved_path:
                try:
                    mtime = os.path.getmtime(path)
                    if mtime > saved_mtime:
                        #dprint("modification time changed: %s to %s for %s" % (saved_mtime, mtime, path))
                        remove_from_cache(fstype, path)
                    else:
                        #dprint("found match %s" % saved_path)
                        return obj
                except:
                    import traceback
                    #traceback.print_exc()
                    #print("Exception: %s" % str(e))
                    remove_from_cache(fstype, path)
                return None
    return None
BaseFS.find_local_cached = staticmethod(find_local_cached)

def store_local_cache(fstype, path, obj):
    if fstype not in cache:
        cache[fstype] = []
    subcache = cache[fstype]
    # new items inserted at the beginning of the list
    subcache[0:0] = [(path, os.path.getmtime(path), obj)]
    #dprint(subcache)
    # truncate the list if it's getting too big.
    if len(subcache) > max_cache:
        subcache = subcache[0:max_cache]
    
BaseFS.store_local_cache = staticmethod(store_local_cache)

# extension to vfs to return a numpy mmap reference
def open_numpy_mmap(ref):
    if not isinstance(ref, Reference):
        ref = get_reference(ref)
    fs = get_file_system(ref.scheme)
    if hasattr(fs, 'open_numpy_mmap'):
        return fs.open_numpy_mmap(ref)
    raise IOError('%s not supported for mmap access' % str(ref))

def open_write(ref):
    """Open a file for writing, and if it exists, truncate it"""
    if not isinstance(ref, Reference):
        ref = get_reference(ref)
    if exists(ref):
        if is_file(ref):
            fh = open(ref, WRITE)
        else:
            raise OSError(u"%s exists and is a directory; can't save as file" % ref)
    else:
        fh = make_file(ref)
    return fh

# extension to vfs to return dictionary containing metadata for the reference
def get_metadata(ref):
    if not isinstance(ref, Reference):
        ref = get_reference(ref)
    fs = get_file_system(ref.scheme)
    if hasattr(fs, 'get_metadata'):
        return fs.get_metadata(ref)
    return {
        'mimetype': fs.get_mimetype(ref),
        'description': '',
        'mtime': fs.get_mtime(ref),
        'size': fs.get_size(ref),
        }

# Register a callback that the vfs can use to prompt the user for a
# username/password combination.  The callback function should take four
# arguments and return a username, password pair if successful or (None, None)
# if canceled by the user.  E.g.:
#
# def sample_authentication_callback(url, scheme, realm, username):
#     return "username", "password"
auth_callback = None
def register_authentication_callback(callback):
    global auth_callback
    auth_callback = callback

def get_authentication_callback():
    global auth_callback
    return auth_callback

class AuthenticationCancelled(RuntimeError):
    pass

class NetworkError(RuntimeError):
    pass
