from ij3d import Image3DUniverse
from ij import IJ

univ = Image3DUniverse()
univ.show()

hyperstackImp = IJ.getImage()
univ.addVoltex(hyperstackImp)

tl = univ.getTimeline()