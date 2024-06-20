import sys, os
sys.path.append("/lmb/home/acardona/lab/scripts/python/imagej/IsoView-GCaMP/")
from net.imglib2.view import Views
from org.janelia.saalfeldlab.n5.universe import N5Factory
from org.janelia.saalfeldlab.n5.imglib2 import N5Utils
from lib.io import readN5


n5pathNew = "/net/zstore1/FIBSEM/MR1.4-3/registration/n5-3/"
n5nameNew = "MR1.4-3"

imgNew, impNew = readN5(n5pathNew, n5nameNew, show="IJ")
impNew.setTitle(impNew.getTitle() + " new")

n5pathOld = "/net/zstore1/FIBSEM/MR1.4-3/registration/n5/"
n5nameOld = "s0"

imgOld = readN5(n5pathOld, n5nameOld, show=None)

missing = Views.interval(imgOld,
                         [0, 0, 16384],
                         [imgOld.dimension(0) -1,
                          imgOld.dimension(1) -1,
                          16399])
             
n5writeNew = N5Factory().openWriter(os.path.join(n5pathNew, n5pathNew))
N5Utils.saveRegion(missing, n5writeNew, "/") # path is relative

impNew.setNSlice(16400)
