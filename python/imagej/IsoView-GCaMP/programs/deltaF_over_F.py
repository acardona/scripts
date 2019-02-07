import sys
sys.path.append("/home/albert/lab/scripts/python/imagej/IsoView-GCaMP/")
from lib.io import readN5
from lib.dogpeaks import createDoG
from lib.synthetic import virtualPointsRAI
from lib.ui import showStack
from net.imglib2 import KDTree
from net.imglib2.neighborsearch import RadiusNeighborSearchOnKDTree
from net.imglib2.view import Views
from net.imglib2.util import Intervals
from net.imglib2.img.array import ArrayImgs
from net.imglib2.algorithm.math.ImgMath import compute, add, sub

n5dir = "/home/albert/shares/cardonalab/Albert/2017-05-10_1018/deconvolved/n5"
dataset_name = "2017-5-10_1018_0-399"

# Load entire 4D IsoView deconvolved and registered data set
img4D = readN5(n5dir, dataset_name)

# Split CM00+CM01 (odd) from CM02+CM03 (even) into two series
img4Da = Views.subsample(img4D,
                         [1, 1, 1, 2]) # step
img4Db = Views.subsample(Views.interval(img4D, [0, 0, 0, 1], Intervals.maxAsLongArray(img4D))
                         [1, 1, 1, 2]) # step

# number of time frames to average
frames = 5 # equivalent to 3.75 seconds: 0.75 * 5

# Deconvolved images have isotropic calibration
calibration = [1.0, 1.0, 1.0]

# Parameters for detecting nuclei
somaDiameter = 8 * calibration[0]
minPeakValue = 30 # determined by hand: the bright peaks
sigmaSmaller = somaDiameter / 4.0 # in calibrated units: 1/4 soma
sigmaLarger = somaDiameter / 2.0  # in calibrated units: 1/2 soma
searchRadius = somaDiameter / 3.0
min_count = 10


def doGPeaks(img):
  # Calibration is 1,1,1, so returned peaks in pixel space coincide with calibrated space,
  # no need for any adjustment of the peaks' positions.
  dog = createDoG(img, calibration, sigmaSmaller, sigmaLarger, minPeakValue)
  return dog.getSubpixelPeaks() # as RealPoint


def merge(nuclei, peaks2):
  """
  nuclei: a dictionary of RealPoint, representing the average position,
          vs the number of points averaged.
  peaks: a list of RealPoint

  Returns the updated nuclei, with possibly new nuclei, and the existing ones
  having their coordinates (and counts of points averaged) updated.
  """
  radius = searchRadius
  peaks1 = nuclei.keys()
  rns = RadiusNeighborSearchOnKDTree(KDTree(peaks1, peaks1))
  for peak2 in peaks2:
    rns.search(peak2, radius, False)
    n = search.numNeighbors()
    if 0 == n:
      # New nuclei not ever seen before
      nuclei[peak2] = 1
    else:
      # Merge peak with nearest found nuclei, which should only be one given the small radius
      peak1 = search.getPosition(0)
      new_count = nuclei[peak1] + 1
      for d in xrange(3):
        peak1.setPosition(peak1.getDoublePosition(d) + peak2.getDoublePosition(d) / new_count, d)
      nuclei[peak1] = new_count
      # Check for more
      if n > 1:
        print "Ignoring %i additional closeby nuclei" % (n - 1)
  # Return nuclei to enable a reduce operation over many sets of peaks
  return nuclei
        

def findMergedPeaks(img4D, frames):
  """
  img4D: a 4D RandomAccessibleInterval
  frames: the number of consecutive time points to average
          towards detecting peaks with difference of Gaussian.

  Returns the merged peaks: a dictionary of RealPoint vs number of peaks
                            that were averaged to compute its position.
  """
  # Work image: the current sum
  sum4D = ArrayImgs.unsignedLongs([img4D.dimension(d) for d in [0, 1, 2]])

  peaks = []

  # Sum of the first set of frames
  compute(add([Views.hyperSlice(img4Da, 3, i) for i in xrange(frames)])).into(sum4D)
  # Extract nuclei from first sum4D
  peaks.append(doGPeaks(sum4D))

  # Running sums: subtract the first and add the last
  for i in xrange(frames, img4D.dimension(3), 1):
    compute(add(sub(sum4D, Views.hyperSlice(img4Da, 3, i - frames)),
                Views.hyperSlice(img4Da, 3, i))) \
      .into(sum4D)
    # Extract nuclei from sum4D
    peaks.append(doGPeaks(sum4D))

  # Cluster nearby nuclei detections:
  # Make a KDTree from points
  # For every point, measure distance to nearby points up to e.g. half a soma diameter
  # and vote on neighboring points, weighed by distance.
  # Points with more than X votes remain.
  merged = reduce(merge, peaks[1:], {peak: 1 for peak in peaks[0]})
  return merged


def filterNuclei(mergedPeaks, min_count):
  """
  mergedPeaks: a dictionary of RealPoint vs count of DoG peaks averaged to make it.
  min_count: the minimum number of detections to consider a mergedPeak valid.

  Returns the list of accepted mergedPeaks.
  """
  return [mergedPeak for mergedPeak, count in mergedPeaks.iteritems() if count > min_count]



#
mergedPeaks = filterNuclei(findMergedPeaks(img4Da, frames), min_count)

# Show as a 3D volume with spheres
spheresRAI = virtualPointsRAI(mergedPeaks, somaDiameter / 2.0, img4Da)
imp = showStack(spheresRAI, title="nuclei (min_count=%i)" % min_count)

