from __future__ import with_statement
import sys, os, csv
sys.path.append("/home/albert/lab/scripts/python/imagej/IsoView-GCaMP/")
from lib.synthetic import virtualPointsRAI
from ij3d import Image3DUniverse
from itertools import islice, imap
from net.imglib2 import FinalInterval, RealPoint
from net.imglib2.view import Views
from net.imglib2.type.numeric.integer import UnsignedByteType
from net.imglib2.img.display.imagej import ImageJVirtualStackUnsignedByte
from ij import ImagePlus, CompositeImage


baseDir = "/home/albert/shares/cardonalab/Albert/2017-05-10_1018/"
# A file whose header has the points as "x::y::z"
csvFilename = "deconvolved/CM00-CM01_deltaFoF.csv"

somaDiameter = 8 # pixels
radius = somaDiameter / 2.0
interval = FinalInterval([406, 465, 325])
minimum = -1.0 # actual min: -5.0
maximum = 2.0 # actual max: 9.4
span = maximum - minimum
range_max = 255 # should be 255

def to8bitRange(values):
  return [UnsignedByteType(int((min(max(val, minimum), maximum) / span) * range_max)) for val in values]

with open(os.path.join(baseDir, csvFilename), 'r') as csvfile:
  reader = csv.reader(csvfile, delimiter=',', quotechar='"')
  header = reader.next()
  peaks = [RealPoint.wrap(imap(float, peak.split('::'))) for peak in islice(header, 1, None)]
  frames = [virtualPointsRAI(peaks, radius, interval, inside=to8bitRange(map(float, islice(row, 1, None)))) for row in reader]
  # DEBUG: only first 10
  frames = frames[:10]
  img4D = Views.stack(frames)
  # Scale by a factor of 2 in every dimension by nearest neighbor, sort of:
  img4D = Views.subsample(img4D, 2)
  imp = ImagePlus("deltaF/F", ImageJVirtualStackUnsignedByte.wrap(img4D))
  imp.setDimensions(1, img4D.dimension(2), img4D.dimension(3))
  imp.setDisplayRange(0, 255)
  com = CompositeImage(imp, CompositeImage.GRAYSCALE)
  com.show()
  univ = Image3DUniverse(512, 512)
  univ.show()
  univ.addVoltex(com)
