from mpicbg.trakem2.transform import ExportUnsignedByte
from ini.trakem2 import Project
from ini.trakem2.display import Display
from ij import ImagePlus

project = Project.getProjects()[0]
layers = project.getRootLayerSet().getLayers()
bounds = Display.getFront().getRoi().getBounds()

pair = ExportUnsignedByte.makeFlatImageFromMipMaps(layers[1].getDisplayables(), bounds, 0, 1.0)

bp = pair.a
mask = pair.b

ImagePlus("bp", bp).show()
ImagePlus("mask", mask).show()
