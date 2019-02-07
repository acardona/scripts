from net.imglib2.img.display.imagej import ImageJFunctions as IL, ImageJVirtualStackUnsignedShort
from net.imglib2.view import Views
from bdv.util import BdvFunctions, Bdv
from ij import ImagePlus, CompositeImage


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
