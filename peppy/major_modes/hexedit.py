# peppy Copyright (c) 2006-2010 Rob McMullen
# Licenced under the GPLv2; see http://peppy.flipturn.org for more info
import os,struct

import wx
import wx.stc
import wx.grid as Grid
from wx.lib.evtmgr import eventManager
import wx.lib.newevent

from peppy.yapsy.plugins import *
from peppy.actions import *
from peppy.major import *
from peppy.stcinterface import *
from peppy.actions.minibuffer import *


class OpenHexEditor(SelectAction):
    """Open a Hex Editor"""
    name = "&Open Hex Editor..."
    default_menu = "&Help/Samples"

##    def isEnabled(self, state=None):
##        return not self.frame.isOpen()

    def action(self, index=-1, multiplier=1):
        self.frame.open("about:0x00-0xff")


class WorksWithHexEdit(object):
    @classmethod
    def worksWithMajorMode(cls, modecls):
        return modecls.keyword == 'HexEdit'

class GotoOffset(WorksWithHexEdit, MinibufferAction):
    """Goto an offset.
    
    Use minibuffer to request an offset, then move the cursor to that
    location in the file.
    """

    name = "Goto Offset..."
    default_menu = ("Edit", 500)
    key_bindings = {'default': 'M-g',}
    minibuffer = IntMinibuffer
    minibuffer_label = "Goto Offset:"

    def processMinibuffer(self, minibuffer, mode, pos):
        """
        Callback function used to set the grid's cursor to the
        specified byte offset.
        """
        #dprint("goto pos = %d" % pos)
        mode.GotoPos(pos)


class HexRecordFormat(WorksWithHexEdit, MinibufferAction):
    """Change how hex values are unpacked to human-readable values 
    
    Use minibuffer to change the struct description of the hex values
    """

    name = "Record Format..."
    default_menu = ("View", -500)
    key_bindings = {'default': 'M-f',}
    minibuffer = TextMinibuffer
    minibuffer_label = "Record Format:"

    def getInitialValueHook(self):
        return self.mode.table.format

    def processMinibuffer(self, minibuffer, mode, text):
        #dprint("changing format to %s" % text)
        self.mode.Update(format=str(text))


class ShowHexDigits(WorksWithHexEdit, ToggleAction):
    """Show or hide the display of hex digits
    
    """
    name = "Show Hex Digits"
    default_menu = ("View", 550)

    def isChecked(self):
        return self.mode.table._show_hex
    
    def action(self, index=-1, multiplier=1):
        #dprint("showing hex digits: %s" % (not self.mode.table._show_hex))
        self.mode.table.showHexDigits(self.mode, not self.mode.table._show_hex)
    

class ShowRecordNumbers(WorksWithHexEdit, ToggleAction):
    """Show record numbers instead of byte offset
    
    """
    name = "Show Record Numbers"
    default_menu = ("View", 551)

    def isChecked(self):
        return self.mode.table._show_record_numbers
    
    def action(self, index=-1, multiplier=1):
        #dprint("showing hex digits: %s" % (not self.mode.table._show_record_numbers))
        self.mode.table.showRecordNumbers(self.mode, not self.mode.table._show_record_numbers)
    

