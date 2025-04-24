# Step 1: montage parameters

import os, re
from mpicbg.imagefeatures import FloatArray2DSIFT
from ij.gui import Roi

# REGISTRATION LIBRARY
libDir = "/lmb/home/acardona/lab/scripts/python/imagej/IsoView-GCaMP/"

# VOLUME
name = "SAM_3M" # Name of the folder containing the .dat files, e.g., "MR1.4-3"
sourceServer = "/net/fibserver1/raw/"
targetServer = "/net/fibserver1/raw/"


# Folders
srcDir = sourceServer + name + "/Y2024/"
tgtDir = targetServer + name + "/registration/"
montageDir = tgtDir + "montage-csv/" # for in-section montaging
repairedDir = targetServer + name + "/repaired/" # Folder with repaired images, if any

# Image tile overlap parameters
offset  =  80 # pixels The left margin of each image is severely elastically deformed.
overlap = 990 # pixels
nominal_overlap = 1000 # 8 microns at 8 nm/px = 1000 px

# Working canvas
section_width  = 13750      # pixels, after section-wise montaging
section_height = 13750      # 

# Skip sections. Define a range to work with.
first_section = 170  # 0-based
last_section = -1

# Replace sections: (0-based, not 1-based !)
# NOTE indices are relative to the first_section as specified above
# Add entries like: 1718: 1719,  indicating that section 1718 is to be replaced by section at 1719, effectively duplicating the latter
# This is desirable to keep the true Euclidean distances and dimensions while overriding a faulty section with e.g, truncated images.
replace_sections = {
  2723: 2724, # stretched horizontally
}

def single_tile_position_fn(tilePath, imp):
  # In volume SAM_3M, montaging was done centering the tiles by default, which makes it hard then to enlarge the canvas later
  # because the position is relative to the size of the canvas.
  # Despite every section having only one tile,  the first few tiles are smaller than the rest, so we have to specify how to center them all
  # relative to the original canvas used for montaging and alignment, and to the size of the image tile itself:
  return int( (13750 - imp.getWidth()) / 2 + 0.5 ), int( (13750 - imp.getHeight()) / 2 + 0.5 )

def loadAsFloatFn(filepath):
  filename = os.path.basename(filepath)
  if filename.endswith(".tif"):
    return False #  already fixed if it's a repaired file
  # Sections before 2723 with groupName "Merlin-FIBdeSEMAna_24-12-03_083917_0-0-0.dat"  have to be opened as float
  yearT, monthT, dayT, secondsT = [24, 12, 3, 83917]
  pattern = re.compile("^(\d+)-(\d+)-(\d+)_(\d+)$")
  year, month, day, seconds = map(int, re.match(pattern, filename[filename.find('_')+1 : filename.rfind('_')]).groups())
  # all values have to be smaller or equal than the cutoff
  if year < yearT:
    return True
  if year > yearT:
    return False
  # year is equal
  if month < monthT:
    return True
  if month > monthT:
    return False
  # month is equal
  if day < dayT:
    return True
  if day > dayT:
    return False
  # day is equal
  return seconds <= secondsT # inclusive of section 2723


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
  "interim_scale": 0.125, # for saving montaged snapshops to disk to be used for evaluation and serial alignment
  "single_tile_position_fn": single_tile_position_fn, # FIX issue with resizing canvas later since single-tile sections were rendered as centered in the montage snapshots.
  "loadAsFloatFn": loadAsFloatFn, # sections 0-2723 or so have to be opened as float
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
  "Merlin-FIBdeSEMAna_24-12-10_225049_0-0-0_bad.dat",
  "Merlin-FIBdeSEMAna_24-12-03_103036_0-0-0.dat", # fails to open
  "Merlin-FIBdeSEMAna_24-12-05_233743_0-0-0.dat", # fails to open
  "Merlin-FIBdeSEMAna_24-12-11_182232_0-0-0.dat", # fails to open
  "Merlin-FIBdeSEMAna_24-12-14_200204_0-0-0.dat", # fails to open
])

# Replacement files to be found under the repaired folder:
# Add key:value entries like this:
# "Merlin-WEMS_24-03-02_190309_0-0-0.dat": "Merlin-WEMS_24-03-02_190309_0-0-0.tif",
replace_images = {
  
}



