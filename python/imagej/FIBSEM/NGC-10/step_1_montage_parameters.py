# Step 1: montage parameters

from mpicbg.imagefeatures import FloatArray2DSIFT
from ij.gui import Roi
import os

# REGISTRATION LIBRARY
libDir = "/lmb/home/phague/fibsem/scripts/python/imagej/IsoView-GCaMP/"

# VOLUME
name = "NGC-10" # Name of the folder containing the .dat files, e.g., "MR1.4-3"
sourceServer = "/net/fibserver1/raw/"
targetServer = "/net/fibserver1/raw/"


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
section_width  = 28000      # pixels, after section-wise montaging
section_height = 28000     # So a canvas of 256,000,000 pixels: 256 MB

# Parameters to filter out features outside the tissue using a LabKit model
# Can be None if you don't want any filtering, but paramsFilterFeatures has to exist as a variable
paramsFilterFeatures = {
  "model_path": os.path.join(tgtDir, "ngc10-240925.classifier"), # Cannot be None. from LabKit.
  "model_width": 400, # Cannot be None. Target width for resizing so as to match the dimensions of the image used when training the model.
  "as3D": False, # False if the LabKit model was explicitly trained to be a 2D model.
  "section_width": section_width, # ASSUMES the model was trained on the whole montage
}

# Skip sections. Define a range to work with.
first_section = 1630  # 0-based
last_section = -1

# Replace sections: (0-based, not 1-based !)
# NOTE indices are relative to the first_section as specified above
# Add entries like: 1718: 1719,  indicating that section 1718 is to be replaced by section at 1719, effectively duplicating the latter
# This is desirable to keep the true Euclidean distances and dimensions while overriding a faulty section with e.g, truncated images.
# Alternatively, add entries as <groupName>: <groupName>, i.e., like:
#     "Merlin-WEMS_24-05-30_104352_": "Merlin-WEMS_24-05-30_112457_"
replace_sections = {
   "Merlin-FIBdeSEMAna_25-07-24_002444_": "Merlin-FIBdeSEMAna_25-07-24_002444_", # 4686
   "Merlin-FIBdeSEMAna_25-07-24_151704_": "Merlin-FIBdeSEMAna_25-07-24_151046_", # 5112
   "Merlin-FIBdeSEMAna_25-07-24_152713_": "Merlin-FIBdeSEMAna_25-07-24_151046_",  # 5113
   "Merlin-FIBdeSEMAna_25-07-24_155413_": "Merlin-FIBdeSEMAna_25-07-24_162420_" # 5114
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

# Sections known to have problems (more will be added when running a file check the first time)
# Add entries like this, with a comment for the record":
# "Merlin-WEMS_24-02-27_170732_" # added 0-0-0 tile to ignore: truncated, no pixels, only header
to_remove = set([
  
])

# Add entries like this, with the file name of individual image tiles and a comment:
# "Merlin-WEMS_24-02-27_170732_0-0-0.dat", # only header, whole image truncated
ignore_images = set([
  
])

# Replacement files to be found under the repaired folder:
# Add key:value entries like this:
# "Merlin-WEMS_24-03-02_190309_0-0-0.dat": "Merlin-WEMS_24-03-02_190309_0-0-0.tif",
replace_images = {
  
}



