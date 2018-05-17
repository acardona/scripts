# Export an ImageStack from a range of TrakEM2 layers

from ini.trakem2.display import Display, Displayable
from ij import ImagePlus, ImageStack

# zero-based index:
index_first_section = 10
index_last_section = 20

magnification = 0.25

front = Display.getFront()
layerset = front.getLayerSet()
layers = layerset.getLayers().subList(index_first_section, index_last_section + 1)
loader = layerset.getProject().getLoader()

# Can be null
roi = front.getRoi()

# The whole 2D area, or just that of the ROI
bounds = roi.getBounds() if roi else layerset.get2DBounds()

stack = ImageStack(int(bounds.width * magnification + 0.5),
                   int(bounds.height * magnification + 0.5))
print stack

for layer in layers:
  imp = loader.getFlatImage(layer, bounds, magnification, -1, ImagePlus.GRAY8, Displayable, False)
  stack.addSlice(imp.getProcessor())

ImagePlus("stack", stack).show()