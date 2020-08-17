from ij import IJ, ImagePlus, WindowManager
from ij.process import FloatProcessor
from ij.gui import OvalRoi, Roi
from ij.plugin.filter import GaussianBlur
from java.util import Random

w, h = 128, 128
fp = FloatProcessor(w, h)
imp = ImagePlus("synth training", fp)

fp.setColor(150) # background
fp.fill()

# neurites
rois = [OvalRoi(w/2 - w/4, h/2 - h/4, w/4, h/2), # stretched vertically
        OvalRoi(w/2, h/2 - h/8, w/4, h/4),
        OvalRoi(w/2 - w/18, h/2 + h/10, w/6, h/4),
        OvalRoi(w/2 - w/18, h/8 + h/16, w/3, h/5)]

fp.setColor(0) # membrane
fp.setLineWidth(3)

for roi in rois:
  fp.draw(roi)

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

imp.show()

# Membrane, from the ovals: 312 points
membrane = reduce(lambda cs, pol: [cs[0] + list(pol.xpoints), cs[1] + list(pol.ypoints)],
                  [roi.getPolygon() for roi in rois], [[], []])

# Background samples: as many as membrane samples
rectangle = Roi(10, 10, w - 20, h - 20)
pol = rectangle.getInterpolatedPolygon(1.0, False) # 433 points
nonmem = (list(int(x) for x in pol.xpoints)[:len(membrane[0])],
          list(int(y) for y in pol.ypoints)[:len(membrane[0])])



####

import sys
sys.path.append("/home/albert/lab/scripts/python/imagej/IsoView-GCaMP/")
from lib.features_em import createSMOClassifier, createRandomForestClassifier, classify
from net.imglib2.img.display.imagej import ImageJFunctions as IL
from itertools import izip

def samples():
  for class_index, (xs, ys) in enumerate([membrane, nonmem]):
    for x, y in izip(xs, ys):
      yield [x, y], class_index

# Create a classifier: support vector machine (SVM, an SMO in WEKA)
# and save it for later
classifierSMO = createSMOClassifier(IL.wrap(imp), samples(), ["membranes", "nonmem"],
                                    n_samples=len(membrane[0]), filepath="/tmp/svm-mem-nonmem")

print classifierSMO.toString()

classifierRF = createRandomForestClassifier(IL.wrap(imp), samples(), ["membranes", "nonmem"],
                                            n_samples=len(membrane[0]), filepath="/tmp/rf-mem-nonmem")


print classifierRF.toString()


impEM = WindowManager.getImage("180-220-sub512x512-30.tif") # IJ.getImage() # e.g. 8-bit EM of Drosophila neurons 180-220-sub512x512-30.tif
#impEM = IJ.openImage("/home/albert/lab/TEM/abd/microvolumes/Seg/180-220-sub/180-220-sub512x512-30.tif")
imgEM = IL.wrap(impEM)

# Classify pixels as membrane or not
resultSMO = classify(imgEM, "/tmp/svm-mem-nonmem", class_names=None)
IL.wrap(resultSMO, "result SMO").show()

resultRF = classify(imgEM, "/tmp/rf-mem-nonmem", class_names=None)
IL.wrap(resultRF, "result RF").show()