class HugeTable(Grid.PyGridTableBase,debugmixin):
    def __init__(self,stc,format="16c"):
        Grid.PyGridTableBase.__init__(self)

        self.setFormat(format)
        self.setSTC(stc)
        
        self._debug=False
        self._show_hex = True
        self._show_record_numbers = False
        self._col_labels = None

    def setFormat(self, format):
        if format:
            try:
                nbytes = struct.calcsize(format)
            except struct.error:
                raise
            
            self.format = format
            self.nbytes = nbytes
            self._hexcols = self.nbytes
            self.parseFormat(self.format)
            self._cols = self._hexcols + self._textcols
            assert self.dprint("# hexcols = %d, # textcols = %d, total=%d" % (self._hexcols, self._textcols, self._cols))
        
        # Any change in the format will invalidate the cache since the cache
        # also stores the unpacked version of the data
        self.invalidateCache()

    def parseFormat(self, format):
        """
        Given a format specifier, parse the string into individual
        cell formats.  A format specifier may have a repeat count, but
        we have to break this down into the format specifiers for each
        cell on the value side.

        @param format: text string specifying the format characters
        """
        self.types=[]
        mult=None
        endian='='
        for c in format:
            assert self.dprint("checking %s" % c)
            if c>='0' and c<='9':
                if mult==None:
                    mult=0
                mult=mult*10+ord(c)-ord('0')
            elif c in ['x','c','b','B','h','H','i','I','l','L','f','d']:
                if mult==None:
                    self.types.append(endian+c)
                elif mult>0:
                    self.types.extend([endian+c]*mult)
                mult=None
                endian='='
            elif c in ['@','=','<','>','!']:
                endian=c
            else:
                assert self.dprint("ignoring %s" % c)
        self.sizes=[]
        self.offsets=[]
        offset=0
        last=self.types[0]
        self.uniform=True
        for c in self.types:
            if c!=last:
                self.uniform=False
            size=struct.calcsize(c)
            self.sizes.append(size)
            self.offsets.append(offset)
            offset+=size
            
        self._textcols=len(self.types)
        assert self.dprint("format = %s" % self.types)
        assert self.dprint("sizes = %s" % self.sizes)
        assert self.dprint("offsets = %s" % self.offsets)
        
    def setSTC(self, stc):
        self.stc=stc
        assert self.dprint("stc = %s" % self.stc        )
        self._rows=((self.stc.GetLength()-1)/self.nbytes)+1
        assert self.dprint(" rows=%d cols=%d" % (self._rows,self._cols))

