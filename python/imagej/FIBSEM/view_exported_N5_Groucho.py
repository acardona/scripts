import sys
#sys.path.append("/lmb/home/acardona/lab/scripts/python/imagej/IsoView-GCaMP/")
sys.path.append("/home/albert/lab/scripts/python/imagej/IsoView-GCaMP/")
from net.imglib2.view import Views
from net.imglib2 import FinalInterval
from lib.io import readN5
from lib.ui import showStack

name = "Groucho"
img3D = readN5("/home/albert/ark/raw/fibsem/pygmy-squid/2021-12_popeye/Popeye2/amphioxus/n5", name, show=None)
#fov = Views.interval(img3D, FinalInterval([4096, 4096, 0], [8192 -1, 8192 -1, 13770 -1]))
fov = img3D # whole
imp = showStack(fov, title=name)
#imp.setPosition(imp.getStack().size()) # last slice