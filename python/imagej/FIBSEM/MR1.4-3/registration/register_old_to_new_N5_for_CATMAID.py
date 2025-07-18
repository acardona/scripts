# Register one N5 volume to another, section by section,
# and emit a translation transform for each section
# so that later it can be applied to CATMAID skeleton data.

import sys, os
sys.path.append("/lmb/home/acardona/lab/scripts/python/imagej/IsoView-GCaMP/")
from net.imglib2.view import Views
from lib.io import readN5
from lib.loop import createBiConsumerTypeSet
from lib.serial2Dregistration import ensureSIFTFeatures, filterFeatures, makeFilterFeaturesFn
from lib.util import isThreadDead, syncPrintQ
from net.imglib2.img.array import ArrayImgs
from net.imglib2.loops import LoopBuilder
from net.imglib2.realtransform import RealViews, Scale
from net.imglib2.interpolation.randomaccess import NLinearInterpolatorFactory
from ij import ImagePlus
from ij.process import ByteProcessor
from mpicbg.models import ErrorStatistic, TranslationModel2D, NotEnoughDataPointsException, PointMatch
from mpicbg.imagefeatures import FloatArray2DSIFT
from mpicbg.ij.util import Filter
from mpicbg.ij import SIFT # see https://github.com/axtimwalde/mpicbg/blob/master/mpicbg/src/main/java/mpicbg/ij/SIFT.java
from mpicbg.ij.clahe import FastFlat as CLAHE
from java.util import ArrayList
from java.lang import Double


# ASSUMES volumes have the same dimensions

name = "MR1.4-3"
tgtDir = "/net/zstore1/FIBSEM/" + name + "/registration/"

# Volumes:
old_n5_path = "/net/fibserver1/raw/MR1.4-3/old_n5/n5-2/"
new_n5_path = "/net/zstore1/FIBSEM/MR1.4-3/registration/MR1.4-3.n5"


output_CSV = os.path.join(tgtDir, "bridge.csv")



# Parameters for SIFT features
paramsSIFT = FloatArray2DSIFT.Param()
paramsSIFT.steps = 1
paramsSIFT.minOctaveSize = 0 # will be updated in a clone
paramsSIFT.maxOctaveSize = 0 # will be updated in a clone
paramsSIFT.initialSigma = 1.6 # default 1.6
paramsSIFT.fdSize = 8 # default is 4
paramsSIFT.fdBins = 8 # default is 8

paramsRANSAC = {
  "iterations": 1000,
  "maxEpsilon": 10, # pixels, maximum error allowed, usual number is 25. Started out as 5 for the first ~6000 sections or so.
  "minInlierRatio": 0.01 # 1%
}

# Parameters for pointmatches
params = {
 'minR': 0.1, # min PMCC (Pearson product-moment correlation coefficient)
 'rod': 0.9, # max second best r / best r
 'max_sd': 1.5, # max_sd: maximal difference in size (ratio max/min)
 'max_id': Double.MAX_VALUE, # max_id: maximal distance in image space
 'rod': 0.9 # rod: ratio of best vs second best
}

# Function to filter out features outside the tissue
model_path = os.path.join(tgtDir, "MR1.4-3_section1+6000_0.025.labkit.classifier") # from LabKit
model_width = 400 # target width for resizing so as to match the dimensions of the image used when training the model.

properties = {
 'scale': 0.2, # 20%
  'filterFeaturesFn': makeFilterFeaturesFn(model_path, model_width), # Filter out features not in the tissue but in the resin, to ignore the resin which has streaks and curtains
}



def sliceAsImp(img, sliceIndex, scale):
  # ASSUMES img is 8-bit
  #
  # Obtain a 2D plane at sliceIndex
  img2d = Views.hyperSlice(img, sliceIndex, 2)
  # Scaled view
  if scale < 1.0:
    imgS = Views.interval(RealViews.transform(Views.interpolate(Views.extendMirror(img2d), NLinearInterpolatorFactory()),
                                              Scale(scale)),
                          [0, 0],
                          [int(img.dimension(i) * scale + 0.5) -1 for i in [0, 1]])
  else:
    imgS = img2d
  # Copy it into a 2D image
  aimg = ArrayImgs.unsignedBytes(Intervals.dimensionsAsLongArray(imgS))
  LoopBuilder.setImages(imgS, aimg) \
                 .multiThreaded(False) \
                 .forEachPixel(createBiConsumerTypeSet(GenericByteType)) # GenericByteType has the "set(Type)" method 
  # Return the 2D plane as an ImagePlus
  return ImagePlus(str(slideIndex),
                   ByteProcessor(aimg.dimension(0),
                                 aimg.dimension(1),
                                 aimg.update(None).getCurrentStorageArray(),
                                 None))
    