##    def GetAttr(self, row, col, kind):
##        attr = [self.even, self.odd][row % 2]
##        attr.IncRef()
##        return attr

    def getTextCol(self,col):
        return col-self._hexcols
    
    def getTextColPreferredWidth(self, col):
        col = self.getTextCol(col)
        format = self.types[col][1] # types is 2 char string: endian + format
        if format in "cbB": # character
            width = self._base_width
        elif format in "hH": # short
            width = self._base_width * 8
        elif format in "iIlLqQ": # int
            width = self._base_width * 14
        elif format in "fd": # floating point
            width = self._base_width * 20
        else:
            width = self._base_width * 4
        width += 4 # pixel offset for borders
        return width
    
    def getHexColPreferredWidth(self):
        if self._show_hex:
            width = self._hexcol_width
        else:
            width = 0
        return width
    
    def showHexDigits(self, grid, state, refresh=True):
        self._show_hex = state
        width = self.getHexColPreferredWidth()
        for col in range(self._hexcols):
            grid.SetColSize(col, width)
        if refresh:
            grid.AdjustScrollbars()
            grid.ForceRefresh()

    def showRecordNumbers(self, grid, state, refresh=True):
        self._show_record_numbers = state
        if refresh:
            grid.ForceRefresh()

    def getLoc(self, row, col):
        """Get the byte offset from start of file given row, col
        position.
        """
        if col<self._hexcols:
            loc = row*self.nbytes + col
        else:
            loc = row*self.nbytes + self.offsets[self.getTextCol(col)]
        return loc

    def getNumberHexCols(self):
        return self._hexcols
    
    def getNumberTextCols(self):
        return self._textcols
    
    def getCursorPosition(self, loc, refcol=0):
        """Get cursor position from byte offset from start of file.
        Optionally take a column parameter that tells us which side of
        the grid we're on, the hex side or the calculated side.
        """
        row=loc/self.nbytes
        col=loc%self.nbytes
        if col>=self._hexcols:
            # convert col to the correct column in the text representation
            pass
        return (row,col)
   
    def getNextCursorPosition(self, row, col):
        if col<self._hexcols:
            col+=1
            if col>=self._hexcols:
                if row<self._rows-1:
                    row+=1
                    col=0
                else:
                    col=self._hexcols-1
        else:
            col+=1
            if col>=self._cols:
                if row<self._rows-1:
                    row+=1
                    col=self._hexcols
                else:
                    col=self._cols-1
        return (row,col)
   
    def getPrevCursorPosition(self, row, col):
        if col<self._hexcols:
            col-=1
            if col<0:
                if row>0:
                    row-=1
                    col=self._hexcols-1
                else:
                    col=0
        else:
            col-=1
            if col<=self._hexcols:
                if row>0:
                    row-=1
                    col=self._cols-1
                else:
                    col=self._hexcols
        return (row,col)
   
    def GetNumberRows(self):
        assert self.dprint("rows = %d" % self._rows)
        return self._rows

    def GetRowLabelValue(self, row):
        if self._show_record_numbers:
            return "%d" % row
        return "%04x" % (row*self.nbytes)

    def GetNumberCols(self):
        assert self.dprint("cols = %d" % self._cols)
        return self._cols

    def GetColLabelValue(self, col):
        assert self.dprint("col=%x" % col)
        if col<self._hexcols:
            return "%x" % col
        else:
            col = self.getTextCol(col)
            if self._col_labels and col < len(self._col_labels):
                return self._col_labels[col]
            return "%x" % self.offsets[col]

    def IsEmptyCell(self, row, col):
        if col<self._hexcols:
            if self.getLoc(row,col)>self.stc.GetLength():
                return True
            else:
                return False
        else:
            return False
    
    def invalidateCache(self, max=100):
        self._cache = {}
        self._cache_max = max
        self._cache_fifo = []
    
    def invalidateCacheRow(self, row):
        if row in self._cache:
            del self._cache[row]
            self._cache_fifo.remove(row)
    
    def getRowData(self, row):
        if len(self._cache_fifo) > self._cache_max:
            amt = self._cache_max / 8
            remove = self._cache_fifo[:amt]
            self._cache_fifo = self._cache_fifo[amt:]
            for r in remove:
                if r != row:
                    del self._cache[r]
                else:
                    # add back the row that we didn't remove
                    self._cache_fifo.append(row)
            #dprint("Removed 1/8 of the cache: %d elements: %s.  cache=%s" % (amt, str(remove), str(self._cache_fifo)))
        if row not in self._cache:
            startpos = row*self.nbytes
            endpos = startpos + self.nbytes
            data = self.stc.GetBinaryData(startpos,endpos)
            
            # pad data with dummy bytes if we've hit the end of file and it's
            # not an even multiple of the column size
            if len(data) < self.nbytes:
                data += '\0' * (self.nbytes - len(data))
            
            s = struct.unpack(self.format, data)
            self._cache[row] = (data, s)
            #dprint("Storing cached data for row %d: %s, %s" % (row, repr(data), str(s)))
            
            self._cache_fifo.append(row)
        return self._cache[row]
    
    def GetValue(self, row, col):
        data, s = self.getRowData(row)
        if col<self._hexcols:
            return "%02x" % ord(data[col])
        else:
            col -= self._hexcols
            return str(s[col])

    def SetValue(self, row, col, value):
        if col<self._hexcols:
            val=int(value,16)
            if val>=0 and val<256:
                bytes = chr(val)
            else:
                assert self.dprint('SetValue(%d, %d, "%s")=%d out of range.' % (row, col, value,val))
        else:
            textcol = self.getTextCol(col)
            fmt = self.types[textcol]
            assert self.dprint('SetValue(%d, %d, %s (%s)) packing with fmt %s.' % (row, col, value, repr(value), fmt))
            fmt_char = fmt[-1]
            if fmt_char == 'f' or fmt_char == 'd':
                value = float(value)
            elif fmt_char in ['bBhHiIlLqQ']:
                value = int(value)
            else:
                value = str(value)
            bytes = struct.pack(fmt, value)
            assert self.dprint('bytes = %s' % repr(bytes))
            
        loc = self.getLoc(row, col)
        locend = loc + len(bytes)
        
        self.stc.SetBinaryData(loc, locend, bytes)
        
        self.invalidateCacheRow(row)

    def ResetView(self, grid, stc, format=None, col_labels=None):
        """
        (Grid) -> Reset the grid view.   Call this to
        update the grid if rows and columns have been added or deleted
        """
        oldrows=self._rows
        oldcols=self._cols
        if format:
            self.setFormat(format)
        self.setSTC(stc)
        
        grid.BeginBatch()

        for current, new, delmsg, addmsg in [
            (oldrows, self._rows, Grid.GRIDTABLE_NOTIFY_ROWS_DELETED, Grid.GRIDTABLE_NOTIFY_ROWS_APPENDED),
            (oldcols, self._cols, Grid.GRIDTABLE_NOTIFY_COLS_DELETED, Grid.GRIDTABLE_NOTIFY_COLS_APPENDED),
        ]:

            if new < current:
                msg = Grid.GridTableMessage(self,delmsg,new,current-new)
                grid.ProcessTableMessage(msg)
            elif new > current:
                msg = Grid.GridTableMessage(self,addmsg,new-current)
                grid.ProcessTableMessage(msg)
                self.UpdateValues(grid)
        grid.EndBatch()

        # update the scrollbars and the displayed part of the grid
        grid.SetColMinimalAcceptableWidth(0)
        font=wx.Font(10, wx.MODERN, wx.NORMAL, wx.NORMAL)
        dc=wx.MemoryDC()
        dc.SetFont(font)
        
        (width, height) = dc.GetTextExtent("M")
        self._base_width = width
        self._hexcol_width = (width * 2) + 4
        grid.SetDefaultRowSize(height)
        
        width = self.getHexColPreferredWidth()
        for col in range(self._hexcols):
            # Can't share GridCellAttrs among columns; causes crash when
            # freeing them.  So, have to individually allocate the attrs for
            # each column
            hexattr = Grid.GridCellAttr()
            hexattr.SetFont(font)
            hexattr.SetBackgroundColour("white")
            assert self.dprint("hexcol %d width=%d" % (col,width))
            grid.SetColMinimalWidth(col, 0)
            grid.SetColSize(col, width)
            grid.SetColAttr(col, hexattr)
            
        for col in range(self._hexcols, self._cols, 1):
            textattr = Grid.GridCellAttr()
            textattr.SetFont(font)
            textattr.SetBackgroundColour(wx.Color(240, 240, 240))
            grid.SetColMinimalWidth(col, 4)
            width = self.getTextColPreferredWidth(col)
            assert self.dprint("textcol %d width=%d" % (col, width))
            grid.SetColSize(col, width)
            grid.SetColAttr(col, textattr)

        self._rows = self.GetNumberRows()
        self._cols = self.GetNumberCols()
