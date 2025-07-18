from __future__ import with_statement
import sys, os
sys.path.append("/lmb/home/acardona/lab/scripts/python/imagej/IsoView-GCaMP/")

from lib.features import PointMatches

path = "/net/zstore1/FIBSEM/MR1.4-3/registration/csvZ/Merlin-WEMS_24-02-22_074319_.Merlin-WEMS_24-02-22_074601_.pointmatches.csv"

pointmatches = PointMatches.fromPath(path).pointmatches

for pm in pointmatches:
  print pm.getP1().getW(), pm.getP2().getW()