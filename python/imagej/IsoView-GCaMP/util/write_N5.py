import sys, os
sys.path.append("/groups/cardona/home/cardonaa/lab/scripts/python/imagej/IsoView-GCaMP/")
from lib.io import writeN5
from net.imglib2.img.display.imagej import ImageJVirtualStack
from net.imglib2.view import Views
from ij import IJ

# Grab the 4D RandomAccessibleInterval from the open VirtualStack
f = ImageJVirtualStack.getDeclaredField("source")
f.setAccessible(True)
img4D = Views.dropSingletonDimensions(f.get(IJ.getImage().getStack()))

print img4D

writeN5(img4D,
        "/groups/cardona/cardonalab/Albert/2017-05-10_2_1019/",
        "2017-05-10_2_1019_0-399_409x509x305x800",
        [409, 509, 5, 1])
