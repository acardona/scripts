from __future__ import with_statement
import sys, os, csv
sys.path.append("/groups/cardona/home/cardonaa/lab/scripts/python/imagej/IsoView-GCaMP/")
from lib.io import readN5
from lib.dogpeaks import createDoG
from lib.synthetic import virtualPointsRAI
from lib.ui import showStack, wrap, showAsComposite
from lib.nuclei import findPeaks, mergePeaks, filterNuclei, findNucleiByMaxProjection
from net.imglib2.util import Intervals, ConstantUtils
from net.imglib2.view import Views
from net.imglib2 import RealPoint
from ij import IJ
from net.imglib2.img.display.imagej import ImageJFunctions as IL
from net.imglib2.roi.geom.real import ClosedWritableSphere
from net.imglib2.roi import Masks, Regions
from itertools import imap, islice, izip
from jarray import zeros, array

baseDir = "/groups/cardona/cardonalab/Albert/2017-05-10_2_1019/"
dataset_name = "2017-05-10_2_1019_0-399_409x509x305x800"

# Load entire 4D IsoView deconvolved and registered data set
img4D = readN5(baseDir, dataset_name)

# Split CM00+CM01 (odd) from CM02+CM03 (even) into two series
series = ["CM00-CM01", "CM02-CM03"]
img4Da = Views.subsample(img4D,
                         [1, 1, 1, 2]) # step
img4Db = Views.subsample(Views.interval(img4D, [0, 0, 0, 1], Intervals.maxAsLongArray(img4D)),
                         [1, 1, 1, 2]) # step

showStack(img4Da, title="%s registered+deconvolved" % series[0])
showStack(img4Db, title="%s registered+deconvolved" % series[1])