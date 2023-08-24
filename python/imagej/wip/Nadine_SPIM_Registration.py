# SPIM_Registration-5.0.16.jar
# Copying from the Data_Explorer PlugIn launcher
from spim.fiji.plugin import Define_Multi_View_Dataset
from spim.fiji.spimdata import SpimData2, XmlIoSpimData2
from spim.fiji.plugin.queryXML import LoadParseQueryXML
from java.awt.event import ActionListener
from spim.fiji.spimdata.explorer import ViewSetupExplorer
from mpicbg.spim.data.generic.sequence import ImgLoaderHints
from net.imglib2.img.display.imagej import ImageJFunctions as IJF

query = "/home/albert/shares/zlaticlab/Nadine/Raghav/2017-05-10/GCaMP6s_1_20170510_115003.corrected/bdv.xml"

class Listener(ActionListener):
  def __init__(self, result):
    self.result = result
  
  def actionPerformed(self, e):
    self.result.setReturnFalse( True )
    self.result.getGenericDialog().dispose()

def run():
  result = LoadParseQueryXML()
  result.addButton("Define a new dataset", Listener(result))
  if not result.queryXML( "XML Explorer", query, False, False, False, False ):
    print "Cancelled dialog"
    return
  print "Resume"
  data = result.getData()
  xml = result.getXMLFileName()
  io = result.getIO()
  explorer = ViewSetupExplorer( data, xml, io )
  explorer.getFrame().toFront()

  # A handle into the data
  spimdata2 = explorer.getSpimData()
  # https://github.com/bigdataviewer/spimdata/blob/master/src/main/java/mpicbg/spim/data/registration/ViewRegistrations.java
  # A map of ViewId vs ViewRegistration (which extends ViewId, so likely are the same)
  # ViewId: https://github.com/bigdataviewer/spimdata/blob/master/src/main/java/mpicbg/spim/data/sequence/ViewId.java
  # ViewRegistration: https://github.com/bigdataviewer/spimdata/blob/master/src/main/java/mpicbg/spim/data/registration/ViewRegistration.java
  viewregs = spimdata2.getViewRegistrations().getViewRegistrations()
  #for k, v in viewregs.iteritems():
  #  print "timepointId:", k.getTimePointId(), "viewSetupId:", k.getViewSetupId(), "value: ", v
  # Shows that there are 4 views per timepoint: not fused!
  # And: each ViewRegistration holds only the transforms of each view of the timepoint, not the 3D pixels.
  # 
  # https://github.com/bigdataviewer/spimdata/blob/master/src/main/java/mpicbg/spim/data/sequence/SequenceDescription.java
  seqdescr = spimdata2.getSequenceDescription()
  imgloader = seqdescr.getImgLoader()
  for view, viewreg in viewregs.iteritems():
    # Each entry has its own TimePointId and ViewId
    viewID = view.getViewSetupId()
    timepointID = view.getTimePointId()
    # Instance of: org.janelia.simview.klb.bdv.KlbImgLoader$KlbSetupImgLoader
    loader = imgloader.getSetupImgLoader(viewID)
    # Dimensions instance
    dim = loader.getImageSize(timepointID)
    # VoxelDimensions instance
    voxelDim = loader.getVoxelSize(timepointID)
    # RandomAccessibleInterval instance
    rai = loader.getImage(timepointID, 0, [ImgLoaderHints.LOAD_COMPLETELY])
    # The transforms
    transformList = viewreg.getTransformList()
    # TODO: register, the transform is in the viewreg
    IJF.show(rai)
    print map(dim.dimension, [0,1,2]) # [576L, 896L, 65L]
    print voxelDim.unit(), voxelDim.numDimensions(), map(voxelDim.dimension, [0,1,2]) # um 3 [1.0, 1.0, 1.0]
    break
    
 


run()
