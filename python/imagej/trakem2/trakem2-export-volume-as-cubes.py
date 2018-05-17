# Export as cubes of about 1 MB each for later inserting into N5

from ini.trakem2 import Project
from ini.trakem2.display import Patch
from ini.trakem2.utils import Utils
from ij import ImagePlus
from ij.io import FileSaver
from java.awt import Color, Rectangle
from java.awt.image import BufferedImage
from java.lang import Runnable, System
from java.util.concurrent import Executors
from java.awt.geom import AffineTransform
from java.awt import Graphics2D, Image, Graphics
from java.awt.image import ImageObserver
from java.lang.reflect import Method
import os
import sys
import traceback


target_dir = "/home/albert/shares/cardona_nearline/Albert/0111-8_whole_L1_CNS/cubes/"


p = Project.getProjects()[0]

# Bounds that enclose all visible Patch instances
max_bounds = p.getRootLayerSet().get2DBounds()

# Cube size should be about 1 MB, isotropic in world coordinates:
# 256 * 256 * 19 = 1245184, given 256 * 3.8 = 972.8 nm and 19 * 50 = 950 nm.

dimensions = (256, 256, 19) # IN PIXELS
cube_width, cube_height, cube_depth = dimensions

# Exclude first layer, which is empty
layers = p.getRootLayerSet().getLayers()[1:]
bounds = [layer.getMinimalBoundingBox(Patch, True) for layer in layers]

# For writing zero-padded file names
n_digits = len(str(max_bounds.width / dimensions[0])), \
                 len(str(max_bounds.height / dimensions[1])), \
                 len(str(len(layers)))

class CubeExporter(Runnable):
  def __init__(self, coords, dimensions, layers, bounds, target_dir, n_digits):
    self.dimensions = dimensions
    self.coords = coords
    self.layers = layers
    self.bounds = bounds
    self.target_dir = target_dir
    self.n_digits = n_digits
    
  def makeFilePath(self):
    x, y, k = self.coords
    xd, yd, kd = self.n_digits # for zero-padding
    xs, ys, ks = str(x).zfill(xd), str(y).zfill(yd), str(k).zfill(kd)
    return self.target_dir + "%s/%s/%s.zip" % (ks, ys, xs)

  def isEmpty(self):
     # Check if the cube would have any data
      x, y, k = self.coords
      width, height, n_layers = self.dimensions
      # Cube's field of view in XY
      fov = Rectangle(x, y, width, height)

      # Join the bounds of the layers
      r = None
      for b in self.bounds[k : min(k + n_layers, len(bounds))]:
        if r is None and b is not None: # can be none when the Layer is empty
          r = Rectangle(b.x, b.y, b.width, b.height)
        elif b is not None:
          r.add(b)
      
      # Return True if not intersecting
      return r is None or not fov.intersects(r)

  def run(self):
    try:
      filepath = self.makeFilePath()
      if os.path.exists(filepath):
        return
      
      x, y, k = self.coords
      width, height, n_layers = self.dimensions
      
      # Cube's field of view in XY
      fov = Rectangle(x, y, width, height)

      # Join the bounds of the layers
      r = None
      for b in self.bounds[k : min(k + n_layers, len(bounds))]:
        if r is None:
          r = Rectangle(b.x, b.y, b.width, b.height)
        else:
          r.add(b)

      if not fov.intersects(r):
        # Would be empty
        return

      drawImage = Graphics2D.getDeclaredMethod("drawImage", [Image, AffineTransform, ImageObserver])
      drawImage.setAccessible(True)
      dispose = Graphics.getDeclaredMethod("dispose", [])
      dispose.setAccessible(True)
    
      # Populate and write cube
      stack = ImageStack(width, height)
      for layer in self.layers[k : min(k + n_layers, len(self.layers))]:
        img = layer.getProject().getLoader().getFlatAWTImage(layer, fov, 1.0, -1, ImagePlus.GRAY8, Patch, None, False, Color.black)
        bi = BufferedImage(img.getWidth(None), img.getHeight(None), BufferedImage.TYPE_BYTE_GRAY)
        g = bi.createGraphics()
        aff = AffineTransform(1, 0, 0, 1, 0, 0)
       #g.drawImage(img, aff, None) # Necessary to bypass issues that result in only using 7-bits and with the ByteProcessor constructor
        drawImage.invoke(g, [img, aff, None])
        #g.dispose()
        dispose.invoke(g, [])
        g = None
        img = None
        stack.addSlice("", ByteProcessor(bi))
        bi.flush()
        bi = None

      imp = ImagePlus("x=%s y=%s k=%s" % (x, y, k), stack)
      Utils.ensure(filepath)
      FileSaver(imp).saveAsZip(filepath)
      imp.flush()
      imp = None
    except:
      e = sys.exc_info()
      System.out.println("Error:" + str(e[0]) +"\n" + str(e[1]) + "\n" + str(e[2]))
      System.out.println(traceback.format_exception(e[0], e[1], e[2]))

exporters = Executors.newFixedThreadPool(24)

print "Max bounds:", max_bounds

futures = []
count = 0

for k in xrange(0, len(layers), cube_depth):
  for x in xrange(max_bounds.x, max_bounds.x + max_bounds.width, cube_width):
    for y in xrange(max_bounds.y, max_bounds.y + max_bounds.height, cube_height):
      cube = CubeExporter((x, y, k), dimensions, layers, bounds, target_dir, n_digits)
      fu = exporters.submit(cube)
      count += 1 # 0 if cube.isEmpty() else 1
      if 0 == count % 1000:
        print "Completed:", count
      futures.append(fu)
      # after submitting 200, wait for the first 100 to complete
      if 200 == len(futures):
        Utils.waitIfAlive(futures[0:101], True)
        futures = futures[101:]

print "Max bounds:", max_bounds
print "Completed:", count