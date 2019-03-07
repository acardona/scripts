from __future__ import with_statement
import sys, os, csv
from org.janelia.simview.klb import KLB
from operator import itemgetter
sys.path.append("/home/albert/lab/scripts/python/imagej/IsoView-GCaMP")
from lib.util import newFixedThreadPool, Task, syncPrint
from net.imglib2.img.array import ArrayImgs
from net.imglib2.util import Intervals
from net.imglib2.img.display.imagej import ImageJFunctions as IL
from java.lang import Runtime, Thread
from net.imglib2.algorithm.math.ImgMath import computeInto, maximum
from lib.io import writeZip, readIJ
from lib.nuclei import doGPeaks
from lib.synthetic import virtualPointsRAI
from lib.ui import showStack

srcDir = "/home/albert/shares/keller-s8/SV4/CW_17-08-26/L6-561nm-ROIMonitoring_20170826_183354.corrected/Results/WeightFused.dFF_offset50_preMed_postMed/"
tgtDir = "/home/albert/Desktop/deltaFoF/CW_17-08-26/L6-561nm-ROIMonitoring_20170826_183354.corrected/Results/WeightFused.dFF_offset50_preMed_postMed/"

#srcDir = "/mnt/keller-s8/SV4/CW_17-08-26/L6-561nm-ROIMonitoring_20170826_183354.corrected/Results/WeightFused.dFF_offset50_preMed_postMed/"
#tgtDir = "/groups/cardona/cardonalab/Albert/CW_17-08-26/L6-561nm-ROIMonitoring_20170826_183354.corrected/Results/WeightFused.dFF_offset50_preMed_postMed/"


if not os.path.exists(tgtDir):
  os.makedirs(tgtDir)

TMs = []

for foldername in sorted(os.listdir(srcDir)):
  index = foldername[2:]
  filename = os.path.join(foldername, "SPM00_TM%s_CM00_CM01_CHN00.weightFused.TimeRegistration.klb" % index)
  TMs.append(filename)


klb = KLB.newInstance()

# Step 1: Compute (or read from a CSV file) the sum of all pixels for each time point
sums = []

csv_sums_path = os.path.join(tgtDir, "sums.csv")
if os.path.exists(csv_sums_path):
  with open(csv_sums_path, 'r') as csvfile:
    reader = csv.reader(csvfile, delimiter=',', quotechar="\"")
    header = reader.next() # skip
    sums = [(filename, float(s)) for i, (filename, s) in enumerate(reader)]
else:
  # Compute:
  exe = newFixedThreadPool(-1)
  try:
    def computeSum(filename, aimg=None):
      syncPrint(filename)
      img = aimg if aimg is not None else klb.readFull(os.path.join(srcDir, filename))
      try:
        return filename, sum(img.getImg().update(None).getCurrentStorageArray())
      except:
        syncPrint("Failed to compute sum: retry")
        return computeSum(filename, aimg=img)

    futures = [exe.submit(Task(computeSum, filename)) for filename in TMs]

    # Store to disk as a CSV file
    with open(os.path.join(tgtDir, "sums.csv"), 'w') as csvfile:
      w = csv.writer(csvfile, delimiter=",", quoting=csv.QUOTE_NONNUMERIC)
      w.writerow(["filename", "sum"])
      for i, future in enumerate(futures):
        filename, s = future.get()
        w.writerow([filename, s])
        sums.append((filename, s))
  finally:
    exe.shutdown()


class Max(Thread):
  def __init__(self, dimensions, filenames):
    super(Thread, self).__init__()
    self.filenames = filenames
    self.aimg = ArrayImgs.floats(dimensions)
    self.klb = KLB.newInstance()
  def run(self):
    for filename in self.filenames:
      try:
        img = self.klb.readFull(os.path.join(srcDir, filename))
        computeInto(maximum(self.aimg, img), self.aimg)
      except:
        syncPrint("Skipping failed image: %s\n%s" % (filename, sys.exc_info()))


# Step 2: project the 4D series into a single 3D image using the maximum function
# (Will read it if it already exists)
max_projection_path = os.path.join(tgtDir, "max_projection.zip")
if os.path.exists(max_projection_path):
  max_projection = readIJ(max_projection_path)
  print "Loaded max_projection.zip file from disk at", max_projection_path
else:
  # Project the time dimension so that 4D -> 3D
  # Take the median
  sums.sort(key=itemgetter(1))
  median = sums[len(sums)/2][1]
  max_sum = sums[-1][1] # last

  print median, max_sum

  # Turns out the maximum is infinity.
  # Therefore, discard all infinity values, and also any above 1.5 * median
  threshold = median * 1.5

  filtered = [filename for filename, pixel_sum in sums if pixel_sum < threshold]

  n_threads = Runtime.getRuntime().availableProcessors()
  threads = []
  chunk_size = len(filtered) / n_threads
  aimgs = []
  first = klb.readFull(os.path.join(srcDir, filtered[0]))
  dimensions = Intervals.dimensionsAsLongArray(first)

  for i in xrange(n_threads):
    m = Max(dimensions, filtered[i * chunk_size : (i +1) * chunk_size])
    m.start()
    threads.append(m)

  # Await completion of all
  for m in threads:
    m.join()

  # Merge all results into a single maximum projection
  max_projection = computeInto(maximum([m.aimg for m in threads]),
                               ArrayImgs.floats(dimensions))

  max3D = writeZip(max_projection, max_projection_path, title="max projection")
  max3D.show()


# Step 3: detect the nuclei and write their coordinates to a CSV file
calibration = [0.40625, 0.40625, 2.5]

somaDiameters = [4, 4.9, 5.7, 6.5] # 10, 12, 14, 16 px

for somaDiameter in somaDiameters:
  # Parameters for detecting nuclei with difference of Gaussian
  print "Detecting nuclei on max_projection image with somaDiameter %i" % somaDiameter
  params = {
   "calibration": calibration,
   "minPeakValue": 50, # determined by hand: the bright peaks
   "sigmaSmaller": somaDiameter / 4.0, # in calibrated units: 1/4 soma
   "sigmaLarger": somaDiameter / 2.0,  # in calibrated units: 1/2 soma
  }
  
  peaks = doGPeaks(max_projection, params)
  
  spheresRAI = virtualPointsRAI(peaks, 0.5 * somaDiameter / calibration[0], max_projection)
  imp = showStack(spheresRAI, title="nuclei somaDiameter=%f" % somaDiameter)


