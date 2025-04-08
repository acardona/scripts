# Step 5: setup parameters for blockmatching fine registration after SIFT registration

import sys, os
from ij.gui import Roi
# Add current directory to path
sys.path.append(os.path.dirname(sys.argv[0]))
# Import parameters used for montaging
from step_1_montage_parameters import libDir, name, tgtDir, section_width, section_height
# Import parameters used towards filtering out pointmatches
from step_3_SIFT_registration_parameters import model_path, model_width
# Import registration library functions
sys.path.append(libDir)
from lib.serial2Dregistration import handleNoPointMatches, makeFilterFeaturesFn
from lib.util import numCPUs


# Folder for storing blockmatching features per montage and pointmatches across montages, and the matrices.csv files
BMdir = tgtDir + "BM-csv/"


propertiesBM = {
 'name': name,
 'scale': 0.5, # Compounds with montaging interim_scale
 'n_threads': numCPUs(),
 'roi': [2000,  # To extract SIFT features from e.g., center part only, reducing ops by 4x
         2400, # [x, y, width, height] or None.
         8000,
         10000],
 'handleNoPointMatchesFn': handleNoPointMatches, # Amounts to no translation, with a single PointMatch at 0,0
 'filterFeaturesFn': None, #makeFilterFeaturesFn(model_path, model_width), # Filter out features not in the tissue but in the resin, to ignore the resin which has streaks and curtains
}

# Parameters for blockmatching
paramsBlockMatching = {
 'scale': propertiesBM['scale'], # Compounds with montaging interim_scale, so 0.5 would mean half of that
 'meshResolution': 20, # 10x10 = 100 points
 'minR': 0.1, # min PMCC (Pearson product-moment correlation coefficient)
 'rod': 0.9, # max second best r / best r
 'maxCurvature': 1000.0, # default is 10
 'searchRadius': 100, # Maximum expected displacement between slices after SIFT-based registration.
                      # Make it large enough, 300 is a good first searcRadius value. 50 to a 100 for a fast run.
 'blockRadius': 200, # small, yet enough: size of the window to use for comparing across images.
}

# Parameters for pointmatches
paramsPMs = {
  'scale': propertiesBM['scale'], # compounds with montage interim_scale
  'rod': 0.9, # ratio of best vs second best
}

# Parameters for computing the transformation models
paramsTileConfigurationBM = {
  "n_adjacent": 3, # minimum of 1; Number of adjacent sections to pair up
  "maxAllowedError": 0, # Saalfeld recommends 0
  "maxPlateauwidth": 200, # Like in TrakEM2
  "maxIterations": 5000, # Optimizer iterations for each chunk of chunk_size sections
  "damp": 1.0, # Saalfeld recommends 1.0, which means no damp
  "nThreadsOptimizer": numCPUs(), # as many as CPU cores
  "chunk_size": 400, # Will align in 50% overlapping chunks for best use of the optimizer
  "chunk_maxIterations": 40000, # Iterations for the cross-chunk alignment
  "fixed_tile_index": 2050, # None implies use the middle tile. Otherwise provide an index (0-based)
}