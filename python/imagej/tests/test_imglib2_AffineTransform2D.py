import os, sys, traceback
from net.imglib2.view import Views
from net.imglib2.realtransform import RealViews
from net.imglib2.interpolation.randomaccess import NLinearInterpolatorFactory
from net.imglib2.img import ImgView
from net.imglib2.util import ImgUtil
from net.imglib2.realtransform import AffineTransform2D
from net.imglib2 import FinalInterval
from net.imglib2.img.display.imagej import ImageJFunctions as IL
from jarray import array
from ij import IJ


def transform(img, matrix, interval):
    affine = AffineTransform2D()
    affine.set(matrix)
    imgI = Views.interpolate(Views.extendZero(img), NLinearInterpolatorFactory())
    imgA = RealViews.transform(imgI, affine)
    imgT = Views.zeroMin(Views.interval(imgA, interval))  # FAILING HERE: the zeroMin !! isolated the problem
    aimg = img.factory().create(interval)
    ImgUtil.copy(ImgView.wrap(imgT, aimg.factory()), aimg)
    return aimg


matrix = array([1.0, 0.0, 0.0, 0.0, 1.0, 0.0], 'd')

interval = FinalInterval([0, 0, 0], [20000, 20000, 34742])

imp = IJ.openImage("https://imagej.nih.gov/ij/images/AuPbSn40.jpg");
img = IL.wrap(imp)


imgT = transform(img, matrix, interval)
print imgT