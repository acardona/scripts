# Test performance of TransformView.transformView
from net.preibisch.mvrecon.process.fusion.transformed import TransformView
from net.imglib2.img.array import ArrayImgs
from net.imglib2.realtransform import AffineTransform3D
from net.imglib2 import FinalInterval
from net.preibisch.mvrecon.process.deconvolution import MultiViewDeconvolution
from random import random
from net.imglib2.algorithm.math import ImgMath
from net.imglib2.util import ImgUtil
from net.imglib2.img import ImgView
import sys
sys.path.append("/home/albert/lab/scripts/python/imagej/IsoView-GCaMP/")
from lib.util import timeit

roi = ([1, 228, 0], # top-left coordinates
       [1 + 406 -1, 228 + 465 -1, 0 + 325 -1]) # bottom-right coordinates (inclusive, hence the -1)

dimensions = [maxC - minC + 1 for minC, maxC in zip(roi[0], roi[1])]

imgU = ArrayImgs.unsignedShorts(dimensions)
imgF = ArrayImgs.floats(dimensions)
#c = imgF.cursor()
#while c.hasNext():
#  c.next().set(random() * 65535)
ImgMath.compute(ImgMath.number(17)).into(imgF)
ImgMath.compute(ImgMath.img(imgF)).into(imgU)
aff = AffineTransform3D()
"""
aff.set(1, 0, 0, 0,
        0, 1, 0, 0,
        0, 0, 1, 0)
"""
aff.set(*[0.9999949529841275, -0.0031770224721305684, 2.3118912942710207e-05, -1.6032353998500826,
     0.003177032139125933, 0.999994860398559, -0.00043086338151948394, -0.4401520585103873,
     -2.1749931475206362e-05, 0.0004309346564745992, 0.9999999069111268, 6.543187040788581])
interval = FinalInterval([0, 0, 0], [d - 1 for d in dimensions])

def test(img):
  imgT = TransformView.transformView(img, aff, interval,
                                     MultiViewDeconvolution.minValueImg,
                                     MultiViewDeconvolution.outsideValueImg,
                                     1) # 1: linear interpolation
  imgA = ArrayImgs.floats(dimensions)
  ImgUtil.copy(ImgView.wrap(imgT, imgA.factory()), imgA)

print "Start test:"
timeit(3, test, imgU)
timeit(3, test, imgF)

# Prints:
# Start test:
# min: 12753.90 ms, max: 15069.83 ms, mean: 13720.68 ms
# min: 13417.38 ms, max: 13563.55 ms, mean: 13506.67 ms
#
# Conclusion: the type difference doesn't matter. Code is optimized anyway.
