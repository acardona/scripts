import sys, os
sys.path.append("//home/albert/lab/scripts/python/imagej/IsoView-GCaMP/")
from net.imglib2.realtransform import Scale3D, AffineTransform3D, RealViews
from net.imglib2.view import Views
from net.imglib2.interpolation.randomaccess import NLinearInterpolatorFactory
from lib.deconvolution import prepareImgForDeconvolution
from lib.util import affine3D
from net.imglib2 import FinalInterval
from net.imglib2.img.array import ArrayImgs
from net.imglib2.img.display.imagej import ImageJFunctions as IL  
from net.imglib2.util import Intervals, ImgUtil
from net.imglib2.img import ImgView
from org.janelia.simview.klb import KLB
from itertools import izip



calibration = [1.0, 1.0, 5.0]

# In pixels
dims0 = [576, 896, 65]
dims1 = [576, 896, 65]
dims2 = [576, 896, 85]
dims3 = [576, 896, 85]

cmTransforms = {
    0: [1.0, 0.0, 0.0, 0.0,
        0.0, 1.0, 0.0, 0.0,
        0.0, 0.0, 1.0, 0.0],
    1: [-1.0, 0.0, 0.0, dims1[0] * calibration[0] - 195,
         0.0, 1.0, 0.0, 54.0,
         0.0, 0.0, 1.0,  8.0],
    2: [ 0.0, 0.0, 1.0,  0.0,
         0.0, 1.0, 0.0, 25.0,
        -1.0, 0.0, 0.0, dims2[2] * calibration[2] + 41.0],
    3: [0.0, 0.0, 1.0,    0.0,
        0.0, 1.0, 0.0,   25.0,
        1.0, 0.0, 0.0, -159.0]
  }

scale3D = AffineTransform3D()
scale3D.set(calibration[0], 0.0, 0.0, 0.0,
            0.0, calibration[1], 0.0, 0.0,
            0.0, 0.0, calibration[2], 0.0)

cmIsotropicTransforms = []
for camera_index in sorted(cmTransforms.keys()):
  aff = AffineTransform3D()
  aff.set(*cmTransforms[camera_index])
  aff.concatenate(scale3D)
  cmIsotropicTransforms.append(aff)

roi = ([1, 228, 0], # top-left coordinates
       [1 + 406 -1, 228 + 465 -1, 0 + 325 -1]) # bottom-right coordinates (inclusive, hence the -1)

fineTransformsPostROICrop = \
   [[1, 0, 0, 0,
     0, 1, 0, 0,
     0, 0, 1, 0],
     
    [0.9999949529841275, -0.0031770224721305684, 2.3118912942710207e-05, -1.6032353998500826,
     0.003177032139125933, 0.999994860398559, -0.00043086338151948394, -0.4401520585103873,
     -2.1749931475206362e-05, 0.0004309346564745992, 0.9999999069111268, 6.543187040788581],
     
    [0.9997987121628504, -0.009472768268010913, -0.01768620419553878, 3.930297652126247,
     0.009342009169030474, 0.9999285252136545, -0.007461322183871208, 2.427195709390503,
     0.017755619453893427, 0.0072945956287064715, 0.999815746451526, 1.0095040792330394],
     
    [0.9998779568655723, -0.015226665797195312, 0.0034957149525624287, 3.2525448680408826,
     0.01523705113687456, 0.9998795170641414, -0.002963718649331728, -2.1506102341571323,
     -0.0034501662251717287, 0.003016621335310332, 0.9999894981192247, 2.447694931285838]]


sourceDir = "/home/albert/shares/zlaticlab/Nadine/Raghav/2017-05-10/GCaMP6s_1_20170510_115003.corrected/SPM00/TM000000/"
filepaths = [os.path.join(sourceDir, filepath) 
             for filepath in sorted(os.listdir(sourceDir))
             if filepath.endswith(".klb")]
for fp in filepaths: print fp

klb = KLB.newInstance()

# TODO: transform an image one way and then the other and compare.

def twoStep(index=0):
  # The current way:
  img = klb.readFull(filepaths[index]) # klb_loader.get(filepaths[index])
  imgE = Views.extendZero(img)
  imgI = Views.interpolate(imgE, NLinearInterpolatorFactory())
  imgT = RealViews.transform(imgI, cmIsotropicTransforms[index])
  imgB = Views.zeroMin(Views.interval(imgT, roi[0], roi[1])) # bounded: crop with ROI
  imgBA = ArrayImgs.unsignedShorts(Intervals.dimensionsAsLongArray(imgB))
  ImgUtil.copy(ImgView.wrap(imgB, imgBA.factory()), imgBA)
  imgP = prepareImgForDeconvolution(imgBA,
                                    affine3D(fineTransformsPostROICrop[index]).inverse(),
                                    FinalInterval([0, 0, 0],
                                                  [imgB.dimension(d) -1 for d in xrange(3)]))
  # Copy transformed view into ArrayImg for best performance in deconvolution
  imgA = ArrayImgs.floats(Intervals.dimensionsAsLongArray(imgP))
  ImgUtil.copy(ImgView.wrap(imgP, imgA.factory()), imgA)
  IL.wrap(imgA, "two step").show()

#twoStep()


def oneStep(index=0):
  # Combining transforms into one, via a translation to account of the ROI crop
  img = klb.readFull(filepaths[index]) # klb_loader.get(filepaths[index])
  t1 = cmIsotropicTransforms[index]
  t2 = affine3D([1, 0, 0, -roi[0][0],
                 0, 1, 0, -roi[0][1],
                 0, 0, 1, -roi[0][2]])
  t3 = affine3D(fineTransformsPostROICrop[index]).inverse()
  aff = AffineTransform3D()
  aff.set(t1)
  aff.preConcatenate(t2)
  aff.preConcatenate(t3)
  # Final interval is now rooted at 0,0,0 given that the transform includes the translation
  imgP = prepareImgForDeconvolution(img, aff, FinalInterval([0, 0, 0], [maxC - minC  for minC, maxC in izip(roi[0], roi[1])]))
  # Copy transformed view into ArrayImg for best performance in deconvolution
  imgA = ArrayImgs.floats(Intervals.dimensionsAsLongArray(imgP))
  ImgUtil.copy(ImgView.wrap(imgP, imgA.factory()), imgA)
  IL.wrap(imgA, "one step index %i" % index).show()

oneStep(index=2)
oneStep(index=3)

# The performance is massively different:
#   oneStep is a few seconds,
#   whereas twoStep takes minutes


