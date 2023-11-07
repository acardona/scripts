import sys
sys.path.append("/lmb/home/acardona/lab/scripts/python/imagej/IsoView-GCaMP/")
from net.imglib2.view import Views
from net.imglib2 import FinalInterval
from lib.io import readN5
from lib.ui import showStack

name = "PedroParker"
img3D = readN5("/net/zstore1/FIBSEM/Pedro_parker/registration-Albert/n5/", name, show=None)
#fov = Views.interval(img3D, FinalInterval([4096, 4096, 0], [8192 -1, 8192 -1, 13770 -1]))
fov = img3D # whole
imp = showStack(fov, title=name)
#imp.setPosition(imp.getStack().size()) # last slice