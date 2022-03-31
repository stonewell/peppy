# peppy Copyright (c) 2006-2010 Rob McMullen
# Licenced under the GPLv2; see http://peppy.flipturn.org for more info
"""Graphviz DOT Language editing support.

L{Graphviz<http://graphviz.org/>} is a high quality open source
program to automatically layout directed and undirected graphs from a
text description of the node and edge relationships.  The description
language is called L{DOT<http://graphviz.org/doc/info/lang.html>} and
in most cases is generated by a program.  It is rare to write one by
hand, but when you have to, this mode is helpful.
"""

import os,struct
import keyword
from cStringIO import StringIO

import wx
import wx.stc

import peppy.vfs as vfs

from peppy.yapsy.plugins import *
from peppy.lib.bitmapscroller import *
from peppy.lib.processmanager import ProcessManager, JobOutputMixin
from peppy.actions import *
from peppy.major import *
from peppy.editra.style_specs import unique_keywords
from peppy.fundamental import FundamentalMode

_sample_file = """// Sample graphviz source file
digraph G {
   Hello->World;
   peppy->"is here";
}
"""

class SampleDot(SelectAction):
    """Open a sample Graphviz file"""
    name = "&Open Sample Graphviz dot file"
    default_menu = "&Help/Samples"

    def action(self, index=-1, multiplier=1):
        self.frame.open("about:sample.dot")


class GraphvizLayout(RadioAction):
    """Dot layout engine""" 
    name = "Layout Engine"
    default_menu = ("Graphviz", 500)

    items = ['dot', 'neato', 'twopi', 'circo', 'fdp', 'sfdp']

    def getIndex(self):
        filt = self.mode.classprefs.layout
        try:
            return self.items.index(filt)
        except:
            return 0

    def getItems(self):
        return self.__class__.items

    def action(self, index=-1, multiplier=1):
        self.mode.classprefs.layout = self.items[index]


class GraphvizOutputFormat(RadioAction):
    """File format to save output image""" 
    name = "Image Format"
    default_menu = ("Graphviz", 500)

    items = ['eps', 'gif', 'jpg' ,'pdf', 'png', 'ps', 'svg']

    def getIndex(self):
        format = self.mode.classprefs.layout
        try:
            return self.items.index(format)
        except:
            return 0

    def getItems(self):
        return self.__class__.items

    def action(self, index=-1, multiplier=1):
        self.mode.classprefs.graphic_format = self.items[index]


class GraphvizMode(FundamentalMode):
    """Major mode for editing Graphviz .dot files.

    Uses the C++ mode of the STC to highlight the files, since
    graphviz .dot files are similar in structure to C++ files.
    """
    keyword = 'Graphviz'
    editra_synonym = 'DOT'
    stc_lexer_id = wx.stc.STC_LEX_CPP
    start_line_comment = u'//'
    end_line_comment = ''
    icon='icons/graphviz.png'


    default_classprefs = (
        StrParam('extensions', 'dot', fullwidth=True),
        StrParam('keyword_set_0', unique_keywords[126], hidden=False, fullwidth=True),
        StrParam('keyword_set_1', unique_keywords[127], hidden=False, fullwidth=True),
        StrParam('path', '/usr/local/bin', 'Path to the graphviz binary programs\nlike dot, neato, and etc.'),

        StrParam('graphic_format', 'png'),
        StrParam('layout', 'dot'),
        SupersededParam('output_log')
        )

    def getInterpreterArgs(self):
        self.dot_output = vfs.reference_with_new_extension(self.buffer.url, self.classprefs.graphic_format)
        # FIXME: if the stdoutCallback worked, the -o flag would not be
        # necessary.
        args = "%s -v -T%s -K%s -o%s" % (self.classprefs.interpreter_args, self.classprefs.graphic_format, self.classprefs.layout, str(self.dot_output.path))
        return args

    def getJobOutput(self):
        return self
    
    def startupCallback(self, job):
        self.process = job
        self.preview = StringIO()

    def stdoutCallback(self, job, text):
        dprint("got stdout: %d bytes" % len(text))
        self.preview.write(text)

    def stderrCallback(self, job, text):
        dprint("got stderr: %d bytes" % len(text))
        dprint(text)

    def finishedCallback(self, job):
        """Callback from the JobOutputMixin when the job terminates."""
        assert self.dprint()
        del self.process
        # FIXME: this doesn't seem to work -- the output consists of only a few
        # return characters, not the binary bytes of the image.  If the same
        # command line is used (e.g.  /usr/bin/dot -v -Tpng -Kdot sample.dot >
        # sample.png) the file is created correctly.  There's something about
        # the interaction of the new threads-based processmanager that fails.
#        fh = vfs.open_write(self.dot_output)
#        fh.write(self.preview.getvalue())
#        fh.close()
        self.frame.findTabOrOpen(self.dot_output)


class GraphvizPlugin(IPeppyPlugin):
    """Graphviz plugin to register modes and user interface.
    """
    def aboutFiles(self):
        return {'sample.dot': _sample_file}
    
    def getMajorModes(self):
        yield GraphvizMode
    
    def getActions(self):
        yield SampleDot

    def getCompatibleActions(self, modecls):
        if issubclass(modecls, GraphvizMode):
            return [
                GraphvizLayout, GraphvizOutputFormat,
                
                ]
