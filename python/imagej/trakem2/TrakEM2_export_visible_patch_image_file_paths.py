from __future__ import with_statement

from ini.trakem2.display import Display

paths = []

for layer in Display.getFront().getLayerSet().getLayers():
  for patch in layer.getDisplayables():
    if patch.isVisible():
      paths.append(patch.getImageFilePath())

print "Number of image paths:", len(paths)

with open("/home/albert/shares/cardona_nearline/Albert/0111-8_whole_L1_CNS/visible_image_filepaths.txt", "w") as f:
  f.write("\n".join(paths))