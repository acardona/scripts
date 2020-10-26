from __future__ import with_statement
import sys
sys.path.append("/home/albert/lab/scripts/python/imagej/IsoView-GCaMP/")
from net.imglib2.view import Views
from net.imglib2 import FinalInterval, RealPoint
from lib.synthetic import virtualPointsRAI
from lib.ui import showStack
from lib.features import makeRadiusSearch
from lib.features_plus_asm import initNativeClasses
from lib.registration import fit, transformedView
from lib.util import numCPUs, nativeArray
from lib.dogpeaks import getDoGPeaks
from lib.nuclei import boundsOf
from mpicbg.models import RigidModel3D, AffineModel3D

ConstellationPlus, PointMatchesPlus = initNativeClasses()

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

bounds1 = boundsOf(FIBSEM_nuclei)
print "FIBSEM nuclei bounds:", bounds1, "in nanometers"

FIBSEM_calibration = 192.0 # nm/px isotropic
GCaMP_calibration = 406.0 # nm/px isotropic
EM_to_LSM = FIBSEM_calibration / GCaMP_calibration # approx 0.5x

# Dimensions of the FIBSEM volume
dimensions1 = [670, 800, 1036] # from boundsOf(FIBSEM_nuclei)[1] with some padding added

# Dimensions of the fused and deconvolved GCaMP 3D volume
dimensions2 = [406, 465, 489]


# Transform FIBSEM: flip horizontally (X axis)
flip_matrix = [
  -1.0, 0.0, 0.0, dimensions1[0],
  0.0, 1.0, 0.0, 0.0,
  0.0, 0.0, 1.0, 0.0]

# Project from EM coordinate space to LSM coordinate space
EM_to_LSM_matrix = [
  EM_to_LSM, 0.0, 0.0, 0.0,
  0.0, EM_to_LSM, 0.0, 0.0,
  0.0, 0.0, EM_to_LSM, 0.0]

# Transform FIBSEM coordinates with an approximate rigid 3D matrix
# estimated manually in the 3D Viewer from a horizontally flipped FIBSEM volume
# rotated and translated over the GCaMP volume.
# NOTE this transformation is relative to the center of the volume, so it needs
# to be corrected by first translating to the center, then transforming, then
# translating back.

FIBSEM_center = [131.19719, 190.40999, 206.82999] # AFTER flip and EM_to_LSM, so in LSM pixel space

coarse_matrix = [
  0.3013336, -0.61400056, -0.72952133, 413.56097,
  0.061801117, -0.75089836, 0.6575198, 210.51689,
  -0.9515139, -0.24321805, -0.18832497, 386.76764]


affineFlip = AffineModel3D()
affineFlip.set(*flip_matrix)
affineEMtoLSM = AffineModel3D()
affineEMtoLSM.set(*EM_to_LSM_matrix)
affine_translate1 = AffineModel3D()
affine_translate1.set(1.0, 0.0, 0.0, -FIBSEM_center[0],
                     0.0, 1.0, 0.0, -FIBSEM_center[1],
                     0.0, 0.0, 1.0, -FIBSEM_center[2])
affineCoarse = AffineModel3D()
affineCoarse.set(*coarse_matrix)
affine_translate2 = AffineModel3D()
affine_translate2.set(1.0, 0.0, 0.0, FIBSEM_center[0],
                     0.0, 1.0, 0.0, FIBSEM_center[1],
                     0.0, 0.0, 1.0, FIBSEM_center[2])

affine = AffineModel3D()
affine.set(affineFlip)
affine.preConcatenate(affineEMtoLSM)
affine.preConcatenate(affine_translate1)
affine.preConcatenate(affineCoarse)
affine.preConcatenate(affine_translate2)

# Ignore calibration (!!)
# FIBSEM: resolution is 192x192x192 nm/px (level 4)
# GCaMP: resolution is 406x406x406 nm/px (deconvolved)
# radius1 = 2000 / 192.0 # 4-micron nucleus
# radius2 = 2000 / 406.0

# Apply transform to FIBSEM
FIBSEM_nuclei = [affine.apply(point) for point in FIBSEM_nuclei]


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


radius = 5


# use dimensions2: the target of the transformation
imp1, img1, points1 = show("FIBSEM", FIBSEM_nuclei, radius, [[0, 0, 0], [d -1 for d in dimensions2]], scale=1.0)
#imp1, img1, points1 = show("FIBSEM", FIBSEM_nuclei, radius2, bounds2, scale=1.0)
# ABOVE, use same radius2, bounds2 as GCaMP, as they are now coarsely pre-registered
# and the scale=192/406.0 isn't needed either

imp2, img2, points2 = show("GCaMP", GCaMP_nuclei, radius, [[0, 0, 0], [d -1 for d in dimensions2]], scale=1.0)


"""

# Register FIBSEM onto GCaMP (they are already at the same scale)
somaDiameter = 4000 / 406.0 # 4 microns
search_radius = 10 * somaDiameter # for searching nearby peaks
max_per_peak = 1000
angle_epsilon = 0.02
len_epsilon_sq = pow(somaDiameter * 0.4, 2) # in calibrated units, squared
min_neighbors = 3
max_neighbors = 4 # will create features with 3, 4, and 5 peaks (center + 2, 3 or 4 neighbors)

search1 = makeRadiusSearch(points1) # FIBSEM points are scaled to match GCaMP points coordinate space
search2 = makeRadiusSearch(points2)

#features1 = extractFeatures(points1, search1, search_radius, min_angle, max_per_peak)
#features2 = extractFeatures(points2, search2, search_radius, min_angle, max_per_peak)

features1 = ConstellationPlus.extractFeatures(points1,
                                              makeRadiusSearch(points1),
                                              search_radius,
                                              max_per_peak,
                                              min_neighbors,
                                              max_neighbors)

features2 = ConstellationPlus.extractFeatures(points2,
                                              makeRadiusSearch(points2),
                                              search_radius,
                                              max_per_peak,
                                              min_neighbors,
                                              max_neighbors)

print "img1: Found %i features" % len(features1)
print "img2: Found %i features" % len(features2)

# Could use "fromNearbyFeatures" if both data sets were roughly aligned already.
pm = PointMatchesPlus.fromFeatures(features1, features2,
                                   angle_epsilon, len_epsilon_sq,
                                   ConstellationPlus.COMPARE_ALL, numCPUs())

print "Found %i pointmatches" % len(pm.pointmatches)

maxEpsilon = 0.5 * somaDiameter # max allowed alignment error in calibrated units (a distance)
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

"""