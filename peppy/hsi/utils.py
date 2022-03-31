# peppy Copyright (c) 2006-2010 Rob McMullen
# Licenced under the GPLv2; see http://peppy.flipturn.org for more info
"""HSI Utilities.

These are utility functions that are in common use by the
hyperspectral classes.  These functions shouldn't have external
dependencies on any other classes in the hsi package.
"""

import os, sys, math, time, threading
from cStringIO import StringIO

from peppy.debug import *

import numpy

import cube as HSI

# number of meters per unit
units_scale={
'nm':1.0e-9,
'um':1.0e-6,
'mm':1.0e-3,
'm':1.0,
}

def normalizeUnits(txt):
    """Return standard units label for the given label.

    Given a text string, return the standard (usually SI)
    abbreviation.  Currently just supports lengths.

    Returns None if label not known.
    """
    units=txt.lower()
    if units[0:4]=='nano' or units[0:2]=='nm':
        return 'nm'
    elif units[0:5]=='micro' or units[0:2]=='um':
        return 'um'
    return None


def getRangeIntersection(x1, x2, bbl1=None):
    """Computes the common range of sampling points.

    Given two lists of sampling points, determine the subset of the
    range of the first set such that the endpoints are guaranteed to
    be within the range of the second set of sampling points.

    @param x1: list of sampling points to subset
    @param x2: list of sampling points of other set
    @param bbl1: optional bad band list of x1 (0 = bad, 1 = good)

    @returns: tuple (index1, index2) specifying indexes that give the
    range within 1st sampling set.  Note the indexes are in the python
    idiom where index2 is actually one beyond the last good value so
    you can do a slice like x1[index1:index2] and get the actual list.
    """
    i1start = 0
    i1end = len(x1)
    while i1start < i1end and x1[i1start] < x2[0]:
        i1start += 1
    while i1start < i1end and x1[i1end-1] > x2[-1]:
        i1end -= 1
    if bbl1 is not None:
        while i1start < i1end and bbl1[i1start] == 0:
            i1start += 1
        while i1start < i1end and bbl1[i1end-1] == 0:
            i1end -= 1
    return (i1start, i1end)


def resample(x1, y1, x2, y2, bbl1=None):
    """Resample using linear interpolation.

    Given two sets of data, resample the second set to match the first
    set's x values and range.

    @returns tuple (sampling, data1, data2)
    """
    xout = []
    y1out = []
    y2out = []

    # only operate on the intersection of the ranges
    i1start, i1end = getRangeIntersection(x1, x2, bbl1)

    # find first value of 2nd set less than intersection
    i2 = 0
    while i2<len(x2)-1 and x2[i2+1] < x1[i1start]:
        i2 += 1

    x2left = x2[i2]
    x2right = x2[i2+1]
    for i in range(i1start, i1end):
        xinterp = x1[i]
        while xinterp > x2right:
            x2left = x2right
            i2 += 1
            x2right = x2[i2+1]
        yinterp = (xinterp - x2left)/(x2right - x2left)*(y2[i2+1] - y2[i2]) + y2[i2]
        xout.append(xinterp)
        y1out.append(y1[i])
        y2out.append(yinterp)
    return (xout, y1out, y2out)
        
def resampleSingle(x1, x2, y2, bbl1=None):
    """Resample using linear interpolation.

    Given a set of x, y values and a new set of x values, resample the y values
    onto the new domain.

    @returns new y values
    """
    y1 = []

    # only operate on the intersection of the ranges
    i1start, i1end = getRangeIntersection(x1, x2, bbl1)

    # find first value of 2nd set less than intersection
    i2 = 0
    while i2<len(x2)-1 and x2[i2+1] < x1[i1start]:
        i2 += 1

    x2left = x2[i2]
    x2right = x2[i2+1]
    for i in range(0, i1start):
        y1.append(y2[i2])
    for i in range(i1start, i1end):
        xinterp = x1[i]
        while xinterp > x2right:
            x2left = x2right
            i2 += 1
            x2right = x2[i2+1]
        yinterp = (xinterp - x2left)/(x2right - x2left)*(y2[i2+1] - y2[i2]) + y2[i2]
        y1.append(yinterp)
    for i in range(i1end, len(x1)):
        y2.append(y2[i2])
    return y1
        
