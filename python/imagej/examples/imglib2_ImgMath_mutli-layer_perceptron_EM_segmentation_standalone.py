# Generate synthetic data emulating an electron microscopy image
# of a serial section of dense neural tissue
from ij import IJ, ImagePlus
from ij.process import FloatProcessor
from ij.gui import OvalRoi, Roi
from ij.plugin.filter import GaussianBlur
from java.util import Random

w, h = 128, 128
fp = FloatProcessor(w, h)
imp_synth = ImagePlus("synth training", fp)
backgroundValue = 150
fp.setColor(backgroundValue)
fp.fill()

# neurites
rois = [OvalRoi(w/2 - w/4, h/2 - h/4, w/4, h/2), # stretched vertically
        OvalRoi(w/2, h/2 - h/8, w/4, h/4),
        OvalRoi(w/2 - w/18, h/2 + h/10, w/6, h/4),
        OvalRoi(w/2 - w/18, h/8 + h/16, w/3, h/5)]

fp.setColor(50) # membrane
fp.setLineWidth(3)

for roi in rois:
  fp.draw(roi)

fp.setColor(90) # oblique membrane
fp.setLineWidth(5)
roi_oblique = OvalRoi(w/2 + w/8, h/2 + h/8, w/4, h/4)
fp.draw(roi_oblique)

# Add noise
# 1. Vesicles
fp.setLineWidth(1)
random = Random(67779)
for i in xrange(150):
  x = random.nextFloat() * (w-1)
  y = random.nextFloat() * (h-1)
  fp.draw(OvalRoi(x, y, 4, 4))

fp.setRoi(None)

# 2. blur
sigma = 1.0
GaussianBlur().blurFloat(fp, sigma, sigma, 0.02)
# 3. shot noise
fp.noise(25.0)

fp.setMinAndMax(0, 255)
imp_synth.show()

# 3 classes, to which we'll assign later indices 0, 1, 2:
# Class 0. Membrane, from the ovals: 312 points
membrane = reduce(lambda cs, pol: [cs[0] + list(pol.xpoints), cs[1] + list(pol.ypoints)],
                  [roi.getPolygon() for roi in rois], [[], []])

# Class 1. Membrane oblique, fuzzy: another 76 points
membrane_oblique = reduce(lambda cs, pol: [cs[0] + list(pol.xpoints), cs[1] + list(pol.ypoints)],
                  [roi.getPolygon() for roi in [roi_oblique]], [[], []])

len_membrane = len(membrane[0]) + len(membrane_oblique[0])

# Class 2. Background samples: as many as membrane samples
rectangle = Roi(10, 10, w - 20, h - 20)
pol = rectangle.getInterpolatedPolygon(1.0, False) # 433 points
nonmem = (list(int(x) for x in pol.xpoints)[:len_membrane],
          list(int(y) for y in pol.ypoints)[:len_membrane])


# Machine learning: learn to classify neuron membranes from the synthetic samples
from weka.classifiers.functions import MultilayerPerceptron
from net.imglib2.algorithm.math.ImgMath import offset
from net.imglib2.view import Views
from net.imglib2.img.display.imagej import ImageJFunctions as IL
import os, tempfile
from itertools import izip
from ij import WindowManager

#####
# NOTE: these functions were defined above but are used here:
#    trainClassifier
#    sampleTrainingData
#    classify
# Please put them in a file along with their imports,
# then import only these two functions like e.g.:
# from mylib import classify, trainClassifier
#####
import sys
sys.path.append("/home/albert/lab/scripts/python/imagej/IsoView-GCaMP/")
from lib.segmentation_em import classify, trainClassifier


# A generator of training samples: coords over the ROIs and their class index
def samples():
  for class_index, (xs, ys) in enumerate([membrane, membrane_oblique, nonmem]):
    for x, y in izip(xs, ys):
      yield [x, y], class_index

class_names = ["membranes", "mem_oblique", "nonmem"]


