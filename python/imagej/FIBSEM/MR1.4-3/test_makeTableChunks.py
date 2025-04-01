from __future__ import with_statement
import sys, os
sys.path.append("/lmb/home/acardona/lab/scripts/python/imagej/IsoView-GCaMP/")
from lib.registration import saveMatrices, loadMatrices
from lib.io import loadFilePaths
from lib.util import syncPrintQ
from lib.ui import grabImg
from lib.serial2Dregistration import align, alignInChunks, handleNoPointMatches, computeShifts, makeFilterFeaturesFn, makeTableChunks
from lib.montage2d import ensureMontages, makeMontageGroups, makeVolume, makeSliceLoader, showAlignedImg, fuseMatrices, fuseTranslationMatrices
from net.imglib2.img.display.imagej import ImageJFunctions as IL
from mpicbg.imagefeatures import FloatArray2DSIFT
from itertools import izip
from net.imglib2 import FinalInterval
from net.imglib2.util import Intervals
from net.imglib2.type.numeric.integer import UnsignedByteType
from net.imglib2.view import Views
from java.lang import Runtime
from ij.gui import Roi
from ij import IJ





# MR1.4-3 volume
# Resolution is: 8x8x8 nm, FIBSEM
name = "MR1.4-3"

# Folders
srcDir = "/net/fibserver1/raw/" + name + "/"
#srcDir = "/data/raw/" + name + "/" # when running from fibserver1
tgtDir = "/net/zstore1/FIBSEM/" + name + "/registration/"
csvDir = tgtDir + "csv/" # for in-section montaging
#csvDirZ = tgtDir + "csvZ-chunked/" # for cross-section alignment with SIFT+RANSAC
csvDirZ = "/data1/acardona/MR1.4-3/registration/csvZ-chunked/" # for cross-section alignment with SIFT+RANSAC
csvDirBM = tgtDir + "csvBM/" # for cross-section alignment with BlockMatching
repairedDir = "/net/zstore1/FIBSEM/" + name + "/repaired/" # Folder with repaired images, if any

# Ensure tgtDir and csvDir exist
for csvD in [csvDir, csvDirZ, csvDirBM]:
  if not os.path.exists(csvD):
    os.makedirs(csvD) # recursive directory creation


# Image tile overlap parameters
offset = 80 # pixels The left margin of each image is severely elastically deformed. Does it matter for SIFT?
overlap = 990 # pixels
nominal_overlap = 1000 # 8 microns at 8 nm/px = 1000 px

# Intra-section montage: expecting either 1 section/slide or 1x2 sections/slice with each tile being 15000x8375
# Will need rotation to the right at the end.
# Single-tile sections have images of 12500x12500 (at least at the beginning)

# Working canvas
section_width = 16000 # pixels, after section-wise montaging
section_height = 16000
# So a canvas of 256,000,000 pixels: just 256 MB

# Image contrast parameters
params_pixels = {
  "invert": True,
  "CLAHE_params": [200, 255, 2.0], # blockRadius, n_bins, and slope in stdDevs
  "as8bit": True,
  "contrast": (500, 1000), # thresholds in pixel counts per histogram bin
  "roiFn": lambda sp: Roi(sp.width / 6, sp.height / 6, 2 * sp.width / 3, 2 * sp.height / 3), # middle 2/3rds to discard edges
}

# CHECK whether some sections have problems
# SOME IMAGES fail to open for reading the header with readFIBSEMHeader
check = False # To be used only the first time that the script is run



# Parameters for SIFT features, in case blockmatching fails due to large translation or image dimension mismatch
paramsSIFT = FloatArray2DSIFT.Param()
paramsSIFT.steps = 1
paramsSIFT.minOctaveSize = 0 # will be updated in a clone
paramsSIFT.maxOctaveSize = 0 # will be updated in a clone
paramsSIFT.initialSigma = 1.6 # default 1.6
paramsSIFT.fdSize = 8 # default is 4
paramsSIFT.fdBins = 8 # default is 8


paramsRANSAC = {
  "iterations": 1000,
   "maxEpsilon": 10, # pixels, maximum error allowed, usual number is 25. Started out as 5 for the first ~6000 sections or so.
   "minInlierRatio": 0.01 # 1%
}

# For intra-section montages:
paramsTileConf = {
  "maxAllowedError": 0, # Saalfeld recommends 0
  "maxPlateauwidth": 200, # Like in TrakEM2
  "maxIterations": 1000, # Saalfeld recommends at least 1000
  "damp": 1.0, # Saalfeld recommends 1.0, which means no damp
  "nThreadsOptimizer": 10 # for the TileUtil.optimizeConcurrently. 2 seems a priori best when running 128 montages in parallel, but 3 ensures full usage of 256 cores
}

# How many sections to montage in parallel
nThreadsMontaging = Runtime.getRuntime().availableProcessors() / 2 # e.g., 128. Each montage uses 2 threads


# Find all .dat files, as a sorted list
filepaths = loadFilePaths(srcDir, ".dat", csvDir, "imagefilepaths")


