from java.lang.reflect import Field
from ini.trakem2.persistence import FSLoader
from ini.trakem2.display import Display

loader = Display.getFront().getProject().getLoader()

f = FSLoader.getDeclaredField("cannot_regenerate")
f.setAccessible(True)
f.get(loader).clear()