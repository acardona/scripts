from __future__ import with_statement
import sys, os, csv
sys.path.append("/home/albert/lab/scripts/python/imagej/IsoView-GCaMP/")
from lib.registration import computeForwardTransforms, asBackwardConcatTransforms, viewTransformed, saveMatrices, loadMatrices
from lib.util import newFixedThreadPool, syncPrint
from org.janelia.simview.klb import KLB
from collections import defaultdict
from net.imglib2.cache import CacheLoader
from java.lang import Runtime
from java.util.concurrent import Executors
from mpicbg.models import TranslationModel3D
from net.imglib2.realtransform import Translation3D
from net.imglib2.img.display.imagej import ImageJFunctions as IL
from net.imglib2.img.io import Load
from net.imglib2.img import ImgView
from itertools import izip
import re

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

pattern = re.compile("^SPM00_TM\d+_CM(\d+)_CHN0[01]\.klb$")

for root, dirs, filenames in os.walk(SPMdir):
  # Ignore hidden files and directories: edit dirs in place (allowed!)
  dirs[:] = [dirname for dirname in dirs if not '.' == dirname[0]]
  for filename in filenames:
    r = re.match(pattern, filename)
    if r:
      camera_index = int(r.groups()[0])
      filepaths[camera_index].append(os.path.join(root, filename))

# Ensure sorted
for ls in filepaths.itervalues():
  ls.sort() # in place


class PlainKLBLoader(CacheLoader):
  def __init__(self):
    self.klb = KLB.newInstance()

  def load(self, path):
    return self.klb.readFull(path)

  def get(self, path):
    return self.load(path)

klb_loader = PlainKLBLoader()


def getCalibration(img_filename):
  #return [0.40625, 0.40625, 2.03125]
  # Preserve XY pixels, expand Z
  return [1.0, 1.0, 5.0]


class RegisteredLoader(CacheLoader):
  def __init__(self, klb_loader, path_transforms):
    self.klb_loader = klb_loader
    self.path_transforms = path_transforms # dict

  def get(self, path):
    img = self.klb_loader.load(path)
    return ImgView.wrap(viewTransformed(img, getCalibration(img), self.path_transforms[path]), img.factory())


def register(view_index, filepaths, modelclass, csv_dir, params, n_threads=0, workaround2487=True):
  # Work around jython bug https://bugs.jython.org/issue2487 , a race condition on type initialization
  if 0 == view_index and workaround2487:
    # bogus call for first two filepaths: single-threaded execution to initalize types
    register(view_index, {view_index: filepaths[view_index][0:2]}, modelclass, "/tmp/", params,
             n_threads=1, workaround2487=False)
  
  exe = newFixedThreadPool(n_threads)
  paths = filepaths[view_index]
  try:
    name ="matrices-view-%i" % view_index
    matrices = loadMatrices(name, csv_dir)
    if not matrices:
      matrices = computeForwardTransforms(paths, klb_loader, getCalibration,
                                          csv_dir, exe, modelclass, params)
      # Debug: print identity transforms
      identity_indices = [i for i, m in enumerate(matrices) if 1.0 == m[0] and 0.0 == m[1] and 0.0 == m[2] and 0.0 == m[3]
                                                           and 0.0 == m[4] and 1.0 == m[5] and 0.0 == m[6] and 0.0 == m[7]
                                                           and 0.0 == m[8] and 0.0 == m[9] and 1.0 == m[10] and 0.0 == m[11]]
      syncPrint("View %i: identity matrices at [%s]" % (view_index, ", ".join(str(index) for index in identity_indices)))
      saveMatrices(name, matrices, csv_dir)
  finally:
    exe.shutdown()

  transforms = asBackwardConcatTransforms(matrices, transformclass=Translation3D)
  path_transforms = dict(izip(paths, transforms))
  registered_loader = RegisteredLoader(klb_loader, path_transforms)

  return Load.lazyStack(paths, registered_loader)


# Parameters
csv_dir = "/mnt/ssd-512/IsoView-1038/20181112/"
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
  "pointmatches_nearby": 1, # if 1 (True), searches for possible matches only within radius
  "pointmatches_search_radius": somaDiameter * 2 #
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


for view_index in filepaths.iterkeys():
  unregistered = Load.lazyStack(filepaths[view_index], klb_loader)
  IL.wrap(unregistered, "unregistered-view-%i" % view_index).show()
  registered = register(view_index, filepaths, TranslationModel3D, csv_dir, params)
  IL.wrap(registered, "registered-view-%i" % view_index).show()


