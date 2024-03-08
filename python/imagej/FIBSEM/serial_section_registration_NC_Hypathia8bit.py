from __future__ import with_statement
import sys, os
sys.path.append("/lmb/home/acardona/lab/scripts/python/imagej/IsoView-GCaMP/")
from lib.registration import saveMatrices, loadMatrices
from lib.io import loadFilePaths
from lib.util import syncPrintQ
from lib.serial2Dregistration import align
from montage2d import ensureMontages2x2, makeMontageGroups, makeVolume, makeSliceLoader, showAlignedImg

from itertools import izip



# Folders
srcDir = "/net/fibserver1/raw/NC_Hypathia/Y2023/"
tgtDir = "/net/zstore1/FIBSEM/NC_Hypathia/Y2023/registration/"
csvDir = "/net/zstore1/FIBSEM/NC_Hypathia/Y2023/registration/csv/" # for in-section montaging
csvDirZ = "/net/zstore1/FIBSEM/NC_Hypathia/Y2023/registration/csvZ/" # for cross-section alignment with SIFT+RANSAC
csvDirBM = "/net/zstore1/FIBSEM/NC_Hypathia/Y2023/registration/csvBM/" # for cross-section alignment with BlockMatching

# Ensure tgtDir and csvDir exist
for csvD in [csvDir, csvDirZ, csvDirBM]:
  if not os.path.exists(csvD):
    os.makedirs(csvD) # recursive directory creation


# Image tile overlap parameters
offset = 80 # pixels The left margin of each image is severely elastically deformed. Does it matter for SIFT?
overlap = 646 # pixels
nominal_overlap = 666 # 8 microns at 12 nm/px = 8000 px

# Intra-section montage: expecting 2x2 with each tile being 6375x6583

# Working canvas
section_width = 14500 # pixels, after section-wise montaging
section_height = 14500

# CHECK whether some sections have problems
check = True



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

# Find all .dat files, as a sorted list
filepaths = loadFilePaths(srcDir, ".dat", csvDir, "imagefilepaths")


# Sections known to have problems
to_remove = set([])


groupNames, tileGroups = makeMontageGroups(filepaths, to_remove)


# DEBUG: print groups
rows = ["section index (1-based),groupName,number of tiles"]
for i, (groupName, tilePaths) in enumerate(izip(groupNames, tileGroups)):
  rows.append("%i,%s,%i" % (i+1, groupName, len(tilePaths)))
with open(os.path.join(csvDir, "sections-list.csv"), 'w') as f:
  f.write("\n".join(rows))


syncPrintQ("Number of sections found valid: %i" % len(groupNames))

# Montage all sections
ensureMontages2x2(groupNames, tileGroups, overlap, offset, paramsSIFT, paramsRANSAC, csvDir)

# Prepare an image volume where each section is a Cell with an ArrayImg showing a montage or a single image, and preprocessed (invert + CLAHE)
# NOTE: it's 8-bit
volumeImg = makeVolume(groupNames, tileGroups, section_width, section_height,
                   show=False, matrices=None, invert=True, CLAHE_params=[200, 255, 3.0], title="Montages")


# Start section registration

# First align sections with SIFT

# Some of these aren't needed here
properties = {
 'name': "NC_Hypathia",
 'img_dimensions': Intervals.dimensionsAsLongArray(volumeImg),
 'srcDir': srcDir,
 'pixelType': UnsignedByteType,
 'n_threads': 200, # use a low number when having to load images (e.g., montaging and feature extraction) and a high number when computing pointmatches.
 'invert': False, # Processing is done already
 'CLAHE_params': None, #[200, 256, 3.0], # For viewAligned. Use None to disable. Blockradius, nBins, slope.
 'use_SIFT': True,  # no need, falls back onto SIFT when needed. In this case, when transitioning from montages to single image sections.
 'SIFT_validateByFileExists': True, # Avoid loading and parsing SIFT features just to make sure they are fine.
 'RANSAC_iterations': 1000,
 'RANSAC_maxEpsilon': 10, # default is 25, for ssTEM 40nm sections cross-section alignment, but FIBSEM at 8nm sections is far thinner
 'RANSAC_minInlierRatio': 0.01,
 'preload': 64 # 64 sections, matching the export as N5 Z axis
}

# Parameters for blockmatching
params = {
 'scale': 0.1, # 10%
 'meshResolution': 20,
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
paramsSIFT.maxOctaveSize = int(max(1024, dimensions[0] * params["scale"]))
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
}

matricesSIFT = align(groupNames, csvDirZ, params, paramsSIFT, paramsTileConfiguration, properties,
                     loaderImp=makeSliceLoader(groupNames, volumeImg))

# Show the volume aligned by SIFT+RANSAC, inverted and processed with CLAHE:
# NOTE it's 8-bit !
volumeImgAlignedSIFT = makeVolume(groupNames, tileGroups, section_width, section_height,
                                  show=True, matrices=matricesSIFT,
                                  invert=True, CLAHE_params=[100, 255, 3.0], title="SIFT+RANSAC")

# Further refine the alignment by aligning the SIFT+RANSAC-aligned volume using blockmatching:
properties["use_SIFT"] = False
properties["n_threads"] = 32
matricesBM = align(groupNames, csvDirBM, params, paramsSIFT, paramsTileConfiguration, properties,
                   loaderImp=makeSliceLoader(groupNames, volumeImgAlignedSIFT))


# Show the re-aligned volume
volumeImgAlignedBM = makeVolume(groupNames, tileGroups, show=True,
                                matrices=fuseMatrices(matricesSIFT, matricesBM),
                                invert=True, CLAHE_params=[100, 255, 3.0], title="SIFT+RANSAC+BlockMatching")


# Show the volume using ImgLib2 interpretation of matrices, with subpixel alignment,
# ready for exporting to N5 (has preloader threads switched on)
img, imp = showAlignedImg(volumeImgAlignedBM)

# Roi for cropping when exporting
imp.setRoi(Roi(432, 480, 24672, 23392))

