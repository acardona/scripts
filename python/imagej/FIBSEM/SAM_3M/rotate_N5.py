# Rotate 180 degrees
import sys, os
libDir = "/lmb/home/acardona/lab/scripts/python/imagej/IsoView-GCaMP/"
sys.path.append(libDir)
from lib.io import readN5, writeN5, ensureDirsExist
from net.imglib2.view import Views
from net.imglib2.img.display.imagej import ImageJFunctions as IL

# N5 volume in disk
n5Dir = "/net/fibserver1/raw/SAM_3M/registration/n5"
name = "s0"

# Load the N5 volume, which is upside down
img = readN5(n5Dir, name, show=None)

# Rotate twice to the right: 180 degrees
img180 = Views.rotate(Views.rotate(img, 0, 1), 0, 1)

# For visualization better use level 5, 's5'
#IL.wrap(img180, "rotated 180").show()

# Write to disk
n5Dir180 = os.path.join(os.path.split(n5Dir)[0], "n5-180")
ensureDirsExist(n5Dir180)
blockSize = [256, 256, 64]
writeN5(img180, n5Dir180, name, blockSize, gzip_compression_level=4, n_threads=128)

