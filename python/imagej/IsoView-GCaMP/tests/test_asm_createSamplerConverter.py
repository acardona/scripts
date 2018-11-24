from net.imglib2.type.numeric.integer import UnsignedByteType
from net.imglib2.type.numeric.real import FloatType

import sys
sys.path.append("/home/albert/lab/scripts/python/imagej/IsoView-GCaMP/")
from lib.converter import createSamplerConverter
from lib.util import timeit


sampler_conv = createSamplerConverter(UnsignedByteType, FloatType)


# Test SamplerConverter:
from net.imglib2.img.array import ArrayImgs
from net.imglib2.converter import Converters
from net.imglib2.util import ImgUtil
from net.imglib2.img import ImgView
from net.imglib2.img.basictypeaccess import FloatAccess
from net.imglib2.converter.readwrite import SamplerConverter

dimensions = [100, 100, 100]
img1 = ArrayImgs.unsignedBytes(dimensions)
c = img1.cursor()
while c.hasNext():
  c.next().setOne()
img2 = ArrayImgs.floats(dimensions)

def testASM():
  ImgUtil.copy(ImgView.wrap(Converters.convertRandomAccessibleIterableInterval(img1, sampler_conv), img1.factory()), img2)

timeit(20, testASM)

class UnsignedByteToFloatAccess(FloatAccess):
  def __init__(self, sampler):
    self.sampler = sampler
  def getValue(self, index):
    return self.sampler.get().getRealFloat()
  def setValue(self, index, value):
    self.sampler.get().setReal(value)

class UnsignedByteToFloatSamplerConverter(SamplerConverter):
  def convert(self, sampler):
    return FloatType(UnsignedByteToFloatAccess(sampler))

def testJython():
  ImgUtil.copy(ImgView.wrap(Converters.convertRandomAccessibleIterableInterval(img1, UnsignedByteToFloatSamplerConverter()), img1.factory()), img2)

timeit(20, testJython)

# ASM: 31 ms
# Jython: 755 ms   -- a factor of 25x or so slowdown
