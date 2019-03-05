import sys
sys.path.append("/home/albert/lab/scripts/python/imagej/IsoView-GCaMP/")
from lib.converter import makeCompositeToRealConverter, convert
from net.imglib2.view import Views
from java.lang import Math
from net.imglib2.img.display.imagej import ImageJFunctions as IL
from ij import IJ

# Create the Converter class
reduce_max = makeCompositeToRealConverter(reducer_class=Math,
                                          reducer_method="max",
                                          reducer_method_signature="(DD)D")

# Testing with the bat cochlea volume,
# projecting it from 3D to 2D with a max intensity projection
img3D = IL.wrap(IJ.getImage())
img3DV = Views.collapseReal(img3D)
img2D = convert(img3DV, reduce_max.newInstance(), img3D.randomAccess().get().getClass())

IL.wrap(img2D, "Z projection").show()