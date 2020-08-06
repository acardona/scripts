from net.imglib2.algorithm.math.ImgMath import compute, gen
from net.imglib2.img.display.imagej import ImageJFunctions as IL
from net.imglib2.type.numeric.integer import UnsignedByteType
from net.imglib2.img.array import ArrayImgs
from net.imglib2.util import Intervals
from net.imglib2 import KDTree, Point

locations = [(10,15), (25, 40), (30, 75), (80, 60)]


points = [Point.wrap([x, y]) for x, y in [(10,15), (25, 40), (30, 75), (80, 60)]]
values = [UnsignedByteType(v) for v in [128, 164, 200, 255]]

kt = KDTree(values, points)
dimensions = [100, 100]

op = gen(kt, 10)
target = ArrayImgs.unsignedBytes(Intervals.dimensionsAsLongArray(op.getInterval()))
compute(op).into(target)

IL.wrap(target, "KDTree").show()
