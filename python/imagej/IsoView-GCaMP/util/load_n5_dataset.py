import sys
sys.path.append("/home/albert/lab/scripts/python/imagej/IsoView-GCaMP/")
from lib.io import readN5

n5dir = "/home/albert/shares/cardonalab/Albert/2017-05-10_1018/deconvolved/n5"

#dataset_name = "2017-5-10_1018_0-399_fullXY_25sections"
dataset_name = "2017-5-10_1018_0-399_X203_Y155_Z65"

img = readN5(n5dir, dataset_name, show="IJ")
#img = readN5(n5dir, dataset_name, show="BDV")
