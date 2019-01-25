from __future__ import with_statement
import sys, os, csv
sys.path.append("/home/albert/lab/scripts/python/imagej/IsoView-GCaMP/")
from lib.register import computeForwardTransforms, asBackwardConcatTransforms, viewTransformed, saveMatrices, loadMatrices
from org.janelia.simview.klb import KLB
from collections import defaultdict
from net.imglib2.cache import CacheLoader
from java.lang import Runtime
from java.util.concurrent import Executors
from mpicbg.models import TranslationModel3D
from net.imglib2.realtransform import Translation3D
from net.imglib2.img.display.imagej import ImageJFunctions as IL
from net.imglib2.img.io import Load

# Loading IsoView 4-camera views.
# Under folder SPM00, there are folders for each timepoint, like TM004399.
# In each TM folder, there are 4 klb files, one for each view, e.g.:
# SPM00_TM004399_CM00_CHN01.klb
# SPM00_TM004399_CM01_CHN01.klb
# SPM00_TM004399_CM02_CHN00.klb
# SPM00_TM004399_CM03_CHN00.klb

SPMdir = "/home/albert/shares/zlaticlab/Nadine/Raghav/2017-05-10/GCaMP6s_1_20170510_115003.corrected/SPM00/"

# Dictionary of view vs list of files from that view
filepaths = defaultdict(list)

for root, dirs, filename in os.walk(SPMdir):
  if filename.endswith(".klb"):
    camera_index = int(filename[filename.find("CM0")+3])
    filepaths[camera_index].append(os.join(root, filename))

# Ensure sorted
for ls in filepaths.itervalues():
  ls.sort()


class PlainKLBLoader():
  def __init__(self):
    self.klb = KLB.newInstance()

  def load(self, path):
    return self.klb.readFull(path)

klb_loader = PlainKLBLoader()


def getCalibration():
  return [0.40625, 0.40625, 2.03125]


def RegisteredLoader(CacheLoader):
  def __init__(self, klb_loader, path_transforms):
    self.klb_loader = klb_loader
    self.path_transforms = path_transforms # dict

  def load(self, path):
    img = self.klb_loader.load(path)
    return viewTransformed(img, getCalibration(img), self.path_transforms[path])


def register(view_index, filepaths, modelclass, csv_dir, params):
  n_threads = Runtime.getRuntime().availableProcessors()
  exe = Executors.newFixedThreadPool(n_threads)
  try:
    name ="matrices-view-%i" % view_index 
    matrices = loadMatrices(name, csvdir)
    if not matrices:
      matrices = computeForwardTransforms(filepaths[view_index], klb_loader, getCalibration,
                                          csv_dir, exe, modelclass, params)
      saveMatrices(name, csv_dir)
  finally:
    exe.shutdown()

  transforms = asBackwardConcatTransforms(matrices, transformclass=Translation3D)
  path_transforms = dict(izip(filepaths[view_index], transforms))
  registered_loader = RegisteredLoader(klb_loader, path_transforms)

  return Load.lazyStack(filepaths[view_index], registered_loader)


# Parameters
csv_dir = "/mnt/ssd-512/IsoView-1038/"
modelclass = TranslationModel3D

# Parameters for DoG difference of Gaussian to detect soma positions
somaDiameter = 8 * getCalibration(None)[0]
paramsDoG = {
  "minPeakValue": 30, # Determined by hand
  "sigmaSmaller": somaDiameter / 4.0, # in calibrated units: 1/4 soma
  "sigmaLarger": somaDiameter / 2.0, # in calibrated units: 1/2 soma
}

paramsFeatures = {
  # Parameters for features
  "radius": somaDiameter * 5, # for searching nearby peaks
  "min_angle": 1.57, # in radians, between vectors to p1 and p2
  "max_per_peak": 3, # maximum number of constellations to create per peak

  # Parameters for comparing constellations to find point matches
  "angle_epsilon": 0.02, # in radians. 0.05 is 2.8 degrees, 0.02 is 1.1 degrees
  "len_epsilon_sq": pow(somaDiameter, 2), # in calibrated units, squared
  "pointmatches_nearby": True, # if True, searches for possible matches only within radius
  "pointmatches_search_radius": somaDiameter #
}

# RANSAC parameters: reduce list of pointmatches to a spatially coherent subset
paramsModel = {
  "maxEpsilon": somaDiameter, # max allowed alignment error in calibrated units (a distance)
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

registered = register(0, filepaths, Translation3D, csv_dir, params)
IL.wrap(registered, "registered").show()

