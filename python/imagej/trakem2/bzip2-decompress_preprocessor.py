# Preprocessor script to cope with bzip2-compressed MRC files
# when the XMLfile of TrakEM2 specifies uncompressed MRCfiles.
#
# Variables imp and patch exist

import MRCBZIP2
from ij import ImagePlus

imp2 = MRCBZIP2.decompress16bit(patch.getImageFilePath() + ".bz2")

print "imp2: ", imp2

imp.setProcessor(imp2.getTitle(), imp2.getProcessor())

print "imp after: ", imp

#ImagePlus(imp.getTitle(), imp.getProcessor().duplicate()).show()
