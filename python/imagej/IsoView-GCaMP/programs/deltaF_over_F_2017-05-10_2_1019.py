from __future__ import with_statement
import sys, os, csv
sys.path.append("/groups/cardona/home/cardonaa/lab/scripts/python/imagej/IsoView-GCaMP/")
from lib.io import readN5
from lib.dogpeaks import createDoG
from lib.synthetic import virtualPointsRAI
from lib.ui import showStack, wrap, showAsComposite
from lib.nuclei import findPeaks, mergePeaks, filterNuclei, findNucleiByMaxProjection
from net.imglib2.util import Intervals, ConstantUtils
from net.imglib2.view import Views
from net.imglib2 import RealPoint
from ij import IJ
from net.imglib2.img.display.imagej import ImageJFunctions as IL
from net.imglib2.roi.geom.real import ClosedWritableSphere
from net.imglib2.roi import Masks, Regions
from itertools import imap, islice, izip
from jarray import zeros, array

baseDir = "/groups/zlatic/zlaticlab/Nadine/Raghav/analysis/2017-05-10/GCaMP6s_2_20170510_143413.corrected/"
srcDir = baseDir + "deconvolved/"
n5dir = "/groups/cardona/cardonalab/Albert/2017-05-10_2_1019/"
dataset_name = "2017-05-10_2_1019_0-399_409x509x305x800"

# Load entire 4D IsoView deconvolved and registered data set
img4D = readN5(n5dir, dataset_name)

# Remove the channel dimension which has size of 1
img4D = Views.dropSingletonDimensions(img4D)

print img4D

# A mask: only nuclei whose x,y,z coordinate has a non-zero value in the mask will be considered
mask = None

# Split CM00+CM01 (odd) from CM02+CM03 (even) into two series
series = ["CM00-CM01", "CM02-CM03"]
img4Da = Views.subsample(img4D,
                         [1, 1, 1, 2]) # step
img4Db = Views.subsample(Views.interval(img4D, [0, 0, 0, 1], Intervals.maxAsLongArray(img4D)),
                         [1, 1, 1, 2]) # step

showStack(img4Da, title="%s registered+deconvolved" % series[0])
showStack(img4Db, title="%s registered+deconvolved" % series[1])

calibration = [1.0, 1.0, 1.0]
somaDiameter = 8 * calibration[0]

