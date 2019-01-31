from ij.gui import PointRoi
from java.awt import Point

def roiPoints(roi):
  """ Return the list of 2D coordinates for pixels inside the ROI. """
  if isinstance(roi, PointRoi):
    return roi.getContainedPoints()
  # Else, one Point per non-zero pixel in the mask
  bounds = roi.getBounds()
  mask = roi.getMask()
  x, y, width, height = bounds.x, bounds.y, bounds.width, bounds.height
  if mask:
    return [Point(x + i % width,
                  y + i / width)
            for i, v in enumerate(mask.getPixels())
            if 0 != v]
  # Else, e.g. Rectangle ROI
  return [Point(x + i % width,
                y + i / width)
          for i in xrange(width * height)]
