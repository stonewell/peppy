# -*- coding: UTF-8 -*-
# peppy Copyright (c) 2006-2010 Rob McMullen
# Licenced under the GPLv2; see http://peppy.flipturn.org for more info
"""Definition and storage of the 'about:' protocol.

This provides the about: protocol handling (a read-only protocol) for
built-in storage of data.  It also provides some global user interface
elements for the help menu and other testing menu items.
"""

import os,os.path,sys,re,time,commands,glob,random
import urllib2

import wx

import peppy.vfs as vfs
from peppy.vfs.itools.vfs.permissions import Permissions

from peppy.debug import *
from peppy.actions import *
from peppy.major import *

# can't use cStringIO because we need to add attributes to it
from StringIO import StringIO

# if you import from peppy instead of main here, the ExtensionPoints
# in peppy will get loaded twice.
from peppy import __version__, __codename__, __revision__, __description__, __author__, __author_email__, __url__
substitutes = {
    'prog': 'peppy',
    'yearrange': '2006-2010',
    'version': __version__,
    'codename': __codename__,
    'revision': __revision__,
    'description': __description__,
    'author': __author__,
    'author_email': __author_email__,
    'url': __url__,
    'license': "Application licensed under the GPLv3; most code also dual licensed under GPLv2",
    'warning': """<P>I've been dogfooding with peppy for over a year and I'm
very happy with its stability.  It's certainly good enough to finally get rid
of the alpha tag and move into beta.  It's not production yet as there are
still rough edges and a general lack of documentation on the internals, but it
is suitable for day-to-day editing tasks.

<P>However, it's always a good idea to turn on the autosave and backup options
in the preferences and save your work often.  Should you run across a problem,
don't hesitate to file a bug report using the <b>Help</b> ->
<b>Report a Bug</b> menu item (or at http://trac.flipturn.org/newticket).
    """,
    'thanks': "",
    'gpl_code': "",
    'license_text': """This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License along
with this program; if not, write to the Free Software Foundation, Inc.,
51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
""",
    'authors': "",
    'contributors': """<p>Contributors to peppy:</p>
<ul>
%(authors)s
</ul>
<p>Some code has been borrowed from the following open source projects:</p>
<ul>
%(gpl_code)s
</ul>
<p>Additional thanks to:</p>
<ul>
%(thanks)s
</ul>""",
    'plugins': "<h1>plugins go here</h1>",
    }
substitutes['copyright'] = 'Copyright (c) %(yearrange)s %(author)s (%(author_email)s)' % substitutes

aboutfiles = {}
aboutmimetype = {}

def guessMime(text):
    sample = text[0:1024].strip()
    if sample and sample[0] == "<":
        return "text/html"
    return "text/plain"

def SetAbout(path, text, mimetype=None, encoding=None):
    #eprint("Setting %s: %d bytes" % (path, len(text)))
    if encoding:
        text = text.encode(encoding)
    aboutfiles[path] = text
    if not mimetype:
        mimetype = guessMime(text)
    aboutmimetype[path] = mimetype

mutators = {}
def addMutator(path, callback):
    """Adds a function that will be used to mutate the about: text."""
    mutators[path] = callback

def mutate(path, text):
    if path in mutators:
        return mutators[path](text)
    return text

def findAbout(path):
    if path in aboutfiles:
        return mutate(path, aboutfiles[path])
    plugins = wx.GetApp().plugin_manager.getActivePluginObjects()
    for plugin in plugins:
        #dprint("checking plugin %s" % plugin)
        files = plugin.aboutFiles()
        if path in files:
            # the file details could include a mimetype
            details = files[path]
            if isinstance(details, str):
                return mutate(path, details)
            else:
                return mutate(path, details[0])
    return None

def findMime(path):
    if path in aboutmimetype:
        return aboutmimetype[path]
    plugins = wx.GetApp().plugin_manager.getActivePluginObjects()
    for plugin in plugins:
        #dprint("checking plugin %s" % plugin)
        files = plugin.aboutFiles()
        if path in files:
            # the file details could include a mimetype
            details = files[path]
            if isinstance(details, str):
                return guessMime(details)
            else:
                return details[1]
    return None

def getAboutUTF8(path):
    text = findAbout(path)
    if text is not None:
        recurse_count = 100
        mimetype = findMime(path)
        if mimetype.startswith("text") and text.find("%(") >= 0:
            updateDynamicSubstitutes()
            while text.find("%(") >= 0 and recurse_count>0:
                text = text % substitutes
                recurse_count -= 1
        text = text.encode('utf-8')
        # FIXME: display error when recurse count is triggered???
    return text

