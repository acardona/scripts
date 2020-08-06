from org.janelia.simview.klb import KLB
import os
from net.imglib2.img.display.imagej import ImageJFunctions as IL

SPMdir = "/home/albert/shares/zlaticlab/Nadine/Raghav/2017-05-10/GCaMP6s_1_20170510_115003.corrected/SPM00/"

klb = KLB.newInstance()

# Open 4 views of first time point
dir0 = SPMdir + "TM000000/"
paths = {filename: os.path.join(dir0, filename)
         for filename in os.listdir(dir0)
         if filename.endswith(".klb")}

for filename, path in paths.iteritems():
  img = klb.readFull(path)
  IL.wrap(filename, img).show()