import sys
sys.path.append("/home/albert/lab/scripts/python/imagej/IsoView-GCaMP")
from lib.io import readFIBSEMdat
from net.imglib2.img.display.imagej import ImageJFunctions as IL

path = "/home/albert/ark/raw/fibsem/pygmy-squid/2021-12_popeye/Popeye2/Y2021/M12/D23/FIBdeSEMAna_21-12-23_235849_0-0-0.dat"

channels = readFIBSEMdat(path, channel_index=0)
print channels
IL.wrap(channels[0], "channel 1").show() # looks good
#IL.wrap(channels[1], "channel 2").show() # looks grainy, lots of shot noise
                                                                                                       
channels = readFIBSEMdat(path, channel_index=0, asImagePlus=True)
channels[0].show()