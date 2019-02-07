import sys
sys.path.append("/home/albert/lab/scripts/python/imagej/IsoView-GCaMP/")
from lib.io import readN5
from lib.dogpeaks import createDoG
from lib.synthetic import virtualPointsRAI
from lib.ui import showStack
from net.imglib2 import RealPoint, FinalInterval


points = [RealPoint.wrap([255, 255, 255]),
          RealPoint.wrap([255, 255, 0]),
          RealPoint.wrap([128, 384, 128])]

rai = virtualPointsRAI(points, 70, FinalInterval([512, 512, 512]))
imp = showStack(rai, title="test virtualPointsRAI")