##        # update the column rendering plugins
##        self._updateColAttrs(grid)
        if col_labels and len(col_labels) >= self._textcols:
            self._col_labels = col_labels
        else:
            self._col_labels = None

        grid.AdjustScrollbars()
        grid.ForceRefresh()


    def UpdateValues(self, grid):
        """Update all displayed values"""
        # This sends an event to the grid table to update all of the values
        msg = Grid.GridTableMessage(self, Grid.GRIDTABLE_REQUEST_VIEW_GET_VALUES)
        grid.ProcessTableMessage(msg)


class HexDigitMixin(object):
    keypad=[ wx.WXK_NUMPAD0, wx.WXK_NUMPAD1, wx.WXK_NUMPAD2, wx.WXK_NUMPAD3, 
             wx.WXK_NUMPAD4, wx.WXK_NUMPAD5, wx.WXK_NUMPAD6, wx.WXK_NUMPAD7, 
             wx.WXK_NUMPAD8, wx.WXK_NUMPAD9
             ]
    
    def isValidHexDigit(self,key):
        return key in HexDigitMixin.keypad or (key>=ord('0') and key<=ord('9')) or (key>=ord('A') and key<=ord('F')) or (key>=ord('a') and key<=ord('f'))

    def getValidHexDigit(self,key):
        if key in HexDigitMixin.keypad:
            return chr(ord('0') + key - wx.WXK_NUMPAD0)
        elif (key>=ord('0') and key<=ord('9')) or (key>=ord('A') and key<=ord('F')) or (key>=ord('a') and key<=ord('f')):
            return chr(key)
        else:
            return None

