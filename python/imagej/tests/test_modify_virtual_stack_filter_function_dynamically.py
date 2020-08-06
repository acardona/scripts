import os, sys
from ij import IJ, ImagePlus, VirtualStack
from mpicbg.ij.plugin import NormalizeLocalContrast

class FilterVirtualStack(VirtualStack):
  def __init__(self, width, height, sourceDir):
    # Tell the superclass to initialize itself with the sourceDir
    super(VirtualStack, self).__init__(width, height, None, sourceDir)
    # Set all TIFF files in sourceDir as slices
    for filename in sorted(os.listdir(sourceDir)):
      if filename.lower().endswith(".png"):
        self.addSlice(filename)
  
  def getProcessor(self, n):
    # Load the image at index n
    filepath = os.path.join(self.getDirectory(), self.getFileName(n))
    imp = IJ.openImage(filepath)
    # Filter it:
    ip = imp.getProcessor()
    # Fail-safe execution of the filter, which is a global function name
    try:
      ip = executeFilter(ip)
    except:
      print sys.exc_info()
    return ip


sourceDir = "/tmp/fib/"
width, height = 256, 256 # Or obtain them from e.g. dimensionsOf
                           # defined in an erlier script

vstack = FilterVirtualStack(width, height, sourceDir)

imp = ImagePlus("FilterVirtualStack with NormalizeLocalContrast", vstack)
imp.show()

# Parameters for the NormalizeLocalContrast plugin
params = {
  "blockRadiusX": 20, # in pixels
  "blockRadiusY": 20, # in pixels
  "stds": 2, # number of standard deviations to expand to
  "center": True, # whether to anchor the expansion on the median value of the block
  "stretch": True # whether to expand the values to the full range, e.g. 0-255 for 8-bit
}

# Doesn't matter that this function is defined after the class method
# that will invoke it: at run time, this function name will be searched for
# among the existing global variables
def executeFilter(ip):
  """ Given an ImageProcessor ip and a dictionary of parameters, filter the ip,
      and return the same or a new ImageProcessor of the same dimensions and type. """
  blockRadiusX = params["blockRadiusX"]
  blockRadiusY = params["blockRadiusY"]
  stds = params["stds"]
  center = params["center"]
  stretch = params["stretch"]
  NormalizeLocalContrast.run(ip, blockRadiusX, blockRadiusY, stds, center, stretch)
  return ip

# Update to actually run the filter function on the slice that shows
imp.updateAndDraw()
          