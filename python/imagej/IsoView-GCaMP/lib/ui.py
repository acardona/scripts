from net.imglib2.img.display.imagej import ImageJFunctions as IL
from net.imglib2.view import Views
from net.imglib2 import FinalInterval
from net.imglib2.util import ImgUtil
from bdv.util import BdvFunctions, Bdv
from ij import ImagePlus, CompositeImage, VirtualStack
from java.awt.event import KeyAdapter, KeyEvent
from lib.util import syncPrintQ, printException
from lib.converter import createConverter, convert
from net.imglib2.img.array import ArrayImgs
from ij.process import FloatProcessor
from net.imglib2.type.numeric.real import FloatType
from ij import IJ


def wrap(img, title="", n_channels=1):
  """ Like ImageJFunctions.wrap but, when n_channels=1 (the default),
      then a new dimension of size 1 is inserted at position 2 to prevent the Z axis
      from showing as the channels axis.
      To enable ImageJFunctions.wrap default behavior, set n_channels to a value other than 1. """
  if 1 == n_channels:
    # Append a dimension of size 1 at the end
    # and permute it iteratively so that it becomes the channels dimension (d=2)
    img = Views.addDimension(img, 1, 1)
    d = img.numDimensions() -1 # starts with the last: the new one of size 1
    while d > 2:
      img = Views.permute(img, d, d -1)
      d -= 1
  #
  return IL.wrap(img, title)
  

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


class ViewFloatProcessor(FloatProcessor):
  """
  A 2D FloatProcessor whose float[] pixel array is populated from the pixels within
  an interval on a source 3D RandomAccessibleInterval at a specified indexZ (the section index).
  The interval and indexZ are editable via the translate method.
  """
  def __init__(self, img3D, interval2D, indexZ):
    self.img3D = img3D
    self.interval2D = interval2D
    self.indexZ = indexZ
    super(FloatProcessor, self).__init__(interval2D.dimension(0), interval2D.dimension(1))
    self.updatePixels()
    
  def translate(self, dx, dy, dz):
    # Z within bounds
    self.indexZ += dz
    self.indexZ = min(self.img3D.dimension(2) -1, max(0, self.indexZ))
    # X, Y can be beyond bounds
    self.interval2D = FinalInterval([self.interval2D.min(0) + dx,
                                     self.interval2D.min(1) + dy],
                                    [self.interval2D.max(0) + dx,
                                     self.interval2D.max(1) + dy])
    self.updatePixels()
    return self.interval2D.min(0), self.interval2D.min(1), self.indexZ
  
  def updatePixels(self):
    # Copy interval into pixels
    view = Views.interval(Views.extendZero(Views.hyperSlice(self.img3D, 2, self.indexZ)), self.interval2D)
    aimg = ArrayImgs.floats(self.getPixels(), [self.interval2D.dimension(0), self.interval2D.dimension(1)])
    ImgUtil.copy(view, aimg)


class SourceNavigation(KeyAdapter):
  def __init__(self, translatable, imp, shift=100, alt=10):
    """
      translatable: an object that has a "translate" method with 3 coordinates as arguments
      imp: the ImagePlus to update
      shift: defaults to 100, when the shift key is down, move by 100 pixels
      alt: defaults to 10, when the alt key is down, move by 10 pixels
      If both shift and alt are down, move by shift*alt = 1000 pixels by default.
    """
    self.translatable = translatable
    self.delta = {KeyEvent.VK_UP: (0, -1, 0),
                  KeyEvent.VK_DOWN: (0, 1, 0),
                  KeyEvent.VK_RIGHT: (1, 0, 0),
                  KeyEvent.VK_LEFT: (-1, 0, 0),
                  KeyEvent.VK_COMMA: (0, 0, -1),
                  KeyEvent.VK_PERIOD: (0, 0, 1),
                  KeyEvent.VK_LESS: (0, 0, -1),
                  KeyEvent.VK_GREATER: (0, 0, 1),
                  KeyEvent.VK_PAGE_DOWN: (0, 0, -1),
                  KeyEvent.VK_PAGE_UP: (0, 0, 1)}
    self.shift = shift
    self.alt = alt
    self.imp = imp
  
  def keyPressed(self, event):
    try:
      dx, dy, dz = self.delta.get(event.getKeyCode(), (0, 0, 0))
      if dx + dy + dz == 0:
        return
      syncPrintQ("Translating source")
      if event.isShiftDown():
        dx *= self.shift
        dy *= self.shift
        dz *= self.shift
      if event.isAltDown():
        dx *= self.alt
        dy *= self.alt
        dz *= self.alt
      syncPrintQ("... by x=%i, y=%i, z=%i" % (dx, dy, dz))
      x, y, z = self.translatable.translate(dx, dy, dz)
      IJ.showStatus("[x=%i y=%i z=%i]" % (x, y, z+1)) # 1-based stack index
      self.imp.updateAndDraw()
      event.consume()
    except:
      printException()
    

def navigate2DROI(img, interval, indexZ=0, title="ROI"):
  """
     Use a FloatProcessor to visualize a 2D slice of a 3D image of any pixel type.
     Internally, uses a ViewFloatProcessor with an editable Interval.
     Here, a SourceNavigation (a KeyListener) enables editing the Interval
     and therefore the FloatProcessor merely shows that interval of the source img.
     
     img: the source 3D RandomAccessibleInterval.
     interval: the initial interval of img to view. Must be smaller than 2 GB.
     indexZ: the initial Z index to show.
     title: the name to give the ImagePlus.
  """
  img = convert(img, FloatType)
  vsp = ViewFloatProcessor(img, interval, indexZ)
  imp = ImagePlus(title, vsp)
  imp.show()
  canvas = imp.getWindow().getCanvas()
  # Place the SourceNavigation KeyListener at the top of the list of KeyListener instances
  kls = canvas.getKeyListeners()
  for kl in kls:
    canvas.removeKeyListener(kl)
  canvas.addKeyListener(SourceNavigation(vsp, imp))
  for kl in kls:
    canvas.addKeyListener(kl)
  return imp

   















