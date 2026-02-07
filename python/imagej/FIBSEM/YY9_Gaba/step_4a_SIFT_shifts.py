# Step 4a: run the SIFT-based detection of large shifts (translations) when imaging,
#          most often caused by redefining the imaging ROI.

import sys, os
# Add current directory to path
sys.path.append(os.path.dirname(sys.argv[0]))

# Import parameters
from step_1_montage_parameters import libDir, \
             name, srcDir, tgtDir, montageDir, repairedDir, \
             offset, overlap, nominal_overlap, \
             section_width, section_height, \
             first_section, last_section, replace_sections, \
             params_pixels, paramsSIFT, paramsRANSAC, paramsTileConf, \
             paramsFilterFeatures, \
             to_remove, ignore_images, replace_images

from step_3_SIFT_registration_parameters import SIFTdir, properties, \
             paramsSIFT, paramsPMs, paramsTileConfiguration

# Import registration library functions
sys.path.append(libDir)
from lib.montage2d import runMontaging
from lib.serial2Dregistration import runShiftDetection


# Open the stack of scaled montages
volumeImgMontaged, groupNames, tileGroups = runMontaging(
             name, srcDir, tgtDir, montageDir, repairedDir,
             offset, overlap, nominal_overlap,
             section_width, section_height,
             first_section, last_section, replace_sections,
             params_pixels, paramsSIFT, paramsRANSAC, paramsTileConf,
             to_remove, ignore_images, replace_images,
             paramsFilterFeatures=paramsFilterFeatures,
             showTable=False, show=True)

# Run pairwise SIFT feature-based computation of translation models
# to detect large translations in X and Y,
# and open the shifted montages: like a pairwise section registration without an optimizer
imgShift, impShift, matricesShifts, shifts = runShiftDetection(
             volumeImgMontaged, groupNames, SIFTdir,
             properties, paramsSIFT, paramsPMs, params_pixels, show=True)
