# Export as 8-bit N5 an open virtual stack that shows an ImgLib2 LazyCellImg
import os, sys
sys.path.append("/lmb/home/acardona/lab/scripts/python/imagej/IsoView-GCaMP/")
from lib.serial2Dregistration import exportN5
from lib.converter import convert2
from lib.io import writeN5
from ij import IJ
from net.imglib2.img.display.imagej import ImageJVirtualStack
from net.imglib2.converter import RealUnsignedByteConverter
from net.imglib2.type.numeric.integer import UnsignedByteType
from net.imglib2.util import Intervals
from net.imglib2.view import Views


def grabImg():
  imp = IJ.getImage()
  stack = imp.getStack() # an ImageJVirtualStackUnsignedShort or similar (for each pixel type) which extends ImageJVirtualStack which has a source field with the ImgLib2 RandomAccessibleInterval instance
  print type(stack)

  if isinstance(stack, ImageJVirtualStack):
    # Make the private field accessible
    f = ImageJVirtualStack.getDeclaredField("source")
    f.setAccessible(True)
    img = f.get(stack)

    print img # A LazyCellImg
    return img, imp.getRoi()


def exportOpenVSAs8bitN5(name, # dataset name
                         exportDir, # target directory
                         block_size, # [128,128,128
                         minimum, # min display range for mapping to 8-bit
                         maximum, # max display range for mapping to 8-bit
                         gzip_compression=6,
                         n_threads=1): # for writing
  img, roi = grabImg()
  if not img:
    print "No ImgLib2 image!"
    return
  # as 8-bit:
  img = convert2(imgT, RealUnsignedByteConverter(minimum, maximum), UnsignedByteType, randomAccessible=True) # use IterableInterval
  # Crop
  if roi:
    bounds = roi.getBounds()
    print "Using ROI:", roi, "\nwith bounds:", bounds
    img = Views.interval(img, [bounds.x, bounds.y, 0],
                              [bounds.x + bounds.width, bounds.y + bounds.height, img.dimension(2) -1])
  # Ready to write
  writeN5(img, exportDir, name,
          block_size, gzip_compression_level=gzip_compression,
          n_threads=n_threads)


exportOpenVSas8bitN5("PedroParker",
                     "/net/zstore1/FIBSEM/Pedro_parker/registration-Albert/n5/",
                     30924,
                     38829, # as measured for slice 4000. Works well for slice 3000, 5000 and 6000 too.
                     [256, 256, 64],
                     gzip_compression=4,
                     n_threads=64)

