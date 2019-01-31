import os, sys
from ij import IJ, ImagePlus, VirtualStack
from loci.formats import ChannelSeparator

sourceDir = "/tmp/images-originals/"
targetDir = "/tmp/images-normalized/"


# Read the dimensions of the image at path by parsing the file header only,
# thanks to the LOCI Bioformats library
def dimensionsOf(path):
  fr = None
  try:
    fr = ChannelSeparator()
    fr.setGroupFiles(False)
    fr.setId(path)
    return fr.getSizeX(), fr.getSizeY()
  except:
    print sys.exc_info()
  finally:
    fr.close()


# A generator over all file paths in sourceDir
def tiffImageFilenames(directory):
  for filename in os.listdir(directory):
    if filename.lower().endswith(".tif"):
      yield filename


# Read the dimensions from the first image
first_path = os.path.join(sourceDir, tiffImageFilenames(sourceDir).next())
width, height = dimensionsOf(first_path)

# Create the VirtualStack without a specific ColorModel
# (which will be set much later upon loading any slice)
vstack = VirtualStack(width, height, None, sourceDir)

# Add all TIFF images in sourceDir as slices in vstack
for filename in tiffImageFilenames(sourceDir):
  vstack.addSlice(filename)

# Visualize the VirtualStack
imp = ImagePlus("virtual stack of images in " + os.path.basename(sourceDir), vstack)
imp.show()


from mpicbg.ij.plugin import NormalizeLocalContrast
from ij.io import FileSaver

# Process and save every slice
for i in xrange(0, vstack.size()):
  ip = vstack.getProcessor(i+1) # 1-based listing of slices
  # Run the NormalizeLocalConstrast plugin on the ImageProcessor
  NormalizeLocalContrast.run(ip, 200, 200, 3, True, True)
  # Store the result
  name = vstack.getFileName(i+1)
  if not name.lower().endswith(".tif"):
    name += ".tif"
  FileSaver(ImagePlus(name, ip)).saveAsTiff(os.path.join(targetDir, name))
