# Concatenate a subset of slices of two open images in Z
# Assumes both have the same X, Y dimensions
# Assumes both are net.imglib2.img.display.imagej.ImageJVirtualStack Img
# and are open in Fiji

import sys, os
sys.path.append("/lmb/home/acardona/lab/scripts/python/imagej/IsoView-GCaMP/")
from net.imglib2.view import Views
from ij import WindowManager
from lib.ui import wrap

# First image: from 0 to lastIndexZ1 (0-based)
lastIndexZ1 = 16999
# Second image: from firstIndexZ2 to the last section (0-based)
firstIndexZ2 = 17000

# Text tags on the title of the open images
titleSuffix1 = "bad" # the old one, to keep from 0 to 16999
titleSuffix2 = "good" # the new one, to appeld from 17000 to the end

# Translation in 2D of the second image
dx2 = 279 # 278.5
dy2 = 67 # 66.6


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

  img1 = imp1.getStack().getSource()
  img2 = imp2.getStack().getSource()

  maxCoords2D = [img1.dimension(i) -1 for i in xrange(2)]

  merged = Views.concatenate(2, # Z axis
                             Views.interval(img1,
                                            [0, 0, 0],
                                            maxCoords2D + [lastIndexZ1]),
                             Views.zeroMin(
                               Views.translate(
                                 Views.interval(img2,
                                                [0, 0, firstIndexZ2],
                                                maxCoords2D + [img2.dimension(2) -1]),
                                 [dx2, dy2])))

  imp3 = wrap(merged)
  imp3.show()


run()
