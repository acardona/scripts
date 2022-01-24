from net.imglib2.img.cell import CellGrid, Cell
from net.imglib2.cache import CacheLoader
from net.imglib2.cache.ref import SoftRefLoaderCache
from net.imglib2.cache.img import CachedCellImg, ReadOnlyCachedCellImgFactory, ReadOnlyCachedCellImgOptions
from net.imglib2.img.basictypeaccess.volatiles.array import VolatileByteArray, VolatileShortArray,\
                                                            VolatileFloatArray, VolatileLongArray
from net.imglib2.type.numeric.integer import UnsignedByteType, UnsignedShortType, UnsignedLongType
from net.imglib2.type.numeric.real import FloatType
from java.nio import ByteBuffer, ByteOrder
from java.io import RandomAccessFile
from jarray import zeros
import os, sys
from net.imglib2.img.display.imagej import ImageJFunctions as IL

# The path to the folder with the serial sections,
# each stored as a single raw 8-bit image
folderpath = "/home/albert/lab/TEM/L3/microvolume/17-sections-raw/"

# The dimensions and pixel depth of each serial section
section_width, section_height = 2560, 1225
bytesPerPixel = 1 # 8-bit pixels

# One file per serial section
filepaths = [os.path.join(folderpath, filename)
             for filename in sorted(os.listdir(folderpath))]

# Desired dimensions for reading in chunks of a single section
#cell_width, cell_height = 1024, 1024 # one megabyte
cell_width, cell_height = 256, 256

# Each Cell is a chunk of a single section, hence 3rd dimension is 1 
cell_dimensions = [cell_width, cell_height, 1]

# Volume dimensions
dimensions = [section_width, section_height, len(filepaths)]

# The grid of the CellImg
grid = CellGrid(dimensions, cell_dimensions)


def createAccess(bytes, bytesPerPixel):
  """ Return a new volatile access instance for the appropriate pixel type.
      Supports byte, short, float and long. """
  if 1 == bytesPerPixel: # BYTE
    return VolatileByteArray(bytes, True)
  # Transform bytes into another type
  bb = ByteBuffer.wrap(bytes).order(ByteOrder.BIG_ENDIAN)
  if 2 == bytesPerPixel: # SHORT
    pixels = zeros(len(bytes) / 2, 's')
    bb.asShortBuffer().get(pixels)
    return VolatileShortArray(pixels, True)
  if 4 == bytesPerPixel: # FLOAT
    pixels = zeros(len(bytes) / 4, 'f')
    bb.asFloatBuffer().get(pixels)
    return VolatileFloatArray(pixels, True)
  if 8 == bytesPerPixel: # LONG
    pixels = zeros(len(bytes) / 8, 'l')
    bb.asLongBuffer().get(pixels)
    return VolatileLongArray(pixels, True)

"""
def createAccess(bytes, bytesPerPixel):
  if 1 == bytesPerPixel:
    return VolatileByteArray(bytes, True)
  # Else, convert
  t = {2: "Short",
       4: "Float",
       8: "Long"}[bytesPerPixel]
  bb = ByteBuffer.wrap(bytes).order(ByteOrder.BIG_ENDIAN)
  pixels = zeros(len(bytes) / bytesPerPixel, t[0].lower()) # t[0].lower() is 's', 'f', 'l'
  getattr(bb, "as%sBuffer" % t)().get(pixels) # e.g. bb.asShortBuffer().get(pixels)
  return locals()["Volatile%sArray" % t](pixels, True) # e.g. VolatileShortArray(pixels, True)
"""
    


def createType(bytesPerPixel):
  if 1:
    return UnsignedByteType()
  if 2:
    return UnsignedShortType()
  if 4:
    return FloatType()
  if 8:
    return UnsignedLongType()