class HexTextCtrl(wx.TextCtrl,HexDigitMixin,debugmixin):
    def __init__(self,parent,id,parentgrid):
        # Don't use the validator here, because apparently we can't
        # reset the validator based on the columns.  We have to do the
        # validation ourselves using EVT_KEY_DOWN.
        wx.TextCtrl.__init__(self,parent, id,
                             style=wx.TE_PROCESS_TAB|wx.TE_PROCESS_ENTER)
        assert self.dprint("parent=%s" % parent)
        self.SetInsertionPoint(0)
        self.Bind(wx.EVT_TEXT, self.OnText)
        self.Bind(wx.EVT_KEY_DOWN, self.OnKeyDown)
        self.parentgrid=parentgrid
        self.setMode('hex')
        self.startValue=None

    def setMode(self, mode):
        self.mode=mode
        if mode=='hex':
            self.SetMaxLength(2)
            self.autoadvance=2
        elif mode=='char':
            self.SetMaxLength(1)
            self.autoadvance=1
        else:
            self.SetMaxLength(0)
            self.autoadvance=0
        self.userpressed=False

    def editingNewCell(self, value, mode='hex'):
        """
        Begin editing a new cell by determining the edit mode and
        setting the initial value.
        """
        # Set the mode before setting the value, otherwise OnText gets
        # triggered before self.userpressed is set to false.  When
        # operating in char mode (i.e. autoadvance=1), this causes the
        # editor to skip every other cell.
        self.setMode(mode)
        self.startValue=value
        self.SetValue(value)
        self.SetFocus()
        self.SetInsertionPoint(0)
        self.SetSelection(-1, -1) # select the text

    def insertFirstKey(self, key):
        """
        Check for a valid initial keystroke, and insert it into the
        text ctrl if it is one.

        @param key: keystroke
        @type key: int

        @returns: True if keystroke was valid, False if not.
        """
        ch=None
        if self.mode=='hex':
            ch=self.getValidHexDigit(key)
        elif key>=wx.WXK_SPACE and key<=255:
            ch=chr(key)

        if ch is not None:
            # set self.userpressed before SetValue, because it appears
            # that the OnText callback happens immediately and the
            # keystroke won't be flagged as one that the user caused.
            self.userpressed=True
            self.SetValue(ch)
            self.SetInsertionPointEnd()
            return True

        return False

    def OnKeyDown(self, evt):
        """
        Keyboard handler to process command keys before they are
        inserted.  Tabs, arrows, ESC, return, etc. should be handled
        here.  If the key is to be processed normally, evt.Skip must
        be called.  Otherwise, the event is eaten here.

        @param evt: key event to process
        """
        assert self.dprint("key down before evt=%s" % evt.GetKeyCode())
        key=evt.GetKeyCode()
        
        if key==wx.WXK_TAB:
            wx.CallAfter(self.parentgrid.advanceCursor)
            return
        if key==wx.WXK_ESCAPE:
            self.SetValue(self.startValue)
            wx.CallAfter(self.parentgrid.abortEdit)
            return
        elif self.mode=='hex':
            if self.isValidHexDigit(key):
                self.userpressed=True
        elif self.mode!='hex':
            self.userpressed=True
        evt.Skip()
        
    def OnText(self, evt):
        """
        Callback used to automatically advance to the next edit field.
        If self.autoadvance > 0, this number is used as the max number
        of characters in the field.  Once the text string hits this
        number, the field is processed and advanced to the next
        position.
        
        @param evt: CommandEvent
        """
        assert self.dprint("evt=%s str=%s cursor=%d" % (evt,evt.GetString(),self.GetInsertionPoint()))
        
        # NOTE: we check that GetInsertionPoint returns 1 less than
        # the desired number because the insertion point hasn't been
        # updated yet and won't be until after this event handler
        # returns.
        if self.autoadvance and self.userpressed:
            if len(evt.GetString())>=self.autoadvance and self.GetInsertionPoint()>=self.autoadvance-1:
                # FIXME: problem here with a bunch of really quick
                # keystrokes -- the interaction with the
                # underlyingSTCChanged callback causes a cell's
                # changes to be skipped over.  Need some flag in grid
                # to see if we're editing, or to delay updates until a
                # certain period of calmness, or something.
                wx.CallAfter(self.parentgrid.advanceCursor)
        

