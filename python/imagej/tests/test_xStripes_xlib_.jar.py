from ij import IJ, ImagePlus
from xjava.filter import xStripes
from jarray import zeros
from ij.process import ShortProcessor, ByteProcessor
from net.imglib2.img.array import ArrayImgs
from net.imglib2.img.basictypeaccess.array import ByteArray, IntArray
from net.imglib2.algorithm.math import ImgMath
from net.imglib2.img.display.imagej import ImageJFunctions

# Test xStripes API - work in progress

# Load an image with severe vertical and horizontal stripes
imp = IJ.openImage("/home/albert/Desktop/t2/20230407 Alexandra Pacureanu X-ray synchrotron/align00.png")

# Run the xStripes plugin as recorded, which opens an image:
#IJ.run(imp, "Stripes Filter", "filter=Wavelet-FFT direction=Both types=Daubechies wavelet=DB15 border=[Symmetrical mirroring] image=don't decomposition=0:5 damping=5 large=100000000 small=1 tolerance=1 half=5 offset=1")

# Run the xStripes plugin from the API
width = imp.getWidth()
height = imp.getHeight()
bytes = imp.getProcessor().getPixels() # bytes, if 8-bit, or shorts, if 16-bit
intPixels = zeros(width * height, 'i') # in integers
# Copy pixels into int[], fast
ba = ArrayImgs.unsignedBytes(ByteArray(bytes), [width, height])
bi = ArrayImgs.unsignedInts(IntArray(intPixels), [width, height])
ImgMath.compute(ImgMath.img(ba)).into(bi)

numBits = 8
numBands = 1 # means: single-channel image, not e.g., RGB with 3 bands
waveletTyp = "db15"
decId = [0, 1, 2, 3, 4, 5] # decomposition 0:5
filtWid = 5.0 # filter width (the damping coefficient defining the width of the Fourier filter)
filtTyp = 'f' # f: FFT; a: subtract average; 'z': set to zero 
wavBord = "sym" # symmetrical mirroring of the edges
horVer = 2 # 0: filter horizontal stripes; 1: filter vertical stripes; 2: filter both
normConstr = 'c' # 'c': constraint output values to numBits; 'n': normalize; ' ': do nothing
doDispl = False # don't show results
ints = xStripes.waveletFilt(width, height,
                            intPixels,
                            numBits,
                            numBands,
                            waveletTyp, decId,
                            filtWid, filtTyp,
                            wavBord, horVer,
                            normConstr, doDispl)
bytesFiltered = zeros(width * height, 'b')
bfa = ArrayImgs.unsignedBytes(ByteArray(bytesFiltered), [width, height])
bfi = ArrayImgs.unsignedInts(IntArray(ints), [width, height])
ImgMath.compute(ImgMath.img(bfi)).into(bfa) # crop ints to byte

impFiltered = ImagePlus("filtered", ByteProcessor(width, height, bytesFiltered, None))
impFiltered.show()

#filtered = ArrayImgs.unsignedInts(IntArray(ints), [width, height])
#ImageJFunctions.wrap(filtered, "xStripes-filtered").show()

                         
                         