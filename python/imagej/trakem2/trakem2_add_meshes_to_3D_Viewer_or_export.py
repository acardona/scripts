#####
#
# A script to fix the failure of TrakEM2 to sometimes show meshes in the 3D Viewer with java 8.
# First attempt to "Show in 3D", which fails.
# With the 3D Viewer window still open, do:
# 1. select a node in TrakEM2's Project Tree,
# 2. edit the "resampling_factor" below,
# 3. and run the loadFromSelectedTreeNode(d3d, project)
# 
# If instead of showing the meshes in the 3D Viewer you'd rather export them
# to an .obj file (Wavefront format), use the exportSelectedAsWavefront function,
# which requires a file path you may want to edit (see at the bottom).
#
# Originally developed for Michaela Wilsch-Bräuninger at the MPI-CBG
#
#####

from ini.trakem2 import Project
from ini.trakem2.display import Display, AreaList, Display3D, ZDisplayable
from customnode import WavefrontExporter

# EDIT ME:
resampling_factor = 8

def addToDisplay3D(d3d, zd):
  pt = zd.project.findProjectThing(zd)
  c = d3d.createMesh(pt, zd, resampling_factor).call()
  d3d.universe.addContentLater(c)

def findZDisplayables(project):
  """ Given a select node in the Project Tree, return a sequence of all ZDisplayable under it). """
  tree = project.getProjectTree()
  selected = tree.getSelectionPath().getLastPathComponent()
  if not selected:
    print "Select a node first in the ProjectTree!"
    return
  pt = selected.getUserObject()
  children_pts = pt.findChildren(None, None, False)
  for child_pt in children_pts:
    zd = child_pt.getObject()
    if isinstance(zd, ZDisplayable):
      yield zd

def loadFromSelectedTreeNode(d3d, project):
  """ Select a node in the Project Tree, then run this function
      to load as meshes into the already opened 3D Viewer `d3d`
      all ZDisplayable under the node. """
  for zd in findZDisplayables(project):
      addToDisplay3D(d3d, zd)


def exportWavefront(zds, filepath):
  """
  Takes a sequence of ZDisplayable instances and saves all as meshes to disk in wavefront format.
  A materials .mtl file is saved along with it.
  See: https://github.com/fiji/3D_Viewer/blob/master/src/main/java/customnode/WavefrontExporter.java
  """
  meshes = {zd.getTitle(): d3d.createMesh(zd.project.findProjectThing(zd), zd, resampling_factor).call()
            for zd in zds}
  WavefrontExporter.save(meshes, filepath)

project = Project.getProjects()[0]
d3d = Display3D.getDisplay(project.getRootLayerSet())


def exportSelectedAsWavefront(project, filepath):
  """ Select a node in the Project Tree, then run this function
      to export the meshes of all ZDisplayable under the node
      in Wavefront format. """
  exportWavefront(list(loadFromSelectedTreeNode(project)), filepath)


# Strategy 1: provide a list of IDs
# The IDs of the AreaList (zDisplayables: arealists, balls etc.) instances
"""
to_add = [67163, 66596]

for zd_id in to_add:
  zd = project.findById(zd_id)
  addToDisplay3D(d3d, zd)
"""

# Strategy 2: select a node in the Project Tree
# WARNING: make sure you open a Display3D first
#loadFromSelectedTreeNode(d3d, project)

# Strategy 3: save meshes to disk.
exportSelectedAsWavefront(project, "/tmp/meshes.obj")

