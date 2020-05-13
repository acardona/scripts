from net.imglib2.img.display.imagej import ImageJFunctions as IL
from net.imglib2.img.array import ArrayImgs
from net.imglib2.roi.geom import GeomMasks
from net.imglib2.roi import Regions
from net.imglib2.view import Views
from net.imglib2.type.logic import BitType
from collections import deque
from itertools import imap

# A binary image
img = ArrayImgs.bits([512, 512, 50])

# Add some data to it
center = img.dimension(0) / 2, img.dimension(1) / 2
for z in xrange(img.dimension(2)):
  radius = img.dimension(0) * 0.5 / (z + 1)
  #print radius
  circle = GeomMasks.openSphere(center, radius)
  # Works, explicit iteration of every pixel
  #for t in Regions.sample(circle, Views.hyperSlice(img, 2, z)):
  #  t.setOne()
  # Works: about twice as fast -- measured with: from time import time .... t0 = time(); ... t1 = time()
  deque(imap(BitType.setOne, Regions.sample(circle, Views.hyperSlice(img, 2, z))), maxlen=0)

IL.wrap(img, "bit img").show()