def spectralAngle(lam1, spectra1, lam2, spectra2, bbl=None):
    """Determine spectral angle between two vectors.

    Computes the spectral angle between the common range of two
    vectors, resampling the second one to conform to the first's
    sampling points if necessary.

    @returns angle in degrees
    """
    new2 = []
    lam, s1, s2 = resample(lam1, spectra1, lam2, spectra2, bbl)
    #print "resampled: lam=%s\ns1=%s\ns2=%s" % (lam, s1, s2)
    
    tot = 0.0
    bot1 = 0.0
    bot2 = 0.0
    top = 0.0
    for i in range(len(lam)):
        y1 = s1[i]
        y2 = s2[i]
        bot1 += y1*y1
        bot2 += y2*y2
        top += y1*y2
    bot = math.sqrt(bot1) * math.sqrt(bot2)
    if bot != 0.0:
        tot = top/bot
    if tot > 1.0:
        tot = 1.0
    alpha = math.acos(tot)*180.0/math.pi
    print "spectral angle=%f: bot=%f top=%f tot=%f" % (alpha, bot, top, tot)

    return alpha

def euclideanDistance(lam1, spectra1, lam2, spectra2, bbl=None):
    """Determine Euclidean distance between two vectors.

    Compute Euclidean distance between the common range of two
    vectors, resampling the second one to conform to the first's
    sampling points.

    @returns distance (units are ???)
    """
    new2 = []
    lam, s1, s2 = resample(lam1, spectra1, lam2, spectra2, bbl)
    #print "resampled: lam=%s\ns1=%s\ns2=%s" % (lam, s1, s2)
    
    dist = 0.0
    for i in range(len(lam)):
        delta = s1[i] - s2[i]
        dist += delta*delta
    dist = math.sqrt(dist)
    print "euclidean distance = %f" % dist
    return dist


def bandPixelize(band, scale):
    """Increase the dimensions of the band by turning each pixel into a scale x
    scale block of pixels.
    
    @param band: 2D numpy array in line x sample format, e.g.  as returned from
    Cube.getBandRaw or similar 
    
    @param scale: scale factor for both pixel dimensions
    
    @return: copy of band scaled to the new dimensions
    """
    return numpy.repeat(numpy.repeat(band, scale, axis=1), scale, axis=0)


def bandReduceSampling(band, scale):
    """Reduce the size of the band by dividing the current dimensions by the
    scale factor.
    
    @param band: 2D numpy array in line x sample format, e.g.  as returned from
    Cube.getBandRaw or similar 
    
    @param scale: scale factor for both pixel dimensions
    
    @return: copy of band scaled to the new dimensions
    """
    # This is a slow implementation of a pixel resampling function
    # that simply averages the pixels in a moving square of [scale
    # x scale] pixels in the source image.  I couldn't find a quick
    # resampling/interpolation/decimation function in numpy.
    output = numpy.empty((band.shape[0] / scale, band.shape[1] / scale), dtype=band.dtype)
    for sample in range(0, output.shape[1]):
        for line in range(0, output.shape[0]):
            s1 = sample * scale
            s2 = s1 + scale
            if s2 > band.shape[1]:
                s2 = band.shape[1]
            l1 = line * scale
            l2 = l1 + scale
            if l2 > band.shape[0]:
                l2 = band.shape[0]
            avg = numpy.average(band[l1:l2, s1:s2])
            output[line, sample] = avg
    return output


