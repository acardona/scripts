import sys, os
sys.path.append("/home/albert/lab/scripts/python/imagej/IsoView-GCaMP/")

from lib.features_plus_asm import initNativeClasses
from lib.features import makeRadiusSearch
from lib.dogpeaks import getDoGPeaks
from lib.util import numCPUs, nativeArray
from lib.registration import fit

from net.imglib2.view import Views
from net.imglib2.img.display.imagej import ImageJFunctions as IL
from net.imglib2.img.io import Load, IJLoader
from mpicbg.models import RigidModel3D, TranslationModel3D
from ij import IJ

ConstellationPlus, PointMatchesPlus = initNativeClasses()


# 3 timepoints of a 4D series, isotropic (already deconvolved and fused from 2 cameras of an IsoView light-sheet microscope)
dataDir = "/home/albert/lab/scripts/data/4D-series-zip/"

filepaths = [os.path.join(dataDir, filename)
             for filename in sorted(os.listdir(dataDir))
             if filename.endswith(".zip")]

unregistered = Load.lazyStack(filepaths, IJLoader())


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
  "min_neighbors": 4,
  "max_neighbors": 4, # will create features with 3, 4, and 5 peaks (center + 2, 3 or 4 neighbors)
  "max_per_peak": 100, # maximum number of constellations to create per peak

  # Parameters for comparing constellations to find point matches
  "angle_epsilon": 0.01, # in radians. 0.05 is 2.8 degrees, 0.02 is 1.1 degrees
  "len_epsilon_sq": pow(somaDiameter*0.1, 2), # in calibrated units, squared
  "pointmatches_nearby": True, # if True, searches for possible matches only within radius
  "pointmatches_search_radius": somaDiameter #
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

img1 = Views.hyperSlice(unregistered, 3, 0)
img2 = Views.hyperSlice(unregistered, 3, 1)

peaks1 = getDoGPeaks(img1, calibration, params["sigmaSmaller"], params["sigmaLarger"], params['minPeakValue'])
peaks2 = getDoGPeaks(img2, calibration, params["sigmaSmaller"], params["sigmaLarger"], params['minPeakValue'])

print "DoG peaks1: %i" % len(peaks1)
print "DoG peaks2: %i" % len(peaks2)

features1 = ConstellationPlus.extractFeatures(peaks1,
                                              makeRadiusSearch(peaks1),
                                              params['radius'],
                                              params['max_per_peak'],
                                              params['min_neighbors'],
                                              params['max_neighbors'])

print "img1: Found %i features" % len(features1)

features2 = ConstellationPlus.extractFeatures(peaks2,
                                              makeRadiusSearch(peaks2),
                                              params['radius'],
                                              params['max_per_peak'],
                                              params['min_neighbors'],
                                              params['max_neighbors'])

print "img2: Found %i features" % len(features2)

#pm = PointMatchesPlus.fromNearbyFeatures(params['pointmatches_search_radius'],
pm = PointMatchesPlus.fromFeatures(
                                         features1,
                                         features2,
                                         params['angle_epsilon'],
                                         params['len_epsilon_sq'],
                                         ConstellationPlus.COMPARE_ALL,
                                         numCPUs())

print "Found %i pointmatches" % len(pm.pointmatches)

model = TranslationModel3D()

modelFound, inliers = fit(model, pm.pointmatches,
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

