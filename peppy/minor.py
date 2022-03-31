# peppy Copyright (c) 2006-2010 Rob McMullen
# Licenced under the GPLv2; see http://peppy.flipturn.org for more info
"""Your one-stop shop for minor mode building blocks.

Minor modes provide enhancements to a major mode or a set of major
modes.  They can be very limited and only apply to some major modes,
or more general and be applicable to lots of major modes.  It just
depends on the implementation and what the goals are.

A minor mode is created by subclassing from L{MinorMode} and
implementing the L{createWindows} method if you are adding a window to
the major mode's AuiManager area, or implementing L{setup} if you
don't need an element.

Registering your minor mode means creating a yapsy plugin extending
the IPeppyPlugin interface that returns a list of minor modes through
the getMinorModes method.
"""

import os,re

import wx
import peppy.third_party.aui as aui

from peppy.yapsy.plugins import *
from peppy.actions import *
from peppy.debug import *
from peppy.lib.userparams import *

from peppy.context_menu import ContextMenuMixin

class MinorMode(ContextMenuMixin, ClassPrefs, debugmixin):
    """
    Mixin class for all minor modes.  A minor mode should generally be
    a subclass of wx.Window (windowless minor modes are coming in the
    future).  Minor modes may also have associated with them:

    * menu, toolbar items -- by associating a check for the existence
      of the minor mode in the actions's worksWithMajorMode classmethod

    * status buttons in the frame's statusbar (ala Mozilla) - not
      implemented yet, but it's coming.
    
    """
    # Keyword should be overriden in subclasses to give this minor mode
    # a unique name among all other minor modes
    keyword = "Abstract Minor Mode"
    
    default_classprefs = (
        # Set default size here.  Probably should override best_*
        # sizes in subclass.
        # FIXME: the AUI manager always seems to go with the minimum size
        # on the initial setup.  Don't know why this is yet...
        IntParam('best_width', 100, 'Desired width of minor mode in pixels'),
        IntParam('best_height', 100, 'Desired height of minor mode in pixels'),
        IntParam('min_width', 100, 'Minimum width of minor mode in pixels\nenforced by the AuiManager'),
        IntParam('min_height', 100, 'Minimum height of minor mode in pixels\nenforced by the AuiManager'),
        ChoiceParam('side', ['top', 'right', 'bottom', 'left'], 'right',
                    help='Positioning of the minor mode window relative to the main window'),
        BoolParam('springtab', False, 'Display in a springtab instead of its own sidebar window'),
        )

    @classmethod
    def getValidMinorModes(cls, mode):
        valid = []
        plugins = wx.GetApp().plugin_manager.getActivePluginObjects()
        for plugin in plugins:
            for minor in plugin.getMinorModes():
                if minor.worksWithMajorMode(mode):
                    valid.append(minor)
            
            # Also add minor modes from the new-style on-demand interface
            compatible = plugin.getCompatibleMinorModes(mode)
            if compatible is not None:
                valid.extend(compatible)
        cls.dprint(valid)
        return valid

    @classmethod
    def worksWithMajorMode(self, modecls):
        """Hook to restrict the minor mode to be displayed only with a specific
        major mode
        
        @param mode: the major mode class (Note: not the instance)
        
        @returns: True if the action is allowed to be associated with the major
        mode
        """
        raise NotImplementedError("Must override this each minor mode subclass to determine if it can work with specified major mode")
    
    @classmethod
    def showWithMajorModeInstance(cls, mode=None, **kwargs):
        """Check to see if the minor mode should be shown given the state of
        the particular instance of major mode.
        
        This is different from L{worksWithMajorMode} because it is possible
        that the minor mode could functionally work with a major mode but it
        may not make sense to display it with the current state of the major
        mode.  This method is so far only called from L{SpringTab}s to see if
        the springtab button should be displayed given the state of the mode.
        
        @param mode: the major mode instance (Note: not the class)
        
        @param kwargs: any additional keyword arguments.  Note that keyword
        arguments are so far only used in the springtab creation process.
        
        @returns: True if the minor mode should be visible given the current
        state of the major mode
        """
        return True
    
    def __init__(self, parent, mode=None, **kwargs):
        """Classes using this mixin should call this method, or at
        least save the major mode."""
        self.parent = parent
        self.mode = mode
        self.window = None
        
        wx.CallAfter(self.initPostCallback)
    
    def getFrame(self):
        return self.mode.frame
    
    def initPostCallback(self):
        """Callback method called to register any event handlers or
        publish/subscribe messages
        """
        self.createContextMenuEventBindings()
        self.createEventBindings()
        self.createListeners()
    
    def activateMinorMode(self):
        """Called by minor mode initialization to signify that the minor mode
        window is ready to be drawn.
        
        Should be overridden by the subclass if some special initialization
        needs to be performed.
        """
        pass
    
    def getOptionsForPopupActions(self):
        options = {'minor_mode': self}
        return options

    def createEventBindings(self):
        """Hook to create any event bindings needed by the minor mode.
        """
        pass
    
    def createListeners(self):
        """Hook to register any publish/subscribe messages needed by the minor
        mode.
        """
        pass
    
    def setup(self):
        """Hook for minor modes that don't need any user inteface
        elements.

        Rather than overriding __init__, if you don't need to create
        any windows, you can override this method to register whatever
        you need to for your minor mode.
        """
        pass

    def deletePreHook(self):
        """Hook to clean up any resources before anything else is
        deleted.

        This hook is called whether or not the minor mode has a window.
        """
        pass

    def getPaneInfo(self):
        """Return the AuiPaneInfo object for this mode.
        
        Note: can't keep a reference to this in the minor mode because the AUI
        manager may recreate the object at will.
        """
        paneinfo = self.mode.wrapper._mgr.GetPane(self)
        return paneinfo

    def createPaneInfo(self):
        """Create the AuiPaneInfo object for this minor mode.
        """
        paneinfo = self.getDefaultPaneInfo()
        self.paneInfoHook(paneinfo)
        return paneinfo

    def getDefaultPaneInfo(self, caption=None):
        """Convenience method to create an AuiPaneInfo object.

        AuiPaneInfo objects are used by the L{BufferFrame} to position
        the new subwindow within the managed area of the major mode.
        This hooks into the class settings (through the MinorMode's
        subclassing of ClassSettings) to allow the user to specify the
        initial size of the minor mode.

        @param caption: text string that will become the caption bar
        of the Aui-managed window.
        """
        if caption is None:
            caption = self.keyword
        paneinfo = aui.AuiPaneInfo().Name(self.keyword).Caption(caption)
        try:
            # Turn the string 'top', 'right', 'bottom' or 'left' into the
            # function that will place the pane on that side of the main
            # window.  The function name is just the string with the first
            # letter capitalized
            side = self.classprefs.side.title()
            func = getattr(paneinfo, side)
            func()
        except Exception, e:
            # default to place on the right side
            paneinfo.Right()
        paneinfo.DestroyOnClose(False)
        paneinfo.BestSize(wx.Size(self.classprefs.best_width,
                                  self.classprefs.best_height))
        paneinfo.MinSize(wx.Size(self.classprefs.min_width,
                                 self.classprefs.min_height))
        return paneinfo

    def paneInfoHook(self, paneinfo):
        """Hook to modify the paneinfo object before the major mode
        does anything with it.
        """
        pass
    
    def ensureVisible(self):
        """Utility method to make the minor mode visible if it isn't already.
        
        """
        paneinfo = self.getPaneInfo()
        if not paneinfo.IsShown():
            paneinfo.Show(True)
            self.mode.wrapper._mgr.Update()


