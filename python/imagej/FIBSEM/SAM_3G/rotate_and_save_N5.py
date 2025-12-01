import os, sys
# REGISTRATION LIBRARY
libDir = "/lmb/home/acardona/lab/scripts/python/imagej/IsoView-GCaMP/"
sys.path.append(libDir)

from lib.io import readN5, writeN5
from net.imglib2.view import Views
from lib.ui import showBDV

n5Dir = "/net/fibserver1/raw/SAM_3G/samia/original_samia.n5/volumes/"
name = "s0"

img = readN5(n5Dir, name, show=None)

# Rotate 90 degrees to the right
img = Views.rotate(img, 0, 1)

# Check rotation
#showBDV(img, title="SAM_3G")

n5DirRotated = "/net/fibserver1/raw/SAM_3G/samia/original_rotated90.n5/"

#  Save as N5
writeN5(img, n5DirRotated, name, [256, 256, 64], gzip_compression_level=4, n_threads=0)