import os,sys,re
from cStringIO import StringIO

import wx.stc
from tests.mock_wx import *

from peppy.stcbase import *
from peppy.fundamental import *
from peppy.plugins.find_replace import *

from nose.tools import *

class TestFind(object):
    # Find service to use.  Don't get the class attribute confused with the
    # instance attribute of the same name.
    service = FindService
    
    def setUp(self):
        self.stc = getSTC(stcclass=FundamentalMode, lexer="None")
        self.stc.SetText("line 0\nline 1\nline a\nline 3\nblah blah blah\nstuff\nthings")
        self.settings = FindSettings()
        self.service = self.__class__.service(self.stc, self.settings)

    def findAll(self, locations, prev=False):
        """Find all matches in the indicated direction
        
        @param locations: list, where each item is either a single integer
        containing the location of the match, or a tuple containing the
        location and the start position
        
        @param prev: True if searching backward; default is forward search
        """
        while True:
            if prev:
                output = self.service.doFindPrev()
            else:
                output = self.service.doFindNext()
            #print(output, locations)
            expected = locations.pop(0)
            if isinstance(expected, int):
                eq_(output[0], expected)
            else:
                eq_(output, expected)
            if output[0] == -1:
                return

    def testFindNext(self):
        self.service.setFindString("line")
        self.findAll([(0,0), (7,4), (14,11), (21,18), (-1,25)])

    def testFindPrevious(self):
        self.stc.GotoPos(1000)
        self.service.setFindString("line")
        self.findAll([(21,55), (14,21), (7,14), (0,7), (-1,0)], prev=True)


class TestFindWildcard(TestFind):
    service = FindWildcardService


class TestFindRegex(TestFind):
    service = FindRegexService

    def testFindAny(self):
        self.service.setFindString("l..e")
        self.findAll([(0,0), (7,4), (14,11), (21,18), (-1,25)])

    def testFindLetter(self):
        self.service.setFindString("l[a-z]+e")
        self.findAll([(0,0), (7,4), (14,11), (21,18), (-1,25)])

    def testFindNumber(self):
        self.service.setFindString("line [0-9]")
        self.findAll([(0,0), (7,6), (21,13), (-1,27)])

    def testFindStart1(self):
        self.service.setFindString("^line")
        self.findAll([(0,0), (7,4), (14,11), (21,18), (-1,25)])

    def testFindStart2(self):
        self.service.setFindString("^.")
        self.findAll([(0,0), (7,1), (14,8), (21,15), (28,22), (43,29), (49,44), (-1,50)])

    def testFindStart3(self):
        self.service.setFindString("^")
        self.findAll([(0,0), (7,0), (14,7), (21,14), (28,21), (43,28), (49,43), (-1,49)])

    def testFindEnd1(self):
        self.service.setFindString("ne [0-9]$")
        self.findAll([(2,0), (9,6), (23,13), (-1,27)])

    def testFindEnd2(self):
        self.service.setFindString(".$")
        self.findAll([(5,0), (12,6), (19,13), (26,20), (41,27), (47,42), (54,48), (-1,55)])

    def testFindEnd3(self):
        self.service.setFindString("$")
        self.findAll([(6,0), (13,6), (20,13), (27,20), (42,27), (48,42), (55,48), (-1,55)])
