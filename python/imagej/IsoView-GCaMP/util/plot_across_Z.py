from ij import IJ
import sys
sys.path.append("/home/albert/lab/scripts/python/imagej/IsoView-GCaMP/")
from lib.plot import plot2DRoiOverZ as plot

imp3D = IJ.getImage()

plot(imp3D, YaxisLabel="Fluorescence intensity", XaxisLabel="Time (seconds)", Zscale=0.75)