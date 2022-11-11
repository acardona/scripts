import sys, csv, math
from net.imglib2 import KDTree, RealPoint
from net.imglib2.neighborsearch import RadiusNeighborSearchOnKDTree
sys.path.append("/home/albert/lab/scripts/python/imagej/IsoView-GCaMP")
from lib.features_asm import initNativeClasses
ConstellationFast, PointMatches = initNativeClasses()
extractFeatures = ConstellationFast.extractFeatures
from lib.util import syncPrintQ, nativeArray
from itertools import combinations
from collections import defaultdict
from pprint import pprint
from mpicbg.models import Point, PointMatch, AffineModel3D, MovingLeastSquaresTransform, NotEnoughDataPointsException
from java.util import ArrayList

# Has a one line header with "<index>, 0, 1, 2"
#em_points_csv = "/home/albert/lab/projects/20221111_Michael_Clayton_EM-LSM_registration/GABA volume/em_points.csv"
#lsm_points_csv = "/home/albert/lab/projects/20221111_Michael_Clayton_EM-LSM_registration/GABA volume/lsm.csv"
em_points_csv = "/home/albert/lab/projects/20221111_Michael_Clayton_EM-LSM_registration/GABA volume/left hemisphere crop/em_points_cut.csv"
lsm_points_csv = "/home/albert/lab/projects/20221111_Michael_Clayton_EM-LSM_registration/GABA volume/left hemisphere crop/lsm_points_cut.csv"

somaDiameter = 8 # one nucleus of 4 micrometres is about 8 pixels

radius = 2.5 * somaDiameter  # search radius for KDTree in arbitrary units
min_angle = 0.1 * math.pi

# Tolerable error
angle_epsilon = math.radians(3) # 3 degrees: acceptable error when comparing constellation angles, in radians
len_epsilon = 3.0 # acceptable error when comparing lengths of the arms of a constellation


# For finding inliners among possible pointmatches
maxEpsilon = somaDiameter # max allowed alignment error in calibrated units  
minInlierRatio = 0.0000001 # ratio inliers/candidates  
minNumInliers = 5 # minimum number of good matches to accept the result  
n_iterations = 100 # for estimating the model  
maxTrust = 4 # for rejecting candidates  


def parseCSV(filepath, header_length=1):
  with open(filepath, 'r') as csvfile:
    reader = csv.reader(csvfile, delimiter=',', quotechar="\"")
    header_rows = [reader.next() for i in xrange(header_length)]
    rows = [columns for columns in reader]
    return header_rows, rows

def loadPoints(filepath):
  return map(lambda row: map(float, row[1:]), parseCSV(filepath)[1])


# Load coordinates
em_points = loadPoints(em_points_csv)
lsm_points = loadPoints(lsm_points_csv)


f_angle = ConstellationFast.getDeclaredField("angle")
f_angle.setAccessible(True)

# Create features that are position and orientation independent, but not size
def makeConstellations(points):
  counter = defaultdict(int)
  tree = KDTree(range(len(points)), map(RealPoint.wrap, points)) # a KDTree that returns the index of the point for each point
  search = RadiusNeighborSearchOnKDTree(tree)
  features = defaultdict(list)
  for k, point in enumerate(points):
    p0 = RealPoint.wrap(point)
    search.search(p0, radius, True) # sorted by distance
    n = search.numNeighbors()
    counter[n] = counter[n] + 1
    # Take all possible pairs from 1 to n exclusive
    for i, j in combinations(xrange(1, n), 2):
      p1, d1 = search.getPosition(i), search.getSquareDistance(i)
      p2, d2 = search.getPosition(j), search.getSquareDistance(j)
      cons = ConstellationFast.fromSearch(p0, p1, d1, p2, d2)
      # Filter by min_angle
      if f_angle.get(cons) >= min_angle:
        features[k].append(cons)
  pprint(counter)
  return tree, search, features

# Constellations
_, em_search, em_features = makeConstellations(em_points)
_, lsm_search, lsm_features = makeConstellations(lsm_points)

print "Number of features: EM ", sum(map(len, em_features.itervalues())), ", LSM: ", sum(map(len, lsm_features.itervalues()))

# Find feature correspondences
correspondences = []
for k, lsm_point in enumerate(lsm_points):
  # List of LSM features to compare against EM features
  lsm_cons = lsm_features[k] # k is the same index over lsm_points
  
  em_search.search(RealPoint.wrap(lsm_point), radius, False) # No need to sort
  n = em_search.numNeighbors()
  for i in xrange(n):
    k_em = em_search.getSampler(i).get()
    for em_con in em_features[k_em]:
      for lsm_con in lsm_cons:
        if lsm_con.matches(em_con, angle_epsilon, len_epsilon):
          correspondences.append([k, lsm_point, k_em, em_points[k_em]])
          #syncPrintQ(correspondences[-1])
    
# Convert to mpicbg datastructures from Saalfeld
pointmatches = [PointMatch(Point(c[1]), Point(c[3])) for c in correspondences]

# RANSAC
def fit(model, pointmatches, n_iterations, maxEpsilon,
        minInlierRatio, minNumInliers, maxTrust):
  """ Fit a model to the pointmatches, finding the subset of inlier pointmatches
      that agree with a joint transformation model. """
  inliers = ArrayList()
  try:
    modelFound = model.filterRansac(pointmatches, inliers, n_iterations,
                                    maxEpsilon, minInlierRatio, minNumInliers, maxTrust)
  except NotEnoughDataPointsException, e:
    syncPrint(str(e))
    return False, inliers
  return modelFound, inliers

model = AffineModel3D()
modelFound, inliers = fit(model, pointmatches, n_iterations, maxEpsilon,
                          minInlierRatio, minNumInliers, maxTrust)

a = nativeArray('d', [3, 4])
model.toMatrix(a) # Can't use model.toArray: different order of elements
matrix = a[0] + a[1] + a[2] # Concat: flatten to 1-dimensional array

print "modelFound", modelFound

print "Model:", a
print "Model:", matrix

for i, pm in enumerate(inliers):
  print i, list(pm.getP1().getW()), list(pm.getP2().getW())


# TODO: MovingLeastSquaresTransform or ThinPlateSplineTransform























