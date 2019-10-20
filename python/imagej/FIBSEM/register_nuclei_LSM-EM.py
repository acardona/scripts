from __future__ import with_statement
import sys
#sys.path.append("/groups/cardona/home/cardonaa/lab/scripts/python/imagej/IsoView-GCaMP/")
sys.path.append("/home/albert/lab/scripts/python/imagej/IsoView-GCaMP/")
from net.imglib2.view import Views
from net.imglib2 import FinalInterval, RealPoint
from lib.synthetic import virtualPointsRAI
from lib.ui import showStack
from lib.features import extractFeatures, makeRadiusSearch, PointMatches
from lib.registration import fit, transformedView
from lib.util import nativeArray
from mpicbg.models import RigidModel3D


# FIBSEM: level 4, 192x192x192 nm/px
# GCaMP: deconvolved, 406x406x406 nm/px

# scale = 192.0 / 406.0

FIBSEM_nuclei_path = "/home/albert/lab/projects/20191014_Champion_FIBSEM_nuclei_detection/CLIJ_mask_destination_nucleis2-1-lbl-sizeOpening-morpho.csv"
GCaMP_nuclei_path  = "/home/albert/lab/projects/20191014_Champion_FIBSEM_nuclei_detection/CM00-CM01_fluorescence.csv"

FIBSEM_nuclei = []
GCaMP_nuclei = None

# Extract GCaMP nuclei coordinates from the header
with open(GCaMP_nuclei_path, 'r') as f:
  line = f.readline().strip() # read first line: the header, without ending line break
  GCaMP_nuclei = [tuple(float(c) for c in p[1:-1].split("::")) # trim quotes
                  for p in line.split(",")[1:]] # skip first column

# Parse nuclei coordinates from FIBSEM
with open(FIBSEM_nuclei_path, 'r') as f:
  col_names = None
  for i, line in enumerate(f):
    cols = line[:-1].split(",")
    if 0 == i:
      col_names = {name: index for index, name in enumerate(cols)}
    else:
      FIBSEM_nuclei.append(tuple(float(v) for v in cols[5:8]))


def boundsOf(nuclei):
  x0, y0, z0 = nuclei[0]
  x1, y1, z1 = nuclei[0]
  for x, y, z in nuclei:
    if x < x0: x0 = x
    if y < y0: y0 = y
    if z < z0: z0 = z
    if x > x1: x1 = x
    if y > y1: y1 = y
    if z > z1: z1 = z
  return [x0, y0, z0], \
         [x1, y1, z1]


bounds1 = boundsOf(FIBSEM_nuclei)
bounds2 = boundsOf(GCaMP_nuclei)


def dimensionsOf(bounds):
  return bounds[1][0] - bounds[0][0], \
         bounds[1][1] - bounds[0][1], \
         bounds[1][2] - bounds[0][2]

dimensions1 = dimensionsOf(bounds1)
dimensions2 = dimensionsOf(bounds2)

print dimensions1
print dimensions2


# Show both datasets
def show(title, nuclei, radius, bounds, scale=1.0):
  points = [RealPoint.wrap([c * scale for c in coords]) for coords in nuclei]
  interval = FinalInterval([int(b * scale) for b in bounds[0]],
                           [int(b * scale) for b in bounds[1]])
  img = virtualPointsRAI(points, radius * scale, interval)
  imp = showStack(img, title=title)
  return imp, img, points

# FIBSEM: resolution is 192x192x192 nm/px (level 4)
radius1 = 2000 / 192.0 # 4-micron nucleus
imp1, img1, points1 = show("FIBSEM", FIBSEM_nuclei, radius1, bounds1, scale=192/406.0)

# GCaMP: resolution is 406x406x406 nm/px (deconvolved)
radius2 = 2000 / 406.0
imp2, img2, points2 = show("GCaMP", GCaMP_nuclei, radius2, bounds2)


# Register FIBSEM onto GCaMP (they are already at the same scale)
somaDiameter = 4000 / 406.0 # 4 microns
search_radius = 10 * somaDiameter
min_angle = 0.1 # in radians  # 0.05 is 2.8 degrees, 0.02 is 1.1 degrees
max_per_peak = 30
angle_epsilon = 0.02
len_epsilon_sq = pow(somaDiameter, 2)

search1 = makeRadiusSearch(points1) # FIBSEM points are scaled to match GCaMP points coordinate space
search2 = makeRadiusSearch(points2)

features1 = extractFeatures(points1, search1, search_radius, min_angle, max_per_peak)
features2 = extractFeatures(points2, search2, search_radius, min_angle, max_per_peak)

# Could use "fromNearbyFeatures" if both data sets were roughly aligned already.
pm = PointMatches.fromFeatures(features1, features2,
                               angle_epsilon, len_epsilon_sq)

maxEpsilon = somaDiameter # max allowed alignment error in calibrated units (a distance)
minInlierRatio = 0.0000001 # ratio inliers/candidates
minNumInliers = 16 # minimum number of good matches to accept the result
n_iterations = 1000 # for estimating the model
maxTrust = 4 # for rejecting candidates

model = RigidModel3D()
modelFound, inliers = fit(model, pm.pointmatches, n_iterations, maxEpsilon,
                          minInlierRatio, minNumInliers, maxTrust)

if modelFound:
  print "Model found:", model
  print "with %i inliers" % len(inliers)
  a = nativeArray('d', [3, 4])
  model.toMatrix(a) # Can't use model.toArray: different order of elements
  matrix = a[0] + a[1] + a[2] # Concat: flatten to 1-dimensional array
  print "and transformation matrix:", list(matrix)

  # Transform the FIBSEM points with the model (rather than transforming the image)
  t_coords = []
  a = nativeArray('d', [3])
  for p in points1:
    p.localize(a)
    t_coords.append(model.apply(a)) # returns a transformed copy of the array
  
  # Show transformed FIBSEM points as a stack
  # Points are already scaled, so use radius2 and bounds2 instead when mapping into GCaMP coordinate space
  t_imp1, t_img1, t_points1 = show("FIBSEM transformed", t_coords, radius2, bounds2, scale=1.0)

else:
  print "Model not found."