class Histogram(object):
    def __init__(self,cube,nbins=500,bbl=None):
        self.cube=cube
        self.width=cube.bands
        self.nbins=nbins
        self.pixelsperband=cube.samples*cube.lines

        # NOTE!  This type must remain numpy.int32, or otherwise the C code
        # must be changed.
        self.data=numpy.zeros((self.width,self.nbins),dtype=numpy.int32)
        self.maxvalue=numpy.zeros((self.width,),dtype=numpy.int32)
        self.maxdiff=numpy.zeros((self.width,),dtype=numpy.int32)

        self.accumulation=None

        self.thresholds=[50,100,200,500]

        if bbl:
            self.bbl=bbl
        else:
            self.bbl=self.cube.getBadBandList()
        # print "Histogram: self.bbl=%s" % self.bbl

    def info(self):
        lastbin=[]
        for band in range(self.width):
            if not self.bbl[band]:
                lastbin.append('bad')
                self.maxdiff[band]=0
            else:
                last=0
                for bin in range(0,self.nbins):
                    if self.data[band][bin]>0:
                        last=bin
                lastbin.append(last)
            if self.maxvalue[band]==0:
                self.maxvalue[band]=1
                
        print "last bin with non-zero value:"
        print lastbin
        print "max values in band:"
        print self.maxvalue
        print "max differences in each band:"
        print self.maxdiff
        print "max percentage difference:"
        print numpy.array2string((self.maxdiff*1000/self.maxvalue)/10.0,
                        precision=2,suppress_small=1)

    def calcAccumulation(self,numcolors=20):
        self.info()
        
        self.accumulation=numpy.zeros((self.width,numcolors),dtype=numpy.int32)

        temp=numpy.zeros((self.nbins,),dtype=numpy.int32)

        validpixels=0
        pixelsbelowthreshold=[0]*len(self.thresholds)

        for band in range(self.width):
            if not self.bbl[band]: continue # only operate on valid bands
            
            accum=self.pixelsperband
            validpixels+=accum

            # create temp, a monotonically decreasing list where the
            # first index contains all the pixels, and each subsequent
            # bin subtracts the histogram value for that bin
            for bin in range(0,self.nbins):
                temp[bin]=accum
                num=self.data[band][bin]
                for i in range(len(self.thresholds)):
                    if bin<=self.thresholds[i]:
                        pixelsbelowthreshold[i]+=num
                accum-=num
            
            # print temp

            # Now turn the temp list into an color index based array
            # (so that it can eventually be plotted) by downsampling
            # the ranges of numbers into buckets.  So, if there are 20
            # colors to be plotted and there are 1000 pixels per band,
            # then accumulations between 1000 & 951 get index 0, 950 &
            # 901 get index 1, etc.
            lastheight=numcolors-1
            currentheight=0
            lastindex=0
            for bin in range(self.nbins):
                index=int(float(((self.pixelsperband-temp[bin])*numcolors)/self.pixelsperband))
                if index>=numcolors: index=numcolors-1
                
                #if index>currentheight:
                
                self.accumulation[band][index]=bin

            height=0
            for index in range(numcolors):
                curr=self.accumulation[band][index]
                if curr>0:
                    self.accumulation[band][index]-=height
                    height=curr

        print "Total pixels from good bands=%d" % validpixels
##        if (hist.isTemperature()) {
##            double gain=hist.getTemperatureGain();
##            threshold = new int[] {10,20,50,100,200,500};
            
##            for (int i=0; i<threshold.length; i++) {
##                System.out.printf("  Threshold %.3f Kelvin: valid=%d  percentage=%f%n",
##                    (threshold[i]/10000.0*gain),pixelsBelowThreshold[i],
##                    (pixelsBelowThreshold[i]*100.0/totalPixelsInValidBands));
##            }
##        }
        for i in range(len(self.thresholds)):
            print "  Threshold %f reflectance units: valid=%d  percentage=%f" % ((self.thresholds[i]*1.0),pixelsbelowthreshold[i],(pixelsbelowthreshold[i]*100.0/validpixels))


