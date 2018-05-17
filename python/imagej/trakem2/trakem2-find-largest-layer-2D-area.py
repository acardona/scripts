# Find out the 2D area of the largest section
# and whether it is larger than 2 GB (for array indexing with signed int)

from ini.trakem2 import Project
from ini.trakem2.display import Patch

p = Project.getProjects()[0]

max_bounds = None

for layer in p.getRootLayerSet().getLayers():
  bounds = layer.getMinimalBoundingBox(Patch)
  if max_bounds is None:
    max_bounds = bounds
  else:
    if bounds is not None and max_bounds.width * max_bounds.height < bounds.width * bounds.height:
      max_bounds = bounds

print max_bounds
print max_bounds.width * max_bounds.height
print max_bounds.width * max_bounds.height > pow(2, 31)
