from __future__ import with_statement
import sys, os, csv
sys.path.append("/home/albert/lab/scripts/python/imagej/IsoView-GCaMP/")
from lib.synthetic import virtualPointsRAI
from lib.ui import wrap
from ij3d import Image3DUniverse
from itertools import islice


baseDir = "/home/albert/shares/cardonalab/Albert/2017-05-10_1018/"
# A file whose header has the points as "x::y::z"
csvFilename"deconvolved/CM00-CM01_deltaFoF.csv"

somaDiameter = 8 # pixels
radius = somaDiameter / 2.0
interval = FinalInterval([406, 465, 325])
minimum = -5.0
maximum = 9.4
span = maximum - minimum

def to8bitRange(values):
  return [int((min(max(val, minimum), maximum) / span) * 255) for val in values]

with open(os.path.join(baseDir, csvFilename), 'r') as csvfile:
  reader = csv.reader(csvfile, delimiter=',', quotechar='"')
  header = reader.next()
  peaks = [RealPeak.wrap(imap(float, peak.split('::'))) for peak in islice(1, header, None)]
  frames = [virtualPointsRAI(peaks, radius, interval, inside=to8bitRange(map(float, islice(1, row, None)))) for row in reader]
  img4D = Views.stack(frames)
  imp4D = wrap(img4D)
  univ = Image3DUniverse(512, 512)
  univ.show()
  univ.addVoltex(imp4D)
