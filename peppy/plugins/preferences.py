# peppy Copyright (c) 2006-2010 Rob McMullen
# Licenced under the GPLv2; see http://peppy.flipturn.org for more info
"""Preferences dialog.

This plugin implements the preferences dialog that is used to modify
the default settings of objects that inherit from the ClassPrefs
class.
"""
import os, sys

from wx.lib.pubsub import Publisher
import wx.grid

from peppy.yapsy.plugins import *
from peppy.actions import *
from peppy.configprefs import *
from peppy.lib.userparams import *
from peppy.lib.iconstorage import *
from peppy.lib.pluginmanager import *

class Preferences(SelectAction):
    """Preferences, settings, and configurations..."""
    name = "&Preferences..."
    default_menu = ("Edit", 1000.1)
    default_toolbar = False
    icon = "icons/wrench.png"
    stock_id = wx.ID_PREFERENCES
    key_bindings = {'mac': 'C-,', }
    osx_minimal_menu = True

    @classmethod
    def showDialog(self, msg=None):
        frame = wx.GetApp().GetTopWindow()
        mode = frame.getActiveMajorMode()
        dlg = PeppyPrefDialog(frame, mode)
        retval = dlg.ShowModal()
        if retval == wx.ID_OK:
            locals = dlg.applyPreferences()
            if locals:
                dlg2 = wx.MessageDialog(dlg, "Some default values have changed that affect\nlocal view settings.  Do you want to update the\nlocal settings for all affected views?\n\nIf not, the settings will not change current views\nbut will remain the defaults to be applied the\nnext time a view is created.", "Apply Local Settings?", wx.YES_NO | wx.ICON_QUESTION )
                retval=dlg2.ShowModal()
                dlg2.Destroy()
                if retval != wx.ID_YES:
                    locals = {}
            Publisher().sendMessage('peppy.preferences.changed', locals)
        dlg.Destroy()

    def action(self, index=-1, multiplier=1):
        self.showDialog()

# FIXME: this is probably not the standard way I want to set up
# messages, but it works for now.  Will refactor at some point.
Publisher().subscribe(Preferences.showDialog, 'peppy.preferences.show')

class PeppyPrefClassList(PrefClassList):
    """Add icon support to PrefClassTree"""

    def setIconStorage(self):
        getIconStorage().assignList(self)

    def getIcon(self, cls):
        icon = None
        if hasattr(cls, 'icon') and cls.icon is not None:
            icon = getIconStorage(cls.icon)
        else:
            icon = getIconStorage("icons/blank.png")
        return icon
    
    def appendItem(self, name):
        cls = self.class_map[name]
        icon = self.getIcon(cls)
        if icon is None:
            icon = -1
        self.InsertImageStringItem(sys.maxint, name, icon)
            
    def setItem(self, index, name):
        cls = self.class_map[name]
        icon = self.getIcon(cls)
        if icon is None:
            icon = -1
        self.SetStringItem(sys.maxint, name, icon)

class PeppyPrefPage(PrefPage):
    def createList(self, classes):
        list = PeppyPrefClassList(self, classes)
        return list

class PeppyPluginPage(PluginPage):
    def applyPreferences(self):
        PluginPage.applyPreferences(self)
        # Send the plugin changed message when the plugin settings are
        # applied
        Publisher().sendMessage('peppy.plugins.changed')

class PeppyPrefDialog(PrefDialog):
    dialog_title = "Peppy Global Preferences"
    static_title = ""

    def createPage(self, tab, classes):
        if tab == "Plugins":
            # Show a plugin control page which augments the standard
            # preference page
            page = PeppyPluginPage(self.notebook, wx.GetApp().plugin_manager)
        else:
            page = PeppyPrefPage(self.notebook, classes)
        return page


class PreferencesPlugin(IPeppyPlugin):
    def getActions(self):
        return [Preferences]
    
