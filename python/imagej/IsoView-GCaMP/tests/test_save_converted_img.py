import sys
sys.path.append("/home/albert/lab/scripts/python/imagej/IsoView-GCaMP/")
from lib.io import writeZip
from lib.converter import samplerConvert, convert
from net.imglib2.type.numeric.integer import UnsignedShortType
from net.imglib2.type.numeric.real import FloatType
from net.imglib2.img.array import ArrayImgs

imgU = ArrayImgs.unsignedShorts([10, 10])
imgF = samplerConvert(imgU, UnsignedShortType, FloatType)
print imgF
print type(imgF)
writeZip(imgF, "/tmp/floats.zip")

imgF2 = convert(imgU, UnsignedShortType, FloatType)
writeZip(imgF2, "/tmp/floats2.zip")