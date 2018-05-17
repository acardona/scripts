# copy original images for patches in layer
from ini.trakem2.display import Display, Patch
from shutil import copy
from os import path

storage = "/mnt/ssd-512/0111-8/debug/original-images/"

for patch in Display.getFrontLayer().getDisplayables(Patch):
  filepath = patch.getImageFilePath()
  print filepath
  copy(filepath, storage)