# Sections known to have problems (found via check = True above)
to_remove = set([
#"Merlin-WEMS_24-02-27_170732_", # added 0-0-0 tile to ignore: truncated, no pixels, only header
#"Merlin-WEMS_24-03-15_130137_", # repaired truncated
#"Merlin-WEMS_24-03-05_062018_", # added 0-1-0 tile to ignore
#"Merlin-WEMS_24-02-27_165658_", # repaired truncated
#"Merlin-WEMS_24-03-13_235528_", # repaired truncated
#"Merlin-WEMS_24-03-01_171102_", # no problems found manually with readFIBSEMdat
#"Merlin-WEMS_24-03-10_054103_", # repaired truncated
#"Merlin-WEMS_24-02-27_201135_", # repaired truncated
#"Merlin-WEMS_24-02-23_213519_", # repair truncated, was opening funny with a duplicated bottom
])

ignore_images = set([
 "Merlin-WEMS_24-02-27_170732_0-0-0.dat", # only header, whole image truncated
 "Merlin-WEMS_24-03-05_062018_0-0-0.dat"  # partial truncation without sample in it, would occlude the 0-1-0 tile
])

replace_images = {
  "Merlin-WEMS_24-03-02_190309_0-0-0.dat": "Merlin-WEMS_24-03-02_190309_0-0-0.tif",
}

# Sorted group names, one per section
# TODO create a way to get images from an alternative folder: the repaired folder
# or to ignore images (e.g., 062018 for 0-0-0)
groupNames, tileGroups = makeMontageGroups(filepaths, to_remove, check,
                                           alternative_dir=repairedDir,
                                           ignore_images=ignore_images,
                                           replace_images=replace_images,
                                           writeDir=csvDir)
                                           
                                           
                                           
# Skip sections 1-963: no sample in them, just resin
# And skip subsequent 1904 sections which end in somas and with a huge gap. 
groupNames = groupNames[964+1904:20000+964]
tileGroups = tileGroups[964+1904:20000+964]


# Sections with problems:
# 1. Merlin-WEMS_24-02-27_170732_ : missing 0-0-0 tile (the top one)
# Solution: replace with next (previous is truncated at the bottom)
# It's at index 1751 (0-based)
groupNames[1751] = groupNames[1752]
tileGroups[1751] = tileGroups[1752]


# Montage all sections
#ensureMontages(groupNames, tileGroups, overlap, nominal_overlap, offset, paramsSIFT, paramsRANSAC, paramsTileConf, csvDir, nThreadsMontaging)

# Prepare an image volume where each section is a Cell with an ArrayImg showing a montage or a single image, and preprocessed (invert + CLAHE)
# NOTE: it's 8-bit
volumeImgMontaged = makeVolume(groupNames, tileGroups, section_width, section_height, overlap, nominal_overlap, offset,
                               paramsSIFT, paramsRANSAC, paramsTileConf, csvDir, params_pixels,
                               show=True, matrices=None, section_offsets=sectionOffsets, title="Montages")


# Function to filter out features outside the tissue
model_path = os.path.join(tgtDir, "MR1.4-3_section1+6000_0.025.labkit.classifier") # from LabKit
model_width = 400 # target width for resizing so as to match the dimensions of the image used when training the model.


#montage_img = grabImg(IJ.getImage())
montage_img = volumeImgMontaged


properties = {
 'name': "MR1.4-3",
 'img_dimensions': Intervals.dimensionsAsLongArray(montage_img),
 'srcDir': srcDir,
 'pixelType': UnsignedByteType,
 'n_threads': 150, # cardona-cpu1 36, # fibserver1 has 40 CPUs # use a low number when having to load images (e.g., montaging and feature extraction) and a high number when computing pointmatches.
 'invert': False, # Processing is done already
 'CLAHE_params': None, #[200, 256, 3.0], # For viewAligned. Use None to disable. Blockradius, nBins, slope.
 'use_SIFT': False,
 'SIFT_validateByFileExists': True, # Avoid loading and parsing SIFT features just to make sure they are fine.
 'RANSAC_iterations': 1000,
 'RANSAC_maxEpsilon': 25, # default is 25, for ssTEM 40nm sections cross-section alignment, but FIBSEM at 8nm sections is far thinner
 'RANSAC_minInlierRatio': 0.01,
 'preload': 64, # 64 sections, matching the export as N5 Z axis
 'handleNoPointMatchesFn': handleNoPointMatches, # Amounts to no translation, with a single PointMatch at 0,0
 'max_n_pointmatches': 1000, # When loading, keep only a sensible subset
 'ignoreCacheFn': lambda index: False, # True if index > 17000 else False
 'filterFeaturesFn': makeFilterFeaturesFn(model_path, model_width), # Filter out features not in the tissue but in the resin, to ignore the resin which has streaks and curtains
}




table, frame, listener = makeTableChunks(groupNames, montage_img, csvDirZ, properties)

