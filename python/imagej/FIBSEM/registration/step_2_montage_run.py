# Step 2: run the montage and export scaled-down images of each montaged section

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
# Import registration library functions
sys.path.append(libDir)
from lib.montage2d import runMontaging


# Run the montage of each section
volumeImgMontaged, groupNames, tileGroups = runMontaging(
             name, srcDir, tgtDir, montageDir, repairedDir,
             offset, overlap, nominal_overlap,
             section_width, section_height,
             first_section, last_section, replace_sections,
             params_pixels, paramsSIFT, paramsRANSAC, paramsTileConf,
             to_remove, ignore_images, replace_images)
