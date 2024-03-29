from java.util import ArrayList
from ij.gui import Line, Overlay, Arrow
from mpicbg.models import TransformMesh, PointMatch, Tile, TranslationModel2D, TileConfiguration, ErrorStatistic
from jarray import array, zeros
from java.lang.reflect.Array import newInstance as newArray
from java.lang import Double
from ij import IJ, ImagePlus, ImageStack
from mpicbg.ij.blockmatching import BlockMatching
from ij.process import ImageProcessor, ShortProcessor
from jitk.spline import ThinPlateR2LogRSplineKernelTransform
from mpicbg.ij import ThinPlateSplineMapping


# Extract blockmatches between two images
# and then estimate an elastic transformation
# Albert Cardona 2023-04-06 at ESRF Grenoble


def extractBlockMatches(
      imp1, # reference image.
      imp2, # moving image.
      scale, # float; between 0 and 1; to speed up if images are very large.
      meshResolution, # integer; number of points on the side of the grid, e.g., 10 means 10x10 = 100 points.
      blockRadius, # integer; size of side of the square block used for cross-correlation.
      searchRadius, # integer; maximum distance from each grid point to run cross-correlations at.
      minR, # float; minimum cross-correlation regression value to accept, discard otherwise. It's the PMCC (Pearson product-moment correlation coefficient)
      rod, # float; ratio of best to second-best cross-correlation scores; discard if lower.
      maxCurvature): # float; default is 10, we use 1000 for TEM image tile registration.

  # Define points from the mesh
  sourcePoints = ArrayList()
  # List to fill
  sourceMatches = ArrayList() # of PointMatch from imp1 to imp2

  mesh = TransformMesh(meshResolution, imp1.getWidth(), imp2.getHeight())
  PointMatch.sourcePoints(mesh.getVA().keySet(), sourcePoints)
  
  BlockMatching.matchByMaximalPMCCFromPreScaledImages(
              imp1.getProcessor().convertToFloat(), # no copy if it's already 32-bit
              imp2.getProcessor().convertToFloat(), # no copy if it's already 32-bit
              scale, # float
              blockRadius, # X
              blockRadius, # Y
              searchRadius, # X
              searchRadius, # Y
              minR, # float
              rod, # float
              maxCurvature, # float
              sourcePoints,
              sourceMatches)
  
  return sourceMatches
  

def showDisplacementVectors(imp2, sourceMatches):
  # Show displacement field as an Overlay
  overlay = Overlay() # Set of Line ROI instances, each depicting a displacement vector
  for pm in sourceMatches:
    p1 = pm.getP1().getW() # a double[] array
    p2 = pm.getP2().getW() # a double[] array
    overlay.add(Line(p1[0], p1[1], p2[0], p2[1]))
  
  imp2copy = imp2.duplicate()
  imp2copy.setTitle("Displacement vectors over 2nd image")
  imp2copy.setOverlay(overlay)
  imp2copy.show()


def computeLinearTransform(
         sourceMatches,
         modelClass, # Can be: TranslationModel2D, RigidModel2D, SimilarityModel2D, AffineModel2D
         maxAllowedError,
         maxPlateauWidth,
         maxIterations,
         damp):
  """
  Returns the affine transform matrix for the second, moving image.
  """
  # Estimate a transformation
  tile1 = Tile(modelClass())
  tile2 = Tile(modelClass())
  tile1.connect(tile2, sourceMatches) # reciprocal connection
  tc = TileConfiguration()
  tc.addTiles([tile1, tile2])
  tc.fixTile(tile1) # only tile2 will move
  tc.optimizeSilentlyConcurrent(ErrorStatistic(maxPlateauwidth + 1), maxAllowedError,
                                maxIterations, maxPlateauwidth, damp)
  a = zeros(6, 'd')
  tile2.getModel().toArray(a)
  affine_matrix = array([a[0], a[2], a[4], a[1], a[3], a[5]], 'd')
  return affine_matrix
  

