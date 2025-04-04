# Step 4: run the SIFT-based registration in chunks

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

# Import registration library functions
sys.path.append(libDir)
from lib.montage2d import runMontaging
from lib.serial2Dregistration import runSIFTAlignment


# Open the stack of scaled montages
volumeImgMontaged, groupNames, tileGroups = runMontaging(
             name, srcDir, tgtDir, montageDir, repairedDir,
             offset, overlap, nominal_overlap,
             section_width, section_height,
             first_section, last_section, replace_sections,
             params_pixels, paramsSIFT, paramsRANSAC, paramsTileConf,
             to_remove, ignore_images, replace_images,
             showTable=False, show=False)

# Align the stack with SIFT features using chunks and open an aligned view
imgSIFT, impSIFT, matrices = runSIFTAlignment(
             volumeImgMontaged, groupNames, SIFTdir,
             properties, paramsSIFT, paramsPMs, paramsTileConfiguration, params_pixels)
