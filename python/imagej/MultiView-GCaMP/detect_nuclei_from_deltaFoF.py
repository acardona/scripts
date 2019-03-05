from __future__ import with_statement
import sys, os, csv
from org.janelia.simview.klb import KLB
from operator import itemgetter
sys.path.append("/home/albert/lab/scripts/python/imagej/IsoView-GCaMP")
from lib.util import newFixedThreadPool, Task, syncPrint
from net.imglib2.img.array import ArrayImgs
from net.imglib2.util import Intervals
from net.imglib2.img.display.imagej import ImageJFunctions as IL

srcDir = "/home/albert/shares/keller-s8/SV4/CW_17-08-26/L6-561nm-ROIMonitoring_20170826_183354.corrected/Results/WeightFused.dFF_offset50_preMed_postMed/"
tgtDir = "/home/albert/Desktop/deltaFoF/CW_17-08-26/L6-561nm-ROIMonitoring_20170826_183354.corrected/Results/WeightFused.dFF_offset50_preMed_postMed/"

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
    sums = [int(time), float(s) for time, s in reader]
else:
  # Compute:
  exe = newFixedThreadPool(-2)
  try:
    def computeSum(filename):
      syncPrint(filename)
      img = klb.readFull(os.path.join(srcDir, filename))
      return sum(img.getImg().update(None).getCurrentStorageArray())

    futures = [exe.submit(Task(computeSum, filename)) for filename in TMs]

    sums = [(i, f.get()) for i, f in enumerate(futures)]

    # Store to disk as a CSV file
    with open(os.path.join(tgtDir, "sums.csv"), 'w') as csvfile:
      w = csv.writer(csvfile, delimiter=",", quoting=csv.QUOTE_NONNUMERIC))
      w.writerow(["time", "sum"])
      for i, s in enumerate(sums):
        w.writerow([i, s])
  finally:
    exe.shutdown()


# Take the median
sums.sort(key=itemgetter(1))
median = sums[len(sums)/2][1]
maximum = sums[-1][1] # last
fraction = median / maximum
threshold = 0.7 # of the maximum value

print median, maximum, fraction

"""
filtered = []

for index, pixel_sum in sums:
  if pixel_sum / maximum < threshold:
    filtered.append(TMs[index])

exe = newFixedThreadPool(14)
try:
  def maximumFn(filenames):
    first = klb.readFull(os.path.join(srcDir, filenames[0]))
    r = ArrayImgs.floats(Intervals.dimensionsAsLongArray(first))
    compute(maximum(first, maximum([klb.readFull(os.path.join(srcDir, filename))
                                    for filename in filenames[1:]]))).into(r)
    return r

  chunk_size = 10
  futures = []
  max_projection = None

  for chunk in (filtered[i:i+chunk_size] for i in xrange(0, len(TMs), chunk_size)):
    futures.append(exe.submit(Task(maximumFn, chunk)))
    if len(futures) == 14:
      if max_projection is None:
        first = futures[0].get()
        max_projection = ArrayImgs.floats(Intervals.dimensionsAsLongArray(first))
      # Compute max for existing images
      compute(maximum(max_projection, maximum([f.get() for f in futures]))).into(max_projection)
      futures = []

  IL.wrap(max_projection, "max projection").show()
  
finally:
  exe.shutdown()
"""




