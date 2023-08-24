from ij import IJ, ImagePlus, WindowManager
from ij.process import FloatProcessor
from ij.gui import OvalRoi, Roi
from ij.plugin.filter import GaussianBlur
import sys
sys.path.append("/home/albert/lab/scripts/python/imagej/IsoView-GCaMP/")
from lib.segmentation_em import createSMOClassifier, createRandomForestClassifier, classify, \
                                filterBank, filterBankRotations, filterBankBlockStatistics, filterBankEdges
from net.imglib2.img.display.imagej import ImageJFunctions as IL
from itertools import izip

# synthetic training data: a bright blob on a black background
width, height = 64, 64
bp = FloatProcessor(width, height)
synth = ImagePlus("synth blob", bp)

bp.setColor(0)
bp.fill()
bp.setColor(255)
oval = OvalRoi(width/4, height/4, width/2, height/2)
bp.fill(oval)
#sigma = 1.0
#GaussianBlur().blurFloat(bp, sigma, sigma, 0.02)
bp.noise(25)

synth.show()

def asIntCoords(roi, asFloat=True, limit=None):
  pol = roi.getInterpolatedPolygon(1.0, False) if asFloat else roi.getPolygon() # FloatPolygon
  coords = [map(int, points) for points in [pol.xpoints, pol.ypoints]]
  if limit:
    coords = coords[0][:limit], coords[1][:limit]
  return coords

# Positive examples
bounds = oval.getBounds()
oval_inside = OvalRoi(bounds.x + 1, bounds.y + 1, bounds.width - 1, bounds.height - 1)
blob_boundary = asIntCoords(oval_inside, asFloat=False)
print len(blob_boundary[0])

coords = [(x, y) for x, y in zip(blob_boundary[0], blob_boundary[1])]
print coords

# Negative examples: as many as positive ones, well oustide the oval but also far from the border
margin = min(width/8, height/8)
background_roi = Roi(margin, margin, width - margin, height - margin)
background = asIntCoords(background_roi, limit=len(blob_boundary[0]))

print len(background[0])

def samples():
  for class_index, (xs, ys) in enumerate([blob_boundary, background]):
    for x, y in izip(xs, ys):
      yield [x, y], class_index

img_training = IL.wrap(synth)
img_test = IL.wrap(WindowManager.getImage("blobs.gif"))

class_names = ["boundary", "background"]
ops = filterBankBlockStatistics(img_training)

classifierSMO = createSMOClassifier(img_training, samples(), class_names, ops=ops,
                                    n_samples=len(blob_boundary[0]), filepath="/tmp/svm-blobs-boundary")
print classifierSMO.toString()


ops = filterBankBlockStatistics(img_test)
# Classify pixels as blob boundary or not
resultSMO = classify(img_test, classifierSMO, class_names, ops=ops)
IL.wrap(resultSMO, "result SMO").show()

