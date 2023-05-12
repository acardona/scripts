# Albert Cardona 2019-05-31
#
# A script to register FIBSEM serial sections.
# ASSUMES there is only one single image per section.
# ASSUMES all images have the same dimensions and pixel type.
# 
# This program is similar to the plugin Register Virtual Stack Slices
# but uses more efficient and densely distributed features,
# and also matches sections beyond the direct adjacent for best stability
# as demonstrated for elastic registration in Saalfeld et al. 2012 Nat Methods.
# 
# The program also offers functions to export for CATMAID as N5 format (not multiresolution,
# the multiresolution pyramid can be generated later with a different software).
#
# 1. Extract blockmatching features for every section.
# 2. Register each section to its adjacent, 2nd adjacent, 3rd adjacent ...
# 3. Jointly optimize the pose of every section.
# 4. View the volume as a virtual stack (no image files copied, all transformed on the fly)
# 5. Export volume for CATMAID as N5.

import os, sys
sys.path.append("/lmb/home/acardona/lab/scripts/python/imagej/IsoView-GCaMP/")
from lib.io import findFilePaths, readFIBSEMdat
from lib.util import numCPUs, syncPrint
from lib.serial2Dregistration import setupImageLoader, viewAligned, export8bitN5
from lib.registration import loadMatrices
from net.imglib2.type.numeric.integer import UnsignedShortType
from net.imglib2 import FinalInterval
from mpicbg.imagefeatures import FloatArray2DSIFT
from ij import IJ



srcDir = "/net/ark/raw/fibsem/pygmy-squid/2021-12_popeye/Popeye2" # MUST have an ending slash
tgtDir = "/data1/acardona/registration/Popeye2/"
tgtDirN5 = "/net/ark/raw/fibsem/pygmy-squid/2021-12_popeye/Popeye2"
csvDir = os.path.join(tgtDir, "csvs")

# Recursive search into srcDir for files ending in InLens_raw.tif
filepaths = findFilePaths(srcDir, ".dat")

# Image properties: ASSUMES all images have the same properties
# (While the script an cope with images of different dimensions for registration,
# the visualization and export would need minor adjustments to cope.)
dimensions = [18214, 14464]

properties = {
 'name': "popeye2",
 'img_dimensions': dimensions,
 'srcDir': srcDir,
 'pixelType': UnsignedShortType,
 'n_threads': 32,
 'invert': True,
 'CLAHE_params': [200, 256, 3.0], # For viewAligned. Use None to disable. Blockradius, nBins, slope.
}

# Validate file sizes:
# header of 1024 bytes
# two 16-bit channel images of width * height
expected_size = 1024 + dimensions[0] * dimensions[1] * 2 * 2
# BUT NO: there is a trailer, in addition to a header, of unknow size
expected_size = 1053794601

filepaths2 = []
for path in filepaths:
  if os.stat(path).st_size != expected_size:
    print os.stat(path).st_size, "vs expected:", expected_size
    print "Corrupted file path:", path
  else:
    filepaths2.append(path)

print "Found ", len(filepaths2) - len(filepaths), "corrupted images"
filepaths = filepaths2


# Parameters for blockmatching
params = {
 'scale': 0.1, # 10%
 'meshResolution': 16, # 10 x 10 points = 100 point matches maximum
 'minR': 0.1, # min PMCC (Pearson product-moment correlation coefficient)
 'rod': 0.9, # max second best r / best r
 'maxCurvature': 1000.0, # default is 10
 'searchRadius': 100, # a low value: we expect little translation
 'blockRadius': 200, # small, yet enough
}

# Parameters for SIFT features, in case blockmatching fails due to large translation or image dimension mistmatch
paramsSIFT = FloatArray2DSIFT.Param()
paramsSIFT.fdSize = 8 # default is 4
paramsSIFT.fdBins = 8 # default is 8
paramsSIFT.maxOctaveSize = int(max(1024, dimensions[0] * params["scale"]))
paramsSIFT.steps = 3
paramsSIFT.minOctaveSize = int(paramsSIFT.maxOctaveSize / pow(2, paramsSIFT.steps))
paramsSIFT.initialSigma = 1.6 # default 1.6


# Parameters for computing the transformation models
paramsTileConfiguration = {
  "n_adjacent": 3, # minimum of 1; Number of adjacent sections to pair up
  "maxAllowedError": 0, # Saalfeld recommends 0
  "maxPlateauwidth": 200, # Like in TrakEM2
  "maxIterations": 1000, # Saalfeld recommends 1000 -- here, 2 iterations (!!) shows the lowest mean and max error for dataset FIBSEM_L1116
  "damp": 1.0, # Saalfeld recommends 1.0, which means no damp
}




# Dimensions of the ROI to show once the registration completes.
# Default: show all. Adjust to show only a cropped area.
x0 = 0 # X coordinate of the first pixel to show
y0 = 0 # Y coordinate of the first pixel to show
x1 = dimensions[0] -1 # X coordinate of the last pixel to show
y1 = dimensions[1] -1 # Y coordinate of the last pixel to show
syncPrint("Crop to: x=%i y=%i width=%i height=%i" % (x0, y0, x1 - x0 + 1, y1 - y0 + 1))


# Adjust image loader as needed:
if filepaths[0].endswith(".dat"):
  loader = lambda filepath: readFIBSEMdat(filepath, channel_index=0, asImagePlus=True, toUnsigned=True)[0]
  syncPrint("Using io.readFIBSEMdat to read image files.")
  setupImageLoader(loader)
else:
  loader = IJ.loadImage
  syncPrint("Using IJ.loadImage to read image files.")


# Triggers the whole alignment and ends by showing a virtual stack of the aligned sections.
# Crashware: can be restarted anytime, will resume from where it left off.
viewAligned(filepaths, csvDir, params, paramsSIFT, paramsTileConfiguration, properties,
            FinalInterval([x0, y0], [x1, y1]))


# When the alignment is good enough, then export as N5 by swapping "False" for "True" below:

if False:
  # Write the whole volume in N5 format
  name = properties["name"] # srcDir.split('/')[-2]
  exportDir = os.path.join(tgtDirN5, "n5")
  # Export ROI:
  # x=864 y=264 width=15312 h=17424
  interval = FinalInterval([0, 0], [dimensions[0] -1, dimensions[1] -1])

  export8bitN5(filepaths,
               loader,
               dimensions,
               loadMatrices("matrices", csvDir), # expects matrices.csv file to exist already
               name,
               exportDir,
               interval,
               gzip_compression=0, # Don't use compression: less than 5% gain, at considerable processing cost
               invert=True,
               CLAHE_params=properties["CLAHE_params"],
               n5_threads=properties["n_threads"],
               block_size=[384, 384, 32]) # ~4 MB per block

