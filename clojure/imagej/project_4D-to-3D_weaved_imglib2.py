# Albert Cardona 2017-11-15
# 
# A script to obtain the maximum intnesity projection, pixel-wise, of a 4D volume
# The 4D volume exists as a series of 3D stacks.
# The projection reduces the 4D volume to a single 3D stack, which is then shown
# as an ImageJ stack.
# 
# Due to a severe memory leak in the SCIFIO wrapper of KLB files,
# the KLB files are opened directly as unsigned 16-bit ImgLib2 files. This is also faster.
# 
# Assumptions:
# 1. All KLB stacks of the series have the same dimensions and pixel iteration order.
# 2. All KLB stacks are unsigned 16-bit.


import os
from ij.io import DirectoryChooser
from org.janelia.simview.klb import KLB
from net.imagej import ImgPlus
from net.imglib2 import Cursor
from net.imglib2.type.numeric.integer import UnsignedShortType
from fiji.scripting import Weaver
from java.lang import Math
from net.imglib2.img.display.imagej import ImageJFunctions as IJF


def run():
  # Ask for a folder containing all the time points, one per folder
  #dc = DirectoryChooser("Choose folder")
  #folder = dc.getDirectory()
  #folder = '/run/user/52828/gvfs/smb-share:server=keller-s7,share=microscopy1/SV3/RC_17-10-31/GCaMP6s_2_20171031_145624.corrected/SPM00'
  folder = "/home/albert/shares/zlaticlab/Nadine/Raghav/2017-05-10/GCaMP6s_1_20170510_115003.corrected/dff_on_fused/from_Raghav/MVD_Results/"
  print folder

  if not folder:
    return

  # Find the list of directories in that folder, and pick
  # one single file inside each, ending in:
  ending = "CM00_CHN00.klb"

  #DEBUGGING
  num_timepoints = 100

  java = Weaver.method("""
    static public final void maxer(final KLB klb, final ImgPlus target, final String path) throws java.io.IOException {
      Cursor c1 = target.cursor();
      Cursor c2 = klb.readFull(path).cursor();
      while (c1.hasNext()) {
        c1.next();
        c2.next();
        UnsignedShortType s1 = (UnsignedShortType) c1.get();
        UnsignedShortType s2 = (UnsignedShortType) c2.get();
        s1.set( (short) Math.max( s1.get(), s2.get() ) );
      }
  }
  """, [KLB, ImgPlus, Cursor, UnsignedShortType])

  max_img = None

  klb = KLB.newInstance()

  counter = 0

  for root, dirs, files in os.walk(folder):
    for filename in files:
      if filename.endswith(ending):
        counter += 1
        path = os.path.join(root, filename)
        print counter, path
  
        # Use the first opened stack as the image stack into which to accumulate max values
        if max_img is None:
          max_img = klb.readFull(path)
        else:
          java.maxer(klb, max_img, path)

      num_timepoints -= 1
      if num_timepoints < 0:
        break
  
  # DONE
  IJF.show(max_img)

run()