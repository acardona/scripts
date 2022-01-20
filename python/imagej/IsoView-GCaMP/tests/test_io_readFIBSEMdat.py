from java.io import RandomAccessFile
from net.imglib2.img.array import ArrayImgs
#from net.imglib2.img.basictypeaccess.array import ShortArray
from jarray import zeros, array
from java.nio import ByteBuffer, ByteOrder
from fiji.scripting import Weaver
from java.lang import Class, Integer
from net.imglib2.img.display.imagej import ImageJFunctions as IL

w = Weaver.method("""
static public final short[][] deinterleave(final short[] source, final int numChannels, final int channel_index) {
  if (channel_index >= 0) {
    // Read a single channel
    final short[] shorts = new short[source.length / numChannels];
    for (int i=channel_index; k=0; i<source.length; ++k, i+=numChannels) {
      shorts[k] = source[i];
    }
    return new short{shorts};
  }
  final short[][] channels = new short[numChannels][source.length / numChannels];
  for (int i=0, k=0; i<source.length; ++k) {
    for (int c=0; c<numChannels; ++c, ++i) {
      channels[c][k] = source[i];
    }
  }
  return channels;
}
""", [], False) # no imports, and don't show code

print w

from org.scijava.plugins.scripting.clojure import ClojureScriptEngine
clj = ClojureScriptEngine()
code = """
(defn deinterleave [source_ numChannels_]
  (let [^shorts source source_
        ^int numChannels numChannels_
        n (count source)
        channels (make-array Short/TYPE numChannels (/ n numChannels))]
    (loop [i 0 ; doesn't accept type hints like ^int because it's initialized by a primitive
           k 0]
      (when (< i n)
        ;(println "i" i "k" k)
        (recur (loop [c 0
                      ii i]
                 ;(println "c" c "ii" i)
                 (if-not (< c numChannels)
                   ii ; return value of the loop
                   (do
                     (aset (aget channels c) k (aget source ii))
                     (recur (inc c) (inc ii)))))
               (inc k))))
    channels))
"""
deinterleave = clj.eval(code).get() # returns a clojure.lang.AFunction


def readFIBSEMdat(path, channel_index=-1, header=1024, magic_number=3555587570):
  """ Read a file from Shan Xu's FIBSEM software, where two channels are interleaved.
      Assumes channels are stored in 16-bit.
      
      path: the file path to the .dat file.
      channel_index: the 0-based index of the channel to parse, or -1 (default) for all.
      header: defaults to a length of 1024 bytes
      magic_number: defaults to that for version 8 of Shan Xu's .dat image file format.
  """
  ra = RandomAccessFile(path, 'r')
  try:
    # Check the magic number
    ra.seek(0)
    if ra.readInt() & 0xffffffff != magic_number:
      print "Magic number mismatch"
      return None
    # Read the number of channels
    ra.seek(32)
    numChannels = ra.readByte() & 0xff # a single byte as unsigned integer
    # Parse width and height
    ra.seek(100)
    width = ra.readInt()
    ra.seek(104)
    height = ra.readInt()
    print numChannels, width, height
    # Read the whole interleaved pixel array
    ra.seek(header)
    bytes = zeros(width * height * 2 * numChannels, 'b') # 2 for 16-bit
    ra.read(bytes)
    print "read", len(bytes), "bytes" # takes ~2 seconds
    # Parse as 16-bit array
    sb = ByteBuffer.wrap(bytes).order(ByteOrder.BIG_ENDIAN).asShortBuffer()
    shorts = zeros(width * height * numChannels, 'h')
    sb.get(shorts)
    # Deinterleave channels
    # With Weaver: fast
    channels = w.deinterleave(shorts, numChannels, channel_index)
    # With python array sampling: very slow, and not just from iterating whole array once per channel
    # seq = xrange(numChannels) if -1 == channel_index else [channel_index]
    #channels = [shorts[i::numChannels] for i in seq]
    # With clojure: extremely slow, may be using reflection unexpectedly
    #channels = deinterleave.invoke(shorts, numChannels)
    print len(channels)
    # Shockingly, these values are signed shorts, not unsigned!
    return [ArrayImgs.shorts(s, [width, height]) for s in channels]
  finally:
    ra.close()


path = "/net/ark/raw/fibsem/pygmy-squid/2021-12_popeye/Popeye2/Y2021/M12/D23/FIBdeSEMAna_21-12-23_235849_0-0-0.dat"


channels = readFIBSEMdat(path)
print channels
IL.wrap(channels[0], "channel 1").show() # looks good
IL.wrap(channels[1], "channel 2").show() # looks grainy, lots of shot noise
                                                                                                       


