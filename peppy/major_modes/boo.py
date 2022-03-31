# peppy Copyright (c) 2006-2009 Rob McMullen
# Licenced under the GPLv2; see http://peppy.flipturn.org for more info
"""Boo programming language editing support.

Major mode for editing Boo files.

Supporting actions and minor modes should go here only if they are uniquely
applicable to this major mode and can't be used in other major modes.  If
actions can be used with multiple major modes, they should be put in a
separate plugin in the peppy/plugins directory.
"""

import os

import wx
import wx.stc

from peppy.lib.foldexplorer import *
from peppy.lib.autoindent import *
from peppy.yapsy.plugins import *
from peppy.major import *
from peppy.editra.style_specs import unique_keywords
from peppy.fundamental import FundamentalMode

class BooMode(FundamentalMode):
    """Stub major mode for editing Boo files.

    This major mode has been automatically generated and is a boilerplate/
    placeholder major mode.  Enhancements to this mode are appreciated!
    """
    keyword = 'Boo'
    editra_synonym = 'Boo'
    stc_lexer_id = wx.stc.STC_LEX_PYTHON
    start_line_comment = u'#'
    end_line_comment = ''
    
    icon = 'icons/page_white.png'
    
    default_classprefs = (
        StrParam('extensions', 'boo', fullwidth=True),
        StrParam('keyword_set_0', unique_keywords[15], hidden=False, fullwidth=True),
       )


class BooModePlugin(IPeppyPlugin):
    """Plugin to register modes and user interface for Boo
    """
   
    def getMajorModes(self):
        yield BooMode