def findAboutNames():
    names = aboutfiles.keys()
    plugins = wx.GetApp().plugin_manager.getActivePluginObjects()
    for plugin in plugins:
        #dprint("checking plugin %s" % plugin)
        files = plugin.aboutFiles()
        names.extend(files)
    return names

def updateDynamicSubstitutes():
    plugins = wx.GetApp().plugin_manager.getAllPlugins()
    entries = []
    for plugin in plugins:
        #dprint("checking plugin %s" % plugin)
        if plugin.plugin_object.is_activated:
            active = "Active"
        else:
            active = "Disabled"
        entries.append((plugin.name, "<tr><td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>\n" % (plugin.name, plugin.author, plugin.version, active)))
    entries.sort()
    plugin_summary = "<h3>Plugins:</h3>\n<table><tr><th>Name</th><th>Author</th><th>Version</th><th>Active</th></tr>%s</table>" % "\n".join([e[1] for e in entries])
    substitutes['plugins'] = plugin_summary


class AboutFS(vfs.BaseFS):
    mtime = time.time()
    
    @staticmethod
    def exists(reference):
        path = str(reference.path)
        text = findAbout(path)
        return text is not None

    @staticmethod
    def is_file(reference):
        return AboutFS.exists(reference)

    @staticmethod
    def is_folder(reference):
        return False

    @staticmethod
    def can_read(reference):
        return AboutFS.exists(reference)

    @staticmethod
    def can_write(reference):
        return False

    @classmethod
    def get_permissions(cls, reference):
        perm = Permissions(0)
        perm.set_mode('u', 'r', True)
        perm.set_mode('u', 'w', True)
        perm.set_mode('g', 'r', True)
        perm.set_mode('o', 'r', True)
        return perm

    @classmethod
    def set_permissions(cls, reference, permissions):
        pass

    @staticmethod
    def get_size(reference):
        path = str(reference.path)
        text = getAboutUTF8(path)
        if text is not None:
            return len(text)
        raise OSError("[Errno 2] No such file or directory: '%s'" % reference)

    @staticmethod
    def get_mtime(reference):
        path = str(reference.path)
        text = findAbout(path)
        if text is not None:
            return AboutFS.mtime
        raise OSError("[Errno 2] No such file or directory: '%s'" % reference)

    @staticmethod
    def get_mimetype(reference):
        path = str(reference.path)
        mimetype = findMime(path)
        if mimetype is not None:
            return mimetype
        raise OSError("[Errno 2] No such file or directory: '%s'" % reference)

    @staticmethod
    def open(reference, mode=None):
        path = str(reference.path)
        #dprint(str(reference))
        text = getAboutUTF8(path)
        if text is None:
            raise IOError("[Errno 2] No such file or directory: '%s'" % reference)
        fh=StringIO()
        fh.write(text)
        fh.seek(0)

        return fh
    
    @staticmethod
    def get_names(reference):
        path = str(reference.path)
        #dprint(path)
        if path != ".":
            raise OSError("[Errno 20] Not a directory '%s'" % path)
        return findAboutNames()


import urlparse
urlparse.uses_fragment.append('about')
urlparse.uses_query.append('about')
vfs.register_file_system('about', AboutFS)


def getNewUntitled():
    """Get a unique filename for a new blank document"""
    root = "untitled"
    name = root
    count = 1
    while name in aboutfiles:
        count += 1
        name = "%s-%d" % (root, count)
    SetAbout(name,'')
    return "about:%s" % name

SetAbout('blank','')
SetAbout('scratch','-*- Fundamental -*-')
SetAbout('thanks', """\
%(contributors)s
""")
SetAbout('peppy',"""\
<h2>%(prog)s %(version)s %(revision)s \"%(codename)s\"</h2>

<h3>%(description)s</h3>

<p>Copyright (c) %(yearrange)s %(author)s (%(author_email)s)</p>

<p>%(license)s</p>

<p>%(warning)s</p>

<p>%(contributors)s</p>

<p>%(plugins)s</p>
""")
SetAbout('0x00-0xff', "".join([chr(i) for i in range(256)]), "application/octet-stream")
SetAbout('red.png',
"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x10\x00\x00\x00\x10\x08\x02\
\x00\x00\x00\x90\x91h6\x00\x00\x00\x03sBIT\x08\x08\x08\xdb\xe1O\xe0\x00\x00\
\x00\x93IDAT(\x91\xb5\x921\x0e\xc3 \x0cE\x7f:0r\x90\x0c,Y\x18\x98\xb8B\x8e\
\xc5\n'\xe4\x160\xfc\x0e\x14K\xb4T(\x91\xf2\xe5\xf1=[\xb2\xbd\x91\xc4\x95\
\xbc.\xd1?B\xadH\t\xdeC)(\x05\xef\x91\x12j\x1d\x18Jr\xe6q\x10\xf8.c\x98\xb3P\
](\x85\xc6LhqJ\x19\x85\x10\xfe\xd2\xadB\x18\x05k\x17\x82\xb5\xa3\xa0\xf5B\
\xd0\xba\x81\xb7\xd7\xba\xef\x0b\xb0\x03]8\xcf\x85 \xc0\xdd\xb5\xb6\xc3M\x9d\
\xf9\xe1dN\x8ct\xee\x83:\xc7\x18\xa5w\xcb\xf6\xf8\xb7\xbe\x01K&\xfa\xcbB\xfe\
\xcc\x08\x00\x00\x00\x00IEND\xaeB`\x82", "image/png")


