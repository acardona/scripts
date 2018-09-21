from ij import IJ, ImagePlus
from net.imglib2.img.cell import LazyCellImg, CellGrid, Cell
from net.imglib2.img.display.imagej import ImageJFunctions as IL
from net.imglib2.view import Views
from net.imglib2.img.basictypeaccess import ByteAccess
from jarray import zeros
from net.imglib2.util import IntervalIndexer

imp = IJ.getImage()

class ProxyByteAccess(ByteAccess):
  def __init__(self, rai, grid):
    self.rai = rai
    self.ra = rai.randomAccess()
    #self.c = rai.cursor() # works, but can only be used once
    self.d = zeros(2, 'i')
  def getValue(self, index):
    #return self.c.next().getByte()
    self.d[0] = index % self.rai.dimension(0)
    self.d[1] = index / self.rai.dimension(0) # divide by width
    self.ra.setPosition(self.d)
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
  def __init__(self, imp, cell_padding, padding_color_value, grid):
    self.stack = imp.getStack()
    self.grid = grid
    self.cell_padding = cell_padding
    self.t = IL.wrap(imp).randomAccess().get().createVariable()
    self.t.setReal(padding_color_value)
    self.cache = {}

  def get(self, index):
    s = self.cache.get(index, None)
    if not s:
      s = self.create(index)
      self.cache[index] = s
    return s

  def create(self, index):
    cell_dimensions = [self.grid.cellDimension(0), self.grid.cellDimension(1)]
    n_cols = grid.imgDimension(0) / cell_dimensions[0]
    x0 = (index % n_cols) * cell_dimensions[0]
    y0 = (index / n_cols) * cell_dimensions[1]
    index += 1 # 1-based slice indices in ij.ImageStack
    if index < 1 or index > self.stack.size():
      # Return blank image: a ByteAccess that always returns 255
      return Cell(cell_dimensions,
                  [x0, y0],
                  type('ConstantValue', (ByteAccess,), {'getValue': lambda self, index: 255})())
    else:
      # ImageJ stack slice indices are 1-based
      img = IL.wrap(ImagePlus("", self.stack.getProcessor(index)))
      # Create extended image with the padding color value
      imgE = Views.extendValue(img, self.t.copy())
      # A view that includes the padding between slices
      minC = [-self.cell_padding for d in xrange(img.numDimensions())]
      maxC = [img.dimension(d) -1 + self.cell_padding for d in xrange(img.numDimensions())]
      imgP = Views.interval(imgE, minC, maxC)
      return Cell(cell_dimensions,
                  [x0, y0],
                  ProxyByteAccess(imgP, self.grid))


n_cols = 10
n_rows = 12
cell_padding = 5 # pixels, effective cell dimensions are 5+width+5, 5+height+5

cell_width = imp.getWidth() + cell_padding * 2
cell_height = imp.getHeight() + cell_padding * 2

grid = CellGrid([n_cols * cell_width, n_rows * cell_height],
                [cell_width, cell_height])

print grid # shows: CellGrid( dims = (1572, 1640), cellDims = (131, 164) )
print "numDim:", grid.numDimensions()
print "gridDim:", grid.getGridDimensions()
print "x, y", grid.gridDimension(0), grid.gridDimension(1)
print "imgDim:", grid.getImgDimensions()
print "cellDim", grid.cellDimension(0), grid.cellDimension(1)
cellMin = zeros(2, 'l')
cellDims = zeros(2, 'i')
grid.getCellDimensions(0, cellMin, cellDims)
print "cellDim 0", cellMin, cellDims
grid.getCellDimensions(5, cellMin, cellDims)
print "cellDim 5", cellMin, cellDims
grid.getCellDimensions(10, cellMin, cellDims)
print "cellDim 10", cellMin, cellDims
grid.getCellDimensions(20, cellMin, cellDims)
print "cellDim 20", cellMin, cellDims


# Padding color: 255 is white for 8-bit images
getter = MontageSlice(imp, cell_padding, 255, grid)

montage = LazyCellImg(grid, getter.t, getter)

IL.wrap(montage, "Montage").show()
