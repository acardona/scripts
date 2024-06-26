# Test PointMatchesFast.fromNearbyFeatures by comparing it to FloatArray2DSIFT.createMatches


import os, sys
sys.path.append("/home/albert/lab/scripts/python/imagej/IsoView-GCaMP/")
from lib.features_asm import initNativeClasses
from mpicbg.ij import SIFT
from mpicbg.imagefeatures import FloatArray2DSIFT
from mpicbg.models import TranslationModel2D
from ij import IJ, ImagePlus
from ij.gui import PointRoi
from java.util import ArrayList
from java.lang import Double, System

_, PointMatchesFast = initNativeClasses()

#folder = "/home/albert/Desktop/t2/FIBSEM_MR1.4-3/"
folder = "/home/albert/lab/projects/20240625_segment_FIBSEM_neural_tissue_vs_background/test-images/"
imp1 = IJ.openImage(folder + "1_0.2_1.tif")
imp2 = IJ.openImage(folder + "1_0.2_2.tif")

radius = 100 # in pixels, as maximum expected displacement

params = {
  "scale": 0.5, # images are pre-scaled to 20%, so 0.5 means 10%
  "rod": 0.9, # rod: ratio of best vs second best
}

paramsSIFT = FloatArray2DSIFT.Param()
paramsSIFT.fdSize = 8 # default is 4
paramsSIFT.fdBins = 8 # default is 8
paramsSIFT.maxOctaveSize = int(max(1024, imp1.getWidth() * params["scale"]))
paramsSIFT.steps = 3
paramsSIFT.minOctaveSize = int(paramsSIFT.maxOctaveSize / pow(2, paramsSIFT.steps))
paramsSIFT.initialSigma = 1.6 # default 1.6


def extractFeatures(imp, paramsSIFT):
  ip = imp.getProcessor()
  paramsSIFT = paramsSIFT.clone()
  ijSIFT = SIFT(FloatArray2DSIFT(paramsSIFT))
  features = ArrayList() # of Feature instances
  ijSIFT.extractFeatures(ip, features)
  return features

print "Extracting features"
features1 = extractFeatures(imp1, paramsSIFT)
features2 = extractFeatures(imp2, paramsSIFT)
print "Extracted %i and %i features" % (len(features1), len(features2))

print "Matches all to all"
t0 = System.nanoTime()
# Below, note as of 2024-06-26 the max_id and the model aren't used at all
matchesAllToAll = FloatArray2DSIFT.createMatches(features1,
                                                 features2,
                                                 params.get("max_sd", 1.5), # max_sd: maximal difference in size (ratio max/min)
                                                 TranslationModel2D(),
                                                 params.get("max_id", Double.MAX_VALUE), # max_id: maximal distance in image space
                                                 params.get("rod", 0.9)) # rod: ratio of best vs second best
t1 = System.nanoTime()
print "Found %i pointmatches via all-to-all" % len(matchesAllToAll)
print "Took:", (t1 - t0) / 1000000.0

print "Matches via KDTree"
t0 = System.nanoTime()
# Below, note as of 2024-06-26 the max_id and the model aren't used at all, because internally it calls
# FloatArray2DSIFT.createMatches which does not use them: a feature that wasn't implemented a decade ago.
matchesKDTree = PointMatchesFast.matchNearbyFeatures(radius * params["scale"],
                                                     features1,
                                                     features2,
                                                     params.get("max_sd", 1.5), # max_sd: maximal difference in size (ratio max/min)
                                                     TranslationModel2D(),
                                                     params.get("max_id", Double.MAX_VALUE), # max_id: maximal distance in image space
                                                     params.get("rod", 0.9)) # rod: ratio of best vs second best

t1 = System.nanoTime()
print "Found %i pointmatches via kdtree" % len(matchesKDTree)
print "Took:", (t1 - t0) / 1000000.0


# Open an image and show the features as a PointRoi
def show(impA, impB, matches, suffix):
  imp1 = ImagePlus(impA.getTitle() + suffix, impA.getProcessor()) # shallow copy
  imp2 = ImagePlus(impB.getTitle() + suffix, impB.getProcessor()) # shallow copy
  proi1 = PointRoi()
  proi1.setShowLabels(True)
  proi2 = PointRoi()
  proi2.setShowLabels(True)
  for pm in matches:
    p1 = pm.getP1().getL()
    proi1.addPoint(p1[0], p1[1])
    p2 = pm.getP2().getL()
    proi2.addPoint(p2[0], p2[1])
  imp1.setRoi(proi1)
  imp1.show()
  imp2.setRoi(proi2)
  imp2.show()

show(imp1, imp2, matchesAllToAll, " all-to-all")
show(imp1, imp2, matchesKDTree, " kdtree")
  
  
# Result: takes 4 times as long to run with a KDTree, and finds only 421 features as opposed to 3191.
# So the result is different and it is slower.
  
  
  
  
  
  
  
  
  
  
  
  