def extractSIFTFeatures(paramsSIFT, properties, img, sliceIndex):
  try:
    if isThreadDead():
      return None
    # Extract features
    imp = sliceAsImp(img, sliceIndex, properties['scale'])
    ip = imp.getProcessor()
    paramsSIFT = paramsSIFT.clone()
    ijSIFT = SIFT(FloatArray2DSIFT(paramsSIFT))
    features = ArrayList() # of Feature instances
    ijSIFT.extractFeatures(ip, features)
    # Filter out features outside the tissue
    filterFeaturesFn = properties.get("filterFeaturesFn", None)
    if filterFeaturesFn:
      features = filterFeaturesFn(ip, features)
    # Flush
    ip = None
    imp.flush()
    imp = None
    syncPrintQ("Extracted %i SIFT features for slice %i" % (features.size(), sliceIndex))
    return features
  except:
    printException()


def computeTranslation(paramsSIFT, properties, params, img1, img2, sliceIndex):
  try:
    # Load from CSV files or extract features de novo
    features1 = extractSIFTFeatures(paramsSIFT, properties, img1, sliceIndex)
    features2 = extractSIFTFeatures(paramsSIFT, properties, img2, sliceIndex)
    # Vector of PointMatch instances
    sourceMatches = FloatArray2DSIFT.createMatches(features1,
                                                   features2,
                                                   params.get("max_sd", 1.5), # max_sd: maximal difference in size (ratio max/min)
                                                   TranslationModel2D(),
                                                   params.get("max_id", Double.MAX_VALUE), # max_id: maximal distance in image space
                                                   params.get("rod", 0.9)) # rod: ratio of best vs second best
    if isThreadDead():
      return None
    
    model = TranslationModel2D()
    msg = ""
    # Filter matches by geometric consensus
    n_pm = sourceMatches.size()
    inliers = ArrayList()
    iterations = properties.get("RANSAC_iterations", 1000)
    maxEpsilon = properties.get("RANSAC_maxEpsilon", 25) # pixels
    minInlierRatio = properties.get("RANSAC_minInlierRatio", 0.01) # 1%
    modelFound = model.filterRansac(sourceMatches, inliers, iterations, maxEpsilon, minInlierRatio)
    if modelFound:
      sourceMatches = inliers
      PointMatch.apply(inliers, model)
      syncPrintQ("Found %i inlier SIFT pointmatches (from %i) for slice $i" % (sourceMatches.size(),
                                                                               n_pm,
                                                                               sliceIndex))
      return model.getTranslation() # an array of two values
    else:
      sourceMatches.clear() # None
      syncPrintQ("SIFT: model NOT FOUND for slice %i\n" % sliceIndex)
      return [float('NaN'), float('NaN')]
  except:
    syncPrintQ("ERROR at slice %i\n" % sliceIndex)
    printException()
    return [float('NaN'), float('NaN')]



def computeSliceTranslations(img1, img2):
  """
  Assumes images have the same dimensions.
  """
  exe = newFixedTheadPool(-1)
  translations = []
  batch_size = (2 * numCPUs())
  try:
    with open(output_CSV, 'a') as csvfile:
      futures = []
      for sliceIndex in xrange(min(img1.dimension(2), img2.dimension(2))):
        futures.append(exe.submit(Task(computeTranslation, paramsSIFT, properties, params, img1, img2, sliceIndex)))
        if 0 == sliceIndex % batch_size:
          for i in xrange(batch_size / 2):
            t = futures.pop(0).get()
            translations.append(t)
            line = "%f, %f\n" % t
            csvfile.write(line)
            syncPrintQ(line)
      for fu in futures: # append any remaining
        t = fu.get()
        line = "%f, %f\n" % t
        csvfile.write(line)
        syncPrintQ(line)
  except:
    printException()
  finally:
    exe.shutdown()


# Test: open the images, check dimensions are the same, otherwise fix that
# Load N5 volumes as CachedImg 3D volumes a 100% magnification
imgOld, impOld = readN5(old_n5_path, "s0", show="IJ", title="old", showImp=False)
imgNew, impNew = readN5(new_n5_path, "s0", show="IJ", title="new", showImp=False)

print impOld
print impNew























