# Step 1: montage parameters

import os
import sys
from mpicbg.imagefeatures import FloatArray2DSIFT
from ij.gui import Roi

# REGISTRATION LIBRARY
#libDir = "/net/fibserver1/raw/YY9_Gaba/scripts/python/imagej/IsoView-GCaMP/"
libDir = "/net/fibserver1/code/scripts/python/imagej/IsoView-GCaMP/"

# Import registration library functions
sys.path.append(libDir)
from lib.serial2Dregistration import makeFilterFeaturesFn

# VOLUME
name = "YY9_Gaba" # Name of the folder containing the .dat files, e.g., "MR1.4-3"
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
section_width  = 16000      # pixels, after section-wise montaging
section_height = 16000     # So a canvas of 256,000,000 pixels: 256 MB

# Parameters to filter out features outside the tissue using a LabKit model
# Can be None if you don't want any filtering, but paramsFilterFeatures has to exist as a variable
paramsFilterFeatures = None

# Skip sections. Define a range to work with.
first_section = 0  # 0-based
last_section = -331


# Replace sections: (0-based, not 1-based !)
# NOTE indices are relative to the first_section as specified above
# Add entries like: 1718: 1719,  indicating that section 1718 is to be replaced by section at 1719, effectively duplicating the latter
# This is desirable to keep the true Euclidean distances and dimensions while overriding a faulty section with e.g, truncated images.
# Alternatively, add entries as <groupName>: <groupName>, i.e., like:
#     "Merlin-WEMS_24-05-30_104352_": "Merlin-WEMS_24-05-30_112457_"
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
  "interim_scale": 0.125, # for saving montaged snapshops to disk to be used for evaluation and serial alignment
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
"Merlin-FIBdeSEMAna_25-12-07_133352_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-07_135434_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-07_134733_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-07_131600_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-07_141249_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-07_132240_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-07_204920_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-07_205632_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-07_212505_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-07_214510_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-07_214803_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-07_221732_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-07_222854_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-07_230627_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-07_231333_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-07_233456_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-07_135434_0-0-1.dat",
"Merlin-FIBdeSEMAna_25-12-07_212505_0-0-1.dat",
"Merlin-FIBdeSEMAna_25-12-07_221732_0-0-1.dat",
"Merlin-FIBdeSEMAna_25-12-07_214803_0-0-1.dat",
"Merlin-FIBdeSEMAna_25-12-07_205632_0-0-1.dat",
"Merlin-FIBdeSEMAna_25-12-07_141249_0-0-1.dat",
"Merlin-FIBdeSEMAna_25-12-07_204920_0-0-1.dat",
"Merlin-FIBdeSEMAna_25-12-07_132240_0-0-1.dat",
"Merlin-FIBdeSEMAna_25-12-07_214510_0-0-1.dat",
"Merlin-FIBdeSEMAna_25-12-07_222854_0-0-1.dat",
"Merlin-FIBdeSEMAna_25-12-07_230627_0-0-1.dat",
"Merlin-FIBdeSEMAna_25-12-08_003144_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-08_072435_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-09_135438_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-10_144846_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-10_145423_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-10_145209_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-13_211256_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-13_211502_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-13_214112_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-07_124802_0-0-1.dat",
"Merlin-FIBdeSEMAna_25-12-07_130858_0-0-1.dat",
"Merlin-FIBdeSEMAna_25-12-07_223147_0-0-1.dat",
"Merlin-FIBdeSEMAna_25-12-07_125911_0-0-1.dat",
"Merlin-FIBdeSEMAna_25-12-07_230917_0-0-1.dat",
"Merlin-FIBdeSEMAna_25-12-07_130734_0-0-1.dat",
"Merlin-FIBdeSEMAna_25-12-07_130323_0-0-1.dat",
"Merlin-FIBdeSEMAna_25-12-07_122817_0-0-1.dat",
"Merlin-FIBdeSEMAna_25-12-07_215633_0-0-1.dat",
"Merlin-FIBdeSEMAna_25-12-13_224648_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-13_224648_0-0-1.dat",
"Merlin-FIBdeSEMAna_25-12-13_225914_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-13_230028_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-13_231028_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-13_212700_0-0-1.dat",
"Merlin-FIBdeSEMAna_25-12-13_231151_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-13_214825_0-0-1.dat",
"Merlin-FIBdeSEMAna_25-12-13_231403_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-13_220945_0-0-1.dat",
"Merlin-FIBdeSEMAna_25-12-13_225514_0-0-1.dat",
"Merlin-FIBdeSEMAna_25-12-13_223646_0-0-1.dat",
"Merlin-FIBdeSEMAna_25-12-13_222401_0-0-1.dat",
"Merlin-FIBdeSEMAna_25-12-13_221529_0-0-1.dat",
"Merlin-FIBdeSEMAna_25-12-13_224105_0-0-1.dat",
"Merlin-FIBdeSEMAna_25-12-14_000358_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-13_231839_0-0-1.dat",
"Merlin-FIBdeSEMAna_25-12-13_232426_0-0-1.dat",
"Merlin-FIBdeSEMAna_25-12-14_000501_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-13_233143_0-0-1.dat",
"Merlin-FIBdeSEMAna_25-12-14_000708_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-14_000914_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-14_010709_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-14_011115_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-14_011659_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-14_022318_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-14_022616_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-14_024831_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-14_035902_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-14_040110_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-14_024831_0-0-1.dat",
"Merlin-FIBdeSEMAna_25-12-14_040213_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-14_040420_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-14_041100_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-14_041225_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-14_011533_0-0-1.dat",
"Merlin-FIBdeSEMAna_25-12-14_042938_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-14_012538_0-0-1.dat",
"Merlin-FIBdeSEMAna_25-12-14_041100_0-0-1.dat",
"Merlin-FIBdeSEMAna_25-12-14_044243_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-14_045423_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-14_052043_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-14_052759_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-14_023507_0-0-1.dat",
"Merlin-FIBdeSEMAna_25-12-14_023211_0-0-1.dat",
"Merlin-FIBdeSEMAna_25-12-14_024411_0-0-1.dat",
"Merlin-FIBdeSEMAna_25-12-14_053642_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-14_052759_0-0-1.dat",
"Merlin-FIBdeSEMAna_25-12-14_055538_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-14_063619_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-14_043232_0-0-1.dat",
"Merlin-FIBdeSEMAna_25-12-14_064501_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-14_065216_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-14_051200_0-0-1.dat",
"Merlin-FIBdeSEMAna_25-12-14_052338_0-0-1.dat",
"Merlin-FIBdeSEMAna_25-12-14_065801_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-14_053515_0-0-1.dat",
"Merlin-FIBdeSEMAna_25-12-14_053935_0-0-1.dat",
"Merlin-FIBdeSEMAna_25-12-14_054358_0-0-1.dat",
"Merlin-FIBdeSEMAna_25-12-14_062612_0-0-1.dat",
"Merlin-FIBdeSEMAna_25-12-14_063452_0-0-1.dat",
"Merlin-FIBdeSEMAna_25-12-14_055116_0-0-1.dat",
"Merlin-FIBdeSEMAna_25-12-14_064039_0-0-1.dat",
"Merlin-FIBdeSEMAna_25-12-14_062151_0-0-1.dat",
"Merlin-FIBdeSEMAna_25-12-14_073401_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-14_070219_0-0-1.dat",
"Merlin-FIBdeSEMAna_25-12-14_073822_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-14_071934_0-0-1.dat",
"Merlin-FIBdeSEMAna_25-12-14_070803_0-0-1.dat",
"Merlin-FIBdeSEMAna_25-12-14_071514_0-0-1.dat",
"Merlin-FIBdeSEMAna_25-12-14_072101_0-0-1.dat",
"Merlin-FIBdeSEMAna_25-12-14_072814_0-0-1.dat",
"Merlin-FIBdeSEMAna_25-12-14_080549_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-14_080549_0-0-1.dat",
"Merlin-FIBdeSEMAna_25-12-14_074116_0-0-1.dat",
"Merlin-FIBdeSEMAna_25-12-14_081433_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-14_132111_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-14_075250_0-0-1.dat",
"Merlin-FIBdeSEMAna_25-12-14_080003_0-0-1.dat",
"Merlin-FIBdeSEMAna_25-12-14_132707_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-14_132811_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-14_081010_0-0-1.dat",
"Merlin-FIBdeSEMAna_25-12-14_081728_0-0-1.dat",
"Merlin-FIBdeSEMAna_25-12-14_132916_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-14_133020_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-14_133124_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-14_140442_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-14_150050_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-14_150809_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-14_150050_0-0-1.dat",
"Merlin-FIBdeSEMAna_25-12-14_151355_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-14_151642_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-14_151642_0-0-1.dat",
"Merlin-FIBdeSEMAna_25-12-14_201155_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-14_201828_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-15_083846_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-15_085335_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-15_092633_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-15_093708_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-15_093941_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-15_095334_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-14_141346_0-0-1.dat",
"Merlin-FIBdeSEMAna_25-12-15_100849_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-14_142134_0-0-1.dat",
"Merlin-FIBdeSEMAna_25-12-15_101121_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-15_101808_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-15_102541_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-15_102039_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-15_102955_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-15_103640_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-15_104507_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-15_105153_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-15_105658_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-15_112357_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-14_143742_0-0-1.dat",
"Merlin-FIBdeSEMAna_25-12-15_112629_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-15_114553_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-15_114825_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-14_151230_0-0-1.dat",
"Merlin-FIBdeSEMAna_25-12-15_115833_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-15_121756_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-15_122026_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-15_122259_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-15_125723_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-15_125953_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-15_130225_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-15_130542_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-15_132010_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-15_132602_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-15_133042_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-15_133634_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-15_134451_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-15_134720_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-15_134950_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-15_140443_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-14_153111_0-0-1.dat",
"Merlin-FIBdeSEMAna_25-12-15_141121_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-15_141438_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-15_142022_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-15_142606_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-15_144001_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-15_145357_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-15_145626_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-15_145855_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-15_150706_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-15_152202_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-15_152746_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-15_172311_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-15_172710_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-15_175431_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-15_195205_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-15_203709_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-15_205738_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-15_210104_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-15_211420_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-15_210742_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-15_214704_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-15_214328_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-15_215511_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-15_220030_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-15_215936_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-15_221447_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-15_223853_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-15_224438_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-15_225526_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-15_230023_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-15_230836_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-15_231333_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-16_074544_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-16_083838_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-16_084928_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-16_092707_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-16_103758_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-16_110317_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-16_152426_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-16_175647_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-16_182554_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-17_044921_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-17_051537_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-17_052350_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-17_075657_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-17_075421_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-17_081240_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-17_081507_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-17_081645_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-17_081734_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-17_083046_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-17_083628_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-17_084955_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-17_084121_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-17_090226_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-17_091932_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-17_085423_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-17_091651_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-17_091411_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-17_090509_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-17_092453_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-17_093201_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-17_093812_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-17_094613_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-17_101737_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-17_102356_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-17_103800_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-17_104026_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-17_104333_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-17_110111_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-17_124958_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-17_130227_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-17_131451_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-17_134649_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-17_140226_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-17_140312_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-17_142325_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-17_143507_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-17_143552_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-17_143638_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-17_145955_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-17_150214_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-17_150300_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-17_150347_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-17_150434_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-17_174639_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-17_174945_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-17_175645_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-17_180301_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-17_181131_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-17_182225_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-17_184548_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-17_184106_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-17_185946_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-17_184020_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-17_185900_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-17_185333_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-17_192103_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-17_190921_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-17_192017_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-18_081035_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-18_081436_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-18_082406_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-18_083240_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-18_083635_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-18_084846_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-18_085329_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-18_091047_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-18_091313_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-18_092158_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-18_092419_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-18_092639_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-18_092859_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-18_093119_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-18_094038_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-18_094738_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-18_094957_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-18_095353_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-18_095614_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-18_100009_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-18_100404_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-18_100912_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-18_104027_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-18_104856_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-18_105513_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-18_110630_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-18_135552_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-18_140653_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-18_142742_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-18_143431_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-18_143738_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-18_144832_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-18_144219_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-18_150452_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-18_145839_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-18_151457_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-18_151149_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-18_150759_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-18_152041_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-18_155407_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-18_155713_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-18_155847_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-18_160643_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-18_161012_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-18_161320_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-18_162725_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-18_163032_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-18_163609_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-18_163522_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-18_163917_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-18_164311_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-18_165013_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-18_165406_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-18_165713_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-18_170413_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-18_171028_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-18_171815_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-18_172123_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-18_172736_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-18_173128_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-18_184316_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-18_184908_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-18_185844_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-18_190150_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-18_190544_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-18_191114_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-18_191422_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-18_191730_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-18_192344_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-18_192651_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-18_193307_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-18_194009_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-18_194403_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-18_194711_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-18_195018_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-18_195457_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-18_200854_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-18_201201_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-18_201508_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-18_202737_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-18_205456_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-18_210332_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-18_205803_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-18_210947_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-18_212434_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-18_213356_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-18_213049_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-18_212741_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-18_214717_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-19_083111_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-19_085431_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-19_090418_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-19_092535_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-19_093752_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-19_095007_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-19_095429_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-19_100225_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-19_100629_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-19_101419_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-19_101725_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-19_102034_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-19_102734_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-19_103125_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-19_103912_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-19_104217_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-19_104744_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-19_105051_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-19_105618_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-19_111018_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-19_112703_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-19_113116_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-19_113511_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-19_114344_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-19_114947_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-19_115419_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-19_115807_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-19_120152_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-19_121017_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-19_121726_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-19_121908_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-19_122144_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-19_122327_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-19_123441_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-19_124047_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-19_124510_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-19_125346_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-19_125431_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-19_125905_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-19_130213_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-19_130954_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-19_132204_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-19_133932_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-19_134234_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-19_135015_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-19_135924_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-19_140227_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-19_141354_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-19_135621_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-19_142413_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-19_143023_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-19_142942_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-19_143838_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-19_151501_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-19_152319_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-19_152839_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-19_153223_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-19_153354_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-19_153738_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-19_154123_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-19_171018_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-19_172240_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-19_202514_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-19_203205_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-19_203452_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-19_213446_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-19_213624_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-19_213919_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-19_214022_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-11-28_045840_0-0-0.dat", # Weird artefact mid-section.
"Merlin-FIBdeSEMAna_25-11-28_045840_0-0-1.dat",
"Merlin-FIBdeSEMAna_25-12-04_073041_0-0-0.dat", # Same artefact
"Merlin-FIBdeSEMAna_25-12-04_073041_0-0-1.dat",
"Merlin-FIBdeSEMAna_25-12-06_213718_0-0-0.dat", # Same artefact
"Merlin-FIBdeSEMAna_25-12-06_213718_0-0-1.dat",
"Merlin-FIBdeSEMAna_25-11-27_185132_0-0-0.dat", # Same artefact
"Merlin-FIBdeSEMAna_25-11-27_185132_0-0-1.dat",
"Merlin-FIBdeSEMAna_25-11-28_004440_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-11-28_004440_0-0-1.dat",
"Merlin-FIBdeSEMAna_25-12-15_195457_0-0-0.dat",
])

# Replacement files to be found under the repaired folder:
# Add key:value entries like this:
# "Merlin-WEMS_24-03-02_190309_0-0-0.dat": "Merlin-WEMS_24-03-02_190309_0-0-0.tif",
replace_images = {
  
}



