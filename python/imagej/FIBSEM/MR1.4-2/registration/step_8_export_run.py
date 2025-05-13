# Step 8: export the aligned volume in N5 format at full resolution

import sys, os
# Add current directory to path
sys.path.append(os.path.dirname(sys.argv[0]))

# Import parameters
from step_1_montage_parameters import libDir, \
             name, srcDir, tgtDir, montageDir, repairedDir, \
             section_width, section_height, \
             first_section, last_section, replace_sections, \
             to_remove, ignore_images, replace_images, \
             params_pixels

from step_3_SIFT_registration_parameters import SIFTdir

from step_5_blockmatching_parameters import BMdir

from step_7_export_parameters import n5Dir, crop_roi, rotate, paramsN5

# Import registration library functions
sys.path.append(libDir)
from lib.serial2Dregistration import loadAlignedImage
from lib.io import writeN5


# Correct for un-rezeroed negative shifts with a positive translation
section_offsets = lambda i: (563, 770) # same for all sections

# Enlarge canvas
section_width += 1000
section_height += 800

# Translate: bring images back into the frame after registration
translation = (2000, 2000)

# ROI: in the coordinate space post section_offsets and translation
crop_roi = [300, 576, 13620, 11664]

# Load the montages in full resolution, unaligned, and cropped as per crop_roi
img, imp = loadAlignedImage(name, srcDir, repairedDir, montageDir,
        SIFTdir, BMdir,
        to_remove, ignore_images, replace_images,
        first_section, last_section, replace_sections,
        section_width, section_height, crop_roi, params_pixels,
        rotate=rotate, preload=paramsN5["block_size"][2],
        section_offsets=section_offsets,
        translation=translation)

#imp.show()

# Write N5 volume
writeN5(img, n5Dir, name,
        paramsN5["block_size"],
        gzip_compression_level=paramsN5["gzip_compression"],
        n_threads=paramsN5["n_threads"])

