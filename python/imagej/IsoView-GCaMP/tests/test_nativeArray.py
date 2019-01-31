import sys
sys.path.append("/home/albert/lab/scripts/python/imagej/IsoView-GCaMP/lib/")

from util import nativeArray

c = nativeArray([3, 4],'c')
print type(c), c