from __future__ import with_statement
import sys, os, csv
sys.path.append(os.path.dirname(os.path.dirname(sys.argv[0]))
from lib.io import readN5
from lib.synthetic import virtualPointsRAI
from lib.ui import showStack, wrap, showAsComposite
from lib.deltaFoverF import computeDeltaFOverF
from net.imglib2.view import Views

baseDir = "/home/albert/shares/cardonalab/Albert/2017-05-10_1018/"
srcDir = baseDir + "deconvolved/"
n5dir = os.path.join(srcDir, "n5")
dataset_name = "2017-5-10_1018_0-399_X203_Y155_Z65"

# Load entire 4D IsoView deconvolved and registered data set
img4D = readN5(n5dir, dataset_name)

# A mask: only nuclei whose x,y,z coordinate has a non-zero value in the mask will be considered
mask = None

# Split CM00+CM01 (odd) from CM02+CM03 (even) into two series
series = ["CM00-CM01", "CM02-CM03"]
img4Da = Views.subsample(img4D,
                         [1, 1, 1, 2]) # step
img4Db = Views.subsample(Views.interval(img4D, [0, 0, 0, 1], Intervals.maxAsLongArray(img4D)),
                         [1, 1, 1, 2]) # step

showStack(img4Da, title="%s registered+deconvolved" % series[0])
showStack(img4Db, title="%s registered+deconvolved" % series[1])

calibration = [1.0, 1.0, 1.0]
somaDiameter = 8 * calibration[0]

# Parameters for detecting nuclei with difference of Gaussian
params = {
 "frames": 5, # number of time frames to average, 5 is equivalent to 3.75 seconds: 0.75 * 5
 "calibration": calibration, # Deconvolved images have isotropic calibration
 "somaDiameter": somaDiameter, # in pixels
 "minPeakValue": 50, # determined by hand: the bright peaks
 "sigmaSmaller": somaDiameter / 4.0, # in calibrated units: 1/4 soma
 "sigmaLarger": somaDiameter / 2.0,  # in calibrated units: 1/2 soma
 "searchRadius": somaDiameter / 3.0,
 "min_count": 20,
 "baseline_window_size": int(30 / 0.75) + 1, # 30 seconds, at 0.75 seconds per timepoint: 40 timepoints, plus 1 to make it odd
                                    # so that it will include 20 timepoints before and 20 after for the baseline calculation.
 "CM00-CM01_noise_stdDev": (3.17 + 3.20) / 2.0, # Measured inside the crop only, using two crops:
                                                # first Roi[Rectangle, x=187, y=400, width=576, height=896]
                                                # second Roi[Rectangle, x=1, y=228, width=406, height=465]
                                                # for both CM00 and CM01, so taking an "average" if that makes sense (they are close anyway)
 "CM00-CM01_noise_mean":  100, # Run a Gaussian with sigma=10 over the darfield noise image of CM00 and CM01.
                               # For both cameras, the range is then 99-101, with almost all values at 100.
}

# For testing: only first 5 timepoints, 3 frames
#min_count = 2
#frames = 5
#img4Da = Views.interval(img4Da, FinalInterval([img4Da.dimension(0), img4Da.dimension(1), img4Da.dimension(2), 5]))



# Camera noise: given the deconvolution, it's unclear what to use.
# The PSF is about 20 pixels wide, so perhaps a Gaussian of radius 10 over the average of both noise images would do.
# Then, the peak is used a center + radius, averaging all pixel values within. So shot noise is not an issue.
# Given that it's most likely constant, I try first with zero as camera noise.

# Ignoring series 1 for now
peaks, measurements, baselines, dFoF = computeDeltaFOverF(tgtDir, series[0], img4Da, params, mask=mask)

with open(os.path.join(srcDir, "%s_deltaFoF.csv" % series[0]), 'w') as csvfile:
  w = csv.writer(csvfile, delimiter=",", quotechar='"', quoting=csv.QUOTE_NONNUMERIC)
  # Header: with peak coordinates
  w.writerow(["timepoint"] + ["%.2f::%.2f::%.2f" % tuple(peak.getFloatPosition(d) for d in xrange(3)) for peak in peaks])
  for t, row in enumerate(dFoF):
    w.writerow([t] + row.tolist())


# TODO: function compute deltaFOverF which reads it from a file if it exists and opens it in 3D spheres,
#       And the 3D Viewer has additional functions to either click on a sphere to see the plot over time,
#       and to enter a coordinate and highlight a sphere.













