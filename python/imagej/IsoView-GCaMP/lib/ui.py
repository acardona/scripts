from net.imglib2.img.display.imagej import ImageJFunctions as IL, ImageJVirtualStackUnsignedShort
from net.imglib2.view import Views
from bdv.util import BdvFunctions, Bdv
from ij import ImagePlus, CompositeImage, VirtualStack


def wrap(img, title="", n_channels=1):
  """ Like ImageJFunctions.wrap but properly choosing the number of channels, slices and frames. """ 
  stack = ImageJVirtualStackUnsignedShort.wrap(img)
  imp = ImagePlus(title, stack)
  n = img.numDimensions()
  n_slices = img.dimension(2) / n_channels if n > 2 else 1
  n_frames = img.dimension(3) if n > 3 else 1
  imp.setDimensions(n_channels, n_slices, n_frames)
  return imp
  

def showAsStack(images, title=None, show=True):
  if not title:
    title = "Stack of %i images" % len(images)
  imp = wrap(Views.stack(images), title)
  if show:
    imp.show()
  return imp


def showInBDV(images, names=None, bdv=None):
  if not names:
    names = ["img%i" % i for i in xrange(len(images))]
  if not bdv:
    bdv = BdvFunctions.show(images[0], names[0])
    images, names = images[1:], names[1:]
  for img, name in izip(images, names):
    BdvFunctions.show(img, name, Bdv.options().addTo(bdv))
  #
  return bdv


def showStack(img, title="", proper=True, n_channels=1):
  # IL.wrap fails: shows slices as channels, and channels as frames
  if not proper:
    imp = IL.wrap(img, title)
    imp.show()
    return imp
  # Proper sorting of slices, channels and frames
  imp = wrap(img, title=title, n_channels=n_channels)
  comp = CompositeImage(imp, CompositeImage.GRAYSCALE if 1 == n_channels else CompositeImage.COLOR)
  comp.show()
  return comp


def showBDV(img, title="", bdv=None):
  if bdv:
    BdvFunctions.show(img, title, Bdv.options().addTo(bdv))
    return bdv
  return BdvFunctions.show(img, title)


class StacksAsChannels(VirtualStack):
  def __init__(self, stacks):
    super(VirtualStack, self).__init__(stacks[0].getWidth(), stacks[0].getHeight(),
                                       max(stack.size() for stack in stacks) * len(stacks))
    self.stacks = stacks # one per channel
  def getPixels(self, i):
    return getProcessor(i).getPixels()
  def getProcessor(self, i):
    channel = (i-1) % len(self.stacks)
    z = (i-1) / len(self.stacks)
    stack = self.stacks[channel]
    return stack.getProcessor(min(z + 1, stack.size()))
    
def showAsComposite(images, title="Composite", show=True):
  imps = []
  # Collect all images as ImagePlus, checking that they have the same XY dimensions.
  # (Z doesn't matter)
  dimensions = None
  for img in images:
    if isinstance(img, ImagePlus):
      imps.append(img)
    else:
      imps.append(IL.wrap(img, ""))
    if not dimensions:
      dimensions = [imps[-1].getWidth(), imps[-1].getHeight()]
    else:
      if imps[-1].width != dimensions[0] or imps[-1].getHeight() != dimensions[1]:
        print "asComposite: dimensions mistach."
        return
  imp = ImagePlus(title, StacksAsChannels([imp.getStack() for imp in imps]))
  imp.setDimensions(len(imps), max(imp.getStack().getSize() for imp in imps), 1)
  comp = CompositeImage(imp, CompositeImage.COMPOSITE)
  if show:
    comp.show()
  print imp.getNChannels(), imp.getNSlices(), imp.getNFrames(), "but imps: ", len(imps)
  return comp
  