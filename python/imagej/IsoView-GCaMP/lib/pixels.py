from ij.process import ImageStatistics

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
