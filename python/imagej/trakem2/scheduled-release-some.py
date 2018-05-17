from java.util.concurrent import Executors, TimeUnit
from java.lang import System
from ini.trakem2.persistence import Loader
from ini.trakem2 import Project
from ini.trakem2.utils import CachingThread
import sys, traceback

exe = Executors.newScheduledThreadPool(1)

def free():
  #Loader.releaseAllCaches()
  #System.out.println("Released all")
  #
  # Instead of releasing all, release half of all loaded images
  # !!! ASSUMES that all cached images are of 4096x4096 dimensions !!!!
  try:
    image_n_bytes = pow(4096, 2) * 4 # RGBA
    projects = Project.getProjects()
    if 0 == projects.size():
      return
    loader = projects[0].getLoader()
    f = Loader.getDeclaredField("mawts")
    f.setAccessible(True)
    mawts = f.get(loader)
    n_cached_images = mawts.size()
    n_bytes_released = 0
    if n_cached_images > 0:
      n_bytes_to_release = int((n_cached_images * 0.5) * image_n_bytes)
      n_bytes_released = loader.releaseMemory(n_bytes_to_release)
      if 0 == n_bytes_released:
        # There may be enough free memory so the loader refused to release anything,
        # therefore ask the cache instance itself to actually remove the amount requested
        n_bytes_released = mawts.removeAndFlushSome(n_bytes_to_release)
      System.out.println("Released " + str(n_bytes_released) + " out of " + str(n_bytes_to_release))
      loader.printCacheStatus()
    if 0 == n_bytes_released:
       # All memory retained is in the form of native arrays stored for loading images later
      System.out.println("Cleared CachingThread cache.")
      CachingThread.releaseAll()
  except:
    traceback.print_exc(file=sys.stdout)

exe.scheduleWithFixedDelay(free, 0, 60, TimeUnit.SECONDS)

# To cancel, call:
#exe.shutdownNow()

