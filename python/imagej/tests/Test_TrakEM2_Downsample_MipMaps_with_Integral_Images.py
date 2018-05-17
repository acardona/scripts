from ini.trakem2.display import Display
from ini.trakem2.persistence import DownsamplerMipMaps
from java.lang import System

def timeIt(fn, n_iterations=10):
  elapsed_times = []
  for i in range(n_iterations):
    t0 = System.nanoTime()
    fn()
    t1 = System.nanoTime()
    elapsed_times.append(t1 - t0)

  smallest = min(elapsed_times)
  largest =  max(elapsed_times)
  average =  sum(elapsed_times) / float(n_iterations)
  print "Elapsed time: min", smallest, "max", largest, "average", average
  return elapsed_time

layer = Display.getFront().getLayer()
patch = layer.getDisplayables().get(0)
print patch
pai = patch.createTransformedImage()
print pai
print patch.hasCoordinateTransform()
print patch.getImageProcessor()
first_level_mipmaps_saved = 0

def testCascade():
  global patch, pai, first_level_mipmaps_saved
  print pai
  b = DownsamplerMipMaps.create(
        patch,
        patch.getType(),
		pai.target,
		pai.mask,
		pai.outside,
		first_level_mipmaps_saved)
  return b


#timeIt(testCascade)