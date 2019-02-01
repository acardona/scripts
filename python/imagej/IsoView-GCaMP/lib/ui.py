from net.imglib2.img.display.imagej import ImageJFunctions as IL
from net.imglib2.view import Views
from bdv.util import BdvFunctions, Bdv

def showAsStack(images, title=None, show=True):
  if not title:
    title = "Stack of %i images" % len(images)
  imp = IL.wrap(Views.stack(images), title)
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


def showStack(img, title=""):
  imp = IL.wrap(img, title)
  imp.show()
  return imp


def showBDV(img, title="", bdv=None):
  if bdv:
    BdvFunctions.show(img, title, Bdv.options().addTo(bdv))
    return bdv
  return BdvFunctions.show(img, title)
