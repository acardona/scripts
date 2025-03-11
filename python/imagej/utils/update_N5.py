import sys, os
sys.path.append("/lmb/home/acardona/lab/scripts/python/imagej/IsoView-GCaMP/")
from ij import IJ
from org.janelia.saalfeldlab.n5.universe import N5Factory
from lib.ui import grabImg
from lib.util import newFixedThreadPool
from net.imglib2.view import Views
from org.janelia.saalfeldlab.n5.imglib2 import N5Utils

# Update specific 2D slices of an an existing N5 volume in disk,
# at its s0 sub-folder, with specific 2D slices
# of another volume that exists as a virtual stack in RAM.

# N5 volume in disk
n5Root = "/net/zstore1/FIBSEM/MR1.4-3/registration/n5-2"
dataset = "s0"
n5 = N5Factory().openWriter(N5Factory.StorageFormat.N5, n5Root)
datasetAttributes = n5.getDatasetAttributes(dataset)

# Indices of 2D slices to update
# 0-based. Keys are the Z coordinates of the N5 on disk, values are those of the volume in RAM.
slice_indices = {7108: 7107, # replace with previous
                 16390: 16390, # replace
                 16392: 16392,
                 16394: 16394,
                 16395: 16395,
                 16403: 16403,
                 16407: 16407,
                 16408: 16408,
                 16409: 16409,
                 16410: 16410,
                 16412: 16412,
                 16413: 16413}

# Volume in RAM (a virtual volume)
imp = IJ.getImage()
print "Will pull slices from: ", imp.getTitle()
roi = imp.getRoi()
img = grabImg(imp)
if roi:
  bounds = roi.getBounds()
  print "Using ROI:", roi, "\nwith bounds:", bounds
  img = Views.zeroMin(Views.interval(img, [bounds.x, bounds.y, 0],
                                          [bounds.x + bounds.width -1, bounds.y + bounds.height -1, img.dimension(2) -1]))

def update(exe):
  print n5
  print datasetAttributes
  for n5index, RAMindex in slice_indices.iteritems():
    print "Processing n5Index", n5index, "with RAMindex", RAMindex
    # An interval of the 3D volume that is a plane with a Z coordinate at the slice to update
    plane = Views.interval(img, [0, 0, RAMindex],
                                [img.dimension(0) -1, img.dimension(1) -1, RAMindex])
    if n5index != RAMindex:
      # translate
      dz = n5index - RAMindex # e.g., +1 for the 7108 entry which was read at 7107
      plane = Views.translate(plane, [0, 0, dz])
    N5Utils.saveRegion(plane, n5, dataset, datasetAttributes, exe)


exe = newFixedThreadPool(250)
try:
  update(exe)
finally:
  exe.shutdown()


