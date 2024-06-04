from org.janelia.saalfeldlab.n5.imglib2 import N5Utils
from org.janelia.saalfeldlab.n5.universe import N5Factory

def test():
  srcDir = "/home/albert/ceph.mzlatic.grp/code/LS_analysis/data/Nadine/"
  path = srcDir + "a_38042/a_38042_1_20240428_112123/merged_registered.zarr"
  dataset = "volumes" # confusing choice of name

  # Open a ZARR volume: these are all 4D, so 4D CellImg
  n5 = N5Factory().openReader(path) # an N5Reader
  img = N5Utils.open(n5, dataset) # a CellImg
  print img


test()