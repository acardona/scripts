from sc.fiji.io import FIBSEM_Reader

#FIBSEM_Reader.openAsFloat = True

import sys
libDir = "/lmb/home/acardona/lab/scripts/python/imagej/IsoView-GCaMP/"
sys.path.append(libDir)

from lib.io import readFIBSEM

path = "/net/fibserver1/raw/Sam3G_90deg/Y2024/M11/D21/Merlin-FIBdeSEMAna_24-11-21_235932_0-0-0.dat"
        



imp = readFIBSEM(path, openAsFloat=True, channel_index=0, scale=False)
imp.show()