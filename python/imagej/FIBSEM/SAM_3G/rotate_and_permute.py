# Figure out a transform that would address the transpose and translation in Clayton's registration of the first block of SAM_3G


from net.imglib2.img.display.imagej import ImageJFunctions
from ij import IJ
from net.imglib2.view import Views
from net.imglib2 import FinalInterval
from net.imglib2.type.numeric.integer import UnsignedByteType


imp = IJ.getImage()
img = ImageJFunctions.wrap(imp)
#imgT = Views.permute(Views.rotate(img, 0, 1), 0, 1)

imgR = Views.rotate(Views.rotate(Views.permute(img, 0, 1), 0, 1), 0, 1)
print imgR.dimension(0), imgR.dimension(1)
ImageJFunctions.show(imgR, "permuted and rotated")
imgZ = Views.extendZero(Views.zeroMin(imgR))
imgTL = Views.translate(imgZ, [-719, 1450])
interval = FinalInterval([imgR.dimension(0), imgR.dimension(1)])
#imgI = Views.zeroMin(Views.interval(imgTL, [0, 0], [imgR.dimension(0) -1, imgR.dimension(1) -1]))
imgI = Views.zeroMin(Views.interval(imgTL, interval))

#imgI = Views.zeroMin(Views.interval(imgZ, [719, imgR.dimension(0) + 719 -1],
#                                          [-1450, imgR.dimension(1) - 1450 -1]))

ImageJFunctions.show(imgI, "translated")

# Missing a translation


# From SIFT registration of the last of Clayton's sections with the same section as the first of the rest:
# Estimated transformation model: [3,3](
# AffineTransform[[-7.582027255E-6, -0.999552274250916, 15684.299667911993],
#                 [-1.000222991420093, 1.52707645215E-4, 14279.663581950259]]) 1.5708477788629969

# Just with translation after rotate and permute:
# Estimated transformation model: [3,3](
# AffineTransform[[1.0, 0.0, 718.9789769496974],
#                 [0.0, 1.0, -1450.1128646590478]]) 2.3272415698225384