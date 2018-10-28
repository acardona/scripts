from mpicbg.imagefeatures import FloatArray2DSIFT, FloatArray2D
from mpicbg.models import PointMatch, TranslationModel2D, NotEnoughDataPointsException
from ij import IJ, ImagePlus
from ij.gui import PointRoi, Roi
from ij.plugin.frame import RoiManager

# Parameters for extracting Scale Invariant Feature Transform features
p = FloatArray2DSIFT.Param()
p.fdSize = 4 # number of samples per row and column
p.fdBins = 8 # number of bins per local histogram
p.maxOctaveSize = 512 # largest scale octave in pixels
p.minOctaveSize = 128   # smallest scale octave in pixels
p.steps = 3 # number of steps per scale octave
p.initialSigma = 1.6

def extractFeatures(ip, params):
  sift = FloatArray2DSIFT(params)
  sift.init(FloatArray2D(ip.convertToFloat().getPixels(),
                         ip.getWidth(), ip.getHeight()))
  features = sift.run() # instances of mpicbg.imagefeatures.Feature
  return features

# Open Nile Bend sample image
imp = IJ.getImage()

# Cut out two overlapping ROIs
roi1 = Roi(1708, 680, 1792, 1760)
roi2 = Roi(520, 248, 1660, 1652)

imp.setRoi(roi1)
imp1 = ImagePlus("cut 1", imp.getProcessor().crop())
imp1.show()

imp.setRoi(roi2)
imp2 = ImagePlus("cut 2", imp.getProcessor().crop())
imp2.show()

features1 = extractFeatures(imp1.getProcessor(), p)
features2 = extractFeatures(imp2.getProcessor(), p)

# Feature locations as points in an ROI
# Store feature locations in the Roi manager for visualization later
roi_manager = RoiManager()

roi1 = PointRoi()
roi1.setName("features for cut1")
for f in features1:
  roi1.addPoint(f.location[0], f.location[1])

roi_manager.addRoi(roi1)

roi2 = PointRoi()
roi2.setName("features for cut2")
for f in features2:
  roi2.addPoint(f.location[0], f.location[1])

roi_manager.addRoi(roi2)

# Find matches between the two sets of features
# (only by whether the properties of the features themselves match,
#  not by their spatial location.)
rod = 0.9 # ratio of distances in feature similarity space (closest/next closest match)
pointmatches = FloatArray2DSIFT.createMatches(features1, features2, rod)

# Some matches are spatially incoherent: filter matches with RANSAC
model = TranslationModel2D() # We know there's only a translation
candidates = pointmatches # possibly good matches as determined above
inliers = [] # good point matches, to be filled in by model.filterRansac
maxEpsilon = 25.0 # max allowed alignment error in pixels (a distance)
minInlierRatio = 0.05 # ratio inliers/candidates
minNumInliers = 5 # minimum number of good matches to accept the result

try:
  modelFound = model.filterRansac(candidates, inliers, 1000,
                                  maxEpsilon, minInlierRatio, minNumInliers)
  if modelFound:
    PointMatch.apply(inliers, model) # TODO what is this for?
except NotEnoughDataPointsException, e:
  print e

if modelFound:
  # Store pointmatches (a subset of the extracted features: the intersection)
  roi1pm = PointRoi()
  roi1pm.setName("matches in cut1")
  roi2pm = PointRoi()
  roi2pm.setName("matches in cut2")

  for pm in inliers:
    p1 = pm.getP1()
    roi1pm.addPoint(p1.getL()[0], p1.getL()[1])
    p2 = pm.getP2()
    roi2pm.addPoint(p2.getL()[0], p2.getL()[1])

  roi_manager.addRoi(roi1pm)
  roi_manager.addRoi(roi2pm)





