from __future__ import with_statement
import sys, os
sys.path.append("/lmb/home/acardona/lab/scripts/python/imagej/IsoView-GCaMP/")
from lib.registration import saveMatrices, loadMatrices
from lib.io import loadFilePaths
from lib.util import syncPrintQ
from lib.serial2Dregistration import align, handleNoPointMatches
from lib.montage2d import ensureMontages, makeMontageGroups, makeVolume, makeSliceLoader, showAlignedImg, fuseMatrices, fuseTranslationMatrices
from mpicbg.imagefeatures import FloatArray2DSIFT
from itertools import izip
from net.imglib2 import FinalInterval
from net.imglib2.util import Intervals
from net.imglib2.type.numeric.integer import UnsignedByteType
from java.lang import Runtime
from ij.gui import Roi


# MR1.4-3 volume
# Resolution is: 8x8x8 nm, FIBSEM
name = "MR1.4-3"

# Folders
srcDir = "/net/fibserver1/raw/" + name + "/"
tgtDir = "/net/zstore1/FIBSEM/" + name + "/registration/"
csvDir = tgtDir + "csv/" # for in-section montaging
csvDirZ = tgtDir + "csvZ/" # for cross-section alignment with SIFT+RANSAC
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
   "maxEpsilon": 25, # pixels, maximum error allowed, usual number is 25. Started out as 5 for the first ~6000 sections or so.
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

# Sorted group names, one per section
# TODO create a way to get images from an alternative folder: the repaired folder
# or to ignore images (e.g., 062018 for 0-0-0)
groupNames, tileGroups = makeMontageGroups(filepaths, to_remove, check,
                                           alternative_dir=repairedDir,
                                           ignore_images=ignore_images,
                                           writeDir=csvDir)


# Don't skip any sections
#groupNames = groupNames[2206:-167]
#tileGroups = tileGroups[2206:-167]

fixed_tile_indices = [7000] # A section in the brain, with 1x2 tiles

# Manual offset for sections with a single tile:
def sectionOffsets(index): # index is 0-based
  # Must always return a tuple with two integers
  #if index >= 10598:
  #  return (4748, 2368)
  # TODO any shifts needed? Or correct in a different way after SIFT registration.
  return (0, 0)


# DEBUG: print groups
if check:
  rows = ["section index (1-based),groupName,number of tiles"]
  for i, (groupName, tilePaths) in enumerate(izip(groupNames, tileGroups)):
    rows.append("%i,%s,%i" % (i+1, groupName, len(tilePaths)))
  with open(os.path.join(csvDir, "sections-list.csv"), 'w') as f:
    f.write("\n".join(rows))




syncPrintQ("Number of sections found valid: %i" % len(groupNames))


# Montage all sections
ensureMontages(groupNames, tileGroups, overlap, nominal_overlap, offset, paramsSIFT, paramsRANSAC, paramsTileConf, csvDir, nThreadsMontaging)

# Prepare an image volume where each section is a Cell with an ArrayImg showing a montage or a single image, and preprocessed (invert + CLAHE)
# NOTE: it's 8-bit
volumeImgMontaged = makeVolume(groupNames, tileGroups, section_width, section_height, overlap, nominal_overlap, offset, paramsSIFT, paramsRANSAC, paramsTileConf, csvDir,
                               show=True, matrices=None, section_offsets=sectionOffsets, invert=True, CLAHE_params=[200, 255, 3.0], title="Montages")


# Start section registration

# First align sections with SIFT

# Some of these aren't needed here
properties = {
 'name': "MR1.4-3",
 'img_dimensions': Intervals.dimensionsAsLongArray(volumeImgMontaged),
 'srcDir': srcDir,
 'pixelType': UnsignedByteType,
 'n_threads': 200, # use a low number when having to load images (e.g., montaging and feature extraction) and a high number when computing pointmatches.
 'invert': False, # Processing is done already
 'CLAHE_params': None, #[200, 256, 3.0], # For viewAligned. Use None to disable. Blockradius, nBins, slope.
 'use_SIFT': True,
 'SIFT_validateByFileExists': True, # Avoid loading and parsing SIFT features just to make sure they are fine.
 'RANSAC_iterations': 1000,
 'RANSAC_maxEpsilon': 25, # default is 25, for ssTEM 40nm sections cross-section alignment, but FIBSEM at 8nm sections is far thinner
 'RANSAC_minInlierRatio': 0.01,
 'preload': 64, # 64 sections, matching the export as N5 Z axis
 'handleNoPointMatchesFn': handleNoPointMatches, # Amounts to no translation, with a single PointMatch at 0,0
}

# Parameters for blockmatching
params = {
 'scale': 0.2, # 20%
 'meshResolution': 20, # 20x20 = 400 points
 'minR': 0.1, # min PMCC (Pearson product-moment correlation coefficient)
 'rod': 0.9, # max second best r / best r
 'maxCurvature': 1000.0, # default is 10
 'searchRadius': 100, # has to account for the montages shifting about ~100 pixels in any direction
 'blockRadius': 100, # small, yet enough
}

