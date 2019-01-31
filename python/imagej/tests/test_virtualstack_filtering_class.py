import os
from ij import IJ, ImagePlus, VirtualStack
from mpicbg.ij.plugin import NormalizeLocalContrast

class FilterVirtualStack(VirtualStack):
  def __init__(self, width, height, sourceDir, params):
    # Tell the superclass to initialize itself with the sourceDir
    super(VirtualStack, self).__init__(width, height, None, sourceDir)
    # Store the parameters for the NormalizeLocalContrast
    self.params = params
    # Set all TIFF files in sourceDir as slices
    for filename in os.listdir(sourceDir):
      if filename.lower().endswith(".tif"):
        self.addSlice(filename)
  
  def getProcessor(self, n):
    # Load the image at index n
    filepath = os.path.join(self.getDirectory(), self.getFileName(n))
    imp = IJ.openImage(filepath)
    # Filter it:
    ip = imp.getProcessor()
    """
    blockRadiusX = self.params["blockRadiusX"]
    blockRadiusY = self.params["blockRadiusY"]
    stds = self.params["stds"]
    center = self.params["center"]
    stretch = self.params["stretch"]
    NormalizeLocalContrast.run(ip, blockRadiusX, blockRadiusY, stds, center, stretch)
    """
    NormalizeLocalContrast.run(ip, *[params.get(k) for k in ["blockRadiusX", "blockRadiusY",
                                                             "stds", "center", "stretch"]])
    return ip

# Parameters for the NormalizeLocalContrast plugin
params = {
  "blockRadiusX": 200, # in pixels
  "blockRadiusY": 200, # in pixels
  "stds": 2, # number of standard deviations to expand to
  "center": True, # whether to anchor the expansion on the median value of the block
  "stretch": True # whether to expand the values to the full range, e.g. 0-255 for 8-bit
}

sourceDir = "/tmp/images-originals/"
width, height = 2048, 2048 # Or obtain them from e.g. dimensionsOf defined in an erlier script

vstack = FilterVirtualStack(width, height, sourceDir, params)

imp = ImagePlus("FilterVirtualStack with NormalizeLocalContrast", vstack)
imp.show()

