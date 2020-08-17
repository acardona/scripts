# Create synthetic EM neuro training data: blurred edges of the same thickness as membranes
"""
from net.imglib2.img.array import ArrayImgs
from jarray import zeros
from java.util import Arrays
from net.imglib2.algorithm.gauss3.Gauss3 import gauss
from net.imglib2.view import Views
from net.imglib2.img.display.imagej import ImageJFunctions as IL


thickness = 4 # of two membranes together
synth = ArrayImgs.floats([32, 32])
pixels = synth.update(None).getCurrentStorageArray() # float[]
# Fill all light grey
Arrays.fill(pixels, 172)
# Paint black horizontal line
for i in xrange(15, 17):
  Arrays.fill(pixels, i * synth.dimension(0), (i + 1) * synth.dimension(0), 0)
# Blur
gauss(1.25, Views.extendMirrorSingle(synth), synth)

imp = IL.wrap(synth, "synth blurred")
imp.getProcessor().setMinAndMax(0, 255)
imp.show()
"""


# With ImageJ data structures
from java.util import Arrays
from ij.process import FloatProcessor, ImageProcessor
from ij import ImagePlus, ImageStack
from ij.plugin.filter import GaussianBlur
from ij.gui import Line


# Synthetic EM double membrane 2D

def syntheticEM(fillLineIndices,
                width, height,
                lineValue, backgroundValue,
                rois=None,
                sigma=1.4,
                noise=False,
                noise_sd=25.0,
                show=False):
  ip = FloatProcessor(width, height)
  pixels = ip.getPixels()
  # Fill background
  Arrays.fill(pixels, backgroundValue)
  # Paint black horizontal line
  for i in fillLineIndices:
    Arrays.fill(pixels, i * width, (i + 1) * height, lineValue)
  if rois:
    ip.setColor(lineValue)
    for roi in rois:
      ip.draw(roi)
  # Blur
  GaussianBlur().blurFloat(ip, 0, sigma, 0.02)
  if noise:
    ip.noise(noise_sd)
  ip.setMinAndMax(0, 255)
  imp = ImagePlus("synth", ip)
  if show:
    imp.show()
  return imp


width, height = 32, 32
fillValue = 0
backgroundValue = 172

synthMembrane = syntheticEM(xrange(14, 17), width, height, fillValue, backgroundValue)
synthMitochondriaBoundary = syntheticEM(xrange(0, 16), width, height, fillValue, backgroundValue)


def generateRotations(imp, backgroundValue):
  # Generate stack of rotations with noise
  ip = imp.getProcessor()
  rotations = ImageStack(ip.getWidth(), ip.getHeight())
  for i in xrange(10): # up to 90 degrees
    ipr = ip.duplicate()
    ipr.setInterpolationMethod(ImageProcessor.BILINEAR)
    ipr.setBackgroundValue(backgroundValue)
    ipr.rotate(i * 10)
    ipr.noise(25) # sd = 25
    rotations.addSlice(ipr)
  return rotations

ImagePlus("synth rot membrane", generateRotations(synthMembrane, 172)).show()
ImagePlus("synth rot mitochondria boundary", generateRotations(synthMitochondriaBoundary, 172)).show()













