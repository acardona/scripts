# Step 1: montage parameters

from mpicbg.imagefeatures import FloatArray2DSIFT
from ij.gui import Roi

# REGISTRATION LIBRARY
libDir = "/lmb/home/acardona/lab/scripts/python/imagej/IsoView-GCaMP/"

# VOLUME
name = "MR1.3-2" # Name of the folder containing the .dat files, e.g., "MR1.4-3"
sourceServer = "/net/fibserver1/raw/"
targetServer = "/net/zstore1/FIBSEM/"


# Folders
srcDir = sourceServer + name + "/"
tgtDir = targetServer + name + "/registration/"
montageDir = tgtDir + "montage-csv/" # for in-section montaging
repairedDir = targetServer + name + "/repaired/" # Folder with repaired images, if any

# Image tile overlap parameters
offset  =  80 # pixels The left margin of each image is severely elastically deformed.
overlap = 990 # pixels
nominal_overlap = 1000 # 8 microns at 8 nm/px = 1000 px

# Working canvas
section_width  = 16000  # should have used 14400    # pixels, after section-wise montaging
section_height = 16000  # should have used 12800   # So a canvas of 256,000,000 pixels: 256 MB

# Skip sections. Define a range to work with.
first_section = 0  # 0-based
last_section = -1 # last 

# Replace sections: (0-based, not 1-based !)
# NOTE indices are relative to the first_section as specified above
# Add entries like: 1718: 1719,  indicating that section 1718 is to be replaced by section at 1719, effectively duplicating the latter
# This is desirable to keep the true Euclidean distances and dimensions while overriding a faulty section with e.g, truncated images.
replace_sections = {

}

# Image contrast parameters
# The roiFn is for using only e.g., the central part of the canvas to compute the display range.
# The contrast is for limiting the min and max to histogram bins that reach that many pixel counts,
# starting from each end respectively.
params_pixels = {
  "invert": True,
  "CLAHE_params": [200, 255, 2.0], # blockRadius, n_bins, and slope in stdDevs
  "as8bit": True,
  "contrast": (500, 1000), # thresholds in pixel counts per histogram bin
  "roiFn": lambda sp: Roi(sp.width / 6, sp.height / 6, 2 * sp.width / 3, 2 * sp.height / 3), # middle 2/3rds to discard edges
  "interim_scale": 0.25, # for saving montaged snapshops to disk to be used for evaluation and serial alignment
  "single_tile_position": ( int((16000 - 13750) / 2 + 0.5), int((16000 - 6750) / 2 + 0.5) ), # FIX issue with resizing canvas later since single-tile sections were rendered as centered in the montage snapshots.
}

# Parameters for SIFT features
paramsSIFT = FloatArray2DSIFT.Param()
paramsSIFT.steps = 1
paramsSIFT.minOctaveSize = 0 # will be updated in a clone
paramsSIFT.maxOctaveSize = 0 # will be updated in a clone
paramsSIFT.initialSigma = 1.6 # default 1.6
paramsSIFT.fdSize = 8 # default is 4
paramsSIFT.fdBins = 8 # default is 8

paramsRANSAC = {
  "iterations": 1000,
  "maxEpsilon": 10, # pixels, maximum error allowed, usual number is 25.
  "minInlierRatio": 0.01 # 1%
}

# For intra-section montages:
paramsTileConf = {
  "maxAllowedError": 0, # Saalfeld recommends 0
  "maxPlateauwidth": 200, # Like in TrakEM2
  "maxIterations": 1000, # Saalfeld recommends at least 1000
  "damp": 1.0, # Saalfeld recommends 1.0, which means no damp
  "nThreadsOptimizer": 10 # for the TileUtil.optimizeConcurrently for each montage.
                          # Consider that (numCPUs / (nThreadsOptimizer/2)) sections will be montaged concurrently.
}

# Sections known to have problems (found via check = True above)
# Add entries like this, with a comment for the record":
# "Merlin-WEMS_24-02-27_170732_" # added 0-0-0 tile to ignore: truncated, no pixels, only header
to_remove = set([
  
])

