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
from lib.ui import wrap8bit

from net.imglib2.view import Views
from net.imglib2 import FinalInterval

K = params_pixels["interim_scale"]

# Turns out Clayton's registration of the first thousands of sections transposed the images when exporting them.
# Also, sections starting at 1216 have a big displacement towards negative Y, which means part of the images are outside the canvas.
def sectionOffsets(index):
  return (int(252 / K + 0.5), int(468 / K + 0.5))

# Also make the canvas wider
section_width += 1700
section_height += 2000
crop_roi[2] = section_width
crop_roi[3] = section_height

# Load the montages in full resolution, unaligned, and cropped as per crop_roi
img, imp = loadAlignedImage(name, srcDir, repairedDir, montageDir,
        SIFTdir, BMdir,
        to_remove, ignore_images, replace_images,
        first_section, last_section, replace_sections,
        section_width, section_height, crop_roi, params_pixels,
        rotate=rotate,
        section_offsets=sectionOffsets,
        preload=paramsN5["block_size"][2])

# Before transposing
#imp.show()

# Correct for transposition of axes in Clayton's volume
imgR = Views.rotate(Views.rotate(Views.permute(img, 0, 1), 0, 1), 0, 1) # rotation around origin of coordinates, so image will be defined in the negative coordinates
imgZ = Views.extendZero(Views.zeroMin(imgR)) # zeroMin to correct for the negative coordinates
# Translation: -846.83, 758.06
imgTL = Views.translate(imgZ, [-847, 758, 0])
interval = FinalInterval([imgR.dimension(0), imgR.dimension(1), imgR.dimension(2)])
imgI = Views.zeroMin(Views.interval(imgTL, interval))
img = imgI

# Make a new ImagePlus to show it
#imp = wrap8bit(imgI, title="transposed")

#imp.show()


# Write N5 volume
writeN5(img, n5Dir, name,
        paramsN5["block_size"],
        gzip_compression_level=paramsN5["gzip_compression"],
        n_threads=paramsN5["n_threads"])

