import os,sys,re
from cStringIO import StringIO

import __builtin__
__builtin__._ = str

import wx
import wx.stc

from peppy.debug import *
import peppy.vfs as vfs
debuglog(sys.stdout)

from peppy.stcbase import PeppyBaseSTC
from peppy.fundamental import FundamentalMode

class MockFont(object):
    def GetFaceName(self):
        return "fixed"
    def GetPointSize(self):
        return 10

class MockEditra(object):
    @classmethod
    def getStyleFile(self):
        return None
    class classprefs(object):
        primary_editing_font = MockFont()
        secondary_editing_font = MockFont()

class MockApp(wx.App):
    fonts = MockEditra()
    def getConfigFilePath(self, file):
        return None
    def GetLog(self):
        return lambda x: True
    

class MockWX(object):
    app = MockApp()
    root = wx.Frame(None, -1)

class MockSTC(PeppyBaseSTC):
    pass

class MockBuffer(object):
    def __init__(self, stc):
        self.stc = stc
        self.url = vfs.normalize("nothing")
    def startChangeDetection(self):
        pass

class MockFrame(wx.Frame):
    def __init__(self, mode):
        wx.Frame.__init__(self, None, -1)
        self.mode = mode
    def getActiveMajorMode(self):
        return self.mode


def getPlainSTC():
    stc = wx.stc.StyledTextCtrl(MockWX.root, -1)
    return stc

def getSTC(init=None, stcclass=FundamentalMode, count=1, lexer="Python", tab_size=4, use_tabs=False):
    refstc = MockSTC(MockWX.root)
    buffer = MockBuffer(refstc)
    frame = MockFrame(refstc)
    stc = stcclass(frame, frame, buffer, frame)
    frame.mode = stc
    #stc.SetLexer(lexer)
    stc.ConfigureLexer(lexer)
#    if lexer == wx.stc.STC_LEX_PYTHON:
#        # FIXME: this is a duplicate of the keyword string from
#        # PythonMode.  Find a way to NotRepeatMyself instead of this.
#        stc.SetKeyWords(0, 'and as assert break class continue def del elif else except exec finally for from global if import in is lambda not or pass print raise return try while True False None self')

    stc.SetText("")
    stc.SetEOLMode(wx.stc.STC_EOL_LF)
    stc.SetProperty("fold", "1")
    stc.SetIndent(tab_size)
    stc.SetUseTabs(use_tabs)   
    if init == 'py':
        stc.SetText("python source goes here")
    elif init == 'columns':
        for i in range(count):
            stc.AddText('%04d-0123456789\n' % i)
    stc.Colourise(0, stc.GetTextLength())
    return stc

def clearSTC(stc):
    stc.SetText("")
    stc.SetEOLMode(wx.stc.STC_EOL_LF)
    stc.SetProperty("fold", "1")
    stc.Colourise(0, stc.GetTextLength())

def prepareSTC(stc, before):
    print "*** before *** repr=%s\n%s" % (repr(before), before)
    cursor = before.find("|")
    stc.SetText(before)

    # change "|" to the cursor
    stc.SetTargetStart(cursor)
    stc.SetTargetEnd(cursor+1)
    stc.ReplaceTarget("")
    stc.GotoPos(cursor)
    
    stc.Colourise(0, stc.GetTextLength())
    stc.showStyle()

def checkSTC(stc, before, after):
    stc.showStyle()

    # change cursor to "|"
    stc.ReplaceSelection("|")
    text = stc.GetText()
    if after == text:
        print "Matched:\n*** stc ***\n%s\n***\n%s\n***" % (text, after)
        return True
    print "Not matched:\n*** stc ***: repr=%s\n%s\n***\n*** should be ***: repr=%s\n%s\n***" % (repr(text), text, repr(after), after)
    return False

def splittests(text):
    tests = []

    # at least 4 '-' characters delimits a test
    groups = re.split('[\r\n]-----*[\r\n]', text)
    #print groups
    for test in groups:
        # 2 '-' characters delimits the before and after pair
        pair = re.split('[\r\n]--[\r\n]', test)
        if len(pair) == 2:
            tests.append(pair)
        elif test:
            print test
            print pair
            tests.append((pair[0], ''))
    #print tests
    return tests

def splittestdict(text):
    tests = []

    # at least 4 '-' characters delimits a test
    test_groups = re.split('([\r\n]+)-----*[\r\n]+', text)
    dprint(test_groups)
    test_count = 0
    while test_count < len(test_groups):
        test = test_groups[test_count]
        test_count += 1
        if test_count < len(test_groups):
            # If there's a return character, add it
            test += test_groups[test_count]
            test_count += 1
            
        # 2 '-' characters delimits the before and after pair
        groups = re.split('([\r\n]+)(--\s*(\S+)).*[\r\n]+', test)
        dprint(groups)
        block = {}
        block['source'] = groups[0] + groups[1]
        count = 2
        while count < len(groups):
            if groups[count].startswith('--'):
                count += 1
                key = groups[count]
                count += 1
                block[key] = groups[count]
                count += 1
                if count < len(groups):
                    # If there's a return character, add it
                    block[key] += groups[count]
                    count += 1
            else:
                block['text'] = groups[count]
                count += 1
                if count < len(groups):
                    # If there's a return character, add it
                    block['text'] += groups[count]
                    count += 1
        tests.append(block)
    print tests
    return tests
