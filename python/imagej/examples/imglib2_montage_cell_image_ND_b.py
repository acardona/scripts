from ij import IJ, ImagePlus
from net.imglib2.img.cell import LazyCellImg, CellGrid, Cell
from net.imglib2.img.display.imagej import ImageJFunctions as IL
from net.imglib2.view import Views
from net.imglib2.img.basictypeaccess import ByteAccess
from jarray import zeros
from net.imglib2.util.IntervalIndexer import indexToPosition, positionToIndex

imp = IJ.getImage()

class ProxyByteAccess(ByteAccess):
  def __init__(self, rai, grid):
    self.rai = rai
    self.ra = rai.randomAccess()
    #self.c = rai.cursor() # works, but can only be used once
    self.dimensions = zeros(rai.numDimensions(), 'l')
    rai.dimensions(self.dimensions)
    self.position = zeros(rai.numDimensions(), 'l')
  def getValue(self, index):
    #return self.c.next().getByte()
    indexToPosition(index, self.dimensions, self.position)
    self.ra.setPosition(self.position)
    return self.ra.get().getByte()
  def setValue(self, index, value):
    pass

class ConstantValue(ByteAccess):
  def __init__(self, value):
    self.value = value
  def getValue(self, index):
    return self.value
  def setValue(self, index, value):
    pass

class MontageSlice(LazyCellImg.Get):
  def __init__(self, img, cell_padding, padding_color_value, grid):
    self.img = img
    self.grid = grid
    self.last_dimension = img.numDimensions() -1
    self.gridDimensions = grid.getGridDimensions()
    self.cell_padding = cell_padding
    self.t = IL.wrap(imp).randomAccess().get().createVariable()
    self.t.setReal(padding_color_value)
    self.cache = {}
    self.cell_dimensions = [self.grid.cellDimension(d) for d in xrange(self.grid.numDimensions())]
    self.position = zeros(len(self.gridDimensions), 'l')

  def get(self, index):
    s = self.cache.get(index, None)
    if not s:
      s = self.create(index)
      self.cache[index] = s
    return s

  def create(self, index):
    indexToPosition(index, self.gridDimensions, self.position)
    c = [p * self.grid.cellDimension(d) for d, p in enumerate(self.position)]
    if index < 0 or c[0] * c[1] > self.last_dimension:
      # Return blank image: a ByteAccess that always returns 255
      return Cell(self.cell_dimensions,
                  c,
                  type('ConstantValue', (ByteAccess,), {'getValue': lambda self, index: 255})())
    else:
      i = c[-1] - c[-1] * (self.gridDimensions[0] * self.gridDimensions[1] - self.img.dimension(self.last_dimension)) + positionToIndex(c[:2], self.gridDimensions[:2])
      img = Views.hyperSlice(self.img, self.last_dimension, i)
      # Create extended image with the padding color value
      imgE = Views.extendValue(img, self.t.copy())
      # A view that includes the padding between slices
      minC = [-self.cell_padding[d] for d in xrange(img.numDimensions())]
      maxC = [img.dimension(d) -1 + self.cell_padding[d] for d in xrange(img.numDimensions())]
      imgP = Views.interval(imgE, minC, maxC)
      return Cell(self.cell_dimensions,
                  c,
                  ProxyByteAccess(imgP, self.grid))


n_cols = 2
n_rows = 2
n_z = 114
cell_padding = [5, 5, 0] # pixels, effective cell dimensions are 5+width+5, 5+height+5

cell_width = imp.getWidth() + cell_padding[0] * 2
cell_height = imp.getHeight() + cell_padding[1] * 2

grid = CellGrid([n_cols * cell_width, n_rows * cell_height, n_z * 1],
                [cell_width, cell_height, 1])

print grid # shows: CellGrid( dims = (1572, 1640), cellDims = (131, 164) )
print "numDim:", grid.numDimensions()
print "gridDim:", grid.getGridDimensions()
print "x, y", grid.gridDimension(0), grid.gridDimension(1)
print "imgDim:", grid.getImgDimensions()
print "cellDim", grid.cellDimension(0), grid.cellDimension(1)
cellMin = zeros(3, 'l')
cellDims = zeros(3, 'i')
grid.getCellDimensions(0, cellMin, cellDims)
print "cellDim 0", cellMin, cellDims
grid.getCellDimensions(5, cellMin, cellDims)
print "cellDim 5", cellMin, cellDims
grid.getCellDimensions(10, cellMin, cellDims)
print "cellDim 10", cellMin, cellDims
grid.getCellDimensions(20, cellMin, cellDims)
print "cellDim 20", cellMin, cellDims

img = IL.wrap(imp)
print img.numDimensions()
img = Views.dropSingletonDimensions(img) # e.g. a channels dimension of size 1
# Swap Z axis with T axis
img = Views.permute(img, 2, 3)

# Padding color: 255 is white for 8-bit images
getter = MontageSlice(img, cell_padding, 255, grid)

montage = LazyCellImg(grid, getter.t, getter)

IL.wrap(montage, "Montage").show()
