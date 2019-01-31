import sys
sys.path.append("/home/albert/lab/scripts/python/imagej/IsoView-GCaMP/")
from lib.registration import saveMatrices, loadMatrices
from jarray import array

matrices = [array((j+i for i in xrange(12)), 'd') for j in xrange(3)]

print matrices

saveMatrices("matrices", matrices, "/tmp/")

m = loadMatrices("matrices", "/tmp/")

print m