import sys
sys.path.append("/home/albert/lab/scripts/python/imagej/IsoView-GCaMP/")
from lib.io import readN5
from lib.dogpeaks import createDoG
from lib.synthetic import virtualPointsRAI
from lib.ui import showStack
from lib.nuclei import findPeaks, mergePeaks, filterNuclei
from net.imglib2.view import Views

n5dir = "/home/albert/shares/cardonalab/Albert/2017-05-10_1018/deconvolved/n5"
dataset_name = "2017-5-10_1018_0-399_X203_Y155_Z65"

# Load entire 4D IsoView deconvolved and registered data set
img4D = readN5(n5dir, dataset_name)

# Split CM00+CM01 (odd) from CM02+CM03 (even) into two series
img4Da = Views.subsample(img4D,
                         [1, 1, 1, 2]) # step
img4Db = Views.subsample(Views.interval(img4D, [0, 0, 0, 1], Intervals.maxAsLongArray(img4D)),
                         [1, 1, 1, 2]) # step

showStack(img4Da, title="CM00+CM01 registered+deconvolved")
showStack(img4Db, title="CM02+CM03 registered+deconvolved")

calibration - [1.0, 1.0, 1.0]
somaDiameter = 8 * calibration

params = {
 "frames": 5, # number of time frames to average, 5 is equivalent to 3.75 seconds: 0.75 * 5
 "calibration": calibration, # Deconvolved images have isotropic calibration
 "somaDiameter": somaDiameter, # in pixels
 "minPeakValue": 40, # determined by hand: the bright peaks
 "sigmaSmaller": somaDiameter / 4.0, # in calibrated units: 1/4 soma
 "sigmaLarger": somaDiameter / 2.0,  # in calibrated units: 1/2 soma
 "searchRadius": somaDiameter / 3.0,
 "min_count": 20,
}

# For testing: only first 5 timepoints, 3 frames
#min_count = 2
#frames = 5
#img4Da = Views.interval(img4Da, FinalInterval([img4Da.dimension(0), img4Da.dimension(1), img4Da.dimension(2), 5]))


peaks = findPeaks(img4Da, params)
mergedPeaks = mergePeaks(peaks, params)
nuclei = filterNuclei(mergedPeaks, params)

# Show as a 3D volume with spheres
spheresRAI = virtualPointsRAI(nuclei, somaDiameter / 2.0, Views.hyperSlice(img4D, 3, 1))
imp = showStack(spheresRAI, title="nuclei (min_count=%i)" % params["min_count"])