class CubeCompare(debugmixin):
    """Compare two HSI cubes for differences.
    
    This class produces a single chart that attempts to show the differences
    between two hyperspectral cubes.  I found the need to have some way to
    quickly check how an algorithm processed a data cube as the algorithm
    evolved, and to do this I was comparing a "known good" data cube to the
    just-processed cube.  It was time consuming because I'd have to load it up
    into a viewer and compare bands manually.
    
    I invented this histogram approach to produce a one-page chart that
    attempts to show how different two data cubes are.  It works on a pixel-
    by-pixel basis on each band, measuring the difference in magnitude is at
    the same (sample, line, band) location between the two cubes.  All these
    measurements are placed in a histogram, which reduces the 4 dimensional
    problem (sample, line, band, value) into 3 dimensions (count, band, value)
    that can be shown on a count vs band plot where the value at each (count,
    band) pair is the number of pixels in that band that have 'count' as the
    difference in magnitude.
    
    To make it even easier to see, the plot is changed to an accumulation where
    the value at each (count, band) pair is the percentage of pixels in the
    image that are less different than that magnitude.  A good comparison will
    have small values for 'count', so all the values will be squashed down
    near the X axis, and at constant band, the 'percentage more different'
    will monotonically decrease.
    
    The simplistic algorithm to generate a histogram is:
    
    for each band index:
        get band1
        get band2
        for each sample index:
            for each line index:
                val = band1[samp,line] - band2[samp,line]
                bin = abs(val)
                histogram[band][bin] += 1
    """
    def __init__(self, c1, c2, line_offset=0):
        """Create the comparitor instance
        
        @param offset: a tuple containing the spatial offset of the smaller
        cube inside the larger cube as (line_offset, sample_offset)
        """
        # Set up the cube attributes so cube1 holds the bigger cube
        if c1.lines >= c2.lines and c1.samples >= c2.samples and c1.bands == c2.bands:
            self.cube1 = c1
            self.cube2 = c2
        elif c2.lines > c1.lines and c2.samples > c1.samples and c1.bands == c2.bands:
            self.cube1 = c2
            self.cube2 = c1
        else:
            raise ValueError("Can't determine which cube is supposed to be the subset of the other: if cubes aren't the same size, one cube must be a spatial subset of the other and both must have the same number of bands")
            
        # common dimensions are from the smaller cube
        self.lines = self.cube2.lines
        self.bands = self.cube2.bands
        self.samples = self.cube2.samples
        
        if line_offset > 0:
            self.line_offset = line_offset
        else:
            self.line_offset = 0
        
        # Parameters common to both cubes
        self.bbl = self.cube1.getBadBandList(self.cube2)
        
        # The data type that can hold both types without losing precision
        self.dtype = numpy.find_common_type([self.cube1.data_type, self.cube2.data_type], [])
        
        self.histogram=None
        self.hashPrintCount=100000
        
    def isBILBIP(self):
        """Test to see if both cubes are BIL or BIP.
        
        They don't need to be the same, but they both must either be BIP or BIL.
        """
        i1 = self.cube1.interleave.lower()
        i2 = self.cube2.interleave.lower()
        return i1 in ['bip', 'bil'] and i2 in ['bip', 'bil']
    
    def iterBILBIP(self):
        """Iterate by line returning the same focal plane in each cube
        
        @return: line number, focal plane image 1, focal plane image 2
        """
        for i in range(self.lines):
            plane1 = self.cube1.getFocalPlaneRaw(i + self.line_offset)
            plane2 = self.cube2.getFocalPlaneRaw(i)
            yield i, plane1, plane2
    
    def getFocalPlaneBadBandMask(self):
        """Calculate the bad band mask for focal plane data
        
        The band band mask is array of (bands, samples) used to multiply
        against the retrieved focal planes that results in zeroing out all the
        data in the bad bands.
        """
        bblmask = numpy.array(self.bbl).repeat(self.samples).reshape(self.bands,self.samples)
        self.dprint(bblmask)
        self.dprint(bblmask.shape)
        return bblmask

    def getHistogramByBand(self,nbins=500):
        """Generate a histogram using bands
        
        Fast for BSQ cubes, slow for BIL, and extremely slow for BIP.  The
        most straight-forward algorithm, but is slow unless the cubes are in
        BSQ format.  Differences the corresponding bands, runs a histogram on
        them, and puts the results into the instance histogram.
        """
        self.histogram=Histogram(self.cube1,nbins,self.bbl)
        h=self.histogram.data

        for i in range(self.cube1.bands):
            band1=self.cube1.getBand(i)
            band2=self.cube2.getBand(i)
            count=(self.samples*self.lines)
            band=abs(band1-band2)
            mx=band.max()
            mn=band.min()
            self.dprint("band %d: local min/max=(%d,%d) " % (i,mn,mx))
            counts, bins = numpy.histogram(band, bins=nbins, range=(0, nbins))
            h[i,:] = counts
        self.dprint(h)
        return self.histogram
    
    def getHistogramByFocalPlane(self, iter, nbins=500):
        """Generate a histogram using focal planes
        
        Fast for BIP and BIL, slow for BSQ.  This is a slightly more
        complicated algorithm that uses focal planes to create the histogram.
        Because there's an extra python loop inside this method, the
        theoretical speed of this method is slower than L{getHistogramByBand}.
        However, because BIL and BIP cubes are structured to read focal
        plane images very quickly, this method is many times faster than
        L{getHistogramByBand} when both cubes are BIL or BIP.  If one cube is
        BSQ, it's probably faster to use L{getHistogramByBand} because more
        work is done by numpy.
        """
        self.histogram = Histogram(self.cube1,nbins,self.bbl)
        h = self.histogram.data

        bandrange = range(self.bands)
        for i, plane1, plane2 in iter:
            plane = abs(plane1 - plane2)
            
            # Need to accumulate by bands, so loop through each band in the
            # focal plane image (bands x samples) and calculate the histogram
            # of those samples.  The small histogram is then accumulated into
            # the total histogram at the band.
            for band in bandrange:
                counts, bins = numpy.histogram(plane[band], bins=nbins, range=(0, nbins))
                h[band,:] += counts

            self.dprint("line %d" % (i))
        self.dprint(h)
        return self.histogram
    
    def getHistogram(self, nbins=500):
        """Generate a histogram.
        
        The driver method for generating a histogram.  Selects the best
        histogram calculation method as appropriate for both cubes.
        """
        if self.isBILBIP():
            iter = self.iterBILBIP()
            return self.getHistogramByFocalPlane(iter, nbins)
        return self.getHistogramByBand(nbins)
    
    def getHeatMapByBand(self,nbins=500):
        """Generate a heat map using bands
        
        Fast for BSQ cubes, slow for BIL, and extremely slow for BIP.  The
        most straight-forward algorithm, but is slow unless the cubes are in
        BSQ format.  Differences the corresponding bands, runs a histogram on
        them, and puts the results into the instance histogram.
        """
        self.heatmap = HSI.createCube('bsq', self.lines, self.samples, 1, self.dtype)
        data = self.heatmap.getBandRaw(0)

        for i in range(self.bands):
            if self.bbl[i]:
                band1 = self.cube1.getBand(i)
                band2 = self.cube2.getBand(i)
                band = abs(band1-band2)
                data += band
        self.dprint(data)
        return self.heatmap
    
    def getHeatMapByFocalPlane(self, iter):
        """Generate a heat map using focal planes
        
        Fast for BIP and BIL, slow for BSQ.  This is a slightly more
        complicated algorithm that uses focal planes to create the histogram.
        Because there's an extra python loop inside this method, the
        theoretical speed of this method is slower than L{getHistogramByBand}.
        However, because BIL and BIP cubes are structured to read focal
        plane images very quickly, this method is many times faster than
        L{getHistogramByBand} when both cubes are BIL or BIP.  If one cube is
        BSQ, it's probably faster to use L{getHistogramByBand} because more
        work is done by numpy.
        """
        self.heatmap = HSI.createCube('bsq', self.lines, self.samples, 1, self.dtype)
        data = self.heatmap.getBandRaw(0)
        bblmask = self.getFocalPlaneBadBandMask()

        for i, plane1, plane2 in iter:
            p1 = plane1 * bblmask
            p2 = plane2 * bblmask
            line = numpy.add.reduce(abs(p1 - p2), axis=0)
            self.dprint("%s %s" % (line.shape, line))
            data[i,:] = line
        self.dprint(data)
        return self.heatmap
    
    def getHeatMap(self):
        """Generate a heat map
        
        The driver method -- selects the fastest calculation method based
        on the interleave of both cubes.
        """
        if self.isBILBIP():
            iter = self.iterBILBIP()
            return self.getHeatMapByFocalPlane(iter)
        return self.getHeatMapByBand()
    
    def getDifferenceByFocalPlane(self, iter):
        """Difference the cubes using focal planes
        
        Fast for BIP and BIL, slow for BSQ.
        """
        self.difference = HSI.createCube('bil', self.lines, self.samples, self.bands, self.dtype)
        bblmask = self.getFocalPlaneBadBandMask()

        for i, plane1, plane2 in iter:
            p1 = plane1 * bblmask
            p2 = plane2 * bblmask
            diff = p1 - p2
            plane = self.difference.getFocalPlaneRaw(i)
            plane[:,:] = diff
            self.dprint("%s %s" % (plane.shape, plane))
        return self.difference
    
    def getDifferenceByBand(self,nbins=500):
        """Difference two cubes using bands
        
        Fast for BSQ cubes, slow for BIL, and extremely slow for BIP.  The most
        straight-forward algorithm, but is slow unless the cubes are in BSQ
        format.  Differences two cubes on a band-by-band basis and puts the
        results in a new cube.
        """
        self.difference = HSI.createCube('bsq', self.lines, self.samples, self.bands, self.dtype)

        for i in range(self.cube1.bands):
            if self.bbl[i]:
                band = self.difference.getBandRaw(i)
                band1 = self.cube1.getBand(i)
                band2 = self.cube2.getBand(i)
                band[:,:] = band1 - band2
                self.dprint(band)
        return self.difference
    
    def getDifference(self):
        """Generate a cube containing the difference between the two cubes
        
        The driver method -- selects the fastest calculation method based
        on the interleave of both cubes.
        """
        if self.isBILBIP():
            iter = self.iterBILBIP()
            self.getDifferenceByFocalPlane(iter)
        else:
            self.getDifferenceByBand()
        self.difference.bbl = self.bbl[:]
        return self.difference
    
    def getEuclideanDistanceByFocalPlane(self, iter, updater=None):
        """Calculate the euclidean distance for every pixel in two cubes using
        focal planes
        
        Fast for BIP and BIL, slow for BSQ.
        """
        euclidean = HSI.createCube('bsq', self.lines, self.samples, 1, numpy.float32)
        data = euclidean.getBandRaw(0)
        bblmask = self.getFocalPlaneBadBandMask()

        for i, plane1, plane2 in iter:
            if updater:
                updater.updateStatus(i, self.lines, "Calculating Euclidean Distance")
            p1 = plane1 * bblmask
            p2 = plane2 * bblmask
            plane = p1 - p2
            line = numpy.sqrt(numpy.add.reduce(plane * plane, axis=0))
            self.dprint("%s %s" % (line.shape, line))
            data[i,:] = line
        self.dprint(data)
        return euclidean
    
    def getEuclideanDistanceByBand(self, nbins=500, updater=None):
        """Calculate the euclidean distance for every pixel in two cubes using
        bands
        
        Fast for BSQ cubes, slow for BIL, and extremely slow for BIP.
        """
        euclidean = HSI.createCube('bsq', self.lines, self.samples, 1, numpy.float32)
        data = euclidean.getBandRaw(0)
        
        working = numpy.zeros((self.lines, self.samples), dtype=numpy.float32)
        for i in range(self.bands):
            if updater:
                updater.updateStatus(i, self.bands, "Calculating Euclidean Distance")
            if self.bbl[i]:
                band1 = self.cube1.getBand(i)
                band2 = self.cube2.getBand(i)
                band = band1 - band2
                working += numpy.square(band)
        
        data = numpy.sqrt(working)
        self.dprint(data)
        return euclidean
    
    def getEuclideanDistance(self, updater=None):
        """Generate a cube containing the euclidean distance between the two cubes
        
        The driver method -- selects the fastest calculation method based
        on the interleave of both cubes.
        """
        if self.isBILBIP():
            iter = self.iterBILBIP()
            cube = self.getEuclideanDistanceByFocalPlane(iter, updater)
        else:
            cube = self.getEuclideanDistanceByBand(updater)
        self.calcStatistics(cube)
        self.euclidean = cube
        return self.euclidean

    def getSpectralAngleByFocalPlane(self, iter, updater=None):
        """Calculate the spectral angle between every pixel in two cubes using
        focal planes
        
        Fast for BIP and BIL, slow for BSQ.
        """
        sam = HSI.createCube('bsq', self.lines, self.samples, 1, numpy.float32)
        data = sam.getBandRaw(0)
        bblmask = self.getFocalPlaneBadBandMask()

        for i, plane1, plane2 in iter:
            if updater:
                updater.updateStatus(i, self.lines, "Calculating Spectral Angle")
            p1 = numpy.cast[numpy.float32](plane1 * bblmask)
            p2 = numpy.cast[numpy.float32](plane2 * bblmask)
            zerotest = numpy.add.reduce(plane1 - plane2)
            
            top = numpy.add.reduce(p1 * p2)
            bot = numpy.sqrt(numpy.add.reduce(p1 * p1)) * numpy.sqrt(numpy.add.reduce(p2 * p2))
            # the arccos may not be zero if the spectra are exactly the same due
            # to round-off error in the squaring/sqrt.  So, we add this check
            # here to force the total to 1.0 if any pixel in plane1 is exactly
            # equal to the pixel in plane 2
            tot = numpy.where(zerotest == 0.0, 1.0, top/bot)
            line = numpy.nan_to_num(numpy.arccos(tot) * (180.0 / math.pi))
            
            self.dprint("%s %s" % (line.shape, line))
            data[i,:] = line
        self.dprint(data)
        return sam
    
    def getSpectralAngleByBand(self, nbins=500, updater=None):
        """Calculate the spectral angle between every pixel in two cubes using
        bands
        
        Fast for BSQ cubes, slow for BIL, and extremely slow for BIP.
        """
        sam = HSI.createCube('bsq', self.lines, self.samples, 1, numpy.float32)
        data = sam.getBandRaw(0)
        
        top = numpy.zeros((self.lines, self.samples), dtype=numpy.float32)
        bot1 = numpy.zeros((self.lines, self.samples), dtype=numpy.float32)
        bot2 = numpy.zeros((self.lines, self.samples), dtype=numpy.float32)
        for i in range(self.bands):
            if updater:
                updater.updateStatus(i, self.bands, "Calculating Spectral Angle")
            if self.bbl[i]:
                band1 = self.cube1.getBand(i)
                band2 = self.cube2.getBand(i)
                top += band1 * band2
                bot1 += numpy.square(band1)
                bot2 += numpy.square(band2)
        
        bot = numpy.sqrt(bot1 + bot2)
        tot = top/bot
        data[:,:] = numpy.nan_to_num(numpy.arccos(tot) * (180.0 / math.pi))
        self.dprint(data)
        return sam
    
    def getSpectralAngle(self, updater=None):
        """Generate a cube containing the spectral angle between the two cubes
        
        The driver method -- selects the fastest calculation method based
        on the interleave of both cubes.
        """
        if self.isBILBIP():
            iter = self.iterBILBIP()
            sam = self.getSpectralAngleByFocalPlane(iter, updater)
        else:
            sam = self.getSpectralAngleByBand(updater)
        self.calcStatistics(sam)
        self.sam = sam
        return self.sam
    
    def calcStatistics(self, cube):
        """Calculate the min, max, mean, and std dev of the data cube
        
        """
        data = cube.getBandRaw(0)

        small = numpy.amin(data)
        big = numpy.amax(data)
        mean = numpy.mean(data)
        stddev = numpy.std(data)
        text = "min: %f\nmax: %f\nmean: %f\nstd dev: %f" % (small, big, mean, stddev)
        cube.description = text

    def getExtrema(self):
        """Really just a test function to see how long it takes to
        seek all the way through one file."""
        
        f1=self.cube1.getFlatView()
        self.dprint(f1)
        i1=0
        progress=0
        minval=100000
        maxval=0
        try:
            while True:
                val=f1[i1]
                if (val>maxval): maxval=val
                if (val<minval): minval=val
                progress+=1
                if progress>1000:
                    #print "#",
                    self.dprint("i1=%d " % (i1))
                    progress=0
                i1+=1
                    
        except IndexError:
            pass
        return (minval,maxval)
    
    def getExtremaChunk(self):
        """Really just a test function to see how long it takes to
        seek all the way through one file."""

        minval=100000
        maxval=0
        
        for i1 in range(self.cube1.bands):
            band=self.cube1.getBand(i1)
            mx=band.max()
            mn=band.min()
            if (mx>maxval): maxval=mx
            if (mn<minval): minval=mn
            self.dprint("band %d: local min/max=(%d,%d)  accumulated min/max=(%d,%d)" % (i1,mn,mx,minval,maxval))
            
        return (minval,maxval)

