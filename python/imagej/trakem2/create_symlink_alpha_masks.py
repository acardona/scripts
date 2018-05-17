# Create symlinks for all alpha masks,
# all of them pointing to the same alpha mask

from __future__ import with_statement
from ini.trakem2.display import Display
from ini.trakem2.utils import Utils
from java.io import File
import os

shared = "/home/albert/Desktop/0111-8/mask-border-12-px.zip"

loader = Display.getFront().getProject().getLoader()

for layer in Display.getFront().getLayerSet().getLayers():
  for patch in layer.getDisplayables():
    # For all, not just the visible
    path = loader.getMasksFolder() \
           + loader.createIdPath(str(patch.getAlphaMaskId()), str(patch.getId()), ".zip")
    Utils.ensure(path)
    if File(path).exists():
      continue
    os.symlink(shared, path)
