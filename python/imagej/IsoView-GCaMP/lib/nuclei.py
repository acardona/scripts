from lib.dogpeaks import createDoG
from lib.synthetic import virtualPointsRAI
from lib.ui import showStack
from net.imglib2 import KDTree, FinalInterval
from net.imglib2.neighborsearch import RadiusNeighborSearchOnKDTree
from net.imglib2.view import Views
from net.imglib2.img.array import ArrayImgs
from net.imglib2.algorithm.math.ImgMath import compute, add, sub


def doGPeaks(img, params):
  # Calibration is 1,1,1, so returned peaks in pixel space coincide with calibrated space,
  # no need for any adjustment of the peaks' positions.
  dog = createDoG(img, params["calibration"], params["sigmaSmaller"], params["sigmaLarger"], params["minPeakValue"])
  return dog.getSubpixelPeaks() # as RealPoint


def __makeMerge(params):
  
  radius = params["searchRadius"]
  
  def merge(nuclei, peaks2):
    """
    nuclei: a dictionary of RealPoint, representing the average position,
            vs the number of points averaged.
    peaks: a list of RealPoint

    Returns the updated nuclei, with possibly new nuclei, and the existing ones
    having their coordinates (and counts of points averaged) updated.
    """
    peaks1 = nuclei.keys()
    search = RadiusNeighborSearchOnKDTree(KDTree(peaks1, peaks1))
    for peak2 in peaks2:
      search.search(peak2, radius, False)
      n = search.numNeighbors()
      if 0 == n:
        # New nuclei not ever seen before
        nuclei[peak2] = 1
      else:
        # Merge peak with nearest found nuclei, which should only be one given the small radius
        peak1 = search.getSampler(0).get()
        count = float(nuclei[peak1])
        new_count = count + 1
        fraction = count / new_count
        for d in xrange(3):
          peak1.setPosition(peak1.getDoublePosition(d) * fraction + peak2.getDoublePosition(d) / new_count, d)
        nuclei[peak1] = new_count
        # Check for more
        if n > 1:
          print "Ignoring %i additional closeby nuclei" % (n - 1)
    # Return nuclei to enable a reduce operation over many sets of peaks
    return nuclei

  return merge


def findPeaks(img4D, params):
  """
  img4D: a 4D RandomAccessibleInterval
  params["frames"]: the number of consecutive time points to average
                    towards detecting peaks with difference of Gaussian.

  Returns a list of lists of peaks found, one list per time point.
  """
  frames = params["frames"]
  # Work image: the current sum
  sum3D = ArrayImgs.unsignedLongs([img4D.dimension(d) for d in [0, 1, 2]])

  peaks = []

  # Sum of the first set of frames
  compute(add([Views.hyperSlice(img4D, 3, i) for i in xrange(frames)])).into(sum3D)
  # Extract nuclei from first sum3D
  peaks.append(doGPeaks(sum3D, params))

  # Running sums: subtract the first and add the last
  for i in xrange(frames, img4D.dimension(3), 1):
    compute(add(sub(sum3D,
                    Views.hyperSlice(img4D, 3, i - frames)),
                Views.hyperSlice(img4D, 3, i))) \
      .into(sum3D)
    # Extract nuclei from sum4D
    peaks.append(doGPeaks(sum3D, params))

  return peaks


def mergePeaks(peaks, params):
  # Cluster nearby nuclei detections:
  # Make a KDTree from points
  # For every point, measure distance to nearby points up to e.g. half a soma diameter
  # and vote on neighboring points, weighed by distance.
  # Points with more than X votes remain.
  merged = reduce(__makeMerge(params), peaks[1:], {peak: 1 for peak in peaks[0]})
  return merged


def filterNuclei(mergedPeaks, params):
  """
  mergedPeaks: a dictionary of RealPoint vs count of DoG peaks averaged to make it.
  params["min_count"]: the minimum number of detections to consider a mergedPeak valid.

  Returns the list of accepted mergedPeaks.
  """
  return [mergedPeak for mergedPeak, count in mergedPeaks.iteritems() if count > min_count]


def findNuclei(img4D, params, show=True):
  """
  params["frames"]: number of time frames to average
  params["calibration"]: e.g. [1.0, 1.0, 1.0]
  params["somaDiameter"]: width of a soma, in pixels
  params["minPeakValue"]: determine it by hand with e.g. difference of Gaussians sigma=somaDiameter/4 minus sigma=somaDiameter/2
  params["sigmaSmaller"]: for difference of Gaussian to detect somas. Recommended somaDiameter / 4.0 -- in pixels
  params["sigmaLarger"]: for difference of Gaussian to detect somas. Recommended somaDiameter / 2.0 -- in pixels
  params["searchRadius"]: for finding nearby DoG peaks which are actually the same soma. Recommended somaDiameter / 3.0 -- in pixels
  parmams["min_count"]: to consider only somas detected in at least min_count time points, i.e. their coordinates are the average
                        of at least min_count independent detections.
  """
  peaks = findPeaks(img4D, params)
  mergedPeaks = mergePeaks(peaks, params)
  nuclei = filterNuclei(mergedPeaks, params)

  # Show as a 3D volume with spheres
  if show:
    spheresRAI = virtualPointsRAI(nuclei, somaDiameter / 2.0, Views.hyperSlice(img4D, 3, 1))
    imp = showStack(spheresRAI, title="nuclei (min_count=%i)" % min_count)
    return peaks, mergedPeaks, nuclei, imp
  
  return peaks, mergedPeaks, nuclei
