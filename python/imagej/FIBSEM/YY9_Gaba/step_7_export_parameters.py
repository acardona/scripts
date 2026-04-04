# Step 7: parameters for exporting the volume into N5 at full resolution

import sys, os
# Add current directory to path
sys.path.append(os.path.dirname(sys.argv[0]))
# Import parameters used for montaging
from step_1_montage_parameters import libDir, name, tgtDir, section_width, section_height, params_pixels
# Import registration library functions
sys.path.append(libDir)
from lib.util import numCPUs



# Directory for exporting the N5 volume
n5Dir = tgtDir + "n5/"

# Region of interest in 2D for exporting
# ROI on the scaled montages volume
roi = [87, 105, 1913 + 180 + 350, 1653]  #  180 + 350 of extra width in the scaled montages
# scaled up to original dimensions
crop_roi = map(lambda v : int(v / params_pixels['interim_scale'] + 0.5), roi)

# Rotate the view: None, "right", "left", or "180"
rotate = "right"

# Parameters on what to export
paramsN5 = {
  "block_size": [256,256,64], # e.g., [128,128,128]
  "gzip_compression": 4, # between 0 (no compression) and 9
  "n_threads": numCPUs() - 2, # for writing
}
