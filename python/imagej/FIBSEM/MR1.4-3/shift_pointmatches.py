# Fix pointmatches after adding more sectionOffsets (aka shifts)

import sys, os
sys.path.append("/lmb/home/acardona/lab/scripts/python/imagej/IsoView-GCaMP/")
from lib.serial2Dregistration import translatePointMatches
from lib.io import loadFilePaths
from lib.montage2d import makeMontageGroups

# MR1.4-3 volume
# Resolution is: 8x8x8 nm, FIBSEM
name = "MR1.4-3"

# Folders
srcDir = "/net/fibserver1/raw/" + name + "/"
tgtDir = "/net/zstore1/FIBSEM/" + name + "/registration/"
csvDir = tgtDir + "csv/" # for in-section montaging
csvDirZ = tgtDir + "csvZ/" # for cross-section alignment with SIFT+RANSAC
csvDirBM = tgtDir + "csvBM/" # for cross-section alignment with BlockMatching
repairedDir = "/net/zstore1/FIBSEM/" + name + "/repaired/" # Folder with repaired images, if any

srcCsvDir = csvDirZ
tgtCsvDir = tgtDir + "csvDirZShifts/"

check = False
n_adjacent = 3


if not os.path.exists(tgtCsvDir):
    os.makedirs(tgtCsvDir) # recursive directory creation


def sectionOffsets(index)
  index += 1904 # add 1904 given that we cropped that many from the start
  dx = 0
  dy = 0
  if index >= 1910 + 1904:
    dx += 61
    dy += 12
  if index >= 1911 + 1904:
    dx += -2
    dy += 3
  if index >= 1912 + 1904:
    dx += -1
    dy += -372
  if index >= 2351 + 1904: # 0-based
    dx += 99
    dy += 35
  if index >= 2352 + 1904:
    dx += 2
    dy += 4
  if index >= 2353 + 1904:
    dx += 1
    dy += -2
  if index >= 2354 + 1904:
    dx += 1
    dy += 0
  
  return dx, dy


# Find all .dat files, as a sorted list
filepaths = loadFilePaths(srcDir, ".dat", csvDir, "imagefilepaths")

# Sections known to have problems (found via check = True above)
to_remove = set([
])

ignore_images = set([
 "Merlin-WEMS_24-02-27_170732_0-0-0.dat", # only header, whole image truncated
 "Merlin-WEMS_24-03-05_062018_0-0-0.dat"  # partial truncation without sample in it, would occlude the 0-1-0 tile
])

# Sorted group names, one per section
groupNames, tileGroups = makeMontageGroups(filepaths, to_remove, check,
                                           alternative_dir=repairedDir,
                                           ignore_images=ignore_images,
                                           writeDir=csvDir)


# Skip sections 1-963: no sample in them, just resin
# Skip sections 964-1904: mostly somas and huge gap between 1903 and 1904
# Skip sections beyond 20964: less milling, overstretched, and full of curtains
groupNames = groupNames[964+1904:20000+964]
tileGroups = tileGroups[964+1904:20000+964]



translatePointMatches(groupNames, sectionOffsets, n_adjacent, srcCsvDir, tgtCsvDir)

