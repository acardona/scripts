from __future__ import with_statement
from ini.trakem2.display import Display
from ini.trakem2.utils import Utils
from java.io import File
import os

loader = Display.getFront().getProject().getLoader()

for layer in Display.getFront().getLayerSet().getLayers():
  for patch in layer.getDisplayables():
    if patch.isPreprocessed() and patch.getFilters() is None: # isPreprocessed returns True if there are filters
      print patch, patch.getPreprocessorScriptPath()

      #OK NONE