# Parameters for detecting nuclei with difference of Gaussian
params = {
 "frames": 5, # number of time frames to average, 5 is equivalent to 3.75 seconds: 0.75 * 5
 "calibration": calibration, # Deconvolved images have isotropic calibration
 "somaDiameter": somaDiameter, # in pixels
 "minPeakValue": 50, # determined by hand: the bright peaks
 "sigmaSmaller": somaDiameter / 4.0, # in calibrated units: 1/4 soma
 "sigmaLarger": somaDiameter / 2.0,  # in calibrated units: 1/2 soma
 "searchRadius": somaDiameter / 3.0,
 "min_count": 20,
 "baseline_window_size": int(30 / 0.75) + 1, # 30 seconds, at 0.75 seconds per timepoint: 40 timepoints, plus 1 to make it odd
                                    # so that it will include 20 timepoints before and 20 after for the baseline calculation.
 "CM00-CM01_noise_stdDev": (3.17 + 3.20) / 2.0, # Measured inside the crop only, using two crops:
                                                # first Roi[Rectangle, x=187, y=400, width=576, height=896]
                                                # second Roi[Rectangle, x=1, y=228, width=406, height=465]
                                                # for both CM00 and CM01, so taking an "average" if that makes sense (they are close anyway)
 "CM00-CM01_noise_mean":  100, # Run a Gaussian with sigma=10 over the darfield noise image of CM00 and CM01.
                               # For both cameras, the range is then 99-101, with almost all values at 100.
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


# Simpler: given a sufficiently good registration, use maximum intensity projection over time

def measureFluorescence(series_name, img4D, mask=None):
  csv_fluorescence = os.path.join(srcDir, "%s_fluorescence.csv" % series_name)
  if not os.path.exists(csv_fluorescence):
    # Generate projection over time (the img3D) and extract peaks with difference of Gaussian using the params
    # (Will check if file for projection over time exists and just load it)
    img3D_filepath = os.path.join(srcDir, "%s_4D-to-3D_max_projection.zip" % series_name)
    img3D, peaks, spheresRAI, impSpheres = findNucleiByMaxProjection(img4D, params, img3D_filepath, show=True)
    comp = showAsComposite([wrap(img3D), impSpheres])
    # Measure intensity over time, for every peak
    # by averaging the signal within a radius of each peak.
    measurement_radius = somaDiameter / 3.0
    spheres = [ClosedWritableSphere([peak.getFloatPosition(d) for d in xrange(3)], measurement_radius) for peak in peaks]
    interval = Intervals.largestContainedInterval(spheres[0])
    insides = [Regions.iterable(
                 Views.interval(
                   Views.raster(Masks.toRealRandomAccessible(sphere)),
                   interval))
               for sphere in spheres]

    count = float(Regions.countTrue(insides[0])) # same for all
    measurements = []

    with open(csv_fluorescence, 'w') as csvfile:
      w = csv.writer(csvfile, delimiter=",", quotechar='"', quoting=csv.QUOTE_NONNUMERIC)
      # Header: with peak coordinates
      w.writerow(["timepoint"] + ["%.2f::%.2f::%.2f" % tuple(peak.getFloatPosition(d) for d in xrange(3)) for peak in peaks])
      # Each time point
      for t in xrange(img4D.dimension(3)):
        img3D = Views.hyperSlice(img4D, 3, t)
        mean_intensities = array(((sum(t.get() for t in Regions.sample(inside, img3D)) / count) for inside in insides), 'f')
        w.writerow([t] + mean_intensities.tolist())
        measurements.append(mean_intensities)

  else:
    # Parse CSV file
    with open(csv_fluorescence, 'r') as csvfile:
      reader = csv.reader(csvfile, delimiter=',', quotechar='"')
      header = reader.next()
      # Parse header, containing peak locations
      peaks = [RealPoint.wrap(map(float, h.split("::"))) for h in islice(header, 1, None)]
      # Parse rows
      measurements = [map(float, islice(row, 1, None)) for row in reader]
  
  return peaks, measurements


def computeBaselineFluorescence(measurements, window_size):
  """
  measurements: a list of lists containing, for each time point, a list of measurements
                of mean fluorescence intensity at each peak (where a peak represents a nuclei).
  window_size: the number of timepoints (i.e. indices in measurements) to use for computing
               the baseline using the mininum fluorescence value across the whole window.
               The window has the timepoint centered on it. So the first and last few timepoints
               will use at least only half a window.
               Makes sense to make window_size an odd number, so an equal amount of timepoints
               are included from before and after each timepoint.
  """
  # List of lists: one for each measurement in measurements
  baselines = []

  n_peaks = len(measurements[0]) # columns
  n_timepoints = len(measurements) # rows

  half_window_size = window_size / 2

  # While I am sure that it can be done more efficiently, this is correct and suffices
  for ti in xrange(n_timepoints):
    b = zeros(n_peaks, 'f')
    for peakIndex in xrange(n_peaks):
      b[peakIndex] = min(measurements[t][peakIndex]
                         for t in xrange(max(0,            ti - half_window_size),
                                         min(n_timepoints, ti + half_window_size)))
    baselines.append(b)

  return baselines


def computeDeltaFOverF(series_name, img4D, params, mask=None, imgCameraNoise=None):
  """
    delta_F_over_F = (fluorescence - baseline) / (baseline - camera_noise + regularizing_factor)

    where the regularizing_factor is expected to be a value so that
    one standard deviation of the camera noise leads to a deltaF/F of 0.04,
    as per Burkhard Hoeckendorf's recommendation.
    This regularizing factor prevents divisions by zero
    and also enabling comparisons across different data sets (different imaging sessions).
  """
  peaks, measurements = measureFluorescence(series_name, img4D, mask=mask)
  baselines = computeBaselineFluorescence(measurements, params["baseline_window_size"])

  # In the absence of measured camera noise, use a pixel value of 0

  # Compute regularizing factor
  # Solve for 0.04 = (stdDev - baseline) / (baseline - camera_noise + regularizing_factor)
  # (baseline - camera_noise + regularizing_factor) = (stdDev - baseline) / 0.04
  # regularizing_factor = ((stdDev - baseline) / 0.04) - baseline + camera_noise
  # BUT: the "baseline" here does not apply, it's zero.
  # So:
  # regularizing_factor = (stdDev / 0.04) + camera_noise
  stdDev = params["CM00-CM01_noise_stdDev"]

  def makeComputeFn():
    if imgCameraNoise:
      ra_noise = imgCameraNoise.randomAccess() # two-dimensional

      def computeDFoFWithNoise(fluorescence, baseline, peakIndex):
        peak = peaks[peakIndex]
        ra_noise.setPosition(int(peak.getDoublePosition(0)), 0)
        ra_noise.setPosition(int(peak.getDoublePosition(1)), 1)
        camera_noise = ra_noise.get().get()
        regularizer = (stdDev / 0.04) + camera_noise
        return (fluorescence - baseline) / (baseline - camera_noise + regularizer)

      return computeDFoFWithNoise
    else:
      camera_noise = params.get("CM00-CM01_noise_mean", 0)
      print "Using as camera noise:", camera_noise
      
      def computeDFoFGaussianNoise(fluorescence, baseline, peakIndex):
        #regularizer = (stdDev / 0.04)
        return (fluorescence - baseline) / (baseline - camera_noise + (stdDev / 0.04))

      return computeDFoFGaussianNoise

  compute = makeComputeFn()

  dFoF = [array((compute(m, b, peakIndex) for peakIndex, (m, b) in enumerate(izip(mrow, brow))), 'f')
          for mrow, brow in izip(measurements, baselines)]

  return peaks, measurements, baselines, dFoF



# Camera noise: given the deconvolution, it's unclear what to use.
# The PSF is about 20 pixels wide, so perhaps a Gaussian of radius 10 over the average of both noise images would do.
# Then, the peak is used a center + radius, averaging all pixel values within. So shot noise is not an issue.
# Given that it's most likely constant, I try first with zero as camera noise.

# Ignoring series 1 for now
peaks, measurements, baselines, dFoF = computeDeltaFOverF(series[0], img4Da, params, mask=mask)

with open(os.path.join(srcDir, "%s_deltaFoF.csv" % series[0]), 'w') as csvfile:
  w = csv.writer(csvfile, delimiter=",", quotechar='"', quoting=csv.QUOTE_NONNUMERIC)
  # Header: with peak coordinates
  w.writerow(["timepoint"] + ["%.2f::%.2f::%.2f" % tuple(peak.getFloatPosition(d) for d in xrange(3)) for peak in peaks])
  for t, row in enumerate(dFoF):
    w.writerow([t] + row.tolist())













