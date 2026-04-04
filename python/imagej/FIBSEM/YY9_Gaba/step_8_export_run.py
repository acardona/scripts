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
             params_pixels, paramsFilterFeatures

from step_3_SIFT_registration_parameters import SIFTdir

from step_5_blockmatching_parameters import BMdir

from step_7_export_parameters import n5Dir, crop_roi, rotate, paramsN5

# Import registration library functions
sys.path.append(libDir)
from lib.serial2Dregistration import loadAlignedImage
from lib.io import writeN5


# SPECIAL for FIBSEM YY9_Gaba: make the canvas wider for the extra crop roi,
# see step 7 export parameters
section_width += int((180 + 350) / params_pixels['interim_scale'] + 0.5)
# Can't be done in earlier steps without regenerating the scaled montages,
# but here the full-resolution original images are used.



# Load the montages in full resolution, unaligned, and cropped as per crop_roi
imgShiftBM, impShiftBM = loadAlignedImage(name, srcDir, repairedDir, montageDir,
        SIFTdir, BMdir,
        to_remove, ignore_images, replace_images,
        first_section, last_section, replace_sections,
        section_width, section_height, crop_roi, params_pixels,
        rotate=rotate, preload=paramsN5["block_size"][2])
        

# Inspect the image and the crop_roi
#impShiftBM.setSlice(4000)
#impShiftBM.show()
#from ij.gui import Roi
#impShiftBM.setRoi(Roi(*crop_roi))



# Every few minutes, flush the caches completely.
from lib.util import newScheduledExecutor, RunTask, printException, syncPrintQ
def emptyCaches(cachedCellImgs):
  for i, img in enumerate(cachedCellImgs):
    try:
      syncPrintQ("Emptying cache of image %i :: %s" % (i, str(img)))
      if rotate:
        img.getSource().getSource().getCache().invalidateAll()
      else: img.getCache().invalidateAll()
    except:
      syncPrintQ("Failed to empty cache for image %i :: %s" % (i, str(img)))
      printException()

exe = newScheduledExecutor()
exe.scheduleAtFixedRate(RunTask(emptyCaches, [imgShiftBM]), 0, 360000) # 7 minutes = 7 * 60 s / min * 1000 ms / s 


# Tell me about the image
syncPrintQ(impShiftBM)
syncPrintQ(imgShiftBM)
syncPrintQ("crop_roi: " + str(crop_roi))

#impShiftBM.show()

# Write N5 volume
writeN5(imgShiftBM, n5Dir, name,
        paramsN5["block_size"],
        gzip_compression_level=paramsN5["gzip_compression"],
        n_threads=paramsN5["n_threads"])

exe.shutdown()


