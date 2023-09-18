import sys, os
sys.path.append("/home/albert/lab/scripts/python/imagej/IsoView-GCaMP/")
from lib.serial2Dregistration import ensureSIFTFeatures
from lib.io import findFilePaths
from collections import defaultdict


srcDir = "/home/albert/zstore1/FIBSEM/Pedro_parker/"
tgtDir = "/home/albert/zstore1/FIBSEM/Pedro_parker/registration/"

# Find all .dat files, as a sorted list
filepaths = findFilePaths(srcDir, ".dat")

# Group files by section, as there could be multiple image tiles per section
groups = defaultdict(list)
for filepath in filepaths:
  path, filename = os.path.split(filepath)
  # filepath looks like: /home/albert/zstore1/FIBSEM/Pedro_parker/M07/D13/Merlin-FIBdeSEMAna_23-07-13_083741_0-0-0.dat
  sectionName = filename[0:-9]
  groups[sectionName].append(filepath)

for groupName, tilePaths in groups.iteritems():
  print groupName, len(tilePaths)

# For each group with more than one member,
# extract features from the appropriate ROI
# along the overlapping edges
for groupName, tilePaths in groups.iteritems():
  if len(tilePaths) > 1:
    # QUESTION: are all images the same width and height?
    # Read dimensions from the .dat header

#filepath, paramsSIFT, properties, csvDir, validateByFileExists=False):