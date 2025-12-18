import sys
libDir = "/lmb/home/acardona/lab/scripts/python/imagej/IsoView-GCaMP/"
sys.path.append(libDir)
from lib.io import readN5, writeN5
from lib.ui import showStack, showBDV
from net.imglib2.view import Views
from net.imglib2 import FinalInterval
from lib.ui import duplicateInParallel
from lib.util import numCPUs


# Concatenate the two SAM_3G volumes, which are already registered.


n5 = "/net/fibserver1/raw/SAM_3G/samia/original_samia2.n5/volumes"
n5_2nd = "/net/fibserver1/raw/SAM_3G/registration/n5-2nd-hemisphere"


def viewZRange(n5path, start, end, title, level="s0"):
  img = readN5(n5path, level, show=None)
  print img
  imgZRange = Views.interval(img,
                             [0, 0, start if start >= 0 else img.dimension(2) + start],
                             [img.dimension(0) -1, img.dimension(1) -1, end if end >= 0 else img.dimension(2) + end])

  imp = showStack(imgZRange, title="%s :: %i-%i" % (title, start, end), show=False)
  duplicateInParallel(imp, range(0, imp.getNSlices()), n_threads=100, shallow=True, show=True)

# View the last 5 sections of the first and the first 5 sections of the second
#viewZRange(n5, -62, -1, "first", "s0")
#viewZRange(n5_2nd, 0, 4, "second", "s0")

# Turns out the first has the last 23 sections black.
# Compose a new joint view, with the larger canvas
img1 = readN5(n5, "s0", show=None, maxNumCacheEntries=7000)
img2 = readN5(n5_2nd, "s0", show=None, maxNumCacheEntries=7000) # its width and height are larger than img1's
# Both images are aligned at 0,0
imgBoth = Views.concatenate(2,
                            [Views.interval(Views.extendZero(img1),
                                            FinalInterval(img2.dimension(0),
                                                          img2.dimension(1),
                                                          img1.dimension(2) - 23)),
                             img2])

#showBDV(imgBoth)

# Write N5 volume
n5Dir = "/net/fibserver1/raw/SAM_3G/registration/joined-n5/"
# Parameters on what to export
paramsN5 = {
  "block_size": [256, 256, 64], # e.g., [128,128,128]
  "gzip_compression": 4, # between 0 (no compression) and 9
  "n_threads": numCPUs(), # for writing
}
writeN5(imgBoth, n5Dir, "s0",
        paramsN5["block_size"],
        gzip_compression_level=paramsN5["gzip_compression"],
        n_threads=paramsN5["n_threads"])

