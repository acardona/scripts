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
from lib.ui import wrap

from net.imglib2.view import Views


# Load the montages in full resolution, unaligned, and cropped as per crop_roi
imgShiftBM, impShiftBM = loadAlignedImage(name, srcDir, repairedDir, montageDir,
        SIFTdir, BMdir,
        to_remove, ignore_images, replace_images,
        first_section, last_section, replace_sections,
        section_width, section_height, crop_roi, params_pixels,
        rotate=rotate, preload=paramsN5["block_size"][2])

print "Loaded shift+BM"

# Load the same but without BM
imgShift, impShift = loadAlignedImage(name, srcDir, repairedDir, montageDir,
        SIFTdir, "/none/", # purposefully giving a folder that doesn't exist for the BMdir
        to_remove, ignore_images, replace_images,
        first_section, last_section, replace_sections,
        section_width, section_height, crop_roi, params_pixels,
        rotate=rotate, preload=paramsN5["block_size"][2])

print "Loaded shifts only"

# Splice 0-438 from shifts volume with 439-end from shift+BM volume
img = Views.concatenate(2, # on the Z axis
                        Views.interval(imgShift, [0, 0, 0], [imgShift.dimension(0) -1, imgShift.dimension(1) -1, 438]),
                        Views.interval(imgShiftBM, [0, 0, 439], [imgShiftBM.dimension(0) -1, imgShiftBM.dimension(1) -1, imgShiftBM.dimension(2) -1]))

print "Spliced."

# View the spliced volume
#wrap(img, title="spliced").show()

impShift.setTitle("shifts")
#impShift.show()
impShiftBM.setTitle("shifts+BM")
#impShiftBM.show()


# To export when the image is showing, comment out the above and uncomment this below:
#from ij import IJ
#img = IJ.getImage().getStack().getSource().getSource().getSource() # IntervalView (4 dim), MixedTransformView (4 dim), StackView (3 dim)
#print img


# Every 10 minutes, flush the caches completely.
from lib.util import newScheduledExecutor, RunTask, printException, syncPrintQ
def emptyCaches(cachedCellImgs):
  for i, img in enumerate(cachedCellImgs):
    try:
      syncPrintQ("Emptying cache of image %i :: %s" % (i, str(img)))
      img.getCache().invalidateAll()
    except:
      syncPrintQ("Failed to empty cache for image %i :: %s" % (i, str(img)))
      printException()

exe = newScheduledExecutor()
exe.scheduleAtFixedRate(RunTask(emptyCaches, [imgShift,imgShiftBM]), 600000, 600000) # 10 minutes = 10 * 60 s / min * 1000 ms / s 

# Write N5 volume
writeN5(img, n5Dir, name,
        paramsN5["block_size"],
        gzip_compression_level=paramsN5["gzip_compression"],
        n_threads=paramsN5["n_threads"])

exe.shutdown()

