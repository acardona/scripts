import sys, os
sys.path.append("/lmb/home/acardona/lab/scripts/python/imagej/IsoView-GCaMP/")

from lib.montage2d import processTo8bit
from ij import IJ, ImagePlus

imp = IJ.getImage()
sp = imp.getProcessor().duplicate()

# in place:
bp = processTo8bit(sp, invert=True, CLAHE_params=[200, 255, 2.0])

imp2 = ImagePlus(imp.getTitle(), sp)
imp3 = ImagePlus(imp.getTitle(), bp)
imp2.show()
imp3.show()