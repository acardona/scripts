from ij import IJ, ImagePlus, VirtualStack

imp = IJ.getImage()
roi = imp.getRoi()
stack = imp.getStack()

class CroppedStack(VirtualStack):
  def __init__(self):
    super(VirtualStack, self).__init__(stack.getWidth(), stack.getHeight(), stack.size())

  def getProcessor(self, n):
    ip = stack.getProcessor(n)
    ip.setRoi(roi)
    return ip.crop()

cropped = ImagePlus("cropped", CroppedStack())
cropped.show()