from ij.gui import Plot
from roi import roiPoints
from util import syncPrint

def plot2DRoiOverZ(imp, roi=None, show=True, XaxisLabel='Z', YaxisLabel='I', Zscale='1.0'):
  """
  Take an ImagePlus and a 2D ROI (optional, can be read from the ImagePlus)
  and plot the average value of the 2D ROI in each Z slice.

  Return 4 elements: the two lists of values for the Y (intensity) and X (slice index),
  and the Plot and PlotWindow instances.
  """
  roi = roi if roi else imp.getRoi()
  if not roi:
    syncPrint("Set a ROI first.")
    return
  # List of 2D points from where pixel values are to be read
  points = roiPoints(roi)
  stack = imp.getStack()
  intensity = [sum(stack.getProcessor(slice_index).getf(p.x, p.y) for p in points) / len(points)
               for slice_index in xrange(1, imp.getNSlices() + 1)]
  xaxis = [z * Zscale for z in range(1, imp.getNSlices() + 1)]
  plot = Plot("Intensity", XaxisLabel, YaxisLabel, xaxis, intensity)
  if show:
    win = plot.show()
  else:
    win = None
  return intensity, xaxis, plot, win