class HexCellEditor(Grid.PyGridCellEditor,HexDigitMixin,debugmixin):
    """
    Cell editor for the grid, based on GridCustEditor.py from the
    wxPython demo.
    """
    def __init__(self,grid):
        Grid.PyGridCellEditor.__init__(self)
        self.parentgrid=grid


    def Create(self, parent, id, evtHandler):
        """
        Called to create the control, which must derive from wx.Control.
        *Must Override*
        """
        assert self.dprint("")
        self._tc = HexTextCtrl(parent, id, self.parentgrid)
        self.SetControl(self._tc)

        if evtHandler:
            self._tc.PushEventHandler(evtHandler)

    def SetSize(self, rect):
        """
        Called to position/size the edit control within the cell rectangle.
        If you don't fill the cell (the rect) then be sure to override
        PaintBackground and do something meaningful there.
        """
        assert self.dprint("rect=%s\n" % rect)
        self._tc.SetDimensions(rect.x, rect.y, rect.width+2, rect.height+2,
                               wx.SIZE_ALLOW_MINUS_ONE)


    def Show(self, show, attr):
        """
        Show or hide the edit control.  You can use the attr (if not None)
        to set colours or fonts for the control.
        """
        assert self.dprint("show=%s, attr=%s" % (show, attr))
        Grid.PyGridCellEditor.Show(self, show, attr)


    def PaintBackground(self, rect, attr):
        """
        Draws the part of the cell not occupied by the edit control.  The
        base  class version just fills it with background colour from the
        attribute.  In this class the edit control fills the whole cell so
        don't do anything at all in order to reduce flicker.
        """
        assert self.dprint("MyCellEditor: PaintBackground\n")


    def BeginEdit(self, row, col, grid):
        """
        Fetch the value from the table and prepare the edit control
        to begin editing.  Set the focus to the edit control.
        *Must Override*
        """
        assert self.dprint("row,col=(%d,%d)" % (row, col))
        self.startValue = grid.GetTable().GetValue(row, col)
        mode='hex'
        table=self.parentgrid.table
        textcol=table.getTextCol(col)
        if textcol>=0:
            textfmt=table.types[textcol]
            if textfmt.endswith('s') or textfmt.endswith('c'):
                if table.sizes[textcol]==1:
                    mode='char'
                else:
                    mode='str'
            else:
                mode='text'
            assert self.dprint("In value area! mode=%s" % mode)
        self._tc.editingNewCell(self.startValue,mode)


    def EndEdit(self, row, col, grid):
        """
        Complete the editing of the current cell. Returns True if the value
        has changed.  If necessary, the control may be destroyed.
        *Must Override*
        """
        assert self.dprint("row,col=(%d,%d)" % (row, col))
        changed = False

        val = self._tc.GetValue()
        
        if val != self.startValue:
            changed = True
            grid.GetTable().SetValue(row, col, val) # update the table

        self.startValue = ''
        self._tc.SetValue('')
        return changed


    def Reset(self):
        """
        Reset the value in the control back to its starting value.
        *Must Override*
        """
        assert self.dprint("")
        self._tc.SetValue(self.startValue)
        self._tc.SetInsertionPointEnd()


    def IsAcceptedKey(self, evt):
        """
        Return True to allow the given key to start editing: the base class
        version only checks that the event has no modifiers.  F2 is special
        and will always start the editor.
        """
        assert self.dprint("keycode=%d" % (evt.GetKeyCode()))

        ## We can ask the base class to do it
        #return self.base_IsAcceptedKey(evt)

        # or do it ourselves
        return (not (evt.ControlDown() or evt.AltDown()) and
                evt.GetKeyCode() != wx.WXK_SHIFT)


    def StartingKey(self, evt):
        """
        If the editor is enabled by pressing keys on the grid, this will be
        called to let the editor do something about that first key if desired.
        """
        assert self.dprint("keycode=%d" % evt.GetKeyCode())
        key = evt.GetKeyCode()
        if not self._tc.insertFirstKey(key):
            evt.Skip()


    def StartingClick(self):
        """
        If the editor is enabled by clicking on the cell, this method will be
        called to allow the editor to simulate the click on the control if
        needed.
        """
        assert self.dprint("")


    def Destroy(self):
        """final cleanup"""
        assert self.dprint("")
        Grid.PyGridCellEditor.Destroy(self)


    def Clone(self):
        """
        Create a new object which is the copy of this one
        *Must Override*
        """
        assert self.dprint("")
        return HexCellEditor(self.parentgrid)






# This creates a new Event class and a EVT binder function
(WaitUpdateEvent, EVT_WAIT_UPDATE) = wx.lib.newevent.NewEvent()

from threading import Thread
class WaitThread(Thread):
    def __init__(self, notify_window, delay=0.2):
        Thread.__init__(self)
        self._notify_window = notify_window
        self._wait=1
        self._delay=delay

    def waitMore(self):
        self._wait=2

    def run(self):
        while self._wait>0:
            time.sleep(self._delay)
            self._wait-=1
        wx.PostEvent(self._notify_window,WaitUpdateEvent())



