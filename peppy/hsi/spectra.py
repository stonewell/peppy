# peppy Copyright (c) 2006-2009 Rob McMullen
# Licenced under the GPLv2; see http://peppy.flipturn.org for more info
"""Convenience classes for managing individual spectra.

This class supports reading HSI data cubes (that are stored in raw,
uncompressed formats) using memory mapped file access.
"""

import os, sys, re
from cStringIO import StringIO

import numpy
import utils

from peppy.debug import *
import peppy.hsi.common as HSI
import peppy.hsi.ENVI as ENVI


class Spectra(debugmixin):
    """Class to store and manipulate spectra.

    """
    
    def __init__(self):
        self.name = None
        self.wavelengths = []
        self.bbl = []
        self.fwhm = []
        self.values = []
        self.scale = 1000
    
    def __str__(self):
        return "Spectra %s: %d entries, %d wavelengths" % (self.name, len(self.values), len(self.wavelengths))
    
    @classmethod
    def getSpectraFromCube(cls, cube, line, sample):
        s = cls()
        s.name = "%s@%d,%d" % (str(cube.url), line, sample)
        s.wavelengths = cube.wavelengths[:]
        s.values = cube.getSpectra(line, sample)
        s.fwhm = cube.fwhm[:]
        s.bbl = cube.bbl[:]
        return s
    
    @classmethod
    def getSpectraFromSpectralLibrary(cls, cube, scale=1000):
        spectras = []
        names = cube.spectra_names
        for i in range(cube.samples):
            s = cls()
            try:
                s.name = names[i]
            except:
                s.name = "spectra#%d" % (i + 1)
            s.wavelengths = cube.wavelengths[:]
            s.values = cube.getSpectra(0, i)
            s.fwhm = cube.fwhm[:]
            s.bbl = cube.bbl[:]
            s.scale = scale
            spectras.append(s)
        return spectras
    
    @classmethod
    def loadSpectraFromSpectralLibrary(cls, url, scale=1000):
        header = HSI.HyperspectralFileFormat.load(url)
        cls.dprint(header)
        cube = header.getCube()
        return cls.getSpectraFromSpectralLibrary(cube, scale)

