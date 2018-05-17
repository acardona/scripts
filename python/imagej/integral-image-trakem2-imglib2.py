from net.imglib2.img.array import ArrayImg
from net.imglib2.img.basictypeaccess.array import LongArray
from net.imglib2.util import Fraction
from net.imglib2.img.display.imagej import ImageJFunctions as IJF
#from net.imglib2.img.array import ArrayImgFactory     
#from net.imglib2.type.numeric.integer import LongType

from ij import IJ
from ini.trakem2.imaging import FastIntegralImage


imp = IJ.getImage()
pix = imp.getProcessor().getPixels()

ii = FastIntegralImage.longIntegralImage(pix, imp.getWidth(), imp.getHeight())
bip = FastIntegralImage.scaleAreaAverage(im, imp.getWidth() + 1, imp.getHeight() + 1, imp.getWidth() / 4, imp.getHeight() / 4)
ImagePlus("25%",
          ByteProcessor(imp.getWidth() / 4,
                        imp.getHeight() / 4,
                        bip,
                        None)
         ).show()

arrayimg = ArrayImg(LongArray(im), [2049, 2049], Fraction())

# Fails: perhaps lacks a converter
IJF.show(arrayimg)

