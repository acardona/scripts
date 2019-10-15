from jarray import array, zeros
from random import random
import sys
sys.path.append("/home/albert/lab/scripts/python/imagej/IsoView-GCaMP/")
from lib.plot import renderHistogram, chartAsImagePlus, saveChartAsSVG
from ij import IJ
from java.awt import Color

def intoBins(values, n_bins, minimum=None, maximum=None):
  """ Sort out the sequence of numeric values into bins, creating a histogram.
      Returns the bins: an array where each slot is a bin and has the count of values
                        that fall within it. """
  bins = zeros(n_bins, 'd')
  minimum = minimum if minimum else min(values)
  maximum = maximum if maximum else max(values)
  span = float(maximum - minimum)
  for v in values:
    index = int(((max(minimum, min(v, maximum)) - minimum) / span) * (n_bins -1))
    bins[index] += 1
  return bins


# Test
n_bins = 100
values = [random() * n_bins for i in xrange(10000)]
chart, frame = renderHistogram(values, n_bins, title="random", color=Color.blue, show=True)

chartAsImagePlus(chart, frame).show()
saveChartAsSVG(chart, "/tmp/chart.svg", frame=frame)
# Load the SVG
IJ.open("/tmp/chart.svg")
  