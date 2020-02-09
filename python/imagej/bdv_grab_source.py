from java.awt import Frame
from net.imglib2.realtransform import AffineTransform3D

for frame in Frame.getFrames():
  if frame.getTitle() == "BigDataViewer":
    root = frame.getComponent(0)
    jlayeredpane = root.getComponents()[1]
    jpanel = jlayeredpane.getComponent(0)
    bdv_viewerpanel = jpanel.getComponent(0)
    #print bdv_viewerpanel
    # see: https://github.com/bigdataviewer/bigdataviewer-core/blob/master/src/main/java/bdv/viewer/ViewerPanel.java
    viewerstate = bdv_viewerpanel.getState() # a copy of the ViewerState instance that wraps the sources
    sources_and_converters = viewerstate.getSources() # a list of SourceState instances wrapping the sources
    for sc in sources_and_converters:
      source = sc.getSpimSource()
      print source # bdv.tools.transformation.TransformedSource
      # Print the transform
      transform = AffineTransform3D()
      timepoint = 0
      mipmap_level = 0
      source.getSourceTransform(timepoint, mipmap_level, transform)
      print transform
      # Grab the RandomAccessible
      print source.getType().getClass()
      rai = source.getSource(timepoint, mipmap_level)
      print rai # an imglib2 PlanarImg that wraps an ij.ImagePlus

# TODO:
# * demonstrate adding another source
# * demonstrate editing a source
# * demonstrate copying a source as transformed



