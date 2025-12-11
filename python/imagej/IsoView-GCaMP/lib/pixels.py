from ij.process import ImageStatistics
from lib.pixels_asm import ImgCompare
from lib.util import printException, newFixedThreadPool, numCPUs, isThreadDead, syncPrintQ, Task
from java.util.concurrent import Callable
from net.imglib2.view import Views

def autoAdjust(ip):
  """
  Find min and max using the equivalent of clicking "Auto"
  in ImageJ/Fiji's Brightness & Contrast dialog (the method autoAdjust
  in the ij.plugin.frame.ContrastAdjuster class).
  
  ip: an ImageProcessor.

  Return the min and max (possibly as floating-point values).
  """
  stats = ImageStatistics.getStatistics(ip, ImageStatistics.MIN_MAX, None)
  limit = stats.pixelCount / 10
  f = ImageStatistics.getDeclaredField("histogram")
  histogram = f.get(stats) # stats.histogram is confused with stats.getHistogram(), with the latter returning a long[] version.
  threshold = stats.pixelCount / 2500 # autoThreshold / 2
  # Search for histogram min
  i = 0
  found = False
  while not found and i < 255:
    count = histogram[i]
    if count > limit:
      count = 0
    found = count > threshold
    i += 1
  hmin = i
  # Search for histogram max
  i = 255
  found = False
  while not found and i > 0:
    count = histogram[i]
    if count > limit:
      count = 0
    found = count > threshold
    i -= 1
  hmax = i
  # Convert hmax, hmin to min, max
  if hmax > hmin:
    minimum = stats.histMin + hmin * stats.binSize
    maximum = stats.histMin + hmax * stats.binSize
    if minimum == maximum:
      minimum = stats.min
      maximum = stats.max
  else:
    sp.findMinAndMax()
    minimum = sp.getMin()
    maximum = sp.getMax()

  return minimum, maximum


class ComputeCosineSimilarity(Callable):
  def __init__(self, img, sqrtSumSq, i, j):
    self.img = img
    self.sqrtSumSq = sqrtSumSq
    self.i = i
    self.j = j
  def call(self):
    if isThreadDead():
      return None
    v = ImgCompare.cosyneSimilarityNorm(Views.hyperSlice(self.img, 2, self.i),
                                        self.sqrtSumSq[self.i],
                                        Views.hyperSlice(self.img, 2, self.j),
                                        self.sqrtSumSq[self.j])
    #syncPrintQ("Cosine similarity for %i-%i: %f" % (self.i, self.j, v))
    return v


def pairwiseCosineSimilarity(imgVolume, nThreads=0, roi=None):
  """
  roi: [x, y, width, height]
  Returns an array of length imgVolume.dimension(2) -1,
  where each item is the cosyne similarity between slice i and i+1.
  """
  exe = newFixedThreadPool(min(numCPUs(), imgVolume.dimension(2)) if 0 == nThreads else nThreads) # 0 means max
  try:
    # Crop view to interval if roi is not None
    if roi:
      imgVolume = Views.interval(imgVolume, [roi[0], roi[0] + roi[2] -1, 0],
                                            [roi[1], roi[1] + roi[3] -1, imgVolume.dimension(2) -1])    
    # Compute all sqrtSumSquares values, one for each 2D section
    futures = []
    for i in xrange(imgVolume.dimension(2)):
      futures.append(exe.submit(Task(ImgCompare.sqrtSumSquares, Views.hyperSlice(imgVolume, 2, i))))
    sqrtSumSq = [fu.get() for fu in futures]
    # Compute all pairwise cosyne similarities
    futures = []
    for i in xrange(imgVolume.dimension(2) -1):
      futures.append(exe.submit(ComputeCosineSimilarity(imgVolume, sqrtSumSq, i, i+1)))
    return [fu.get() for fu in futures]
  except:
    printException()
  finally:
    exe.shutdown()



def pairwiseCosineSimilarityST(imgVolume, roi=None):
  """
  roi: [x, y, width, height]
  Returns an array of length imgVolume.dimension(2) -1,
  where each item is the cosyne similarity between slice i and i+1.
  Runs on the calling thread, single-threaded.
  """
  try:
    # Crop view to interval if roi is not None
    if roi:
      imgVolume = Views.interval(imgVolume, [roi[0], roi[0] + roi[2] -1, 0],
                                            [roi[1], roi[1] + roi[3] -1, imgVolume.dimension(2) -1])    
    # Compute all sqrtSumSquares values, one for each 2D section
    sqrtSumSq = [ImgCompare.sqrtSumSquares(Views.hyperSlice(imgVolume, 2, i))
                 for i in xrange(imgVolume.dimension(2))]
    # Compute all pairwise cosyne similarities
    cs = [ComputeCosineSimilarity(imgVolume, sqrtSumSq, i, i+1).call()
          for i in xrange(imgVolume.dimension(2) -1)]
    return cs
  except:
    printException()








