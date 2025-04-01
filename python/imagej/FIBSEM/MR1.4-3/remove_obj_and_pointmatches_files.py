from __future__ import with_statement
import sys, os
sys.path.append("/lmb/home/acardona/lab/scripts/python/imagej/IsoView-GCaMP/")
from lib.io import loadFilePaths
from lib.util import syncPrintQ
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


# CHECK whether some sections have problems
# SOME IMAGES fail to open for reading the header with readFIBSEMHeader
check = False # To be used only the first time that the script is run

# Find all .dat files, as a sorted list
filepaths = loadFilePaths(srcDir, ".dat", csvDir, "imagefilepaths")

# Sections known to have problems (found via check = True above)
to_remove = set([
#"Merlin-WEMS_24-02-27_170732_", # added 0-0-0 tile to ignore: truncated, no pixels, only header
#"Merlin-WEMS_24-03-15_130137_", # repaired truncated
#"Merlin-WEMS_24-03-05_062018_", # added 0-1-0 tile to ignore
#"Merlin-WEMS_24-02-27_165658_", # repaired truncated
#"Merlin-WEMS_24-03-13_235528_", # repaired truncated
#"Merlin-WEMS_24-03-01_171102_", # no problems found manually with readFIBSEMdat
#"Merlin-WEMS_24-03-10_054103_", # repaired truncated
#"Merlin-WEMS_24-02-27_201135_", # repaired truncated
#"Merlin-WEMS_24-02-23_213519_", # repair truncated, was opening funny with a duplicated bottom
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
# Skip sections beyond 20964: less milling, overstretched, and full of curtains
groupNames = groupNames[964:20000+964]
tileGroups = tileGroups[964:20000+964]


n_adjacent = 3

# Write which files to remove: .obj and pointmatches files beyond 17000
with open(os.path.join(csvDirZ, "to_delete_17000"), 'w') as f:
  for i, groupName in enumerate(groupNames):
    if i > 17000:
      # Remove OBJ SIFT features file
      path = os.path.join(csvDirZ, "%s.SIFT-features.obj" % groupName)
      if os.path.exists(path):
        f.write(path)
        f.write('\n')
      else:
        syncPrintQ("Path does not exist: %i, %s" % (i, path))
      # Remove pointmatches files
      for j in xrange(i+1, min(len(groupNames), i + n_adjacent + 1)):
        path = os.path.join(csvDirZ, "%s.%s.pointmatches.csv" % (groupName, groupNames[j]))
        if os.path.exists(path):
          f.write(path)
          f.write('\n')
        else:
          syncPrintQ("Patch does not exist: %i, %i, %s" % (i, j, path))
      
      
      
      
      
      
      
      
      
      
      
      