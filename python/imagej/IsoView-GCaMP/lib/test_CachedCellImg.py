import os, sys
sys.path.append("/home/albert/lab/scripts/python/imagej/IsoView-GCaMP/")
from lib.ui import showStack
from lib.io import SectionCellLoader, lazyCachedCellImg
from net.imglib2.type.numeric.integer import UnsignedShortType
from net.imglib2.img.array import ArrayImgs
from net.imglib2.type.PrimitiveType import BYTE
from net.imglib2.type.numeric.integer import UnsignedByteType
from mpicbg.ij.plugin import NormalizeLocalContrast
from functools import partial


srcDir = "/home/albert/Desktop/t2/189/section189-images/"
filepaths = [os.path.join(srcDir, filename) for filename in sorted(os.listdir(srcDir)) if filename.endswith(".tif")]

dims = [2048, 2048]
voldims = [dims[0],
           dims[1],
           len(filepaths)]
cell_dimensions = [dims[0],
                   dims[1],
                   1]

def asNormalizedUnsignedByteArrayImg(blockRadius, stds, center, stretch, imp):
  sp = imp.getProcessor() # ShortProcessor
  NormalizeLocalContrast().run(sp, blockRadius, blockRadius, stds, center, stretch)
  return ArrayImgs.unsignedBytes(sp.convertToByte(True).getPixels(), [sp.getWidth(), sp.getHeight()])


loader = SectionCellLoader(filepaths, asArrayImg=partial(asNormalizedUnsignedByteArrayImg, 400, 3, True, True))

cachedCellImg = lazyCachedCellImg(loader, voldims, cell_dimensions, UnsignedByteType, BYTE)

showStack(cachedCellImg)