class ThreadedCubeCompare(threading.Thread):
    """Background file loading thread.
    
    Uses peppy.lib.threadutils.ThreadStatus to communicate with GUI thread
    """
    def __init__(self, cube1, cube2, updater):
        threading.Thread.__init__(self)
        self.comp = CubeCompare(cube1, cube2)
        self.updater = updater
        self.output = None
    
    def run(self):
        try:
            comp = self.comp
            self.updater.setNumberOfWorkItems(2)
            dist = comp.getEuclideanDistance(updater=self.updater)
            self.updater.finishedWorkItem()
            sam = comp.getSpectralAngle(updater=self.updater)
            self.updater.finishedWorkItem()
            dtype = numpy.find_common_type([dist.data_type, sam.data_type], [])
            self.output = HSI.createCubeLike(dist, 'bsq', bands=2, datatype=dtype)
            outputband = self.output.getBandRaw(0)
            source = dist.getBandRaw(0)
            outputband[:,:] = source[:,:]
            outputband = self.output.getBandRaw(1)
            source = sam.getBandRaw(0)
            outputband[:,:] = source[:,:]
            
            self.output.band_names = ['Euclidean Distance', 'Spectral Angle']
            self.output.description = "Euclidean Distance Statistics:\n%s\n\nSpectral Angle Statistics:\n%s\n" % (dist.description, sam.description)
            self.updater.reportSuccess("Completed calculations", self.output)
        except:
            import traceback
            error = traceback.format_exc()
            self.updater.reportFailure(error)

