from ini.trakem2.display import Display
import MRCBZIP2

# Open image by decompressing first
patch = Display.getFrontLayer().getDisplayables().get(0)
imp = MRCBZIP2.decompress16bit(patch.getImageFilePath() + ".bz2")
imp.show()