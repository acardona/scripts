from java.lang.reflect import Field
from java.lang import Runtime
from ini.trakem2.persistence import FSLoader
from ini.trakem2 import Project

loader = Project.getProjects()[0].getLoader()

f = FSLoader.getDeclaredField("regenerator")
f.setAccessible(True)
f.get(loader).shutdownNow()

loader.restartMipMapThreads(Runtime.getRuntime().availableProcessors())

f = FSLoader.getDeclaredField("regenerating_mipmaps")
f.setAccessible(True)
f.get(loader).clear()

f = FSLoader.getDeclaredField("n_regenerating")
f.setAccessible(True)
f.get(loader).set(0)

  