def createPerceptronClassifier(img, samples, class_names, ops,
                               n_samples=0, filepath=None, params={}):
  mp = MultilayerPerceptron()
  if "learning_rate" in params:
    # In (0, 1]
    mp.setLearningRate(params.get("learning_rate", mp.getLearningRate()))
  # Number of nodes per layer: a set of comma-separated values (numbers), or:
  # 'a' = (number of attributes + number of classes) / 2
  # 'i' = number of attributes,
  # 'o' = number of classes
  # 't' = number of attributes + number of classes.
  # See MultilayerPerceptron.setHiddenLayers
  # https://weka.sourceforge.io/doc.dev/weka/classifiers/functions/MultilayerPerceptron.html#setHiddenLayers-java.lang.String-
  hidden_layers = "%i,%i,%i" % (len(ops) * 3, int(len(ops) * 1.5 + 0.5), len(ops) * 3)
  mp.setHiddenLayers(params.get("hidden_layers", hidden_layers))
  return trainClassifier(mp, img, samples, class_names, ops=ops,
                         n_samples=n_samples, filepath=filepath)


def readPatch(img, width=5):
  """ Returns as many ops as pixels within a square block of pixels (a patch) 
      centered each pixel, each reading the plain pixel value. """
  half = width / 2 # e.g. for 5, it's 2
  imgE = Views.extendBorder(img)
  ops = [offset(imgE, [x, y]) for x in xrange(-half, half + 1)
                              for y in xrange(-half, half + 1)]
  return ops


# Train a multi-layer perceptron with the synthetic data
img_synth = IL.wrap(imp_synth)

ops = readPatch(img_synth, width=5)
params = {"learning_rate": 0.5,
          "hidden_layers": "%i,%i,%i" % (len(ops) * 3, int(len(ops) * 1.5 + 0.5), len(ops) * 3)
         }
filepath = os.path.join(tempfile.gettempdir(), "mp-mem-nonmem")
classifierMP = createPerceptronClassifier(img_synth, samples(), class_names, ops,
                                          n_samples=len(membrane[0]),
                                          filepath=filepath,
                                          params=params)
print classifierMP.toString()

# Apply the trained perceptron to the EM image
# ASSUMES the image 180-220-sub512x512-30.tif is open
imgEM = IL.wrap(WindowManager.getImage("180-220-sub512x512-30.tif"))
ops = readPatch(imgEM, width=5)

resultMP = classify(imgEM, classifierMP, class_names, ops=ops,
                    distribution_class_index=-1)
IL.wrap(resultMP, "Multi-layer perceptron segmentation").show()



# Now with block statistics, including rotated blocks

from net.imglib2.realtransform import AffineTransform2D
from net.imglib2.realtransform import RealViews as RV
from net.imglib2.util import Intervals
from net.imglib2.interpolation.randomaccess import NLinearInterpolatorFactory
from net.imglib2.type.numeric.real import FloatType
from net.imglib2.algorithm.math.ImgMath import compute, minimum
from itertools import product, repeat
from jarray import array, zeros
from java.util import ArrayList
from math import radians, floor, ceil

####
# Note, as before, you'll need to import also this function
# that was defined above, e.g. if you save it in mylib.py then
####
from lib.segmentation_em import filterBankBlockStatistics


def rotatedView(img, angle, enlarge=True, extend=Views.extendBorder):
  """ Return a rotated view of the image, around the Z axis,
      with an expanded (or reduced) interval view so that all pixels are exactly included.

      img: a RandomAccessibleInterval
      angle: in degrees
  """
  cx = img.dimension(0) / 2.0
  cy = img.dimension(1) / 2.0
  toCenter = AffineTransform2D()
  toCenter.translate(-cx, -cy)
  rotation = AffineTransform2D()
  # Step 1: place origin of rotation at the center of the image
  rotation.preConcatenate(toCenter)
  # Step 2: rotate around the Z axis
  rotation.rotate(radians(angle))
  # Step 3: undo translation to the center
  rotation.preConcatenate(toCenter.inverse())
  rotated = RV.transform(Views.interpolate(extend(img),
                         NLinearInterpolatorFactory()), rotation)
  if enlarge:
    # Bounds:
    bounds = repeat((sys.maxint, 0)) # initial upper- and lower-bound values  
                                     # for min, max to compare against  
    transformed = zeros(2, 'f')
    for corner in product(*zip(repeat(0), Intervals.maxAsLongArray(img))):
      rotation.apply(corner, transformed)
      bounds = [(min(vmin, int(floor(v))), max(vmax, int(ceil(v))))
                for (vmin, vmax), v in zip(bounds, transformed)]
    minC, maxC = map(list, zip(*bounds)) # transpose list of 2 pairs
                                         # into 2 lists of 2 values
    imgRot = Views.zeroMin(Views.interval(rotated, minC, maxC))
  else:
    imgRot = Views.interval(rotated, img)
  return imgRot