# Parameters for SIFT features, in case blockmatching fails due to large translation or image dimension mistmatch
paramsSIFT = FloatArray2DSIFT.Param()
paramsSIFT.fdSize = 8 # default is 4
paramsSIFT.fdBins = 8 # default is 8
paramsSIFT.maxOctaveSize = int(max(1024, section_width * params["scale"]))
paramsSIFT.steps = 3
paramsSIFT.minOctaveSize = int(paramsSIFT.maxOctaveSize / pow(2, paramsSIFT.steps))
paramsSIFT.initialSigma = 1.6 # default 1.6

# Parameters for computing the transformation models
paramsTileConfiguration = {
  "n_adjacent": 3, # minimum of 1; Number of adjacent sections to pair up
  "maxAllowedError": 0, # Saalfeld recommends 0
  "maxPlateauwidth": 200, # Like in TrakEM2
  "maxIterations": 1000, # Saalfeld recommends 1000
  "damp": 1.0, # Saalfeld recommends 1.0, which means no damp
  "nThreadsOptimizer": Runtime.getRuntime().availableProcessors() # as many as CPU cores
}



matricesSIFT = align(groupNames, csvDirZ, params, paramsSIFT, paramsTileConfiguration, properties,
                     loaderImp=makeSliceLoader(groupNames, volumeImgMontaged),
                     fixed_tile_indices=fixed_tile_indices)

cropInterval = FinalInterval([section_width, section_height]) # The whole 2D view
imgSIFT, impSIFT = showAlignedImg(volumeImgMontaged, cropInterval, groupNames, properties,
                                  matricesSIFT,
                                  rotate=None, # None, "right", "left", or "180"
                                  title_addendum=" SIFT+RANSAC")



# To be determined:
#impSIFT.setRoi(Roi(8, 252, 11992, 12096))


# From NC_Hypathia volume: Below: blockmatching always looks worse than 6-adjacent SIFT
# SIFT has under 6 pixel error, whereas blockmatching gets 11.2
# This is likely because section thickness is large for this volume.


"""

# Show the volume aligned by SIFT+RANSAC, inverted and processed with CLAHE:
# NOTE it's 8-bit !
#volumeImgAlignedSIFT = makeVolume(groupNames, tileGroups, section_width, section_height, overlap, nominal_overlap, offset, paramsSIFT, paramsRANSAC, paramsTileConf, csvDir,
#                                  show=True, matrices=matricesSIFT,
#                                  section_offsets=sectionOffsets,
#                                  invert=True, CLAHE_params=[100, 255, 3.0], title="SIFT+RANSAC",
#                                  cache_size=properties["n_threads"] + paramsTileConfiguration["n_adjacent"] + 1) # Cache of SoftReference entries anyway


# Further refine the alignment by aligning the SIFT+RANSAC-aligned volume using blockmatching:
properties["use_SIFT"] = False # Will still fall back to SIFT if blockmatching fails
properties["n_threads"] = 64 # for scale=0.2 use 128
paramsTileConfiguration["n_adjacent"] = 3
matricesBM = align(groupNames, csvDirBM, params, paramsSIFT, paramsTileConfiguration, properties,
                   loaderImp=makeSliceLoader(groupNames, imgSIFT),
                   fixed_tile_indices=fixed_tile_indices)


# Show the re-aligned volume
#volumeImgAlignedBM = makeVolume(groupNames, tileGroups, section_width, section_height, overlap, nominal_overlap, offset, paramsSIFT, paramsRANSAC, paramsTileConf, csvDir,
#                                show=True,
#                                section_offsets=sectionOffsets,
#                                matrices=fuseMatrices(matricesSIFT, matricesBM),
#                                invert=True, CLAHE_params=[100, 255, 3.0], title="SIFT+RANSAC+BlockMatching")


# Show the volume using ImgLib2 interpretation of matrices, with subpixel alignment,
# ready for exporting to N5 (has preloader threads switched on)
cropInterval = FinalInterval([section_width, section_height]) # The whole 2D view
img, imp = showAlignedImg(imgSIFT, cropInterval, groupNames, properties,
                          matricesBM,
                          rotate="180",
                          title_addendum=" BM")


# Also directly from the montages to avoid interpolation of an interpolated image
img, imp = showAlignedImg(volumeImgMontaged, cropInterval, groupNames, properties,
                          fuseTranslationMatrices(matricesSIFT, matricesBM),
                          rotate="180",
                          title_addendum=" single interpolation")
imp.setTitle(imp.getTitle() + )


# Roi for cropping when exporting
# to be determined # imp.setRoi(Roi(432, 480, 24672, 23392))

"""
