import os
from net.imglib2.type.numeric.integer import UnsignedShortType
from org.janelia.saalfeldlab.n5.universe import N5Factory
from ij.process import ShortProcessor
from ij.gui import Roi
from net.imglib2.img.display.imagej import ImageJFunctions
from org.janelia.saalfeldlab.n5 import GzipCompression
from net.imglib2.util import Intervals, ConstantUtils
from ij import ImageStack, ImagePlus
from org.janelia.saalfeldlab.n5.imglib2 import N5Utils
from net.imglib2.img.display.imagej import ImageJFunctions as IL
from bdv.util import BdvFunctions, Bdv
from org.janelia.saalfeldlab.n5.imglib2 import N5Utils
from org.janelia.saalfeldlab.n5 import N5FSReader, N5FSWriter, GzipCompression, RawCompression
from com.google.gson import GsonBuilder


# Create an image whose value at every point equals its z-position + 256.
# Important!
# The Interval of the resulting image is [0,255] x [0,255] x [zSlice,zSlice]
# Return RandomAccessibleInterval<UnsignedShortType>
def makeImageToInsert( zSlice ):
  t = UnsignedShortType()
  t.setInteger( 256 + zSlice )
  return ConstantUtils.constantRandomAccessibleInterval( t,
				                                         Intervals.createMinMax( 0, 0, zSlice, 127, 127, zSlice ) )


# Saves an image whose value at every point equals its z-position
def writeInitialImage( n5, dataset ):
  stack = ImageStack(128, 128)
  for i in xrange(128):
    bp = ShortProcessor(128, 128)
    bp.setValue(i)
    bp.setRoi(Roi(0, 0, 128, 128))
    bp.fill()
    stack.addSlice(bp)
  imp = ImagePlus("stack", stack)
  img = ImageJFunctions.wrap(imp)
  N5Utils.save( img, n5, dataset, [64, 64, 64], GzipCompression() )


n5Root = "/tmp/save-region-demo.n5"
dataset = "s0"
n5 = N5Factory().openWriter( n5Root )

if not os.path.exists("%s/%s" % (n5Root, dataset)):
  writeInitialImage( n5, dataset )

datasetAttributes = n5.getDatasetAttributes( dataset )
print datasetAttributes

zSlice = 99
#  create a new image for the requested zSlice 
slice = makeImageToInsert( zSlice )

# overwrite the slice at the requested position
N5Utils.saveRegion( slice, n5, dataset, datasetAttributes )


# Now open it and read properties
n5Root = "/tmp/save-region-demo.n5"
dataset = "s0"
n5 = N5Factory().openWriter( n5Root )
datasetAttributes = n5.getDatasetAttributes( dataset )
print datasetAttributes # not None

img = N5Utils.open(N5FSReader(n5Root, GsonBuilder()), dataset)
# As an ImageJ stack
IL.show(img, dataset)
# As a BigDataViewer
#BdvFunctions.show(img, dataset)

# WORKS: slice 100 at zero-based index 99 is updated.


