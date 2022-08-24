# How to run this script:
# 1. Download Fiji from https://fiji.sc
# 2. $ git clone https://github.com/acardona/scripts
# 3. Launch Fiji, then File - New - Script
# 4. Open the script file or copy-paste it in and select "Language - Python"
# 5. Edit the sys.path.append to point to where you cloned the git repos
# 6. Edit the file path to the source N5 volume.
# 7. Click "Run" in the Script Editor.

# Convention:
# "imp" is a variable pointing to an ij.ImagePlus instance
# "img" is a variable pointint to a net.imglib2.RandomAccessibleInterval
#       which often is also a net.imglib2.IterableInterval and net.imglib2.img.Img
#       and most likely also a net.imglib2.img.cell.CellImg or net.imglib2.img.array.ArrayImg

import sys
sys.path.append("/home/albert/lab/scripts/python/imagej/IsoView-GCaMP")
from lib.io import readN5, writeN5
from lib.ui import showStack
from net.imglib2.view import Views
from net.imglib2.img.display.imagej import ImageJFunctions as IL

# Path to the parent directory of the N5 volume
n5dir = "/home/albert/catsop-server/volumes/fibsem/all-larvae.n5/1120/v0/raw/"

name = "s0"  # Name of the N5 volume

# To open the whole N5 volume as an ImageJ virtual stack:
#img = readN5(n5dir, name, show="IJ")

# To open the whole N5 volume with the BigDataViewer:
#img = readN5(n5dir, name, show="BDV")

# To open only a subvolume of the N5 volume:
img = readN5(n5dir, name, show=None)
minCoords = [12029, 10063, 4495]
maxCoords = [13724, 11455, 5120]
view = Views.interval(img, minCoords, maxCoords)
imp = showStack(Views.zeroMin(view), title="octo_AL_crop")


# To write the subvolume as N5, do:
targetN5dir = "/home/albert/Desktop/t2/"
name_subvolume = name + "-" + "_".join("%s%s" % (c, l) for c, l in zip(minCoords + maxCoords, "xyzxyz"))
block_size = [256, 256, 256]
gzip_compression_level = 0 # from 0 (none) to 9 (max), often 4 is a good trade off in speed vs amount of de/compression
writeN5(view, targetN5dir, name_subvolume, block_size, gzip_compression_level=gzip_compression_level)

