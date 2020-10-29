from __future__ import with_statement
import sys, os, csv
from lib.ui import showStack, wrap, showAsComposite
from lib.nuclei import findPeaks, mergePeaks, filterNuclei, findNucleiByMaxProjection
from net.imglib2.util import Intervals
from net.imglib2.view import Views
from net.imglib2.roi.geom.real import ClosedWritableSphere
from net.imglib2.roi import Masks, Regions
from itertools import islice, izip
from jarray import zeros, array


def measureFluorescence(tgtDir, series_name, img4D, params, mask=None, showDetections=True):
  """
  srcDir: the directory containing the CSV files and max intensity projection .zip file.
  series_name: the name or title, to be used for e.g. writing (and finding to load when it exists)
               a .zip file with the max intensity projection used for detecting nuclei,
               and for the .csv file containing the fluorescence measurements.
  img4D: the ImgLib2 data (ideally e.g. an N5 volume for fast access).
  params: the dictionary of parameters for detecting nuclei with difference of Gaussian.
          See nuclei.py:findNucleiByMaxProjection for the parameter keys.
  mask: optional, defaults to None. If it exists, it is a 3D volume with zero for space to ignore
        nuclei detections, and non-zero otherwise.
  """
  csv_fluorescence = os.path.join(tgtDir, "%s_fluorescence.csv" % series_name)
  if not os.path.exists(csv_fluorescence):
    # Generate projection over time (the img3D) and extract peaks with difference of Gaussian using the params
    # (Will check if file for projection over time exists and just load it)
    img3D_filepath = os.path.join(tgtDir, "%s_4D-to-3D_max_projection.zip" % series_name)
    img3D, peaks, spheresRAI, impSpheres = findNucleiByMaxProjection(img4D, params, img3D_filepath, mask=mask, show=showDetections)
    comp = showAsComposite([wrap(img3D), impSpheres])
    # Measure intensity over time, for every peak
    # by averaging the signal within a radius of each peak.
    measurement_radius = somaDiameter / 3.0
    spheres = [ClosedWritableSphere([peak.getFloatPosition(d) for d in xrange(3)], measurement_radius) for peak in peaks]
    insides = [Regions.iterable( # TODO can be simplified with new method Masks.toIterableRegion
                 Views.interval(
                   Views.raster(Masks.toRealRandomAccessible(sphere)),
                   Intervals.largestContainedInterval(sphere))
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
        w.writerow([t] + mean_intensities)
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


def computeDeltaFOverF(tgtDir, series_name, img4D, params, mask=None, imgCameraNoise=None, showDetections=True):
  """
    delta_F_over_F = (fluorescence - baseline) / (baseline - camera_noise + regularizing_factor)

    where the regularizing_factor is expected to be a value so that
    one standard deviation of the camera noise leads to a deltaF/F of 0.04,
    as per Burkhard Hoeckendorf's recommendation.
    This regularizing factor prevents divisions by zero
    and also enabling comparisons across different data sets (different imaging sessions).

    tgtDir: directory into which to save CSV files.
    series_name: used to write relevant files (see function measureFluorescence),
                 and also to find the stdDev param in the params dict.
    img4D: the ImgLib2 4D volume.
    params: dictionary of parameters, see function measureFluorescence.
    mask: consider only nuclei detections within the mask, which has zero values for outside voxels.
    imgCameraNoise: defaults to None, meaning a value of zero for every pixel.
    showDetections: show the 3D max projection plus the nuclei detections.
  """
  peaks, measurements = measureFluorescence(tgtDir, series_name, img4D, params, mask=mask, showDetections=showDetections)
  baselines = computeBaselineFluorescence(measurements, params["baseline_window_size"])

  # In the absence of measured camera noise, use a pixel value of 0

  # Compute regularizing factor
  # Solve for 0.04 = (stdDev - baseline) / (baseline - camera_noise + regularizing_factor)
  # (baseline - camera_noise + regularizing_factor) = (stdDev - baseline) / 0.04
  # regularizing_factor = ((stdDev - baseline) / 0.04) - baseline + camera_noise
  # BUT: the "baseline" here does not apply, it's zero.
  # So:
  # regularizing_factor = (stdDev / 0.04) + camera_noise
  stdDev = params[series_name + "_noise_stdDev"]

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
      camera_noise = params.get(series_name + "_noise_mean", 0)
      print "Using as camera noise:", camera_noise
      
      def computeDFoFGaussianNoise(fluorescence, baseline, peakIndex):
        #regularizer = (stdDev / 0.04)
        return (fluorescence - baseline) / (baseline - camera_noise + (stdDev / 0.04))

      return computeDFoFGaussianNoise

  compute = makeComputeFn()

  dFoF = [array((compute(m, b, peakIndex) for peakIndex, (m, b) in enumerate(izip(mrow, brow))), 'f')
          for mrow, brow in izip(measurements, baselines)]

  return peaks, measurements, baselines, dFoF