def computeElasticTransform(pointmatches):
  # Format pointmatches into two separate lists
  sourcePoints = newArray(Double.TYPE, [2, pointmatches.size()]) # 2D double array
  targetPoints = newArray(Double.TYPE, [2, pointmatches.size()]) # 2D double array  
  for i, pointmatch in enumerate(pointmatches):
    srcPt = pointmatch.getP1().getL()
    tgtPt = pointmatch.getP2().getW()
    sourcePoints[0][i] = srcPt[0]
    sourcePoints[1][i] = srcPt[1]
    targetPoints[0][i] = tgtPt[0]
    targetPoints[1][i] = tgtPt[1]
  
  # Return a new thin-plate spline transform
  return ThinPlateR2LogRSplineKernelTransform(2, sourcePoints, targetPoints)
  
  
def transformImage(imp, transform):
  """
  imp: the ImagePlus to transform.
  transform: the transformation model from the image to transform to the reference image.
  """
  # Pixel by pixel method. To delegate entirely to java libraries, see: TransformMapping and TransformMeshMapping
  width, height = imp.getWidth(), imp.getHeight()
  ip = imp.getProcessor()
  spT = ShortProcessor(width, height)
  ip.setInterpolate(True)
  ip.setInterpolationMethod(ImageProcessor.BILINEAR) # can also use BICUBIC
  position = zeros(2, 'd') # double array
  
  for y in xrange(height):
    for x in xrange(width):
      position[0] = x
      position[1] = y
      transform.applyInPlace(position)
      # ImageProcessor.putPixel does array boundary checks
      spT.putPixel(x, y, ip.getPixelInterpolated(position[0], position[1]))
  
  return ImagePlus("transformed with " + type(transform).getSimpleName(), spT)


def transformImageFast(imp, thin_plate_spline_transform):
  """
  imp: the ImagePlus to transform
  thin_plate_spline_transform: an instance of ThinPlateR2LogRSplineKernelTransform
  
  This method is specific of ThinPlateR2LogRSplineKernelTransform because
  it uses a dedicated class for execution, named ThinPlateSplineMapping.
  By avoiding the heavy overhead of looping over all pixels with jython, execution is considerably faster.
  """
  impTarget = ImagePlus("transformed", imp.getProcessor().createProcessor(imp.getWidth(), imp.getHeight()))
  mapping = ThinPlateSplineMapping(thin_plate_spline_transform)
  mapping.mapInterpolated(imp.getProcessor(), impTarget.getProcessor())
  return impTarget


# Test:

# Two 16-bit images, the first original and the second deformed by hand non-linearly
#imp1 = IJ.openImage("/home/albert/Desktop/t2/blockmatching_test/08apr22a_gb27932_D4b_12x12_1_00005gr_01767ex.mrc.tif")
#imp2 = IJ.openImage("/home/albert/Desktop/t2/blockmatching_test/08apr22a_gb27932_D4b_12x12_1_00005gr_01767ex_deformed.mrc.tif")

# Using a reproducibly deformed image, generated buy the script "example_generate_elastically_deformed_image.py"
imp12 = IJ.getImage()
imp1 = ImagePlus("original", imp12.getStack().getProcessor(1))
imp2 = ImagePlus("deformed", imp12.getStack().getProcessor(2))

# Parameters
scale = 1.0 # float; between 0 and 1; to speed up if images are very large.
meshResolution = 50 # integer; number of points on the side of the grid, e.g., 10 means 10x10 = 100 points.
blockRadius = 40 # integer; size of the side of a square block used for cross-correlation.
searchRadius = 35 # integer; maximum distance from each grid point to run cross-correlations at.
minR = 0.1 # float; minimum cross-correlation regression value to accept, discard otherwise. It's the PMCC (Pearson product-moment correlation coefficient)
rod = 0.9 # float; ratio of best to second-best cross-correlation scores; discard if lower.
maxCurvature = 1000 # integer; default is 10, we use 1000 for TEM image tile registration.

pointmatches = extractBlockMatches(imp1, imp2, scale, meshResolution, blockRadius, searchRadius, minR, rod, maxCurvature)

showDisplacementVectors(imp2, pointmatches)


thin_plate_spline = computeElasticTransform(pointmatches)
impT = transformImageFast(imp2, thin_plate_spline)
impT.show()

stack = ImageStack() # of ShortProcessor
stack.addSlice("imp1", imp1.getProcessor()) # The first image, intact
stack.addSlice("impT", impT.getProcessor()) # The second image, transformed
stack.addSlice("imp2", imp2.getProcessor()) # The second image again, intact, for comparison
impTstack = ImagePlus("imp1 + tranformed imp2 + original imp2", stack)
impTstack.show()


  
