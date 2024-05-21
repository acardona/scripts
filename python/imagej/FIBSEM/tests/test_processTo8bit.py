import sys, os
sys.path.append("/lmb/home/acardona/lab/scripts/python/imagej/IsoView-GCaMP/")

from lib.montage2d import processTo8bit
from ij import IJ, ImagePlus
from ij.gui import Roi

imp = IJ.getImage()
sp = imp.getProcessor().duplicate()

# Image contrast parameters
params_pixels = {
  "invert": True,
  "CLAHE_params": [200, 255, 2.0], # blockRadius, n_bins, and slope in stdDevs
  "as8bit": True,
  "contrast": (500, 1000), # thresholds in pixel counts per histogram bin
  "roiFn": lambda sp: Roi(sp.getWidth() / 6, sp.getHeight() / 6, 2 * sp.getWidth() / 3, 2 * sp.getHeight() / 3), # middle 2/3rds to discard edges}
}

# in place:
bp = processTo8bit(sp, params_pixels)

imp2 = ImagePlus(imp.getTitle(), sp)
imp3 = ImagePlus(imp.getTitle(), bp)
imp3.setRoi(params_pixels["roiFn"](bp))
imp2.show()
imp3.show()