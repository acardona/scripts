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
imp.show()

# Try training for slightly off-center pixels from the drawed lines
#ovals1 = [OvalRoi(r.x -1, r.y -1, r.width +1, r.height +1) for r in [oval.getBounds() for oval in rois]]
#ovals2 = [OvalRoi(r.x +1, r.y +1, r.width -1, r.height -1) for r in [oval.getBounds() for oval in rois]]

# Membrane, from the ovals: 312 points
membrane = reduce(lambda cs, pol: [cs[0] + list(pol.xpoints), cs[1] + list(pol.ypoints)],
                  [roi.getPolygon() for roi in rois], [[], []])

# Membrane oblique, fuzzy: another 76 points
membrane_oblique = reduce(lambda cs, pol: [cs[0] + list(pol.xpoints), cs[1] + list(pol.ypoints)],
                  [roi.getPolygon() for roi in [roi_oblique]], [[], []])

len_membrane = len(membrane[0]) + len(membrane_oblique[0])

# Background samples: as many as membrane samples
rectangle = Roi(10, 10, w - 20, h - 20)
pol = rectangle.getInterpolatedPolygon(1.0, False) # 433 points
nonmem = (list(int(x) for x in pol.xpoints)[:len_membrane],
          list(int(y) for y in pol.ypoints)[:len_membrane])



####

import sys
sys.path.append("/home/albert/lab/scripts/python/imagej/IsoView-GCaMP/")
from lib.segmentation_em import createSMOClassifier, createRandomForestClassifier, classify, \
                                filterBank, filterBankRotations, filterBankBlockStatistics
from net.imglib2.img.display.imagej import ImageJFunctions as IL
from itertools import izip

def samples():
  for class_index, (xs, ys) in enumerate([membrane, membrane_oblique, nonmem]):
    for x, y in izip(xs, ys):
      yield [x, y], class_index

class_names = ["membranes", "mem_oblique", "nonmem"]

img = IL.wrap(imp)

ops = filterBank(img)
angles = [0, 30] # range(0, 46, 9)
#ops = filterBankRotations(img, angles=angles, bs=4, bl=8)
#ops = filterBankBlockStatistics(img, block_width=5, block_height=5)

# Create a classifier: support vector machine (SVM, an SMO in WEKA)
# and save it for later
classifierSMO = createSMOClassifier(img, samples(), class_names, ops=ops,
                                    n_samples=len(membrane[0]), filepath="/tmp/svm-mem-nonmem")

print classifierSMO.toString()

classifierRF = createRandomForestClassifier(img, samples(), class_names, ops=ops,
                                            n_samples=len(membrane[0]), filepath="/tmp/rf-mem-nonmem")


print classifierRF.toString()


impEM = WindowManager.getImage("180-220-sub512x512-30.tif") # IJ.getImage() # e.g. 8-bit EM of Drosophila neurons 180-220-sub512x512-30.tif
#impEM = IJ.openImage("/home/albert/lab/TEM/abd/microvolumes/Seg/180-220-sub/180-220-sub512x512-30.tif")
imgEM = IL.wrap(impEM)

ops = filterBank(imgEM)
#ops = filterBankRotations(imgEM, angles=angles)
#ops = filterBankBlockStatistics(imgEM, block_width=5, block_height=5)

# Classify pixels as membrane or not
resultSMO = classify(imgEM, classifierSMO, class_names, ops=ops)
IL.wrap(resultSMO, "result SMO %s" % str(angles)).show()

resultRF = classify(imgEM, classifierRF, class_names, ops=ops, distribution_class_index=-1)
IL.wrap(resultRF, "result RF %s" % str(angles)).show()