# A class to load each Cell
class CellLoader(CacheLoader):
  def get(self, index):
    ra = None
    try:
      # Read cell origin and dimensions for cell at index
      cellMin  = zeros(3, 'l') # long[3]
      cellDims = zeros(3, 'i') # integer[3]
      grid.getCellDimensions(index, cellMin, cellDims)
      # Unpack Cell origin (in pixel coordinates)
      x, y, z = cellMin
      # Unpack Cell dimensions: at margins, may be smaller than cell_width, cell_height
      width, height, _ = cellDims # ignore depth: it's 1
      # Read cell from file into a byte array
      ra = RandomAccessFile(filepaths[z], 'r')
      read_width = width * bytesPerPixel
      bytes = zeros(read_width * height, 'b') # will contain the entire Cell pixel data
      # Initial offset to the Cell origin
      offset = (section_width * y + x) * bytesPerPixel
      n_pixels = width * height
      if width == section_width:
        # Read whole block in one go: cell data is continuous in the file
        ra.seek(offset)
        ra.read(bytes, 0, n_pixels * bytesPerPixel)
      else:
        # Read line by line
        n_read = 0
        while n_read < n_pixels:
          ra.seek(offset)
          ra.read(bytes, n_read, read_width)
          n_read += read_width # ensure n_read advances in case file is truncated to avoid infinite loop
          offset += section_width * bytesPerPixel
      # Create a new Cell of the right pixel type
      return Cell(cellDims, cellMin, createAccess(bytes, bytesPerPixel))
    except:
      print sys.exc_info()
    finally:
      if ra:
        ra.close()

# Create the cache, which can load any Cell when needed using CellLoader
loading_cache = SoftRefLoaderCache().withLoader(CellLoader()).unchecked()
# Create a CachedCellImg: a LazyCellImg that caches Cell instances with a SoftReference, for best performance
# and also self-regulating regarding the amount of memory to allocate to the cache.
cachedCellImg = ReadOnlyCachedCellImgFactory().createWithCacheLoader(
                  dimensions, createType(bytesPerPixel), loading_cache,
                  ReadOnlyCachedCellImgOptions.options().volatileAccesses(True).cellDimensions(cell_dimensions))

# View the image as an ImageJ ImagePlus with an underlying VirtualStack
IL.wrap(cachedCellImg, "sections").show()


# Now show a UI that enables moving a window around a data set
from net.imglib2.view import Views
from net.imglib2 import FinalInterval
from jarray import array
from java.awt.event import KeyAdapter, KeyEvent
from net.imglib2.img.display.imagej import ImageJVirtualStack

mins = array([1307, 448, 0], 'l')
maxs = array([1307 + 976 -1, 448 + 732 -1, len(filepaths) -1], 'l')
imgE = Views.extendZero(cachedCellImg)
crop = Views.interval(imgE, FinalInterval(mins, maxs))
imp = IL.wrap(crop, "sections crop") # ImagePlus
imp.show()

# Once shown, a reference to the ij.gui.ImageWindow exists
win = imp.getWindow()

# Remove and store key listeners from the ImageCanvas
kls = win.getCanvas().getKeyListeners()
for kl in kls:
  win.getCanvas().removeKeyListener(kl)

stack = imp.getStack() # an net.imglib2.img.display.imagej.ImageJVirtualStackUnsignedByte
fsource = ImageJVirtualStack.getDeclaredField("source")
fsource.setAccessible(True)

class Navigator(KeyAdapter):
  moves = {KeyEvent.VK_UP:    (1, -1),
           KeyEvent.VK_DOWN:  (1,  1),
           KeyEvent.VK_LEFT:  (0, -1),
           KeyEvent.VK_RIGHT: (0,  1)}
  def keyPressed(self, ke):
    keyCode = ke.getKeyCode()
    if ke.isControlDown() and keyCode in Navigator.moves:
      d, sign = Navigator.moves[keyCode]
      inc = 200 if ke.isShiftDown() else 20
      mins[d] += sign * inc
      maxs[d] += sign * inc
      # Replace source with shifted cropped volume
      fsource.set(stack, Views.zeroMin(Views.interval(imgE, FinalInterval(mins, maxs))))
      imp.updateVirtualSlice()
      return
    # Else, pass the event onto other listeners
    for kl in kls:
      kl.keyPressed(ke)

win.getCanvas().addKeyListener(Navigator())

