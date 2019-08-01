# Albert Cardona 2019-05-31
#
# A series of scripts to register FIBSEM serial sections.
# ASSUMES there is only one single image per section.
# ASSUMES all images have the same dimensions and pixel type.
# 
# This program is similar to the plugin Register Virtual Stack Slices
# but uses more efficient and densely distributed features,
# and also matches sections beyond the direct adjacent for best stability
# as demonstrated for elastic registration in Saalfeld et al. 2012 Nat Methods.
# 
# The program also offers functions to export for CATMAID.
#
# 1. Extract blockmatching features for every section.
# 2. Register each section to its adjacent, 2nd adjacent, 3rd adjacent ...
# 3. Jointly optimize the pose of every section.
# 4. Export volume for CATMAID.

import os, sys, traceback
sys.path.append("/groups/cardona/home/cardonaa/lab/scripts/python/imagej/IsoView-GCaMP/")
from mpicbg.models import TranslationModel2D
from mpicbg.imagefeatures import FloatArray2DSIFT
from net.imglib2.img.io.proxyaccess import ShortAccessProxy
from net.imglib2.type.numeric.integer import UnsignedByteType, UnsignedShortType
from lib.serial2Dregistration import align, viewAligned, export8bitN5, loadImp



srcDir = "/groups/cardona/cardonalab/FIBSEM_L1085/" # MUST have an ending slash
tgtDir = "/groups/cardona/cardonalab/Albert/FIBSEM_L1085/" # for CSV files
exportDir = os.path.join(tgtDir, "n5/") # for the N5 volume

filepaths = [os.path.join(srcDir, filename)
             for filename in sorted(os.listdir(srcDir))
             if filename.endswith("InLens_raw.tif")]
interval = None #[[4096, 4096],
                # [12288 -1, 12288 -1]] # to open only that, or None
pixelType = UnsignedShortType
proxyType = ShortAccessProxy

# Parameters for blockmatching
params = {
 'scale': 0.1, # 10%
 'meshResolution': 10, # 10 x 10 points = 100 point matches maximum
 'minR': 0.1, # min PMCC (Pearson product-moment correlation coefficient)
 'rod': 0.9, # max second best r / best r
 'maxCurvature': 1000.0, # default is 10
 'searchRadius': 100, # a low value: we expect little translation
 'blockRadius': 200 # small, yet enough
}

# Parameters for computing the transformation models
paramsTileConfiguration = {
  "n_adjacent": 3, # minimum of 1; Number of adjacent sections to pair up
  "maxAllowedError": 0, # Saalfeld recommends 0
  "maxPlateauwidth": 200, # Like in TrakEM2
  "maxIterations": 2, # Saalfeld recommends 1000 -- here, 2 iterations (!!) shows the lowest mean and max error for dataset FIBSEM_L1116
  "damp": 1.0, # Saalfeld recommends 1.0, which means no damp
}

# Parameters for SIFT features, in case blockmatching fails due to large translation
paramsSIFT = FloatArray2DSIFT.Param()
paramsSIFT.fdSize = 8 # default is 4
paramsSIFT.fdBins = 8 # default is 8
paramsSIFT.maxOctaveSize = 1024 # will be changed later to adapt to image size
paramsSIFT.steps = 3
paramsSIFT.minOctaveSize = 256 # will be changed later to adapt to image size
paramsSIFT.initialSigma = 1.6 # default 1.6

params["paramsSIFT"] = paramsSIFT


# Ensure target directories exist
if not os.path.exists(tgtDir):
  os.mkdir(tgtDir)

csvDir = os.path.join(tgtDir, "csvs")

if not os.path.exists(csvDir):
  os.mkdir(csvDir)


# Run the alignment
matrices = align(filepaths, csvDir, params, paramsTileConfiguration)


"""
# Show only a cropped middle area
x0 = 3 * dimensions[0] / 8
y0 = 3 * dimensions[1] / 8
x1 = x0 + 2 * dimensions[0] / 8 -1
y1 = y0 + 2 * dimensions[1] / 8 -1
print "Crop to: x=%i y=%i width=%i height=%i" % (x0, y0, x1 - x0 + 1, y1 - y0 + 1)
#viewAligned(filepaths, csvDir, params, paramsTileConfiguration, dimensions,
#            FinalInterval([x0, y0], [x1, y1]))
"""


# Write the whole volume in N5 format
name = srcDir.split('/')[-2]
# Export ROI:
# x=864 y=264 width=15312 h=17424
interval = FinalInterval([864, 264], [864 + 15312 -1, 264 + 17424 -1])


# Don't use compression: less than 5% gain, at considerable processing cost.
# Expects matrices.csv file to exist already
#export8bitN5(filepaths, dimensions, loadMatrices("matrices", csvDir),
#             name, exportDir, interval, gzip_compression=0, block_size=[256, 256, 64], # ~4 MB per block
#             copy_threads=1, n5_threads=0)
