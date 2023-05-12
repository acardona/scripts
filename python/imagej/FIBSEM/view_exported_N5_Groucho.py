import sys
#sys.path.append("/lmb/home/acardona/lab/scripts/python/imagej/IsoView-GCaMP/")
sys.path.append("/home/albert/lab/scripts/python/imagej/IsoView-GCaMP/")
from net.imglib2.view import Views
from net.imglib2 import FinalInterval
from lib.io import readN5
from lib.ui import showStack, wrap, navigate2DROI
from java.awt import Rectangle

name = "s0"
img3D = readN5("/home/albert/ark/raw/fibsem/amphioxus/groucho/n5", name, show=None)
#fov = Views.interval(img3D, FinalInterval([4096, 4096, 0], [8192 -1, 8192 -1, 13770 -1]))
fov = img3D # whole


# UNCOMMENT to open the whole stack
#imp = showStack(fov, title=name)
#imp.show()


# Directly open section 8031 and only for an ROI over a bit of the brain
x = 11227
y = 7897
width = 3240
height = 3320
"""
fov = Views.interval(img3D, FinalInterval([x, y, 0], # min coords
                                          [x + width - 1, # max coords
                                           y + height -1,
                                           img3D.dimension(2) -1]))
imp = wrap(fov, title="Small ROI in the Groucho brain", n_channels=1)
imp.setPosition(8031) # in the middle of a 64-section block
imp.show()
"""

# Better: navigatable with arrows in X,Y and < > in Z
impN = navigate2DROI(img3D,
                     FinalInterval([x, y], # min coords
                                   [x + width - 1, # max coords
                                    y + height -1]),
                     indexZ=9718) # section shown

