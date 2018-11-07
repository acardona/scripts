from net.imglib2.algorithm.dog import DogDetection
from net.imglib2.view import Views


def createDoG(img, calibration, sigmaSmaller, sigmaLarger, minPeakValue):
  """ Create difference of Gaussian peak detection instance.
      sigmaSmaller and sigmalLarger are in calibrated units. """
  # Fixed parameters
  extremaType = DogDetection.ExtremaType.MAXIMA
  normalizedMinPeakValue = False
  
  imgE = Views.extendMirrorSingle(img)
  # In the differece of gaussian peak detection, the img acts as the interval
  # within which to look for peaks. The processing is done on the infinite imgE.
  return DogDetection(imgE, img, calibration, sigmaLarger, sigmaSmaller,
    extremaType, minPeakValue, normalizedMinPeakValue)


def getDoGPeaks(img, calibration, sigmaSmaller, sigmaLarger, minPeakValue):
  """ Return a list of peaks as net.imglib2.RealPoint instances, calibrated. """
  dog = createDoG(img, calibration, sigmaSmaller, sigmaLarger, minPeakValue)
  peaks = dog.getSubpixelPeaks()
  # Return peaks in calibrated units (modify in place)
  for peak in peaks:
    for d, cal in enumerate(calibration):
      peak.setPosition(peak.getFloatPosition(d) * cal, d)
  return peaks

