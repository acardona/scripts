import sys, os
sys.path.append("/home/albert/lab/scripts/python/imagej/IsoView-GCaMP/")

from lib.io import read2DImageROI
from lib.ui import wrap
from ij.io import TiffDecoder
from net.imglib2.type.numeric.integer import UnsignedByteType, UnsignedShortType
from net.imglib2.type.numeric.real import FloatType

path = "/home/albert/Desktop/t2/189/section189-images/08apr22a_gb27932_D4b_12x12_1_00005gr_01755ex.mrc.tif"

# Read header from TIFF file
folder, filename = os.path.split(path)
decoder = TiffDecoder(folder, filename)
fis = decoder.getTiffInfo()
print "header:", fis[0].offset
print "width:", fis[0].width
print "height:", fis[0].height
print "bytes per pixel:", fis[0].getBytesPerPixel()

# In a production script, you'd know these 4 values before hand.
header, width, height = fis[0].offset, fis[0].width, fis[0].height

# ... and the type:
pixelType = {1: UnsignedByteType,
             2: UnsignedShortType,
             4: FloatType}[fis[0].getBytesPerPixel()]

# ROI
x, y, w, h = 396, 698, 552, 514
img = read2DImageROI(path,
                     [width, height],
                     [[x, y],
                      [x + w - 1, y + h - 1]],
                     pixelType=pixelType,
                     header=header)

wrap(img, title=filename).show()