# Test registration using the constellation features described here:
# Preibisch, Saalfeld, Schindelin, Tomancak 2010 Software for bead-based registration of selective plane illumination microscopy data
# and implemented here:
# https://github.com/PreibischLab/multiview-reconstruction/blob/master/src/main/java/net/preibisch/mvrecon/process/pointcloud/pointdescriptor/test/TestPointDescriptor.java

import os, sys
sys.path.append("/home/albert/lab/scripts/python/imagej/IsoView-GCaMP/")
from lib.dogpeaks import getDoGPeaks
from lib.registration import fit
from mpicbg.models import Point, RigidModel3D, AffineModel3D, TranslationModel3D
from net.imglib2.img.io import Load, IJLoader
from net.imglib2.view import Views
from net.imglib2 import KDTree
from net.imglib2.neighborsearch import KNearestNeighborSearchOnKDTree, NearestNeighborSearchOnKDTree
from net.preibisch.mvrecon.process.pointcloud.pointdescriptor import ModelPointDescriptor
from net.preibisch.mvrecon.process.pointcloud.pointdescriptor.matcher import SimpleMatcher
from net.preibisch.mvrecon.process.pointcloud.pointdescriptor.model import TranslationInvariantRigidModel3D
from net.preibisch.mvrecon.process.pointcloud.pointdescriptor.similarity import SquareDistance
from jarray import zeros

# 3 timepoints of a 4D series, isotropic (already deconvolved and fused from 2 cameras of an IsoView light-sheet microscope)
dataDir = "/home/albert/lab/scripts/data/4D-series-zip/"

filepaths = [os.path.join(dataDir, filename)
             for filename in sorted(os.listdir(dataDir))
             if filename.endswith(".zip")]

# Parameters for DoG difference of Gaussian to detect soma positions
somaDiameter = 8
paramsDoG = {
  "minPeakValue": 30, # Determined by hand
  "sigmaSmaller": somaDiameter / 4.0, # in calibrated units: 1/4 soma
  "sigmaLarger": somaDiameter / 2.0, # in calibrated units: 1/2 soma
}

paramsFeatures = {
  # Parameters for features
  "radius": somaDiameter * 2, # for searching nearby peaks
  "min_neighbors": 3,
  "max_neighbors": 4, # will create features with 3, 4, and 5 peaks (center + 2, 3 or 4 neighbors)
  "max_per_peak": 1000, # maximum number of constellations to create per peak

  # Parameters for comparing constellations to find point matches
  "max_difference": 0.1
}

# RANSAC parameters: reduce list of pointmatches to a spatially coherent subset
paramsModel = {
  "maxEpsilon": somaDiameter * 0.1, # max allowed alignment error in calibrated units (a distance)
  "minInlierRatio": 0.0000001, # ratio inliers/candidates
  "minNumInliers": 5, # minimum number of good matches to accept the result
  "n_iterations": 2000, # for estimating the model
  "maxTrust": 4, # for rejecting candidates
}

# Joint dictionary of parameters
params = {}
params.update(paramsDoG)
params.update(paramsFeatures)
params.update(paramsModel)

calibration = [1.0, 1.0, 1.0]


unregistered = Load.lazyStack(filepaths, IJLoader())

img1 = Views.hyperSlice(unregistered, 3, 0)
img2 = Views.hyperSlice(unregistered, 3, 1)

peaks1 = getDoGPeaks(img1, calibration, params["sigmaSmaller"], params["sigmaLarger"], params['minPeakValue'])
peaks2 = getDoGPeaks(img2, calibration, params["sigmaSmaller"], params["sigmaLarger"], params['minPeakValue'])

print "peaks1: %i" % len(peaks1)
print "peaks2: %i" % len(peaks2)

# extract point descriptors			
numNeighbors = 3
pd_model = TranslationInvariantRigidModel3D()
matcher = SimpleMatcher(numNeighbors)
similarityMeasure = SquareDistance()


# Creates features from a list of peaks
def createModelPointDescriptors(kdtree, peaks, numNeighbors, pd_model, matcher, similarityMeasure):
  #
  def asPoint(peak):
    a = zeros(3, 'd')
    peak.localize(a)
    return Point(a)
  
  nnsearch = KNearestNeighborSearchOnKDTree(kdtree, numNeighbors + 1)
  descriptors = []
  
  for peak in peaks:
    nnsearch.search(peak)
    try: # There may not be enough neighbors
      neighbors = [asPoint(nnsearch.getSampler(i).get())
                   for i in xrange(1, numNeighbors + 2)] # from 1 to <= numNeighbors + 1
      descriptors.add(ModelPointDescriptor(asPoint(peak), neighbors, pd_model, similarityMeasure, matcher))
    except:
      print sys.exc_info()
  return descriptors


kdtree1 = KDTree(peaks1, peaks1)
kdtree2 = KDTree(peaks2, peaks2)

descriptors1 = createModelPointDescriptors(kdtree1, peaks1, numNeighbors, pd_model, matcher, similarityMeasure)
descriptors2 = createModelPointDescriptors(kdtree2, peaks2, numNeighbors, pd_model, matcher, similarityMeasure)

print "descriptors1: %i" % len(descriptors1)
print "descriptors2: %i" % len(descriptors2)

# Create pointmatches from two lists of features, all to all
pointmatches = []
max_difference = params['max_difference']
for d1 in descriptors1:
  for d2 in descriptors2:
    difference = d1.descriptorDistance(d2)
    if difference < max_difference:
      pointmatches.append(PointMatch(d1.getBasisPoint(), d2.getBasisPoint()))

print "Found %i pointmatches" % len(pointmatches)

model = TranslationModel3D()

modelFound, inliers = fit(model, pointmatches,
                          params['n_iterations'], params['maxEpsilon'],
                          params['minInlierRatio'], params['minNumInliers'], params['maxTrust'])

if modelFound:
  print "Model found from %i inliers" % len(inliers)
  a = nativeArray('d', [3, 4])
  model.toMatrix(a) # Can't use model.toArray: different order of elements
  matrix = a[0] + a[1] + a[2] # Concat: flatten to 1-dimensional array
  print matrix
else:
  print "Model not found"




