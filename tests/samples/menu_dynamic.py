"""
Extra Help menu appears on WXMAC
"""
import wx

class Frame(wx.Frame):
    def __init__(self, *args, **kwargs):
        super(self.__class__, self).__init__(*args, **kwargs)
        #self.panel = wx.Panel(self)


        menu = wx.Menu()
        menu.AppendItem(wx.MenuItem(menu, 10002, "Recreate Menu With 2 Items"))
        menu.AppendItem(wx.MenuItem(menu, 10003, "Recreate Menu With 3 Items"))
        menu.AppendItem(wx.MenuItem(menu, 10004, "Recreate Menu With 4 Items"))
        menu.AppendItem(wx.MenuItem(menu, 10005, "Recreate Menu With 5 Items"))
        menu.AppendItem(wx.MenuItem(menu, 10006, "Recreate Menu With 6 Items"))
        menu.AppendItem(wx.MenuItem(menu, wx.ID_EXIT, "Exit"))
        menubar = wx.MenuBar()
        menubar.Append(menu, 'Menu')
        
        help = wx.Menu()
        help.AppendItem(wx.MenuItem(menu, wx.ID_ABOUT, "About..."))
        help.AppendSeparator()
        help.AppendItem(wx.MenuItem(menu, -1, "History:"))
        menubar.Append(help, "&Help")

        # From Editra source, found out that this must be set after all the
        # menus are created but before setting the menu bar
        wx.GetApp().SetMacHelpMenuTitleName("&Help")
        self.SetMenuBar(menubar)

        self.Bind(wx.EVT_MENU, self.OnMenuSelected)
    
    def createDynamic(self, num):
        menubar = self.GetMenuBar()
        help_pos = menubar.GetMenuCount() - 1
        help_menu = menubar.GetMenu(help_pos)
        print("help menu position: %d" % help_pos)
        
        pos = 1
        for title in ["Test%d" % (i + 1) for i in range(0, num)]:
            menu = wx.Menu()
            if pos < help_pos:
                print("root menu title %d: %s, replacing %s" % (pos, title, menubar.GetMenuLabel(pos)))
                old = menubar.Replace(pos, menu, title)
                old.Destroy()
            else:
                print("root menu title %d: %s, inserting before help" % (pos, title))
                menubar.Insert(pos, menu, title)
            pos += 1
        extra = help_pos - pos
        while (extra > 0):
            print("removing %d: %s" % (pos, menubar.GetMenuLabel(pos)))
            old = menubar.Remove(pos)
            old.Destroy()
            extra -= 1
        
        help_menu.AppendItem(wx.MenuItem(menu, -1, "Changed to %d items" % num))
        wx.GetApp().SetMacHelpMenuTitleName("&Help")

    def OnMenuSelected(self, evt):
        print evt
        id = evt.GetId()
        if id == wx.ID_EXIT:
            wx.GetApp().ExitMainLoop()
        number = evt.GetId() - 10000
        if number > 0 and number < 10:
            print "Recreate with %d items" % number
            self.createDynamic(number)

print 1
app = wx.App(False)
print 2
frame = Frame(None)
print 3
frame.Show()
print 4
app.MainLoop()
print 5