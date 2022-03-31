##from wx import wxApp
import wx
import wx.richtext as rt
#import images
import wx.aui
from configobj import ConfigObj, ConfigObjError
from validate import Validator
import os,sys

class MyFrame(wx.Frame):
   def __init__(self, parent, ID, title):
       wx.Frame.__init__(self, parent, ID, title,wx.DefaultPosition, wx.Size(800, 600),
                         style=wx.DEFAULT_FRAME_STYLE | wx.NO_FULL_REPAINT_ON_RESIZE)

       pnl = wx.Panel(self, style=wx.WANTS_CHARS)
       self.pnl = pnl

       self.mgr = wx.aui.AuiManager()
       self.mgr.SetManagedWindow(pnl)
       self.Centre(wx.BOTH)

       self.MakeMenuBar()
       self.MakeToolBar()
       self.CreateStatusBar()
       self.SetStatusText("Welcome!")

       # Create a TreeCtrl
       leftPanel = wx.Panel(pnl, style=wx.TAB_TRAVERSAL|wx.CLIP_CHILDREN)
       self.tree = wx.TreeCtrl(leftPanel, -1, wx.DefaultPosition, wx.Size(200, 495), wx.TR_DEFAULT_STYLE | wx.NO_BORDER)
       self.root = self.tree.AddRoot("File")
       self.tree.SetPyData(self.root, None)
       self.tree.Bind(wx.EVT_TREE_SEL_CHANGED, self.OnActivatedTreeItem)

       leftBox = wx.BoxSizer(wx.VERTICAL)
       leftBox.Add(self.tree, 1, wx.EXPAND)
       leftPanel.SetSizer(leftBox)

       self.rtc = rt.RichTextCtrl(pnl, style=wx.VSCROLL|wx.HSCROLL|wx.NO_BORDER)
       self.errorlog = wx.TextCtrl(pnl, -1,style = wx.TE_MULTILINE|wx.TE_READONLY|wx.HSCROLL)
       self.errorlog.Bind(wx.EVT_LEFT_DOWN, self.OnLeftDown)
       #wx.CallAfter(self.rtc.SetFocus)
       self.rtc.Freeze()
       self.rtc.BeginSuppressUndo()
       self.rtc.BeginParagraphSpacing(0, 20)

       self.rtc.BeginAlignment(rt.TEXT_ALIGNMENT_CENTRE)
       self.rtc.BeginBold()

       self.rtc.BeginFontSize(14)
       self.rtc.WriteText("Welcome!")
       self.rtc.Newline()
       self.rtc.WriteText("Please select a Config file to edit ...")
       self.rtc.Newline()
       self.rtc.EndFontSize()

       self.rtc.EndBold()
       self.rtc.EndAlignment()
       self.rtc.EndParagraphSpacing()
       self.rtc.EndSuppressUndo()
       self.rtc.Thaw()

       self.mgr.AddPane(self.rtc, wx.aui.AuiPaneInfo().CenterPane().Name("Notebook"))
       self.mgr.AddPane(leftPanel,
                        wx.aui.AuiPaneInfo().
                        Left().Layer(2).BestSize((240, -1)).
                        MinSize((160, -1)).
                        Floatable(False).FloatingSize((240, 700)).
                        Caption("Config sections and keywords").
                        CloseButton(False).
                        Name("Tree"))
       self.mgr.AddPane(self.errorlog,
                        wx.aui.AuiPaneInfo().
                        Bottom().BestSize((-1, 150)).
                        MinSize((-1, 60)).
                        Floatable(False).FloatingSize((500, 160)).
                        Caption("Error Log").
                        CloseButton(False).
                        Name("Log"))
       self.mgr.Update()

   def MakeMenuBar(self):
       def doBind(item, handler, updateUI=None):
           self.Bind(wx.EVT_MENU, handler, item)
           if updateUI is not None:
               self.Bind(wx.EVT_UPDATE_UI, updateUI, item)

       fileMenu = wx.Menu()
       doBind( fileMenu.Append(-1, "&Open\tCtrl+O", "Open a file"),
               self.OnFileOpen )
       doBind( fileMenu.Append(-1, "&Save\tCtrl+S", "Save a file"),
               self.OnFileSave )
       doBind( fileMenu.Append(-1, "&Save As...\tF12", "Save to a new file"),
               self.OnFileSaveAs )
       fileMenu.AppendSeparator()
       doBind( fileMenu.Append(-1, "E&xit\tCtrl+Q", "Quit this program"),
               self.OnFileExit )

       editMenu = wx.Menu()
       doBind( editMenu.Append(wx.ID_UNDO, "&Undo\tCtrl+Z"),
               self.ForwardEvent, self.ForwardEvent)
       doBind( editMenu.Append(wx.ID_REDO, "&Redo\tCtrl+Y"),
               self.ForwardEvent, self.ForwardEvent )
       editMenu.AppendSeparator()
       doBind( editMenu.Append(wx.ID_CUT, "Cu&t\tCtrl+X"),
               self.ForwardEvent, self.ForwardEvent )
       doBind( editMenu.Append(wx.ID_COPY, "&Copy\tCtrl+C"),
               self.ForwardEvent, self.ForwardEvent)
       doBind( editMenu.Append(wx.ID_PASTE, "&Paste\tCtrl+V"),
               self.ForwardEvent, self.ForwardEvent)
       doBind( editMenu.Append(wx.ID_CLEAR, "&Delete\tDel"),
               self.ForwardEvent, self.ForwardEvent)
       editMenu.AppendSeparator()
       doBind( editMenu.Append(wx.ID_SELECTALL, "Select A&ll\tCtrl+A"),
               self.ForwardEvent, self.ForwardEvent )

       mb = wx.MenuBar()
       mb.Append(fileMenu, "&File")
       mb.Append(editMenu, "&Edit")
       self.SetMenuBar(mb)

   def MakeToolBar(self):
       def doBind(item, handler, updateUI=None):
           self.Bind(wx.EVT_TOOL, handler, item)
           if updateUI is not None:
               self.Bind(wx.EVT_UPDATE_UI, updateUI, item)

       tbar = self.CreateToolBar()
       image = wx.ArtProvider_GetBitmap(wx.ART_QUESTION, wx.ART_OTHER, wx.Size(16,16))
       doBind( tbar.AddTool(-1, image,
                           shortHelpString="Open"), self.OnFileOpen)
       doBind( tbar.AddTool(-1, image,
                           shortHelpString="Save"), self.OnFileSave)
       tbar.AddSeparator()
       doBind( tbar.AddTool(wx.ID_CUT, image,
                           shortHelpString="Cut"), self.ForwardEvent, self.ForwardEvent)
       doBind( tbar.AddTool(wx.ID_COPY, image,
                           shortHelpString="Copy"), self.ForwardEvent, self.ForwardEvent)
       doBind( tbar.AddTool(wx.ID_PASTE, image,
                           shortHelpString="Paste"), self.ForwardEvent, self.ForwardEvent)
       tbar.AddSeparator()
       doBind( tbar.AddTool(wx.ID_UNDO, image,
                           shortHelpString="Undo"), self.ForwardEvent, self.ForwardEvent)
       doBind( tbar.AddTool(wx.ID_REDO, image,
                           shortHelpString="Redo"), self.ForwardEvent, self.ForwardEvent)
       tbar.Realize()

   def SetTitle(self, filename):
       """Adds the filename to the title"""
       wx.Frame.SetTitle(self, filename)

   def OnLeftDown(self, evt):
       evt.Skip()
       # hit --> (result, col, row)
       hit = self.errorlog.HitTest(evt.GetPosition())
       wx.CallAfter(self.LeftDownAction, hit)

   def LeftDownAction(self, hit):
       #print evt.GetPosition()
       self.selection = hit
       line_number = hit[2]
       err_text = self.errorlog.GetLineText(line_number)
       if err_text.strip() != "" :
           err_text = err_text[err_text.rfind(" ")+1:len(err_text)]
           err_text = err_text.replace('"',"")
           err_text = err_text.replace('.',"")
           line_number = int(err_text)
           start = self.rtc.XYToPosition(0,line_number - 1)
           self.rtc.ShowPosition(start)

   def OnFileOpen(self, evt):
       # This gives us a string suitable for the file dialog based on
       # the file handlers that are loaded
       wildcard, types = rt.RichTextBuffer.GetExtWildcard(save=False)
       dlg = wx.FileDialog(self, "Choose a filename",
                           wildcard="*.ini",
                           style=wx.OPEN)
       if dlg.ShowModal() == wx.ID_OK:
           wildcard, types = rt.RichTextBuffer.GetExtWildcard(save=False)
           path = dlg.GetPath()
           if path:
               self.SetTitle(path)
               fileType = types[dlg.GetFilterIndex()]
               self.rtc.LoadFile(path, fileType)
               self.SetDefaultTextColour()
               self.ReadConfigFile(path)
       dlg.Destroy()

   def ConfigError (self, error):
       attr = rt.TextAttrEx()
       attr.SetFlags(rt.TEXT_ATTR_TEXT_COLOUR)

       self.SetDefaultTextColour()

       for e in error.errors :
           line_number = e.line_number

           attr.SetTextColour((255, 0, 0))
           start = self.rtc.XYToPosition(0,line_number-1)
           end = self.rtc.XYToPosition(len(self.rtc.GetLineText(line_number-1)),line_number-1)
           self.rtc.ShowPosition(start)
           self.rtc.SetSelection(start, end)
           r = self.rtc.GetSelectionRange()
           self.rtc.SetStyle(r, attr)

           self.rtc.SelectNone()
           self.errorlog.WriteText(e.message + "\n")

   def AppendItemToTree (self, parent, sections, line_number, rowCount):
       for el in sections :
           line_number = self.GetLineNumberConfig(el[0], line_number, rowCount)
           section = self.tree.AppendItem(parent, el[0])
           self.tree.SetPyData(section, line_number)
           if line_number>=self.rtc.GetNumberOfLines() :
               dlg = wx.MessageDialog(self, 'The section "' + el[0] + '" is missing.',
                                      'Warning',
                                      wx.OK | wx.ICON_INFORMATION
                                      #wx.YES_NO | wx.NO_DEFAULT | wx.CANCEL | wx.ICON_INFORMATION
                                      )
               dlg.ShowModal()
               dlg.Destroy()
           #print "item : " + el[0] + " Line Number : " + str(line_number) + " Start : " + str(line_number)
           for j in range(1,len(el)) :
               if str(type(el[j]))!="<type 'str'>" and str(type(el[j]))!="<type 'list'>" and str(type(el[j]))!="<type 'int'>":
                   subsections = [(k, v) for (k, v) in el[j].iteritems()]
                   if len(subsections) >0 :
                       line_number = self.AppendItemToTree(section, subsections, line_number+1, rowCount)
       return line_number + 1

   def validate_err(self,ErrorList,newKeyList, parent="") :
       for k,v in ErrorList.iteritems():
           if v is True:
               continue
           if isinstance(v,dict):
               self.validate_err(v, newKeyList,k)
           else :
               newKeyList.append(parent + "->" + k + "=" + str(v)[str(v).find('"')+1:str(v).rfind('"')])
       return newKeyList

   def ReadConfigFile (self, path):
       self.errorlog.Clear()
       self.tree.DeleteAllItems()
       self.root = self.tree.AddRoot(path)
       self.tree.SetPyData(self.root, None)
       try:
           if path[path.rfind("\\")+1:] == "DSMConfig.ini" :
               val = Validator()
               configspec = ConfigObj(os.path.realpath(os.path.dirname(sys.argv[0])) + "\configspec\configspec.ini", interpolation=False, list_values=False,
                  _inspec=True)
               config = ConfigObj(path, file_error=True,configspec=configspec)
               validationResult = config.validate(val,preserve_errors=True)
               #print flatten_errors(config, ErrorList)
               invalidKeys=[]
               invalidKeys = self.validate_err(validationResult,invalidKeys)
               attr = rt.TextAttrEx()
               attr.SetFlags(rt.TEXT_ATTR_TEXT_COLOUR)
               self.SetDefaultTextColour()
               for key in invalidKeys:
                   key1 = key.split("->")
                   for j in range(0,self.rtc.GetNumberOfLines()) :
                       pos = self.rtc.GetLineText(j).find(key1[0])
                       if pos>=0 : break
                   for i in range(j+1,self.rtc.GetNumberOfLines()) :
                       key2 = key1[1].split("=")
                       pos0 = self.rtc.GetLineText(i).find(key2[0])
                       if key2[1]=="" :
                           pos1 = -1
                       else :
                           pos1 = self.rtc.GetLineText(i).find(key2[1])
                       pos2 = self.rtc.GetLineText(i).find("=")
                       pos3 = self.rtc.GetLineText(i).find("#")
                       if pos0 >= 0 and pos1>=0 and pos2>=0 and pos3<0 :
                           start = self.rtc.XYToPosition(0,i)
                           end = self.rtc.XYToPosition(len(self.rtc.GetLineText(i)),i)
                           attr.SetTextColour((255, 0, 0))
                           self.rtc.SetSelection(start, end)
                           r = self.rtc.GetSelectionRange()
                           self.rtc.SetStyle(r, attr)
                           self.rtc.SelectNone()
                           self.errorlog.WriteText('Invalid format for "' + key + '" at line ' + str(i+1) + '.\n')
                           break
           else :
               config = ConfigObj(path, file_error=True)
           sections = [(k, v) for (k, v) in config.iteritems()]
           line_number = self.AppendItemToTree(self.root,sections, 0, self.rtc.GetNumberOfLines())
           self.tree.Expand(self.root)
       except (ConfigObjError, IOError), e:
           self.ConfigError(e)

   def OnFileSave(self, evt):
       if not self.rtc.GetFilename():
           self.OnFileSaveAs(evt)
           return
       self.rtc.SaveFile(self.rtc.GetFilename(),1)
       self.ReadConfigFile(self.rtc.GetFilename())

   def OnFileSaveAs(self, evt):
       wildcard, types = rt.RichTextBuffer.GetExtWildcard(save=False)
       dlg = wx.FileDialog(self, "Choose a filename",
                           wildcard="*.ini",
                           style=wx.SAVE)
       if dlg.ShowModal() == wx.ID_OK:
           wildcard, types = rt.RichTextBuffer.GetExtWildcard(save=False)
           path = dlg.GetPath()
           if path:
               fileType = types[dlg.GetFilterIndex()]
               self.rtc.SaveFile(path, fileType)
               self.ReadConfigFile(path)
       dlg.Destroy()

   def OnFileExit(self, evt):
       self.Close(True)

   def GetLineNumberConfig(self, key, startLine, endLine):
       for i in range(startLine,endLine) :
           text=""
           pos = self.rtc.GetLineText(i).find(key)
           if pos >= 0 :
               if self.rtc.GetLineText(i).find("[") >= 0 :
                   text = self.rtc.GetLineText(i).replace("[","")
                   text = text.replace("]","")
               elif self.rtc.GetLineText(i).find("=") >= 0 :
                   text = self.rtc.GetLineText(i)[0:self.rtc.GetLineText(i).find("=")].strip()
               if text.strip() == key.strip() :
                   return i
       return startLine

   def OnActivatedTreeItem(self, evt):
       item = evt.GetItem()
       if self.tree.GetPyData(item) != None :
           line_number = self.tree.GetPyData(item)
           if line_number<self.rtc.GetNumberOfLines() :
               attr = rt.TextAttrEx()
               attr.SetFlags(rt.TEXT_ATTR_TEXT_COLOUR)

               self.SetDefaultTextColour()

               attr.SetTextColour((0, 200, 0))
               start = self.rtc.XYToPosition(0,line_number)
               end = self.rtc.XYToPosition(len(self.rtc.GetLineText(line_number)),line_number)
               self.rtc.ShowPosition(start)
               self.rtc.SetSelection(start, end)
               r = self.rtc.GetSelectionRange()
               self.rtc.SetStyle(r, attr)
               self.rtc.SelectNone()
           else :
               dlg = wx.MessageDialog(self, 'This section is missing.',
                                      'Warning',
                                      wx.OK | wx.ICON_INFORMATION
                                      #wx.YES_NO | wx.NO_DEFAULT | wx.CANCEL | wx.ICON_INFORMATION
                                      )
               dlg.ShowModal()
               dlg.Destroy()

   def ForwardEvent(self, evt):
       # The RichTextCtrl can handle menu and update events for undo,
       # redo, cut, copy, paste, delete, and select all, so just
       # forward the event to it.
       self.rtc.ProcessEvent(evt)

   def SetDefaultTextColour(self):
       attr = rt.TextAttrEx()
       attr.SetFlags(rt.TEXT_ATTR_TEXT_COLOUR)

       attr.SetTextColour((0, 0, 0))
       self.rtc.SelectAll()
       r = self.rtc.GetSelectionRange()
       self.rtc.SetStyle(r, attr)

       isMultiLine=0
       for i in range(0,self.rtc.GetNumberOfLines()) :
           text=self.rtc.GetLineText(i)
           start = 0
           end = 0
           if isMultiLine==0 :
               attr.SetBackgroundColour((255, 255, 255))
               if text.find("=") >= 0 :
                   #attr.SetTextColour((182, 6, 249))
                   attr.SetTextColour((0, 64, 0))
                   start = self.rtc.XYToPosition(0,i)
                   end = self.rtc.XYToPosition(text.find("="),i)
                   self.rtc.SetSelection(start, end)
                   if self.rtc.IsSelectionBold() != True :
                       self.rtc.ApplyBoldToSelection()
                   r = self.rtc.GetSelectionRange()
                   self.rtc.SetStyle(r, attr)
               elif text.find("[") >= 0 :
                   attr.SetTextColour((0, 0, 255))
                   start = self.rtc.XYToPosition(0,i)
                   end = self.rtc.XYToPosition(text.rfind("]")+1,i)
                   self.rtc.SetSelection(start, end)
                   if self.rtc.IsSelectionBold() != True :
                       self.rtc.ApplyBoldToSelection()
                   r = self.rtc.GetSelectionRange()
                   self.rtc.SetStyle(r, attr)

               if text.find("#") >= 0 :
                   attr.SetTextColour((187, 187, 187))
                   start = self.rtc.XYToPosition(text.find("#"),i)
                   end = self.rtc.XYToPosition(len(text),i)
                   self.rtc.SetSelection(start, end)
                   if self.rtc.IsSelectionItalics() != True :
                       self.rtc.ApplyItalicToSelection()
                   if self.rtc.IsSelectionBold() == True :
                       self.rtc.ApplyBoldToSelection()
                   r = self.rtc.GetSelectionRange()
                   self.rtc.SetStyle(r, attr)

               text = text.replace('"""',"'''")
               if text.find("'''") >= 0 :
                   isMultiLine=1
                   attr.SetBackgroundColour((232, 232, 232))
                   attr.SetTextColour((0, 0, 0))
                   start = self.rtc.XYToPosition(text.find("'''"),i)
                   end = self.rtc.XYToPosition(len(text),i)
                   self.rtc.SetSelection(start, end)
                   if self.rtc.IsSelectionItalics() == True :
                       self.rtc.ApplyItalicToSelection()
                   if self.rtc.IsSelectionBold() == True :
                       self.rtc.ApplyBoldToSelection()
                   r = self.rtc.GetSelectionRange()
                   self.rtc.SetStyle(r, attr)
           else :
               text = text.replace('"""',"'''")
               start = self.rtc.XYToPosition(0,i)
               if text.find("'''") >= 0 :
                   isMultiLine=0
                   end = self.rtc.XYToPosition(text.find("'''") + 3,i)
               else :
                   end = self.rtc.XYToPosition(len(text),i)
               self.rtc.SetSelection(start, end)
               if self.rtc.IsSelectionItalics() == True :
                   self.rtc.ApplyItalicToSelection()
               if self.rtc.IsSelectionBold() == True :
                   self.rtc.ApplyBoldToSelection()
               r = self.rtc.GetSelectionRange()
               self.rtc.SetStyle(r, attr)
       self.rtc.SelectNone()

class MyApp(wx.App):
   def OnInit(self):
       frame = MyFrame(None, -1, "ConfigObj File Editor")
       frame.Show(True)
       self.SetTopWindow(frame)
       return True

print "1"
app = MyApp(0)
print "2"
app.MainLoop()
