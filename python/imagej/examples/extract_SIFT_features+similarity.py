from mpicbg.imagefeatures import FloatArray2DSIFT, FloatArray2D
from mpicbg.models import PointMatch, SimilarityModel2D, NotEnoughDataPointsException
from ij import IJ, ImagePlus, ImageStack
from ij.gui import PointRoi, Roi, PolygonRoi
from ij.plugin.frame import RoiManager
from jarray import zeros
from collections import deque

# Open Nile Bend sample image
imp = IJ.getImage()
#imp = IJ.openImage("https://imagej.nih.gov/ij/images/NileBend.jpg")

# Cut out two overlapping ROIs
roi1 = Roi(1708, 680, 1792, 1760)
roi2 = Roi(520, 248, 1660, 1652)

imp.setRoi(roi1)
imp1 = ImagePlus("cut 1", imp.getProcessor().crop())
imp1.show()

imp.setRoi(roi2)
ipc2 = imp.getProcessor().crop()
ipc2.setInterpolationMethod(ipc2.BILINEAR)
ipc2.rotate(67) # degrees clockwise
ipc2 = ipc2.resize(int(ipc2.getWidth() / 1.6 + 0.5))
imp2 = ImagePlus("cut 2", ipc2)
imp2.show()

# Parameters for extracting Scale Invariant Feature Transform features
p = FloatArray2DSIFT.Param()
p.fdSize = 4 # number of samples per row and column
p.fdBins = 8 # number of bins per local histogram
p.maxOctaveSize = 1024 # largest scale octave in pixels
p.minOctaveSize = 128   # smallest scale octave in pixels
p.steps = 4 # number of steps per scale octave
p.initialSigma = 1.6

def extractFeatures(ip, params):
  sift = FloatArray2DSIFT(params)
  sift.init(FloatArray2D(ip.convertToFloat().getPixels(),
                         ip.getWidth(), ip.getHeight()))
  features = sift.run() # instances of mpicbg.imagefeatures.Feature
  return features

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
model = SimilarityModel2D()
candidates = pointmatches # possibly good matches as determined above
inliers = [] # good point matches, to be filled in by model.filterRansac
maxEpsilon = 25.0 # max allowed alignment error in pixels (a distance)
minInlierRatio = 0.05 # ratio inliers/candidates
minNumInliers = 5 # minimum number of good matches to accept the result

try:
  modelFound = model.filterRansac(candidates, inliers, 1000,
                                  maxEpsilon, minInlierRatio, minNumInliers)
  if modelFound:
    # Apply the transformation defined by the model to the first point
    # of each pair (PointMatch) of points. That is, to the point from
    # the first image.
    PointMatch.apply(inliers, model)
except NotEnoughDataPointsException, e:
  print e

if modelFound:
  # Store inlier pointmatches: the spatially coherent subset
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

  # Register images  
  # Transform the top-left and bottom-right corner of imp2
  # (use applyInverse: the model describes imp1 -> imp2)
  x0, y0 = model.applyInverse([0, 0])
  x1, y1 = model.applyInverse([imp2.getWidth(), 0])
  x2, y2 = model.applyInverse([0, imp2.getHeight()])
  x3, y3 = model.applyInverse([imp2.getWidth(), imp2.getHeight()])
  xtopleft = min(x0, x1, x2, x3)
  ytopleft = min(y0, y1, y2, y3)
  xbottomright = max(x0, x1, x2, x3)
  ybottomright = max(y0, y1, y2, y3)
  
  # Determine dimensions of the montage of registered images
  canvas_width = int(max(imp1.getWidth(), xtopleft) - min(0, xtopleft))
  canvas_height = int(max(imp1.getHeight(), ytopleft) - min(0, ytopleft))
  
  # Create a 2-slice stack with both images aligned, one on each slice
  stack = ImageStack(canvas_width, canvas_height)

  # Insert imp1
  slice1 = imp1.getProcessor().createProcessor(canvas_width, canvas_height)
  slice1.insert(imp1.getProcessor(), int(0 if xtopleft > 0 else abs(xtopleft)),
                                     int(0 if ytopleft > 0 else abs(ytopleft)))
  stack.addSlice("cut1", slice1)
  
  # Transform imp2 into imp1 coordinate space
  source = imp2.getProcessor()
  source.setInterpolationMethod(source.BILINEAR)
  target = imp1.getProcessor().createProcessor(int(xbottomright - xtopleft),
                                               int(ybottomright - ytopleft))
  
  p = zeros(2, 'd')

  # The translation offset: the transformed imp2 layes mostly outside
  # of imp1, so shift x,y coordinates to be able to render it within target
  xoffset = 0 if xtopleft > 0 else xtopleft
  yoffset = 0 if ytopleft > 0 else ytopleft

  def pull(source, target, x, xoffset, y, yoffset, p, model):
    p[0] = x + xoffset
    p[1] = y + yoffset
    model.applyInPlace(p) # imp1 -> imp2, target is in imp1 coords, source in imp2 coords.
    # getPixelInterpolated returns 0 when outside the image
    target.setf(x, y, source.getPixelInterpolated(p[0], p[1]))
  
  deque(pull(source, target, x, xoffset, y, yoffset, p, model)
          for x in xrange(target.getWidth())
          for y in xrange(target.getHeight()),
        maxlen=0)

  slice2 = slice1.createProcessor(canvas_width, canvas_height)
  slice2.insert(target, int(0 if xtopleft < 0 else xtopleft),
                        int(0 if ytopleft < 0 else ytopleft))
  stack.addSlice("cut2", slice2)
  imp = ImagePlus("registered", stack)
  imp.show()
