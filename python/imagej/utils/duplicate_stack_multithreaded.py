# Duplicate a stack in parallel
import sys, os
sys.path.append("/lmb/home/acardona/lab/scripts/python/imagej/IsoView-GCaMP/")
from lib.ui import duplicateInParallel
from ij import IJ


imp = IJ.getImage()
# NC_Hypathia transition from 2x2 tiles to single tile
#copy = duplicateInParallel(imp, range(3490, 3493), n_threads=10, shallow=True)

#copy = duplicateInParallel(imp, range(3470, 3520), n_threads=50, shallow=True, show=True)

#copy = duplicateInParallel(imp, range(1990, 2010), n_threads=50, shallow=True, show=True)

#copy = duplicateInParallel(imp, range(10590, 10610), n_threads=50, shallow=True, show=True)

#copy = duplicateInParallel(imp, range(8980, 9000), n_threads=50, shallow=True)

# no jump:
#copy = duplicateInParallel(imp, range(8500, 8700), n_threads=50, shallow=True)

#copy = duplicateInParallel(imp, range(8880, 8902), n_threads=50, shallow=True)

#copy = duplicateInParallel(imp, range(8700, 9000), n_threads=50, shallow=True)

#copy = duplicateInParallel(imp, range(11885, 12054), n_threads=50, shallow=True, show=True)

# MR1.4-3
#copy = duplicateInParallel(imp, range(2725, 2731), n_threads=50, shallow=True, show=True)

#copy = duplicateInParallel(imp, range(963, 1000), n_threads=50, shallow=True, show=True)


# Region with single PointMatch
#copy = duplicateInParallel(imp, range(949 -3, 965 + 3), n_threads=50, shallow=True, show=True)

# Region with single PointMatch across missing sections
#copy = duplicateInParallel(imp, range(2726 -3, 2730 + 3), n_threads=50, shallow=True, show=True)

# Before boundary between 1 tile and 1x2 tiles (2865 to 2868) and actual boundary (2869)
#copy = duplicateInParallel(imp, range(2865 -3, 2869 + 3), n_threads=50, shallow=True, show=True)

# To estimate manual shift to avoid too many optimizer iterations
#copy = duplicateInParallel(imp, range(2868 -1, 2869 +1), n_threads=50, shallow=True, show=True)


copy = duplicateInParallel(imp, range(2868 -5 -964, 2869 +5 -964), n_threads=50, shallow=True, show=True)

copy = duplicateInParallel(imp, range(100, 200), n_threads=100, shallow=True, show=True)