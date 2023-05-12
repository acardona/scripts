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
sys.path.append("/lmb/home/acardona/lab/scripts/python/imagej/IsoView-GCaMP/")
from mpicbg.models import TranslationModel2D
from mpicbg.imagefeatures import FloatArray2DSIFT
from net.imglib2.type.numeric.integer import UnsignedShortType
from net.imglib2 import FinalInterval
from lib.util import syncPrint
from lib.io import findFilePaths, readFIBSEMdat
from lib.registration import loadMatrices
from lib.serial2Dregistration import setupImageLoader, align, viewAligned, viewAlignedPlain, exportN5, computeMaxInterval
from ij import IJ


srcDir = "/net/ark/janelia/dm11/cardonalab/FIBSEM_L1120_FullCNS_8x8x8nm/" # MUST have an ending slash
tgtDir = "/net/zstore1/achampion/alignment/output/1120/v0/" # for CSV files
exportDir = "/net/zstore1/acardona/20230329_FIBSEM_L1120_octo_without_CLAHE/" # for the N5 volume

# Recursive search into srcDir for files ending a given extension
filepaths = findFilePaths(srcDir, ".dat")

# Image properties: ASSUMES all images have the same properties
# (While the script an cope with images of different dimensions for registration,
# the visualization and export would need minor adjustments to cope.)
dimensions = [20000, 20000] # WARNING after 0-based index 12554 images are 15000x10000 px

properties = {
 'name': "octo",
 'img_dimensions': dimensions,
 'srcDir': srcDir,
 'pixelType': UnsignedShortType,
 'n_threads': 32,
 'invert': True,
 'CLAHE_params': None, # [200, 256, 3.0], # For viewAligned. Use None to disable. Blockradius, nBins, slope.
 'preload': 5,
}

# Parameters for blockmatching
params = {
 'scale': 0.5, # 10%
 'meshResolution': 750, # 10 x 10 points = 100 point matches maximum
 'minR': 0.3, # min PMCC (Pearson product-moment correlation coefficient)
 'rod': 0.9, # max second best r / best r
 'maxCurvature': 1000.0, # default is 10
 'searchRadius': 100, # a low value: we expect little translation
 'blockRadius': 120, # small, yet enough
 'siftRod': 0.5 # UNSURE that this belongs here TODO
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
paramsSIFT.maxOctaveSize = 4096 # will be changed later to adapt to image size
paramsSIFT.steps = 3
paramsSIFT.minOctaveSize = 1024 # will be changed later to adapt to image size
paramsSIFT.initialSigma = 1.6 # default 1.6

# Ensure target directories exist
if not os.path.exists(tgtDir):
  os.mkdir(tgtDir)

csvDir = os.path.join(tgtDir, "csvs")

if not os.path.exists(csvDir):
  os.mkdir(csvDir)

# Adjust image loader as needed:
if filepaths[0].endswith(".dat"):
  loader = lambda filepath: readFIBSEMdat(filepath, channel_index=0, asImagePlus=True, toUnsigned=True)[0]
  syncPrint("Using io.readFIBSEMdat to read image files.")
  setupImageLoader(loader)
else:
  loader = IJ.loadImage
  syncPrint("Using IJ.loadImage to read image files.")



print "Filepaths found:", len(filepaths)

# Use the whole interval
interval3D = computeMaxInterval(os.path.join(csvDir, "matrices.csv"), dimensions, limit=12554) # NOTE limit is unnecesary here, the -10000 displacement is in the first set for some reason.
print "Interval", interval3D
# Use only 2 dimensions
interval = FinalInterval([interval3D.min(0), interval3D.min(1)], [interval3D.max(0), interval3D.max(1)])

# Run the alignment
matrices = align(filepaths, csvDir, params, paramsSIFT, paramsTileConfiguration, properties)


#for i, m in enumerate(matrices):
#  print m




# Visualize the result of the alignment with a VirtualStack
img = viewAlignedPlain(filepaths, csvDir, params, paramsSIFT, paramsTileConfiguration, properties, interval)



# Write the whole volume in N5 format
name = srcDir.split('/')[-2]

# Don't use compression: less than 5% gain, at considerable processing cost.
# Expects matrices.csv file to exist already
"""
exportN5(filepaths, dimensions, loadMatrices("matrices", csvDir),
         name, exportDir, interval,
         gzip_compression=0,
        invert=True, CLAHE=None,
        block_size=[256, 256, 64], # ~4 MB per block
        n5_threads=0, as8bit=False)
"""
