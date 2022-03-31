# peppy Copyright (c) 2006-2010 Rob McMullen
# Licenced under the GPLv2; see http://peppy.flipturn.org for more info
"""Synthetic cubes made from subsets of other cubes

This wrapper allows datasets to be created from subsets of other cubes, so that
to the hyperspectral code it appears to be a new dataset.
"""

import os,os.path,sys,re,struct,stat
from cStringIO import StringIO

import peppy.hsi.common as HSI
import peppy.vfs as vfs
from peppy.debug import *
import numpy


class SubDataset(HSI.MetadataMixin):
    """Synthetic dataset representing a subset of another dataset
    """
    format_id="SubDataset"
    format_name="SubDataset"

    def __init__(self, cube):
        self.cube = cube
        
    def __str__(self):
        fs=StringIO()
        fs.write("Subset of cube %s" % self.cube)
        return fs.getvalue()

    @classmethod
    def identify(cls, url):
        return url.scheme == 'dataset'

    def save(self, url=None):
        if url:
            dprint("Save not implemented yet!\n")

    def getCube(self, filename=None, index=0, progress=None, options=None):
        self.dprint(filename)
        return self.cube

    def write(self,fh):
        pass


class SubCubeReader(HSI.CubeReader):
    def __init__(self, parent):
        HSI.CubeReader.__init__(self)
        self.parent = parent
        self.clearSubset()
    
    def clearSubset(self):
        self.l1 = 0
        self.l2 = self.parent.lines
        self.s1 = 0
        self.s2 = self.parent.samples
        self.b1 = 0
        self.b2 = self.parent.bands
    
    def markSubset(self, l1, l2, s1, s2, b1, b2):
        self.clearSubset()
        if l1 >= 0:
            self.l1 = l1
        if l2 >= 0:
            self.l2 = l2
        if s1 >= 0:
            self.s1 = s1
        if s2 >= 0:
            self.s2 = s2
        if b1 >= 0:
            self.b1 = b1
        if b2 >= 0:
            self.b2 = b2

    def getRaw(self):
        """Return the raw numpy array"""
        parent_io = self.parent.cube_io
        interleave = parent_io.getInterleave()
        raw = parent_io.getRaw()
        if interleave == 'bip':
            raw = raw[self.l1:self.l2, self.s1:self.s2, self.b1:self.b2]
        elif interleave == 'bil':
            raw = raw[self.l1:self.l2, self.b1:self.b2, self.s1:self.s2]
        elif interleave == 'bsq':
            raw = raw[self.b1:self.b2, self.l1:self.l2, self.s1:self.s2]
        else:
            raise RuntimeError("Parent cube %s not memory mapped." % str(self.parent.url))
        return raw
    
    def getPixel(self, line, sample, band):
        """Get an individual pixel at the specified line, sample, & band"""
        return self.parent.getPixel(self.l1 + line, self.s1 + sample, self.b1 + band)

    def getBandRaw(self, band, use_progress=False):
        """Get the slice of the data array (lines x samples) at the
        specified band.  This points to the actual in-memory array."""
        s=self.parent.getBandRaw(self.b1 + band)[self.l1:self.l2, self.s1:self.s2]
        return s

    def getFocalPlaneRaw(self, line, use_progress=False):
        """Get the slice of the data array (bands x samples) at the specified
        line, which corresponds to a view of the data as the focal plane would
        see it.  This points to the actual in-memory array.
        """
        s=self.parent.getFocalPlaneRaw(self.l1 + line)[self.b1:self.b2, self.s1:self.s2]
        return s

    def getFocalPlaneDepthRaw(self, sample, band):
        """Get the slice of the data array through the cube at the specified
        sample and band.  This points to the actual in-memory array.
        """
        s=self.parent.getFocalPlaneDepthRaw(self.s1 + sample, self.b1 + band)[self.l1:self.l2]
        return s

    def getSpectraRaw(self,line,sample):
        """Get the spectra at the given pixel.  Calculate the extrema
        as we go along."""
        spectra=self.parent.getSpectraRaw(self.l1 + line, self.s1 + sample)[self.b1:self.b2]
        return spectra

    def getLineOfSpectraCopy(self,line):
        """Get the all the spectra along the given line.  Calculate
        the extrema as we go along."""
        spectra=self.parent.getLineOfSpectraCopy(self.l1 + line)[self.s1:self.s2, self.b1:self.b2]
        return spectra

    def locationToFlat(self, line, sample, band):
        return -1


class SubCube(HSI.Cube):
    def __init__(self, parent=None):
        HSI.Cube.__init__(self)
        self.setParent(parent)

    def __str__(self):
        current = HSI.Cube.__str__(self)
        parent = str(self.parent)
        return "%s%s--subset of %s" % (current, os.linesep, parent)
        
    def setParent(self, parent):
        self.parent = parent
        #self.parent.progress = None
        self.clearSubset()

        # date/time metadata
        self.imaging_date = parent.imaging_date
        self.file_date = parent.file_date

        self.interleave = parent.interleave
        self.byte_order = parent.byte_order
        self.data_bytes = 0 # will be calculated when subset is defined
        self.data_type = parent.data_type

        # wavelength units: 'nm' for nanometers, 'um' for micrometers,
        # None for unknown
        self.wavelength_units = parent.wavelength_units

        self.description = parent.description

        self.rgbbands=[0]
        
        self.cube_io = SubCubeReader(parent)
        
    def open(self, url=None):
        pass

    def save(self,filename=None):
        if filename:
            self.setURL(filename)

        if self.url:
            pass

    def clearSubset(self):
        self.lines = self.parent.lines
        self.samples = self.parent.samples
        self.bands = self.parent.bands
        self.data_type = None
        self.data_bytes = 0
        self.byte_order = HSI.nativeByteOrder
        
        self.wavelengths = self.parent.wavelengths[:]
        self.bbl = self.parent.bbl[:]
        self.fwhm = self.parent.fwhm[:]
        self.band_names = self.parent.band_names[:]

    def subset(self, l1=-1, l2=-1, s1=-1, s2=-1, b1=-1, b2=-1):
        """Subset the parent cube by line, sample, and band.
        
        Any of the entries may be -1 indicating that the original value from
        the full cube should be used.
        """
        self.cube_io.markSubset(l1, l2, s1, s2, b1, b2)
        self.lines = self.cube_io.l2 - self.cube_io.l1
        self.samples = self.cube_io.s2 - self.cube_io.s1
        self.bands = self.cube_io.b2 - self.cube_io.b1
        
        self.initializeSizes()
        
        b1 = self.cube_io.b1
        b2 = self.cube_io.b2
        self.wavelengths = self.parent.wavelengths[b1:b2]
        self.bbl = self.parent.bbl[b1:b2]
        self.fwhm = self.parent.fwhm[b1:b2]
        self.band_names = self.parent.band_names[b1:b2]
        
        self.url = "%dx%dx%d subset of %s" % (self.samples, self.lines, self.bands, str(self.parent.url))


HSI.HyperspectralFileFormat.addDefaultHandler(SubDataset)
