# Concatenate a subset of slices of two open images in Z
# Assumes both have the same X, Y dimensions
# Assumes both are net.imglib2.img.display.imagej.ImageJVirtualStack Img
# and are open in Fiji

import sys, os
sys.path.append("/lmb/home/acardona/lab/scripts/python/imagej/IsoView-GCaMP/")
from net.imglib2.view import Views
from net.imglib2.img.display.imagej import ImageJVirtualStack, ImageJFunctions as IL
from ij import WindowManager
from lib.ui import wrap

# First image: from 0 to lastIndexZ1 (0-based)
lastIndexZ1 = 16399
# Second image: from firstIndexZ2 to the last section (0-based)
firstIndexZ2 = 16400

# Text tags on the title of the open images
titleSuffix1 = "bad" # the old one, to keep from 0 to 16999
titleSuffix2 = "good" # the new one, to appeld from 17000 to the end

# Translation in 2D of the second image
dx2 = -1 # -0.975
dy2 = 0 # -0.179


def run():
  imp1 = None
  imp2 = None

  for ID in WindowManager.getIDList():
    imp = WindowManager.getImage(ID)
    if imp.getTitle().endswith(titleSuffix1):
      imp1 = imp
    elif imp.getTitle().endswith(titleSuffix2):
      imp2 = imp

  if imp1 is None:
    print "Missing imp1 with suffix", titleSuffix1
    return
  
  if imp2 is None:
    print "Missing imp2 with suffix", titleSuffix2
    return

  # getSource() is not yet available in the version of imglib2-ij I have installed
  #img1 = imp1.getStack().getSource()
  #img2 = imp2.getStack().getSource()
  
  # Hack it instead
  f = ImageJVirtualStack.getDeclaredField("source")
  f.setAccessible(True)
  img1 = f.get(imp1.getStack())
  img2 = f.get(imp2.getStack())

  maxCoords2D = [img1.dimension(i) -1 for i in xrange(2)]
  
  vd = Views.interval(Views.extendZero(img2),
                      [0, 0, firstIndexZ2],
                      maxCoords2D + [img2.dimension(2) -1])

  merged = Views.concatenate(2, # Z axis
                             Views.interval(img1,
                                            [0, 0, 0],
                                            maxCoords2D + [lastIndexZ1]),
                             Views.zeroMin(
                               Views.interval(
                                 Views.translate(vd, [dx2, dy2, 0]),
                                 vd)))
                                 

  imp3 = IL.wrap(merged, "MR1.4-3")
  if imp1.getRoi():
    imp3.setRoi(imp1.getRoi())
  imp3.show()


run()
