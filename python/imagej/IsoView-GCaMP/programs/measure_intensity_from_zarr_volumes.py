# Albert Cardona 2024-05-31
# Load a numner of ZARR volumes as 4D stacks and measure pixel intensity
# within spheres centered on a given list of 3D landmarks for each stack.
# Works as a standalone script for Fiji.

from __future__ import with_statement
import sys, os, csv
from net.imglib2.roi.geom import GeomMasks
from net.imglib2.roi import Regions
from net.imglib2.view import Views
from net.imglib2.util import Intervals
from net.imglib2.type.numeric.integer import UnsignedShortType
from java.lang import Double
from java.util.stream import StreamSupport
from java.util.function import Function, BinaryOperator
from java.util.concurrent import Executors, Callable
from org.janelia.saalfeldlab.n5.imglib2 import N5Utils
from org.janelia.saalfeldlab.n5.universe import N5Factory
from itertools import imap


# Number of parallel threads to use:
n_threads = 128

# Volumes to measure in:
ceph = "/net/ceph.mzlatic.grp/"
zarrsDir = ceph + "code/LS_analysis/data/Nadine/"
dataset = "volumes" # same for each ZARR 4D volume
pixelType = UnsignedShortType
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

# Directory with CSV files with 3D coordinates, one for each ZARR volume:
csvDir = "/lmb/home/acardona/lab/projects/20240531_Nadine_Randel_fluorescence_measurements/"

# Directory to write measurement CSV files
resultsDir = csvDir + "measurements/"

# Calibration
pixelWidth = 325.0 # nanometers per pixel
pixelHeight = 325.0
pixelDepth = 1000.0

# Radius of the sphere to measure centred at each 3D coordinate
radius = 2000 # in nanometers

# Radius dimensions in pixels
rX = radius / pixelWidth
rY = radius / pixelHeight
rZ = radius / pixelDepth

print "Radii used (in pixels): %f, %f, %f" % (rX, rY, rZ)


# Load a ZARR volume as a 4D CellImg
def load(zarr_path, dataset):
  # Open a ZARR volume: these are all 4D, so 4D CellImg
  n5 = N5Factory().openReader(zarr_path) # an N5Reader
  img = N5Utils.open(n5, dataset) # a CellImg
  return img


def makeROIs(points, rX, rY, rZ):
  # List of OpenSphere ROIs, each centered on an integer-rounded 3D coordinate
  # NOTE if the volume to measure is not a sphere, then use a openSuperEllipsoid instead of an openSphere.
  # The GeomMasks.openSuperEllipsoid takes the point, the list of 3 radii, and an exponent of 2.
  if rX == rY and rY == rZ:
    rois = [GeomMasks.openSphere(point, radius) for point in points]
  else:
    rois = [GeomMasks.openSuperEllipsoid(point, [rX, rY, rZ], 2) for point in points]
  return rois


def parseCSVCoordinates(csvPath):
  points = []
  with open(csvPath, 'r') as f:
    reader = csv.reader(f, delimiter=',', quotechar="\"")
    header = reader.next() # skip first line
    for row in reader:
      # Columns at index 2, 3, 5 are the X, Y, Z of a coordinate in the LSM volume
      points.append([float(row[2]),
                     float(row[3]),
                     float(row[5])])
  return points

# Work around jython limitations: can't use a static method as a Stream Function
class GetValue(Function):
  apply = pixelType.getDeclaredMethod("get").invoke # 'get' returns a floating-point number

class DoubleSum(BinaryOperator):
  apply = Double.sum

class Measure(Callable):
  def __init__(self, img4D, t, rois):
    self.img4D = img4D
    self.t = t
    self.rois = rois
  def call(self):
    # Grab the 3D volume at timepoint t
    img3D = Views.hyperSlice(self.img4D, 3, self.t)
    # Assumes the ROI is small enough that the sum won't lose accuracy
    measurements = []
    for roi in self.rois:
      nucleus = Regions.sample(roi, img3D) # IterableInterval over the voxels of the spheroid
      count = Intervals.numElements(nucleus) # number of pixels
      sumOfVoxels = StreamSupport.stream(nucleus.spliterator(), False).map(GetValue()).reduce(0, DoubleSum())
      measurements.append(sumOfVoxels / float(count))
    return self.t, measurements

def writeToCSV(f, future):
  # f is a file handle
  # t is the index of the time point
  t, measurements = future.get()
  # Write a row to the CSV file
  f.write("%i, " % t)
  f.write(", ".join(imap(str, measurements)))
  f.write("\n")


# For one ZARR volume, measure average pixel intensity for every 3D coordinate at every time point
# and write them to a new CSV file in the resultsDir.
def measure(zarrsDir, zarr, dataset, csvDir, resultsDir, rX, rY, rZ, exe, n_threads):
  """
  The path to the ZARR volume is zarrsDir + zarr, which is a directory.
  The 'dataset' is the name of the volume in that ZARR directory, which is a subdirectory.
  The csvDir contains a CSV file named like part of the zarr path, containing 3D coordinates.
  The goal is to measure the pixel intensity for a 3D spherical ROI at each 3D coordinate
  and write them all into the resultsDir, with the same name as the CSV file.
  """
  # Find the CSV file with 3D coordinates to measure
  name = zarr[zarr.find('/') + 1 : zarr.rfind('/')]
  csvPath = os.path.join(csvDir, name + ".csv")
  if not os.path.exists(csvPath):
    "Cannot process " + zarr + ": no CSV file with coordinates at " + csvDir
    return
  
  # Parse 3D coordinates from CSV file
  points = parseCSVCoordinates(csvPath) # in pixel coordinates
  
  # Create 3D spheroid ROIS
  rois = makeROIs(points, rX, rY, rZ) # in pixel coordinates
  
  # Load 4D lazy CellImg of the ZARR volume
  img4D = load(os.path.join(zarrsDir, zarr), dataset)
  print img4D
  
  # Open new CSV file for writing the measurements
  with open(os.path.join(resultsDir, name + ".measurements.csv"), 'w') as f:
    # Write the header of the CSV file
    header = ["timepoint"] + ['"%f::%f::%f"' % (x,y,z) for (x,y,z) in points] # each point is a 3d list
    f.write(", ".join(header))
    f.write("\n")
    futures = []
    for t in xrange(img4D.dimension(3)):
      futures.append(exe.submit(Measure(img4D, t, rois)))
      # Write to the CSV file when twice as many jobs have been submitted than threads
      if len(futures) >= n_threads * 2:
        # await and write up to n_threads of the presently submitted
        while len(futures) > n_threads:
          writeToCSV(f, futures.pop(0)) # process and pop out the first one
    # Await and write all remaining
    for fu in futures:
      writeToCSV(f, fu)


# Process all ZARR volumes, one by one but each timepoint in parallel
try:
  # Ensure target directory exists:
  if not os.path.exists(resultsDir):
    os.mkdir(resultsDir)
  exe = Executors.newFixedThreadPool(n_threads)
  for i, zarr in enumerate(zarrs):
    print "processing %i/%i" % (i+1, len(zarrs))
    measure(zarrsDir, zarr, dataset, csvDir, resultsDir, rX, rY, rZ, exe, n_threads)
finally:
  exe.shutdown()




























