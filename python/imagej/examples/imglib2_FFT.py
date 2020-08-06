from net.imglib2.algorithm.fft2 import FFT
from net.imglib2.img.display.imagej import ImageJFunctions as IL
from net.imglib2.img.array import ArrayImgFactory
from net.imglib2.type.numeric.complex import ComplexFloatType
from ij import IJ

img = IL.wrap(IJ.getImage()) # a RealType image
imgfft = FFT.realToComplex(img, ArrayImgFactory(ComplexFloatType()))

IL.wrap(imgfft, "fft").show()