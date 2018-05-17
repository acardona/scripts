
import os
from ij.io import DirectoryChooser
from ij import IJ, ImagePlus, ImageStack
from ij.process import ImageProcessor
from fiji.scripting import Weaver
from java.lang import Math


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
    static public final void maxer(final ImagePlus target, final String path) {
      ImagePlus imp = IJ.openImage(path);
      ImageStack stack1 = target.getStack();
      ImageStack stack2 = imp.getStack();
      ImageProcessor ip1, ip2;
      for (int i=0; i < stack1.getSize(); ++i) {
        ip1 = stack1.getProcessor(i+1);
        ip2 = stack2.getProcessor(i+1);
        final int count = ip1.getWidth() * ip1.getHeight();
        for (int k=0; k<count; ++k) {
          ip1.setf(k, Math.max( ip1.getf(k),
                                ip2.getf(k) ) );
        }
      }
      stack1 = null;
      stack2 = null;
      imp.setIgnoreFlush(false);
      imp.unlock();
      imp.flush();
      imp = null;
  }
  """, [IJ, ImagePlus, ImageStack, ImageProcessor, Math])

  max_imp = None

  counter = 0

  for root, dirs, files in os.walk(folder):
    for filename in files:
      if filename.endswith(ending):
        counter += 1
        path = os.path.join(root, filename)
        print counter, path
        
  
        # Use the first opened stack as the image stack into which to accumulate max values
        if max_imp is None:
          max_imp = IJ.openImage(path)
        else:
          java.maxer(max_imp, path)

      num_timepoints -= 1
      if num_timepoints < 0:
        break
  
  # DONE
  max_imp.show()

run()