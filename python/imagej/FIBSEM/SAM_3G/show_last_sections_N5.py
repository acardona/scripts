import sys
libDir = "/lmb/home/acardona/lab/scripts/python/imagej/IsoView-GCaMP/"

sys.path.append(libDir)
from lib.io import readN5
from lib.ui import showStack
from net.imglib2.view import Views

path = "/net/fibserver1/raw/SAM_3G/samia/original_samia2.n5/volumes/"
name = "s0"
img = readN5(path, name, show=None)

imgLast10 = Views.interval(img,
                           [0, 0, img.dimension(2) -100],
                           [img.dimension(0) -1, img.dimension(1) -1, img.dimension(2) - 1])

imp = showStack(imgLast10, title="%i-%i" % (img.dimension(2) -10, img.dimension(2) -1))