class MinorModeEntry(object):
    """Simple wrapper to hold a class and an instance"""
    def __init__(self, minorcls):
        self.minorcls = minorcls
        self.win = None

class MinorModeList(debugmixin):
    """Container holding a list of minor modes attached to a parent major mode
    
    """
    def __init__(self, parent, mgr, mode=None, initial=[], perspectives={}):
        self.mode = mode
        self.map = {}
        self.order = []
        self.parent = parent
        self.mgr = mgr

        if mode:
            minors = MinorMode.getValidMinorModes(mode)
            assert self.dprint("major = %s, minors = %s" % (mode, minors))
            for minorcls in minors:
                if minorcls.classprefs.springtab:
                    self.mode.wrapper.spring.addTab(minorcls.keyword, minorcls, minorcls.showWithMajorModeInstance, mode=self.mode)
#                else:
                if True:
                    self.map[minorcls.keyword] = MinorModeEntry(minorcls)
                    self.order.append(minorcls.keyword)
                    # A minor mode will be shown either if it's been saved the
                    # last time the user edited this file, or if it exists in
                    # the minor mode startup list
                    if minorcls.keyword in perspectives:
                        self.create(minorcls.keyword, perspectives[minorcls.keyword])
                    elif minorcls.__name__ in initial or minorcls.keyword in initial:
                        self.create(minorcls.keyword)
            if self.mode.wrapper.spring_aui:
                spring_paneinfo = self.mgr.GetPane(self.mode.wrapper.spring)
                if self.mode.wrapper.spring.hasTabs():
                    spring_paneinfo.Show()
                else:
                    spring_paneinfo.Hide()
            else:
                self.mode.wrapper.Layout()
            self.mgr.Update()

        self.order.sort()
    
    def getKeywordOrder(self):
        """Return the sort order of the minor modes."""
        return self.order
    
    def _getEntry(self, index):
        """Return the MinorModeEntry given its index"""
        keyword = self.order[index]
        entry = self.map[keyword]
        return entry
    
    def getWindow(self, keyword):
        """Get the minor mode window given its keyword"""
        if keyword in self.map:
            return self.map[keyword].win
    
    def isVisible(self, index):
        """Is the minor mode specified by the index shown?
        
        This is used in the menu bar code to present a check list of active
        modes.
        """
        entry = self._getEntry(index)
        if entry.win:
            assert self.dprint("index=%d shown=%s" % (index, entry.win.getPaneInfo().IsShown()))
            return entry.win.getPaneInfo().IsShown()
        assert self.dprint("index=%d shown=%s" % (index, False))
        return False
    
    def toggle(self, index):
        """Toggle the shown state, or create the minor mode if necessary.
        
        Minor modes are created on demand if not speficied as one of the modes
        to load at mode startup time.  If an entry doesn't exist and it is
        attempted to be toggled, it is created and shown.
        """
        entry = self._getEntry(index)
        if entry.win:
            paneinfo = entry.win.getPaneInfo()
            paneinfo.Show(not paneinfo.IsShown())
        else:
            self.create(self.order[index])
        self.mgr.Update()

    def hideAll(self):
        """Toggle the shown state, or create the minor mode if necessary.
        
        Minor modes are created on demand if not speficied as one of the modes
        to load at mode startup time.  If an entry doesn't exist and it is
        attempted to be toggled, it is created and shown.
        """
        for entry in self.map.itervalues():
            if entry.win:
                entry.win.getPaneInfo().Show(False)
        self.mgr.Update()

    def create(self, keyword, perspective=None):
        """Create the minor mode.
        
        Create the minor mode given its keyword.  It is shown automatically.
        """
        entry = self.map[keyword]
        entry.win = entry.minorcls(self.parent, mode=self.mode)
        entry.win.activateMinorMode()
        paneinfo = entry.win.createPaneInfo()
        if perspective:
            self.mgr.LoadPaneInfo(perspective, paneinfo)
        paneinfo.Show(True)
        try:
            self.mgr.AddPane(entry.win, paneinfo)
        except Exception, e:
            assert self.dprint("Failed adding minor mode %s: error: %s" % (keyword, str(e)))
        assert self.dprint("Created minor mode %s: %s" % (keyword, entry))
        return entry
    
    def getActive(self, ignore_hidden=False):
        """Get a list of all created minor modes.
        
        @param ignore_hidden: if True, only return the minor mode if it's
        currently visible
        """
        for entry in self.map.itervalues():
            if entry.win:
                if ignore_hidden and not entry.win.getPaneInfo().IsShown():
                    continue
                yield entry.win

    def deleteAll(self):
        """Delete all minor modes, removing the windows if they exist."""
        for entry in self.map.itervalues():
            if entry.win:
                minor = entry.win
                minor.deletePreHook()
                if self.mgr.GetPane(minor):
                    self.mgr.DetachPane(minor)
                    minor.Destroy()
                entry.win = None
