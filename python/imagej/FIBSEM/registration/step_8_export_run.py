# Step 8: export the volume in N5 format at full resolution

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

from step_7_export_parameters import n5Dir, crop_roi, paramsN5

# Import registration library functions
sys.path.append(libDir)
from lib.montage2d import runMontaging
from lib.serial2Dregistration import runSIFTAlignment
from lib.serial2Dregistration import runBlockMatchingAlignment
from lib.io import writeN5

# ImgLib2 functions
from net.imglib2.view import Views


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
imgSIFT, impSIFT, matricesSIFT = runSIFTAlignment(
             volumeImgMontaged, groupNames, SIFTdir,
             properties, paramsSIFT, paramsPMs, paramsTileConfiguration,
             params_pixels, show=False)

# Open the blockmatching finely aligned using chunks
imgBM, impBM, matricesBM = runBlockMatchingAlignment(
             imgSIFT, matricesSIFT, volumeImgMontaged,
             groupNames, BMdir, propertiesBM,
             paramsSIFT, paramsBlockMatching, paramsTileConfigurationBM,
             params_pixels, show=False)

# The ImgLib2 image to export in N5 format to n5Dir
img = imgBM

# Crop
if crop_roi:
  print "Using ROI nwith bounds:", crop_roi
  x, y, width, height = crop_roi
  img = Views.zeroMin(Views.interval(imgBM, [x, y, 0],
                                            [x + width -1, y + height -1, img.dimension(2) -1]))

# Write N5 volume
writeN5(img, n5Dir, name,
        paramsN5["block_size",
        gzip_compression_level=paramsN5["gzip_compression"],
        n_threads=params["n_threads"])

