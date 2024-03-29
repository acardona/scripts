package my;

public class IO_DAT {

static public final void toUnsigned(final short[] signed) {
  short min = 32767; // max possible signed short value
  for (int i=0; i<signed.length; ++i) {
    if (signed[i] < min) min = signed[i];
  }
  if (min < 0) {
    for (int i=0; i<signed.length; ++i) {
      signed[i] -= min;
    }
  }
}

static public final short[][] deinterleave(final short[] source,
                                           final int numChannels,
                                           final int channel_index) {
  if (channel_index >= 0) {
    // Read a single channel
    final short[] shorts = new short[source.length / numChannels];
    for (int i=channel_index, k=0; i<source.length; ++k, i+=numChannels) {
      shorts[k] = source[i];
    }
    return new short[][]{shorts};
  }
  final short[][] channels = new short[numChannels][source.length / numChannels];
  for (int i=0, k=0; i<source.length; ++k) {
    for (int c=0; c<numChannels; ++c, ++i) {
      channels[c][k] = source[i];
    }
  }
  return channels;
}

}
