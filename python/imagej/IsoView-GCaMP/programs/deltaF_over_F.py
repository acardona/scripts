from __future__ import with_statement
import sys, os, csv
sys.path.append("/home/albert/lab/scripts/python/imagej/IsoView-GCaMP/")
from lib.io import readN5
from lib.dogpeaks import createDoG
from lib.synthetic import virtualPointsRAI
from lib.ui import showStack, wrap, showAsComposite
from lib.nuclei import findPeaks, mergePeaks, filterNuclei, findNucleiByMaxProjection
from net.imglib2.util import Intervals
from net.imglib2.view import Views
from ij import IJ
from net.imglib2.img.display.imagej import ImageJFunctions as IL
from net.imglib2.roi.geom.real import ClosedWritableSphere
from net.imglib2.roi import Masks, Regions
from itertools import imap

srcDir = "/home/albert/shares/cardonalab/Albert/2017-05-10_1018/deconvolved/"
n5dir = os.path.join(srcDir, "n5")
dataset_name = "2017-5-10_1018_0-399_X203_Y155_Z65"

# Load entire 4D IsoView deconvolved and registered data set
img4D = readN5(n5dir, dataset_name)

# Split CM00+CM01 (odd) from CM02+CM03 (even) into two series
img4Da = Views.subsample(img4D,
                         [1, 1, 1, 2]) # step
img4Db = Views.subsample(Views.interval(img4D, [0, 0, 0, 1], Intervals.maxAsLongArray(img4D)),
                         [1, 1, 1, 2]) # step

#showStack(img4Da, title="CM00+CM01 registered+deconvolved")
#showStack(img4Db, title="CM02+CM03 registered+deconvolved")

calibration = [1.0, 1.0, 1.0]
somaDiameter = 8 * calibration[0]

params = {
 "frames": 5, # number of time frames to average, 5 is equivalent to 3.75 seconds: 0.75 * 5
 "calibration": calibration, # Deconvolved images have isotropic calibration
 "somaDiameter": somaDiameter, # in pixels
 "minPeakValue": 50, # determined by hand: the bright peaks
 "sigmaSmaller": somaDiameter / 4.0, # in calibrated units: 1/4 soma
 "sigmaLarger": somaDiameter / 2.0,  # in calibrated units: 1/2 soma
 "searchRadius": somaDiameter / 3.0,
 "min_count": 20,
}

# For testing: only first 5 timepoints, 3 frames
#min_count = 2
#frames = 5
#img4Da = Views.interval(img4Da, FinalInterval([img4Da.dimension(0), img4Da.dimension(1), img4Da.dimension(2), 5]))


"""
# Could work, but would need rewriting to use a graph approach,
# linking together peaks within less than e.g. 1/3 of a soma diameter
# from each other, and then applying connected components to discover
# the clusters--with each cluster being a possible soma--,
# and then filtering out clusters whose maximum diameter (maximum
# distance between any pair of peaks) is larger than a soma diameter.
# Not yet implemented, may be worth trying eventually.
peaks = findPeaks(img4Da, params)
mergedPeaks = mergePeaks(peaks, params)
nuclei = filterNuclei(mergedPeaks, params)

# Show as a 3D volume with spheres
spheresRAI = virtualPointsRAI(nuclei, somaDiameter / 2.0, Views.hyperSlice(img4D, 3, 1))
imp = showStack(spheresRAI, title="nuclei (min_count=%i)" % params["min_count"])
"""


# Easier: use maximum intensity projection over time

# Using a ready-made max projection for testing
impMax = IJ.getImage()
img3D = IL.wrap(impMax)

peaks, spheresRAI, impSpheres = findNucleiByMaxProjection(img4Da, params, img3D=img3D)
comp = showAsComposite([impMax, impSpheres])

# Measure intensity over time, for every peak
# by averaging the signal within a radius of each peak.

csv_fluorescence = os.path.join(srcDir, "fluorescence.csv")

measurement_radius = somaDiameter / 3.0
spheres = [ClosedWritableSphere([peak.getFloatPosition(d) for d in xrange(3)], measurement_radius) for peak in peaks]
insides = [Regions.iterable(
             Views.interval(
               Views.raster(Masks.toRealRandomAccessible(sphere)),
               Intervals.largestContainedInterval(sphere)))
           for sphere in spheres]

def get(t):
  return t.get()

count = float(Regions.countTrue(insides[0])) # same for all

with open(csv_fluorescence, 'w') as csvfile:
  w = csv.writer(csvfile, delimiter=",", quotechar='"', quoting=csv.QUOTE_NONNUMERIC)
  # Header: with peak coordinates
  w.writerow(["timepoint"] + ["%.2f::%.2f::%.2f" % tuple(peak.getFloatPosition(d) for d in xrange(3)) for peak in peaks])
  # Each time point
  for t in xrange(img4Da.dimension(3)):
    img3D = Views.hyperSlice(img4D, 3, t)
    w.writerow([t] + [sum(imap(get, Regions.sample(inside, img3D))) / count for inside in insides])

    

    




