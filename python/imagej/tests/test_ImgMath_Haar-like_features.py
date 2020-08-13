from net.imglib2.algorithm.math.ImgMath import compute, block, sub, add, maximum, minimum
from net.imglib2.img.display.imagej import ImageJFunctions as IL
from net.imglib2.algorithm.integral import IntegralImg
from net.imglib2.type.numeric.integer import UnsignedLongType
from net.imglib2.type.numeric.real import FloatType
from net.imglib2.view import Views
from net.imglib2.algorithm.math.abstractions import Util
from ij import IJ, WindowManager
import re


imp = WindowManager.getImage("180-220-sub512x512-30.tif") # IJ.getImage() # e.g. 8-bit EM of Drosophila neurons 180-220-sub512x512-30.tif
#imp = IJ.openImage("/home/albert/lab/TEM/abd/microvolumes/Seg/180-220-sub/180-220-sub512x512-30.tif")
img = IL.wrap(imp)

# Create the integral image, stored as 64-bit
alg = IntegralImg(img, UnsignedLongType(), Util.genericIntegerTypeConverter())
alg.process()
integralImg = alg.getResult()
imgE = Views.extendBorder(integralImg)

# Haar-like features from Viola and Jones
# tuned to identify neuron membranes

# Two adjacent vertical rectangles 4x8 - 4x8
cornersVL = [[-3, -4], [0, -4], [-3, 3], [0, 3]]
cornersVR = [[ 1, -4], [4, -4], [ 1, 3], [4, 3]]
blockVL = block(imgE, cornersVL)
blockVR = block(imgE, cornersVR)
op1 = sub(blockVL, blockVR)
op2 = sub(blockVR, blockVL)

# Two adjacent horizontal rectangles 4x8 - 4x8
cornersHT = [[-4, -3], [3, -3], [-4, 0], [3, 0]]
cornersHB = [[-4,  1], [3,  1], [-4, 4], [3, 4]]
blockHT = block(imgE, cornersHT)
blockHB = block(imgE, cornersHB)
op3 = sub(blockHT, blockHB)
op4 = sub(blockHB, blockHT)

for i, op in enumerate([op1, op2, op3, op4]):
  IL.wrap(op.view(FloatType()), "op%i" % i).show()
