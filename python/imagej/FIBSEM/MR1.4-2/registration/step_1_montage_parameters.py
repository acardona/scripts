# Step 1: montage parameters

from mpicbg.imagefeatures import FloatArray2DSIFT
from ij.gui import Roi

# REGISTRATION LIBRARY
libDir = "/lmb/home/acardona/lab/scripts/python/imagej/IsoView-GCaMP/"

# VOLUME
name = "MR1.4-2" # Name of the folder containing the .dat files, e.g., "MR1.4-3"
sourceServer = "/net/fibserver1/raw/"
targetServer = "/net/fibserver1/raw/"


# Folders
srcDir = sourceServer + name + "/"
tgtDir = targetServer + name + "/registration/"
montageDir = tgtDir + "montage-csv/" # for in-section montaging
#repairedDir = targetServer + name + "/repaired/" # Folder with repaired images, if any
repairedDir = "/net/zstore1/FIBSEM/" + name + "/repaired/" # Folder with repaired images, if any

# Image tile overlap parameters
offset  =  80 # pixels The left margin of each image is severely elastically deformed.
overlap = 990 # pixels
nominal_overlap = 1000 # 8 microns at 8 nm/px = 1000 px

# Working canvas
section_width  = 13500      # pixels, after section-wise montaging
section_height = 11720


# Skip sections. Define a range to work with.
first_section = 0  # 0-based
last_section = -1

# Replace sections: (0-based, not 1-based !)
# NOTE indices are relative to the first_section as specified above
# Add entries like: 1718: 1719,  indicating that section 1718 is to be replaced by section at 1719, effectively duplicating the latter
# This is desirable to keep the true Euclidean distances and dimensions while overriding a faulty section with e.g, truncated images.
replace_sections = {
  1132: 1131, # missing lower tile
  1134: 1133, # missing lower tile
  2738: 2737, # missing lower tile
  3245: 3244, # missing lower tile
  3907: 3906, # upper tile renders at the bottom and is incomplete, repaired
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
  "maxEpsilon": 25, # pixels, maximum error allowed, usual number is 25.
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

# Sections known to have problems (more will be added when running a file check the first time)
# Add entries like this, with a comment for the record":
# "Merlin-WEMS_24-02-27_170732_" # added 0-0-0 tile to ignore: truncated, no pixels, only header
to_remove = set([
  "Merlin-FIBdeSEMAna_24-06-10_204041_" # section 3311 (1-based) has no data, just white noise
])

# Add entries like this, with the file name of individual image tiles and a comment:
# "Merlin-WEMS_24-02-27_170732_0-0-0.dat", # only header, whole image truncated
ignore_images = set([
  "Merlin-FIBdeSEMAna_24-06-08_214955_0-1-0.dat", # empty file
  "Merlin-FIBdeSEMAna_24-06-08_215138_0-1-0.dat", # empty file
])

# Replacement files to be found under the repaired folder:
# Add key:value entries like this:
# "Merlin-WEMS_24-03-02_190309_0-0-0.dat": "Merlin-WEMS_24-03-02_190309_0-0-0.tif",
replace_images = {
  "Merlin-FIBdeSEMAna_24-06-11_064022_0-0-0.dat": "Merlin-FIBdeSEMAna_24-06-11_064022_0-0-0.dat.tif",
  #"Merlin-FIBdeSEMAna_24-06-11_071856_0-0-0.dat": "Merlin-FIBdeSEMAna_24-06-11_071856_0-0-0.dat.tif", # 3910
  #"Merlin-FIBdeSEMAna_24-06-11_071856_0-1-0.dat": "Merlin-FIBdeSEMAna_24-06-11_071856_0-1-0.dat.tif", # 3910
  "Merlin-FIBdeSEMAna_24-06-10_203932_0-0-0.dat": "Merlin-FIBdeSEMAna_24-06-10_203932_0-0-0.dat.tif", # 3310
  "Merlin-FIBdeSEMAna_24-06-10_203932_0-1-0.dat": "Merlin-FIBdeSEMAna_24-06-10_203932_0-1-0.dat.tif", # 3310
  "Merlin-FIBdeSEMAna_24-06-10_205538_0-0-0.dat": "Merlin-FIBdeSEMAna_24-06-10_205538_0-0-0.dat.tif", # 3311
  "Merlin-FIBdeSEMAna_24-06-10_205538_0-1-0.dat": "Merlin-FIBdeSEMAna_24-06-10_205538_0-1-0.dat.tif"  # 3311
}



