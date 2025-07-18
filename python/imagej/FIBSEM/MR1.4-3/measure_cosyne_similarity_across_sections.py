# Analyse registration by measuring cosyne similarity across adjacent sections

import sys, os
sys.path.append("/lmb/home/acardona/lab/scripts/python/imagej/IsoView-GCaMP/")
from net.imglib2.view import Views
from org.janelia.saalfeldlab.n5.universe import N5Factory
from org.janelia.saalfeldlab.n5.imglib2 import N5Utils
from lib.io import readN5
from lib.pixels import pairwiseCosyneSimilarity
from ij.measure import ResultsTable

n5path = "/net/zstore1/FIBSEM/MR1.4-3/registration/n5-chunked2/"
n5name = "s3"  # much smaller

img, imp = readN5(n5path, n5name, show="IJ")
imp.show()

cs = pairwiseCosyneSimilarity(img)

table = ResultsTable()
for i, v in enumerate(cs):
  table.incrementCounter()
  table.addValue("section", i+1)
  table.addValue("cosSim", v)

table.show("cosyne similarity")

