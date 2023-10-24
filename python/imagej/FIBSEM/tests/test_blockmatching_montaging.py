import sys
from sc.fiji.io import FIBSEM_Reader
from ij import IJ, ImagePlus
from ij.gui import Roi
from java.io import File, FileInputStream
from mpicbg.models import ErrorStatistic, TranslationModel2D, TransformMesh, PointMatch, NotEnoughDataPointsException, Tile, TileConfiguration
from mpicbg.imagefeatures import FloatArray2DSIFT
from mpicbg.ij.blockmatching import BlockMatching
sys.path.append("/home/albert/lab/scripts/python/imagej/IsoView-GCaMP/")
from lib.io import readFIBSEMdat
from java.util import ArrayList
from ij.plugin.filter import GaussianBlur

paths = [
"/home/albert/zstore1/FIBSEM/Pedro_parker/M07/D14/Merlin-FIBdeSEMAna_23-07-14_000300_0-0-0.dat",
"/home/albert/zstore1/FIBSEM/Pedro_parker/M07/D14/Merlin-FIBdeSEMAna_23-07-14_000300_0-0-1.dat",
"/home/albert/zstore1/FIBSEM/Pedro_parker/M07/D14/Merlin-FIBdeSEMAna_23-07-14_000300_0-1-0.dat",
"/home/albert/zstore1/FIBSEM/Pedro_parker/M07/D14/Merlin-FIBdeSEMAna_23-07-14_000300_0-1-1.dat"]

sp1 = readFIBSEMdat(paths[0], channel_index=0, asImagePlus=True)[0].getProcessor()
sp2 = readFIBSEMdat(paths[1], channel_index=0, asImagePlus=True)[0].getProcessor()

beam_offset = 60 # the first few pixels are warped
overlap_width = 124
overlap_height = sp1.getHeight()/2 # half the image

roi000 = Roi(sp1.getWidth() - overlap_width, sp1.getHeight()/2,
             overlap_width, overlap_height)
roi001 = Roi(beam_offset, sp2.getHeight()/2,
             overlap_width, overlap_height)

sp1.setRoi(roi000)
crop1 = sp1.crop().convertToFloat()
sp2.setRoi(roi001)
crop2 = sp2.crop().convertToFloat()

# Gaussian blur - no need anymore
#radius = 1.0
#GaussianBlur().blurGaussian(crop1, radius)
#GaussianBlur().blurGaussian(crop2, radius)

# Debug:
#ImagePlus("0", crop1).show()
#ImagePlus("1", crop2).show()

# Define points from the mesh
sourcePoints = ArrayList()
# List to fill
sourceMatches = ArrayList() # of PointMatch from filepath1 to filepath2



params = {
  "meshResolutionX": 3,
  "meshResolutionY": 200,
  "scale": 0.5,
  "blockRadius": 100,
  "searchRadius": overlap_width/2,
  "minR": 0.1,
  "rod": 0.9,
  "maxCurvature": 1000
}

# Fill the sourcePoints
mesh = TransformMesh(params["meshResolutionX"], params["meshResolutionY"], crop1.getWidth(), crop1.getHeight())
PointMatch.sourcePoints( mesh.getVA().keySet(), sourcePoints )
print "Extracting block matches for \n S: " + paths[0] + "\n T: " + paths[1] + "\n  with " + str(sourcePoints.size()) + " mesh sourcePoints."

observer = ErrorStatistic(1000)

BlockMatching.matchByMaximalPMCC(
              crop1,
              crop2,
              None, # no mask
              None,
              params["scale"], # float
              TranslationModel2D(), # identity
              params["blockRadius"], # X
              params["blockRadius"], # Y
              params["searchRadius"], # X
              params["searchRadius"], # Y
              params["minR"], # float
              params["rod"], # float
              params["maxCurvature"], # float
              sourcePoints,
              sourceMatches,
              observer)

tiles = [Tile(TranslationModel2D()) for _ in [0, 1]]
tiles[0].connect(tiles[1], sourceMatches)

print "number of sourceMatches:", sourceMatches.size()

for pm in sourceMatches:
  print p.getP1(), p.getP2()

tc = TileConfiguration()
tc.addTiles(tiles)
tc.fixTile(tiles[0])

paramsTileConfiguration = {
  "maxAllowedError": 0, # Saalfeld recommends 0
  "maxPlateauwidth": 200, # Like in TrakEM2
  "maxIterations": 10, # Saalfeld recommends 1000 -- here, 2 iterations (!!) shows the lowest mean and max error for dataset FIBSEM_L1116
  "damp": 1.0, # Saalfeld recommends 1.0, which means no damp
}


maxAllowedError = paramsTileConfiguration["maxAllowedError"]
maxPlateauwidth = paramsTileConfiguration["maxPlateauwidth"]
maxIterations = paramsTileConfiguration["maxIterations"]
damp = paramsTileConfiguration["damp"]
tc.optimizeSilentlyConcurrent(ErrorStatistic(maxPlateauwidth + 1), maxAllowedError,
                              maxIterations, maxPlateauwidth, damp)

# First tile doesn't move
a = zeros(6, 'd')
tiles[1].getModel().toArray(a)

print "Translation: x,y = %f, %f" %(a[4], a[5])

