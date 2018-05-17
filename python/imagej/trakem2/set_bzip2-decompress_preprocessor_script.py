from __future__ import with_statement
from ini.trakem2.display import Display
from ini.trakem2.utils import Utils
from java.io import File
import os

pps = "/home/albert/Desktop/0111-8/scripts/bzip2-decompress_preprocessor.py"
loader = Display.getFront().getProject().getLoader()

for layer in Display.getFront().getLayerSet().getLayers():
  for patch in layer.getDisplayables():
    loader.setPreprocessorScriptPathSilently(patch, pps)