def filterBankRotations(img,
                        filterBankFn, # function that takes an img as sole positional argument
                        angles=xrange(0, 46, 9), # sequence, in degrees
                        outputType=FloatType()):
  """ img: a RandomAccessibleInterval.
      filterBankFn: the function from which to obtain a sequence of ImgMath ops.
      angles: a sequence of angles in degrees.
      outputType: for materializing rotated operations and rotating them back.

      For every angle, will prepare a rotated view of the image,
      then create a list of ops on the basis of that rotated view,
      then materialize each op into an image so that an unrotated view
      can be returned back.

      returns a list of unrotated views, each containing the values of applying
      each op to the rotated view. 
  """
  ops_rotations = []
  
  for angle in angles:
    imgRot = img if 0 == angle else rotatedView(img, angle)
    ops = filterBankFn(imgRot)

    # Materialize these two combination ops and rotate them back (rather, a rotated view)
    interval = Intervals.translate(img, [(imgRot.dimension(d) - img.dimension(d)) / 2
                                         for d in xrange(img.numDimensions())])
    for op in ops:
      imgOpRot = compute(op).intoArrayImg(outputType)
      if 0 == angle:
        ops_rotations.append(imgOpRot)
        continue
      # Rotate them back and crop view
      imgOpUnrot = rotatedView(imgOpRot, -angle, enlarge=False)
      imgOp = Views.zeroMin(Views.interval(imgOpUnrot, interval))
      ops_rotations.append(imgOp)
  
  return ops_rotations


def makeOps(img, angles):
  # Block statistics of rotations of an elongated block
  ops = filterBankRotations(img, angles=angles,
                            filterBankFn=lambda img: filterBankBlockStatistics(img, block_width=3, block_height=7))
  # Makes it worse, surprisingly
  #ops += filterBankRotations(img, angles=angles,
  #                           filterBankFn=lambda img: filterBankBlockStatistics(img, block_width=7, block_height=3))
  # Plain block statistics of a small square block
  ops += filterBankBlockStatistics(img, block_width=3, block_height=3)
  return ops

"""
# Explicitly introduce nicks on membranes: creates more nicks!
nicks = [(34, 47), (40, 92), (112, 92)]
for x, y in nicks:
  for dx in xrange(-2, 2):
    for dy in xrange(-2, 2):
      fp.setf(x + dx, y + dy, backgroundValue)

imp_synth_nicked = ImagePlus("synth with nicks", fp)
imp_synth_nicked.show()
img_synth_nicked = IL.wrap(imp_synth_nicked)
img_synth = img_synth_nicked
"""

# List of angles for rotations
angles = [0, 15, 30, 45, 60, 75, 90]

# Train the multi-layer perceptron
ops = makeOps(img_synth, angles)
params = {"learning_rate": 0.5,
          "hidden_layers": "%i,%i,%i" % (len(ops) * 3, int(len(ops) * 1.5 + 0.5), len(ops) * 1)
         }
classifierMP = createPerceptronClassifier(img_synth, samples(), class_names, ops=ops,
                                          n_samples=len(membrane[0]),
                                          filepath="/tmp/mp-mem-nonmem-rotations-%s" % "-".join(map(str, angles)),
                                          params=params)
print classifierMP.toString()

# Apply the classifier to the electron microscopy image of nervous tissue
impEM = WindowManager.getImage("180-220-sub512x512-30.tif")
imgEM = IL.wrap(impEM)
ops = makeOps(imgEM, angles)
resultMProtations = classify(imgEM, classifierMP, class_names, ops=ops, distribution_class_index=-1)
IL.wrap(resultMProtations, "Multi-layer perceptron segmentation angles=%s" % str(angles)).show()


# The minimum of the two
combined = compute(minimum(resultMP, resultMProtations)).intoArrayImg()
IL.wrap(combined, "minimum of the two").show()

