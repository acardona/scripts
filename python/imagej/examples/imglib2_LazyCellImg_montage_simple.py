from ij import IJ, ImagePlus
from net.imglib2.img.cell import LazyCellImg, CellGrid, Cell
from net.imglib2.img.basictypeaccess.array import ByteArray
from net.imglib2.img.basictypeaccess import ByteAccess
from net.imglib2.img.display.imagej import ImageJFunctions as IL
from java.lang import System

imp = IJ.getImage()
img = IL.wrap(imp) # Creates PlanarImg instance with pointers to imp's slices

class SliceGet(LazyCellImg.Get):
  def __init__(self, imp, grid):
    self.imp = imp
    self.grid = grid
    self.cell_dimensions = [self.imp.getWidth(), self.imp.getHeight()]
    self.cache = {}
  def get(self, index):
    cell = self.cache.get(index, None)
    if not cell:
      cell = self.makeCell(index)
      self.cache[index] = cell
    return cell
  def makeCell(self, index):
    n_cols = self.grid.imgDimension(0) / self.grid.cellDimension(0)
    x0 = (index % n_cols) * self.grid.cellDimension(0)
    y0 = (index / n_cols) * self.grid.cellDimension(1)
    index += 1 # 1-based slice indices in ij.ImageStack
    if index < 1 or index > self.imp.getStack().size():
      # Return blank image: a ByteAccess that always returns 255
      return Cell(self.cell_dimensions,
                  [x0, y0],
                  type('ConstantValue', (ByteAccess,), {'getValue': lambda self, index: 255})())
    else:
      return Cell(self.cell_dimensions,
                  [x0, y0],
                  ByteArray(self.imp.getStack().getProcessor(index).getPixels()))

n_cols = 12
n_rows = 10
cell_width = imp.getWidth()
cell_height = imp.getHeight()

grid = CellGrid([n_cols * cell_width, n_rows * cell_height],
                [cell_width, cell_height])

montage = LazyCellImg(grid, img.cursor().next().createVariable(), SliceGet(imp, grid))

IL.show(montage, "Montage")