class HexEditMode(STCInterface, Grid.Grid, MajorMode):
    """
    View for editing in hexidecimal notation.
    """
    keyword = 'HexEdit'
    emacs_synonyms = 'hexl'
    
    icon='icons/tux.png'
    mimetype = 'application/octet-stream'
    
    @classmethod
    def verifyCompatibleSTC(self, stc_class):
        return hasattr(stc_class, 'GetBinaryData')

    def __init__(self, parent, wrapper, buffer, frame):
        """Create the HexEdit viewer
        """
        MajorMode.__init__(self, parent, wrapper, buffer, frame)
        assert self.dprint("creating new HexEditMode window")
        Grid.Grid.__init__(self, parent, -1)
        self.table = HugeTable(self.buffer.stc, "16c")

        # The second parameter means that the grid is to take
        # ownership of the table and will destroy it when done.
        # Otherwise you would need to keep a reference to it and call
        # its Destroy method later.
        self.SetTable(self.table, True)
        self.SetMargins(0,0)
        self.SetColMinimalAcceptableWidth(10)
        self.EnableDragGridSize(False)

        self.RegisterDataType(Grid.GRID_VALUE_STRING, None, None)
        self.SetDefaultEditor(HexCellEditor(self))

        self.updateUICallback = None
        self.Bind(Grid.EVT_GRID_CELL_LEFT_CLICK, self.OnLeftDown)
        self.Bind(Grid.EVT_GRID_CELL_RIGHT_CLICK, self.OnRightDown)
        self.Bind(Grid.EVT_GRID_SELECT_CELL, self.OnSelectCell)
        self.Bind(wx.EVT_KEY_DOWN, self.OnKeyDown)
        self.Bind(EVT_WAIT_UPDATE,self.OnUnderlyingUpdate)
        self.Show(True)

    def createPostHook(self):
        self.buffer.startChangeDetection()
        self.Update(self.buffer.stc)

    def createListenersPostHook(self):
        # Thread stuff for the underlying change callback
        self.waiting=None

        # Multiple binds to the same handler, ie multiple HexEditModes
        # trying to do self.buffer.stc.Bind(wx.stc.EVT_STC_MODIFIED,
        # self.underlyingSTCChanged) don't work.  Need to use the
        # event manager for multiple bindings.
        if hasattr(self.buffer.stc, 'addModifyCallback'):
            self.buffer.stc.addModifyCallback(self.underlyingSTCChanged)

    def removeListenersPostHook(self):
        if hasattr(self.buffer.stc, 'removeModifyCallback'):
            assert self.dprint("unregistering %s" % self.underlyingSTCChanged)
            self.buffer.stc.removeModifyCallback(self.underlyingSTCChanged)
        
    def Update(self, stc=None, format=None, col_labels=None):
        assert self.dprint("Need to update grid")
        if stc is None:
            stc = self.buffer.stc
        try:
            self.table.ResetView(self, stc, format, col_labels)
            self.setStatusText("Record format = '%s', %d bytes per record" % (self.table.format, self.table.nbytes))
        except struct.error:
            self.setStatusText("Bad record format: %s" % format)

    def OnUnderlyingUpdate(self, evt, loc=None):
        """Data has changed in some other view, so we need to update
        the grid and reset the grid's cursor to the updated position
        if the location is given.
        """
        assert self.dprint("OnUnderlyingUpdate: slow way of updating the grid -- updating the whole thing.")
        assert self.dprint(evt)

        self.table.invalidateCache()
        self.table.ResetView(self,self.table.stc) # FIXME: this is slow.  Put it in a thread or something.

        if loc is not None:
            self.GotoPos(loc)

    def OnRightDown(self, evt):
        assert self.dprint(self.GetSelectedRows())

    def OnLeftDown(self, evt):
        evt.Skip()
        wx.CallAfter(self.doUpdateUICallback)

    def OnSelectCell(self, evt):
        evt.Skip()
        wx.CallAfter(self.doUpdateUICallback)

    def OnKeyDown(self, evt):
        assert self.dprint("evt=%s" % evt)
        if evt.GetKeyCode() == wx.WXK_RETURN or evt.GetKeyCode()==wx.WXK_TAB:
            if evt.ControlDown():   # the edit control needs this key
                evt.Skip()
            else:
                self.DisableCellEditControl()
                if evt.ShiftDown():
                    (row,col)=self.GetTable().getPrevCursorPosition(self.GetGridCursorRow(),self.GetGridCursorCol())
                else:
                    (row,col)=self.GetTable().getNextCursorPosition(self.GetGridCursorRow(),self.GetGridCursorCol())
                self.SetGridCursor(row,col)
                self.MakeCellVisible(row,col)
        else:
            evt.Skip()
            
        wx.CallAfter(self.doUpdateUICallback)

    def abortEdit(self):
        self.DisableCellEditControl()

    def advanceCursor(self):
        self.DisableCellEditControl()
        # FIXME: moving from the hex region to the value region using
        # self.MoveCursorRight(False) causes a segfault, so make sure
        # to stay in the same region
        (row,col)=self.GetTable().getNextCursorPosition(self.GetGridCursorRow(),self.GetGridCursorCol())
        self.SetGridCursor(row,col)
        self.EnableCellEditControl()

    ## STC interface

    def GetCurrentLine(self):
        return self.GetGridCursorRow()

    def GetCurrentPos(self):
        return -1

    def GetColumn(self, pos):
        return self.GetGridCursorCol()

    def GotoPos(self, pos):
        row, col=self.GetTable().getCursorPosition(pos, self.GetGridCursorCol())
        self.SetGridCursor(row,col)
        self.MakeCellVisible(row,col)
    
    def addUpdateUIEvent(self, callback):
        """Add the equivalent to STC_UPDATEUI event for UI changes.

        The STC supplies the EVT_STC_UPDATEUI event that fires for
        every change that could be used to update the user interface:
        a text change, a style change, or a selection change.  If the
        editing (viewing) window does not use the STC to display
        information, you should supply the equivalent event for the
        edit window.
        
        @param callback: event handler to execute on event
        """
        self.updateUICallback = callback

    def doUpdateUICallback(self):
        if self.updateUICallback is not None:
            self.updateUICallback(None)
        
    def transModType(self, modType):
        st = ""
        table = [(wx.stc.STC_MOD_INSERTTEXT, "InsertText"),
                 (wx.stc.STC_MOD_DELETETEXT, "DeleteText"),
                 (wx.stc.STC_MOD_CHANGESTYLE, "ChangeStyle"),
                 (wx.stc.STC_MOD_CHANGEFOLD, "ChangeFold"),
                 (wx.stc.STC_PERFORMED_USER, "UserFlag"),
                 (wx.stc.STC_PERFORMED_UNDO, "Undo"),
                 (wx.stc.STC_PERFORMED_REDO, "Redo"),
                 (wx.stc.STC_LASTSTEPINUNDOREDO, "Last-Undo/Redo"),
                 (wx.stc.STC_MOD_CHANGEMARKER, "ChangeMarker"),
                 (wx.stc.STC_MOD_BEFOREINSERT, "B4-Insert"),
                 (wx.stc.STC_MOD_BEFOREDELETE, "B4-Delete")
                 ]

        for flag,text in table:
            if flag & modType:
                st = st + text + " "

        if not st:
            st = 'UNKNOWN'

        return st

    def underlyingSTCChanged(self,evt):
        # Short-circuit this callback when we are editing this grid.
        # The event is fired regardless of how the data is changed, so
        # without some sort of check, the grid ends up getting
        # modified twice.  If the current mode is in the active frame
        # and it is the active major mode, we know that we are editing
        # this grid by hand.
        if self.frame.isTopWindow() and self.frame.getActiveMajorMode()==self:
            assert self.dprint("TopWindow!  Skipping underlyingSTCChanged!")
            return
        
        # As the comment in the createWindow method noted, we have to
        # screen for the events we're interested in because we're not
        # allowed to change the events that self.buffer.stc sees.
        etype=evt.GetModificationType()
        if etype&wx.stc.STC_MOD_INSERTTEXT or etype&wx.stc.STC_MOD_DELETETEXT:
            assert self.dprint("""UnderlyingSTCChanged
            Mod type:     %s
            At position:  %d
            Lines added:  %d
            Text Length:  %d
            Text:         %s\n""" % ( self.transModType(evt.GetModificationType()),
                                      evt.GetPosition(),
                                      evt.GetLinesAdded(),
                                      evt.GetLength(),
                                      repr(evt.GetText()) ))

            #self.win.underlyingUpdate(self.buffer.stc,evt.GetPosition())
            if self.waiting:
                if self.waiting.isAlive():
                    assert self.dprint("found active wait thread")
                    self.waiting.waitMore()
                else:
                    self.waiting.join()
                    self.waiting=None
                    assert self.dprint("wait thread destroyed")
                    # start a new thread below

            # don't use an else here so that a new thread will be
            # started if we just destroyed the old thread.
            if not self.waiting:
                assert self.dprint("starting wait thread")
                self.waiting=WaitThread(self)
                self.waiting.start()


class HexEditPlugin(IPeppyPlugin, debugmixin):
    def getMajorModes(self):
        yield HexEditMode

    def getActions(self):
        return [OpenHexEditor, GotoOffset, HexRecordFormat, ShowHexDigits,
                ShowRecordNumbers]
