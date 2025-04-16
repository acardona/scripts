# Step 3: SIFT registration parameters

import sys, os
from mpicbg.imagefeatures import FloatArray2DSIFT
from ij.gui import Roi
# Add current directory to path
sys.path.append(os.path.dirname(sys.argv[0]))
# Import parameters used for montaging
from step_1_montage_parameters import libDir, name, tgtDir, montageDir, section_width, section_height, params_pixels
# Import registration library functions
sys.path.append(libDir)
from lib.serial2Dregistration import handleNoPointMatches, makeFilterFeaturesFn
from lib.util import numCPUs
from java.lang import Double


# Folder for storing SIFT features per montage and pointmatches across montages, and the matrices.csv file
SIFTdir = tgtDir + "SIFT-csv/"


# EDIT below until the end if needed

# Parameters to filter out features outside the tissue using a LabKit model
# Can be None
model_path = None # os.path.join("/net/zstore1/FIBSEM/MR1.4-3/registration/MR1.4-3_section1+6000_0.025.labkit.classifier") # from LabKit
model_width = None # 400 # target width for resizing so as to match the dimensions of the image used when training the model.


# Parameters for extracting SIFT features
properties = {
 'name': name,
 'scale': 0.5, # Compounds with montaging interim_scale
 'n_threads': numCPUs(),
 'roi': None, #[3600, # x      -  [x, y, width, height] or None. To e.g. extract SIFT features from center part only.
         #1800, # y     NOTE: in full image resolution coordinates.
         #7200, # width
         #8200], # height
 'RANSAC_iterations': 1000,
 'RANSAC_maxEpsilon': 25, # default is 25, for ssTEM 40nm sections cross-section alignment, but FIBSEM at 8nm sections is far thinner
 'RANSAC_minInlierRatio': 0.01,
 'handleNoPointMatchesFn': handleNoPointMatches, # Amounts to no translation, with a single PointMatch at 0,0
 'filterFeaturesFn': None, # makeFilterFeaturesFn(model_path, model_width), # Filter out features not in the tissue but in the resin, to ignore the resin which has streaks and curtains
}


# Parameters for SIFT features
paramsSIFT = FloatArray2DSIFT.Param()
paramsSIFT.fdSize = 8 # default is 4
paramsSIFT.fdBins = 8 # default is 8
paramsSIFT.maxOctaveSize = 500 # effective scale: section_width=16000, interim_scale=0.25 (4000), so 0.25/8 !
paramsSIFT.steps = 3
paramsSIFT.minOctaveSize = 250
paramsSIFT.initialSigma = 1.6 # default 1.6

# Parameters for pointmatches
paramsPMs = {
  'scale': properties.get('scale', 0.5), # compounds with montage interim_scale
  'rod': 0.9, # ratio of best vs second best
  'max_sd': 1.5, # maximal difference in size (ratio max/min)
  'max_id': Double.MAX_VALUE, # max allowed distance between features in full image space
}

# Parameters for computing the SIFT-based transformation models
paramsTileConfiguration = {
  "n_adjacent": 3, # minimum of 1; Number of adjacent sections to pair up
  "maxAllowedError": 0, # Saalfeld recommends 0
  "maxPlateauwidth": 200, # Like in TrakEM2
  "maxIterations": 20000, # Optimizer iterations for each chunk of chunk_size sections
                         # Using a low number like 1000 to start with. If one chunk fails
                         # to align well, re-run that chunk with more iterations (like 20x, 20000).
  "damp": 1.0, # Saalfeld recommends 1.0, which means no damp
  "nThreadsOptimizer": numCPUs(), # as many as CPU cores
  "chunk_size": 400, # Will align in 50% overlapping chunks for best use of the optimizer
  "chunk_maxIterations": 100000, # Iterations for the cross-chunk alignment
  "fixed_tile_index": 2050, # None implies use the middle tile. Otherwise provide an index (0-based)
}