def unicodify(text):
    """Change to unicode if not already a unicode string"""
    if not isinstance(text, unicode):
        return text.decode('utf-8')
    return text


needs_sort = True
authors={}
credits={}
copyrights = {}

def randomizeCredits(text):
    global needs_sort
    if needs_sort:
        #dprint("Randomizing credits!")
        for name, map in [('authors', authors), ('thanks', credits)]:
            items = ["<li>%s - %s</li>" % (a,c) for a,c in map.iteritems()]
            random.shuffle(items)
            substitutes[name]="\n".join(items)
        items = ["<li>%(reason)s <a href=\"%(website)s\">%(project)s</a> Copyright (c) %(date)s %(author)s</i>" % c for c in copyrights.values()]
        random.shuffle(items)
        substitutes['gpl_code']="\n".join(items)
        
        needs_sort = False
    
    # Don't actually do anything with the text, we just use this as the hook to
    # sort the stuff.
    return text

addMutator('peppy', randomizeCredits)
addMutator('thanks', randomizeCredits)

def AddAuthor(author, contribution):
    global needs_sort
    needs_sort = True
    authors[unicodify(author)] = unicodify(contribution)
AddAuthor("Christopher Armstrong", "for patches to improve emacs compatibility")
AddAuthor("Jesse Aldridge", "for testing and bug reports on Ubuntu Linux")
AddAuthor("Chris Barker", "for patches, testing and bug reports on Mac OSX")

def AddCredit(author, contribution):
    global needs_sort
    needs_sort = True
    credits[unicodify(author)] = unicodify(contribution)
        
AddCredit("Mark James", "for the <a href=\"http://www.famfamfam.com/lab/icons/silk/\">free silk icon set</a>")
AddCredit("Julian Back", "for the framework for the C edit mode")
AddCredit("Thibauld Nion", "for the Yapsy plugin framework.  Note: Yapsy is BSD licensed and can be downloaded under that license from the <a href=\"http://yapsy.sourceforge.net/\">yapsy homepage</a>")
AddCredit("Peter Damoc", "for the feature suggestions")
AddCredit("Stani Michiels", "for the scintilla fold explorer he shared with the pyxides mailing list")
AddCredit("David Eppstein", "for his public domain python implementation of the TeX word wrapping algorithm")
AddCredit("Robin Dunn", "for the omnipresence on the wxPython mailing list and the feature list on his blog")
AddCredit("Dinu Gherman", "for the <a href=\"http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/68205\">Null object implementation</a>")
AddCredit("Frank Niessink", "for the i18n utilities from <a href=\"http://www.taskcoach.org\">Task Coach</a>")
AddCredit("Christopher Thoday", "for some code from <a href=\"http://luke-sdk.berlios.de\">Luke SDK</a> that became the spell checker")
AddCredit("Anders Lund", "for the regex based autoindenter transcribed from Kate, the KDE text editor")

def AddCopyright(project, website, author, date, reason=""):
    global needs_sort
    needs_sort = True
    key = project + reason
    copyrights[key] = ({'website': unicodify(website),
                       'project': unicodify(project),
                       'author': unicodify(author),
                       'date': unicodify(date),
                       'reason': unicodify(reason),
                       })

# Can't include copyrights for itools stuff in the vfs because about has a
# dependency on vfs, leading to a circular dependency if imported from vfs
AddCopyright("itools", "http://www.ikaaro.org/itools", u"Juan David Ibáñez Palomar et al.", "2002-2007", "Virtual filesystem implementation from")
AddCopyright("Chandler Project", "http://chandlerproject.org/Projects/Davclient", "Open Source Applications Foundation", "2006-2007", "WebDAV implementation from")
