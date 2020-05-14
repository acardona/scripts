from net.imglib2.img.display.imagej import ImageJFunctions as IL
from net.imglib2.view import Views
import sys, os
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(sys.argv[0])), "IsoView-GCaMP"))
from lib.io import parse_TIFF_IFDs, read_TIFF_plane, lazyCachedCellImg, TIFFSlices


filepath =  "/home/albert/Desktop/t2/bat-cochlea-volume.compressed-packbits.tif"

# The whole TIFF file as one Cell per slice, independently loadable
slices = TIFFSlices(filepath)
imgLazyTIFF = slices.asLazyCachedCellImg()

# The whole file
#imp = IL.wrap(imgTIFF, os.path.basename(filepath))
#imp.show()

width, height, _ = slices.cell_dimensions

# Pick only from slices 3 to 6
view_3_to_6 = Views.interval(imgLazyTIFF, [0, 0, 0],
                                          [width -1, height -1, 5])
imp_3_to_6 = IL.wrap(view_3_to_6, "3 to 6")
imp_3_to_6.show()

# Pick only every 3rd slice
#view_every_3 = Views.subsample(imgTIFF, [1, 1, 3])
#imp_every_3 = IL.wrap(view_every_3, "every 3")
#imp_every_3.show()
