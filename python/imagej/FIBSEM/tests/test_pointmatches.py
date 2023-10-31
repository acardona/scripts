# Visualize pointmatches

from __future__ import with_statement
import sys, os
sys.path.append("/home/albert/lab/scripts/python/imagej/IsoView-GCaMP/")
from lib.features import loadPointMatches
from lib.io import readFIBSEMdat
from ij.gui import PointRoi
from jarray import zeros
from ij import ImagePlus
from ij.process import ShortProcessor


root = "/home/albert/zstore1/FIBSEM/Pedro_parker/"


group1 = "Merlin-FIBdeSEMAna_23-07-14_110407_"
group2 = "Merlin-FIBdeSEMAna_23-07-14_110750_"


# Shows massive displacement of the points for the first image, as if it was the second.
# The first image is much larger, one of the over 2G images.
#group1 = "Merlin-FIBdeSEMAna_23-07-14_110750_"
#group2 = "Merlin-FIBdeSEMAna_23-07-14_112606_"

# Shows systematic displacement of features. Less noticeable because the two images have the same dimensions and are consecutive.
#group1 = "Merlin-FIBdeSEMAna_23-07-14_112606_"
#group2 = "Merlin-FIBdeSEMAna_23-07-14_112836_"

filepath1 = root + "M07/D14/" + group1 + "0-0-0.dat"
filepath2 = root + "M07/D14/" + group2 + "0-0-0.dat"


csvDir = root + "registration-Albert/csvZ-debug/"

params = {"rod": 0.9}

pointmatches = loadPointMatches(group1, group2, csvDir, params)
x1, y1, x2, y2 = [zeros(len(pointmatches), 'f') for i in xrange(4)]
for i, pm in enumerate(pointmatches):
  x1[i] = pm.getP1().getL()[0]
  y1[i] = pm.getP1().getL()[1]
  x2[i] = pm.getP2().getL()[0]
  y2[i] = pm.getP2().getL()[1]

roi1 = PointRoi(x1, y1, len(x1))
roi2 = PointRoi(x2, y2, len(x2))

imp1, imp2 = [readFIBSEMdat(filepath, channel_index=0, asImagePlus=True)[0] for filepath in [filepath1, filepath2]]

# Map images to 26000x26000
imp1c = ImagePlus(imp1.getTitle(), ShortProcessor(26000, 26000))
imp1c.getProcessor().insert(imp1.getProcessor(), 0, 0)
imp2c = ImagePlus(imp2.getTitle(), ShortProcessor(26000, 26000))
imp2c.getProcessor().insert(imp2.getProcessor(), 0, 0)

imp1c.setRoi(roi1)
imp2c.setRoi(roi2)

imp1c.show()
imp2c.show()