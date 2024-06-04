# Albert Cardona 2024-05-31
# Load a 4D stack and measure pixel intensity
# within spheres centered on a given list of 3D landmarks.
# Works as a standalone script for Fiji

from __future__ import with_statement
import sys, os, csv, operator
from net.imglib2.roi.geom import GeomMasks
from net.imglib2.roi import Masks, Regions
from net.imglib2.cache.ref import SoftRefLoaderCache, BoundedSoftRefLoaderCache
from net.imglib2.cache import CacheLoader
from net.imglib2.cache.img import CachedCellImg
from net.imglib2.img.basictypeaccess import AccessFlags, ArrayDataAccessFactory
from net.imglib2.img.cell import CellGrid, Cell
from net.imglib2.img.display.imagej import ImageJFunctions as IL
from net.imglib2.algorithm.math import ImgMath
from net.imglib2.view import Views
from net.imglib2.util import Intervals
from java.lang import Double, System
from java.util.stream import StreamSupport
from java.util.function import Function, BinaryOperator
from ij import IJ
from itertools import imap
from java.util.concurrent import Executors, Callable

from org.janelia.saalfeldlab.n5.imglib2 import N5Utils
from org.janelia.saalfeldlab.n5.universe import N5Factory

def test():
  srcDir = "/home/albert/ceph.mzlatic.grp/code/LS_analysis/data/Nadine/"
  path = srcDir + "a_38042/a_38042_1_20240428_112123/merged_registered.zarr"
  dataset = "volumes" # confusing choice of name

  # Open a ZARR volume: these are all 4D, so 4D CellImg
  n5 = N5Factory().openReader(path) # an N5Reader
  img = N5Utils.open(n5, dataset) # a CellImg
  print img


# Volumes to measure in:
rootDir = "/ceph.groups/mzlatic.grp/code/LS_analysis/data/Nadine/"
dataset = "volumes" # same for each ZARR 4D volume
zarrs = [
  "a_38042/a_38042_1_20240428_112123/merged_registered.zarr",
  "a_38042/a_38042_2_20240428_145317/merged_registered.zarr",
  "a_38042/a_38042_3_20240428_153721/merged_registered.zarr",
  "a_4245/a_4245_1_20240425_122140/merged_registered.zarr",
  "a_4245/a_4245_3_20240425_151140/merged_registered.zarr",
  "a_4245/a_4245_5_20240427_115946/merged_registered.zarr",
  "a_4245/a_4245_2_20240425_142343/merged_registered.zarr",
  "a_4245/a_4245_4_20240425_155227/merged_registered.zarr",
  "ab/1_1_20240303_171154/merged_registered.zarr",
  "ab/1_2_20240303_172421/merged_registered.zarr",
  "ab/2_1_20240306_111439/merged_registered.zarr",
  "ab/3_1_20240306_155600/merged_registered.zarr",
  "af/af_5_20240425_111945/merged_registered.zarr",
  "af/af_2_20240424_120457/merged_registered.zarr",
  "af/af_4_20240424_165016/merged_registered.zarr",
  "ak/a_k_1__20240330_112923/merged_registered.zarr",
  "ak/a_k_2__20240330_141859/merged_registered.zarr",
  "ak/a_k_3__20240330_154256/merged_registered.zarr",
]


def load(zarr_path, dataset):
  # Open a ZARR volume: these are all 4D, so 4D CellImg
  n5 = N5Factory().openReader(zarr_path) # an N5Reader
  img = N5Utils.open(n5, dataset) # a CellImg
  return img

