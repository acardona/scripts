# Test that deserialized SIFT features match the image they were supposedly extracted from

from __future__ import with_statement
import sys, os
sys.path.append("/home/albert/lab/scripts/python/imagej/IsoView-GCaMP/")
from lib.features import loadPointMatches
from lib.io import readFIBSEMdat, deserialize
from ij.gui import PointRoi
from jarray import zeros
from ij import ImagePlus
from ij.process import ShortProcessor


root = "/home/albert/zstore1/FIBSEM/Pedro_parker/"

# Shows massive displacement of the points for the first image, as if it was the second.
# The first image is much larger, one of the over 2G images.
group1 = "Merlin-FIBdeSEMAna_23-07-14_110750_"
group2 = "Merlin-FIBdeSEMAna_23-07-14_112606_"

# Shows systematic displacement of features. Less noticeable because the two images have the same dimensions and are consecutive.
#group1 = "Merlin-FIBdeSEMAna_23-07-14_112606_"
#group2 = "Merlin-FIBdeSEMAna_23-07-14_112836_"

# Same: subtle displacement.
#group1 = "Merlin-FIBdeSEMAna_23-07-14_110407_"
#group2 = "Merlin-FIBdeSEMAna_23-07-14_110750_"


filepath1 = root + "M07/D14/" + group1 + "0-0-0.dat"
filepath2 = root + "M07/D14/" + group2 + "0-0-0.dat"


csvDir = root + "registration-Albert/csvZ-debug/"

features1, features2 = [deserialize(csvDir + group + ".SIFT-features.obj") for group in [group1, group2]]

# Last element of the list is the FloatArray2DSIFT$Param instance
features1.remove(features1.size()-1)
features2.remove(features2.size()-1)

print len(features1)
print len(features2)

def run(features):
  x1, y1 = [zeros(len(features), 'f') for i in xrange(2)]
  for i, feature in enumerate(features):
    loc = feature.location
    x1[i] = loc[0]
    y1[i] = loc[1]
  roi = PointRoi(x1, y1, len(features))
  return roi

roi1 = run(features1)
roi2 = run(features2)

imp1, imp2 = [readFIBSEMdat(filepath, channel_index=0, asImagePlus=True)[0] for filepath in [filepath1, filepath2]]


imp1.setRoi(roi1)
imp1.show()

imp2.setRoi(roi2)
imp2.show()