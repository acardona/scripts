from net.imglib2.algorithm.math import ImgMath
from net.imglib2.img.array import ArrayImgs
from net.imglib2.view import Views
from net.imglib2.img.cell import CellImg, CellGrid
from net.imglib2.img.display.imagej import ImageJFunctions as IL
from net.imglib2.util import Intervals
from net.imglib2.cache.ref import SoftRefLoaderCache, BoundedSoftRefLoaderCache
from net.imglib2.cache.img import CellLoader, CachedCellImg, ReadOnlyCachedCellImgFactory, ReadOnlyCachedCellImgOptions
from net.imglib2.img.basictypeaccess import ArrayDataAccessFactory, AccessFlags
from lib.ui import addWindowListener
from functools import partial


def makeImg(filepaths, pixelType, loadImg, img_dimensions, matrices, cropInterval, preload):
  """ Note that when preload > 0, the returned CellLoader will have created an ExecutorService
      that can be shutdown by invoking destroy() on it.
  """
  dims = Intervals.dimensionsAsLongArray(cropInterval)
  voldims = [dims[0],
             dims[1],
             len(filepaths)]
  cell_dimensions = [dims[0],
                     dims[1],
                     1]
  grid = CellGrid(voldims, cell_dimensions)
  
  # Old approach:
  #cellGet = TranslatedSectionGet(filepaths, loadImg, matrices, img_dimensions, cell_dimensions,
  #                               cropInterval, preload=preload)
  #return LazyCellImg(grid, pixelType(), cellGet), cellGet

  # New approach: delegate the cache entirely to ImgLib2
  cell_loader = CellLoader(filepaths, loadImg, matrices,
                           img_dimensions, cell_dimensions,
                           cropInterval)
  # Create the cache, which can load any Cell when needed using CellLoader
  loading_cache = SoftRefLoaderCache().withLoader(cell_loader).unchecked()
  # Create a CachedCellImg: a LazyCellImg that caches Cell instances with a SoftReference, for best performance
  # and also self-regulating regarding the amount of memory to allocate to the cache.
  cachedCellImg = ReadOnlyCachedCellImgFactory().createWithCacheLoader(
                    voldims, pixelType(), loading_cache,
                    ReadOnlyCachedCellImgOptions.options().volatileAccesses(True).cellDimensions(cell_dimensions))
  cell_loader.setCache(cachedCellImg, preload)
  return cachedCellImg, cell_loader


def showAlignedImg(img, cropInterval, groupNames, properties, matrices, rotate=None, title_addendum=""):
  """
  rotate: "right" or "left" or "180" or None
  """
  # Show the volume using ImgLib2 interpretation of matrices, with subpixel alignment
  def loadImg(img, index):
    if isinstance(img, CellImg):
      cell = img.getCells().randomAccess().setPositionAndGet([0, 0, index])
      pixels = cell.getData().getCurrentStorageArray()
      return ArrayImgs.unsignedBytes(pixels, [img.dimension(0), img.dimension(1)])
    else:
      img2d = Views.hyperSlice(img, 2, index)
      aimg = ArrayImgs.unsignedBytes(Intervals.dimensionsAsLongArray(img2d))
      ImgMath.compute(ImgMath.img(img2d)).into(aimg)
      return aimg
      
  
  cellImg, cellGet = makeImg(range(len(groupNames)), properties["pixelType"],
                             partial(loadImg, img), properties["img_dimensions"],
                             matrices, cropInterval, properties.get('preload', 0))


  if "right" == rotate or "left" == rotate:
    # By 90 or -90 degrees
    a, b = (0, 1) if "right" == rotate else (1, 0) # left
    img = Views.rotate(cellImg, a, b) # the 0 and 1 are the two axis (dimensions) of reference, e.g., pux X (the 0) into Y (the 1).
  elif "180" == rotate:
    # Rotate twice to the right
    img = Views.rotate(Views.rotate(cellImg, 0, 1), 0, 1)
  else:
    img = cellImg

  imp = IL.wrap(img, properties.get("name", "") + " aligned subpixel" + title_addendum)
  imp.show()
  # Ensure cleanup of threads upon closing the window
  addWindowListener(imp.getWindow(), lambda event: cellGet.destroy())
  
  return img, imp


def lazyCachedCellImg(loader, volume_dimensions, cell_dimensions, pixelType, primitiveType, maxRefs=0):
  """ Create a lazy CachedCellImg, backed by a SoftRefLoaderCache,
      which can be used to e.g. create the equivalent of ij.VirtualStack but with ImgLib2,
      with the added benefit of a cache based on SoftReference (i.e. no need to manage memory).

      loader: a CacheLoader that returns a single Cell for each index (like the Z index in a VirtualStack).
      volume_dimensions: a list of int or long numbers, with the last dimension
                         being the number of Cell instances (i.e. the number of file paths).
      cell_dimensions: a list of int or long numbers, whose last dimension is 1.
      pixelType: e.g. UnsignedByteType
      primitiveType: e.g. BYTE
      maxRefs: defaults to zero which means unbounded, that is, soft references may have been garbage collected
               but entries in the cache table are still around. When maxRefs larger > 0, then only that many references
               will be kept as entries by using a BoundedSoftRefLoaderCache.

      Returns a CachedCellImg.
  """
  cache = SoftRefLoaderCache() if 0 == maxRefs else BoundedSoftRefLoaderCache(maxRefs)
  return CachedCellImg(CellGrid(volume_dimensions, cell_dimensions),
                       pixelType(),
                       cache.withLoader(loader),
                       ArrayDataAccessFactory.get(primitiveType, AccessFlags.setOf(AccessFlags.VOLATILE)))
