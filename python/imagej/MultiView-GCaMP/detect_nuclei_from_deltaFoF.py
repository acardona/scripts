from __future__ import with_statement
import sys, os, csv
from org.janelia.simview.klb import KLB
from operator import itemgetter
sys.path.append("/groups/cardona/home/cardonaa/lab/scripts/python/imagej/IsoView-GCaMP")
from lib.util import newFixedThreadPool, Task, syncPrint
from net.imglib2.img.array import ArrayImgs
from net.imglib2.util import Intervals
from net.imglib2.img.display.imagej import ImageJFunctions as IL
from java.lang import Runtime, Thread
from net.imglib2.algorithm.math.ImgMath import compute, maximum

srcDir = "/mnt/keller-s8/SV4/CW_17-08-26/L6-561nm-ROIMonitoring_20170826_183354.corrected/Results/WeightFused.dFF_offset50_preMed_postMed/"
tgtDir = "/groups/cardona/cardonalab/Albert/CW_17-08-26/L6-561nm-ROIMonitoring_20170826_183354.corrected/Results/WeightFused.dFF_offset50_preMed_postMed/"

if not os.path.exists(tgtDir):
  os.makedirs(tgtDir)

TMs = []

for foldername in sorted(os.listdir(srcDir)):
  index = foldername[2:]
  filename = os.path.join(foldername, "SPM00_TM%s_CM00_CM01_CHN00.weightFused.TimeRegistration.klb" % index)
  TMs.append(filename)


klb = KLB.newInstance()

# Compute (or read from a CSV file) the sum of all pixels for each time point
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


# Take the median
sums.sort(key=itemgetter(1))
median = sums[len(sums)/2][1]
max_sum = sums[-1][1] # last

print median, max_sum

# Turns out the maximum is infinity.
# Therefore, discard all infinity values, and also any above 1.5 * median
threshold = median * 1.5

filtered = [filename for filename, pixel_sum in sums if pixel_sum < threshold]

class Max(Thread):
  def __init__(self, dimensions, filenames):
    super(Thread, self).__init__()
    self.filenames = filenames
    self.aimg = ArrayImgs.floats(dimensions)
    self.klb = KLB.newInstance()
  def run(self):
    for filename in self.filenames:
      img = self.klb.readFull(os.path.join(srcDir, filename))
      compute(maximum(self.aimg, img)).into(self.aimg)

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
max_projection = compute(maximum([m.aimg for m in threads])).into(ArrayImgs.floats(dimensions))

IL.wrap(max_projection, "max projection").show()