# Add entries like this, with the file name of individual image tiles and a comment:
# "Merlin-WEMS_24-02-27_170732_0-0-0.dat", # only header, whole image truncated
ignore_images = set([
"Merlin-WEMS_24-07-03_192127_0-1-0.dat", # lower tile from many consecutive sections around the brain commissure
"Merlin-WEMS_24-07-03_192238_0-1-0.dat",
"Merlin-WEMS_24-07-03_192348_0-1-0.dat",
"Merlin-WEMS_24-07-03_192459_0-1-0.dat",
"Merlin-WEMS_24-07-03_192608_0-1-0.dat",
"Merlin-WEMS_24-07-03_192719_0-1-0.dat",
"Merlin-WEMS_24-07-03_192829_0-1-0.dat",
"Merlin-WEMS_24-07-03_192940_0-1-0.dat",
"Merlin-WEMS_24-07-03_193054_0-1-0.dat",
"Merlin-WEMS_24-07-03_193208_0-1-0.dat",
"Merlin-WEMS_24-07-03_193321_0-1-0.dat",
"Merlin-WEMS_24-07-03_193431_0-1-0.dat",
"Merlin-WEMS_24-07-03_193543_0-1-0.dat",
"Merlin-WEMS_24-07-03_193655_0-1-0.dat",
"Merlin-WEMS_24-07-03_193807_0-1-0.dat",
"Merlin-WEMS_24-07-03_193919_0-1-0.dat",
"Merlin-WEMS_24-07-03_194030_0-1-0.dat",
"Merlin-WEMS_24-07-03_194141_0-1-0.dat",
"Merlin-WEMS_24-07-03_194252_0-1-0.dat",
"Merlin-WEMS_24-07-03_194403_0-1-0.dat",
"Merlin-WEMS_24-07-03_194514_0-1-0.dat",
"Merlin-WEMS_24-07-03_194625_0-1-0.dat",
"Merlin-WEMS_24-07-03_194736_0-1-0.dat",
"Merlin-WEMS_24-07-03_194846_0-1-0.dat",
"Merlin-WEMS_24-07-03_194958_0-1-0.dat",
"Merlin-WEMS_24-07-03_195111_0-1-0.dat",
"Merlin-WEMS_24-07-03_195222_0-1-0.dat",
"Merlin-WEMS_24-07-03_195333_0-1-0.dat",
"Merlin-WEMS_24-07-03_195444_0-1-0.dat",
"Merlin-WEMS_24-07-03_195555_0-1-0.dat",
"Merlin-WEMS_24-07-03_195706_0-1-0.dat",
"Merlin-WEMS_24-07-03_195818_0-1-0.dat",
"Merlin-WEMS_24-07-03_195930_0-1-0.dat",
"Merlin-WEMS_24-07-03_200041_0-1-0.dat",
"Merlin-WEMS_24-07-03_200153_0-1-0.dat",
"Merlin-WEMS_24-07-03_200306_0-1-0.dat",
"Merlin-WEMS_24-07-03_200420_0-1-0.dat",
"Merlin-WEMS_24-07-03_200532_0-1-0.dat",
"Merlin-WEMS_24-07-03_200644_0-1-0.dat",
"Merlin-WEMS_24-07-03_200757_0-1-0.dat",
"Merlin-WEMS_24-07-03_200911_0-1-0.dat",
"Merlin-WEMS_24-07-03_201022_0-1-0.dat",
"Merlin-WEMS_24-07-03_201134_0-1-0.dat",
"Merlin-WEMS_24-07-03_201247_0-1-0.dat",
"Merlin-WEMS_24-07-03_201401_0-1-0.dat",
"Merlin-WEMS_24-07-03_201514_0-1-0.dat",
"Merlin-WEMS_24-07-03_201626_0-1-0.dat",
"Merlin-WEMS_24-07-03_201739_0-1-0.dat",
"Merlin-WEMS_24-07-03_201852_0-1-0.dat",
"Merlin-WEMS_24-07-03_202004_0-1-0.dat",
"Merlin-WEMS_24-07-03_202117_0-1-0.dat",
"Merlin-WEMS_24-07-03_202231_0-1-0.dat",
"Merlin-WEMS_24-07-03_202344_0-1-0.dat",
"Merlin-WEMS_24-07-03_202457_0-1-0.dat",
"Merlin-WEMS_24-07-03_202610_0-1-0.dat",
"Merlin-WEMS_24-07-03_202723_0-1-0.dat",
"Merlin-WEMS_24-07-03_202836_0-1-0.dat",
"Merlin-WEMS_24-07-03_202949_0-1-0.dat",
"Merlin-WEMS_24-07-03_203103_0-1-0.dat",
"Merlin-WEMS_24-07-03_203215_0-1-0.dat",
"Merlin-WEMS_24-07-03_203328_0-1-0.dat",
"Merlin-WEMS_24-07-03_203440_0-1-0.dat",
"Merlin-WEMS_24-07-03_203553_0-1-0.dat",
"Merlin-WEMS_24-07-03_203706_0-1-0.dat",
"Merlin-WEMS_24-07-03_203816_0-1-0.dat",
"Merlin-WEMS_24-07-03_203928_0-1-0.dat",
"Merlin-WEMS_24-07-03_204040_0-1-0.dat",
"Merlin-WEMS_24-07-03_204151_0-1-0.dat",
"Merlin-WEMS_24-07-03_204304_0-1-0.dat",
"Merlin-WEMS_24-07-03_204416_0-1-0.dat",
"Merlin-WEMS_24-07-03_204528_0-1-0.dat",
"Merlin-WEMS_24-07-03_204640_0-1-0.dat",
"Merlin-WEMS_24-07-03_204753_0-1-0.dat",
"Merlin-WEMS_24-07-03_204906_0-1-0.dat",
"Merlin-WEMS_24-07-03_205019_0-1-0.dat",
"Merlin-WEMS_24-07-03_205131_0-1-0.dat",
"Merlin-WEMS_24-07-03_205243_0-1-0.dat",
"Merlin-WEMS_24-07-03_205355_0-1-0.dat",
"Merlin-WEMS_24-07-03_205508_0-1-0.dat",
"Merlin-WEMS_24-07-03_205621_0-1-0.dat",
"Merlin-WEMS_24-07-03_205733_0-1-0.dat",
"Merlin-WEMS_24-07-03_205845_0-1-0.dat",
"Merlin-WEMS_24-07-03_205956_0-1-0.dat",
"Merlin-WEMS_24-07-03_210107_0-1-0.dat",
"Merlin-WEMS_24-07-03_210218_0-1-0.dat",
"Merlin-WEMS_24-07-03_210327_0-1-0.dat",
"Merlin-WEMS_24-07-03_210437_0-1-0.dat",
"Merlin-WEMS_24-07-03_210546_0-1-0.dat",
"Merlin-WEMS_24-07-03_210657_0-1-0.dat",
"Merlin-WEMS_24-07-03_210808_0-1-0.dat",
"Merlin-WEMS_24-07-03_210918_0-1-0.dat",
"Merlin-WEMS_24-07-03_211048_0-1-0.dat",
"Merlin-WEMS_24-07-03_211159_0-1-0.dat",
"Merlin-WEMS_24-07-03_211311_0-1-0.dat",
"Merlin-WEMS_24-07-03_211423_0-1-0.dat",
"Merlin-WEMS_24-07-03_211534_0-1-0.dat",
"Merlin-WEMS_24-07-03_211645_0-1-0.dat",
"Merlin-WEMS_24-07-03_211756_0-1-0.dat",
"Merlin-WEMS_24-07-03_211907_0-1-0.dat",
"Merlin-WEMS_24-07-03_212018_0-1-0.dat",
"Merlin-WEMS_24-07-03_212118_0-1-0.dat",
"Merlin-WEMS_24-07-03_212217_0-1-0.dat",
"Merlin-WEMS_24-07-03_212317_0-1-0.dat",
"Merlin-WEMS_24-07-03_212417_0-1-0.dat",
"Merlin-WEMS_24-07-03_212516_0-1-0.dat",
"Merlin-WEMS_24-07-03_212626_0-1-0.dat",
"Merlin-WEMS_24-07-03_212734_0-1-0.dat",
"Merlin-WEMS_24-07-03_212833_0-1-0.dat",
"Merlin-WEMS_24-07-03_212933_0-1-0.dat",
"Merlin-WEMS_24-07-03_213038_0-1-0.dat",
"Merlin-WEMS_24-07-03_213141_0-1-0.dat",
"Merlin-WEMS_24-07-03_213245_0-1-0.dat",
"Merlin-WEMS_24-07-03_213346_0-1-0.dat",
"Merlin-WEMS_24-07-03_213446_0-1-0.dat",
"Merlin-WEMS_24-07-03_213547_0-1-0.dat",
"Merlin-WEMS_24-07-03_213647_0-1-0.dat",
"Merlin-WEMS_24-07-03_213748_0-1-0.dat",
"Merlin-WEMS_24-07-03_213847_0-1-0.dat",
"Merlin-WEMS_24-07-03_213948_0-1-0.dat",
"Merlin-WEMS_24-07-03_214047_0-1-0.dat",
"Merlin-WEMS_24-07-03_214151_0-1-0.dat",
"Merlin-WEMS_24-07-03_214302_0-1-0.dat",
"Merlin-WEMS_24-07-03_214413_0-1-0.dat",
"Merlin-WEMS_24-07-03_214515_0-1-0.dat",
"Merlin-WEMS_24-07-03_214615_0-1-0.dat",
"Merlin-WEMS_24-07-03_214714_0-1-0.dat",
"Merlin-WEMS_24-07-03_214814_0-1-0.dat",
"Merlin-WEMS_24-07-03_214913_0-1-0.dat",
"Merlin-WEMS_24-07-03_215013_0-1-0.dat",
"Merlin-WEMS_24-07-03_215119_0-1-0.dat",
"Merlin-WEMS_24-07-03_215225_0-1-0.dat",
"Merlin-WEMS_24-07-03_215324_0-1-0.dat",
"Merlin-WEMS_24-07-03_215425_0-1-0.dat",
"Merlin-WEMS_24-07-03_215525_0-1-0.dat",
"Merlin-WEMS_24-07-03_215632_0-1-0.dat",
"Merlin-WEMS_24-07-03_215744_0-1-0.dat",
"Merlin-WEMS_24-07-03_215849_0-1-0.dat",
"Merlin-WEMS_24-07-03_215948_0-1-0.dat",
"Merlin-WEMS_24-07-03_220047_0-1-0.dat",
"Merlin-WEMS_24-07-03_220148_0-1-0.dat",
"Merlin-WEMS_24-07-03_220248_0-1-0.dat",
"Merlin-WEMS_24-07-03_220348_0-1-0.dat",
"Merlin-WEMS_24-07-03_220448_0-1-0.dat",
"Merlin-WEMS_24-07-03_220547_0-1-0.dat",
"Merlin-WEMS_24-07-03_220648_0-1-0.dat",
"Merlin-WEMS_24-07-03_220748_0-1-0.dat",
"Merlin-WEMS_24-07-03_220848_0-1-0.dat",
"Merlin-WEMS_24-07-03_220948_0-1-0.dat",
"Merlin-WEMS_24-07-03_221048_0-1-0.dat",
])

# Replacement files to be found under the repaired folder:
# Add key:value entries like this:
# "Merlin-WEMS_24-03-02_190309_0-0-0.dat": "Merlin-WEMS_24-03-02_190309_0-0-0.tif",
replace_images = {
  "Merlin-WEMS_24-03-02_190309_0-0-0.dat": "Merlin-WEMS_24-03-02_190309_0-0-0.tif",  
}



