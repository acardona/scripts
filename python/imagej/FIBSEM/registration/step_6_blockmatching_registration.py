# Step 6: run the blockmatching-based registration in chunks

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
             to_remove, ignore_images, replace_images

from step_3_SIFT_registration_parameters import SIFTdir, properties, \
             paramsSIFT, paramsPMs, paramsTileConfiguration
             
from step_5_blockmatching_parameters import BMdir, propertiesBM, paramsBlockMatching, paramsTileConfigurationBM

# Import registration library functions
sys.path.append(libDir)
from lib.montage2d import runMontaging
from lib.serial2Dregistration import runSIFTAlignment
from lib.serial2Dregistration import runBlockMatchingAlignment


# Open the stack of scaled montages
volumeImgMontaged, groupNames, tileGroups = runMontaging(
             name, srcDir, tgtDir, montageDir, repairedDir,
             offset, overlap, nominal_overlap,
             section_width, section_height,
             first_section, last_section, replace_sections,
             params_pixels, paramsSIFT, paramsRANSAC, paramsTileConf,
             to_remove, ignore_images, replace_images,
             showTable=False, show=False)

# Open the stack pre-aligned with SIFT features using chunks
#imgSIFT, impSIFT, matricesSIFT = runSIFTAlignment(
#             volumeImgMontaged, groupNames, SIFTdir,
#             properties, paramsSIFT, paramsPMs, paramsTileConfiguration,
#             params_pixels, show=False)

# Open the stack of shifted montages, with shifts computed with a TranslationModel2D using SIFT features and pointmatches
imgShift, impShift, matricesShifts, shifts = runShiftDetection(
             volumeImgMontaged, groupNames, SIFTdir,
             properties, paramsSIFT, paramsPMs, params_pixels, show=False)

# Open the blockmatching finely aligned using chunks
imgBM, impBM, matricesBM = runBlockMatchingAlignment(
             imgShift, matricesShifts, volumeImgMontaged,
             groupNames, BMdir, propertiesBM,
             paramsSIFT, paramsBlockMatching, paramsTileConfigurationBM,
             params_pixels)