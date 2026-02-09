import sys, os
sys.path.append("/net/fibserver1/code/scripts/python/imagej/IsoView-GCaMP/")

from lib.io import readFIBSEMHeader, readFIBSEMdat
from lib.util import timeit, newFixedThreadPool, Task
from lib.ui import showTable
#from java.nio.file import Files, Paths
from java.io import File, FilenameFilter
from java.lang import String
from ij import IJ

base_path = "/net/fibserver1/raw/YY9_Gaba/repaired/"

#repaired = "/net/fibserver1/raw/YY9_Gaba/repaired/repaired_dat.txt"
#filenames = [[filename] for filename in Files.readAllLines(Paths.get(repaired))]

class RepairedFileFilter(FilenameFilter):
  def __init__(self):
    pass
  def accept(self, folder, filename):
    return filename.endswith(".dat") or filename.endswith(".tif")


filenames = [[filename] for filename in File(base_path).list(RepairedFileFilter())]

# ExecutorService for opening images
exe = None

def openDAT(filename):
  try:
    #date = filename.split("_")[1].split("-")
    #filepath = "%s/Y20%s/M%s/D%s/%s" % (base_path, date[0], date[1], date[2], filename)
    filepath = base_path + filename
    IJ.log("Opening %s" % filename)
    imp = readFIBSEMdat(filepath, channel_index=0, asImagePlus=True, toUnsigned=True)[0]
    imp.setTitle(filename)
    imp.show()
  except:
    print "Failed to open:\n%s" % filepath
    print sys.exc_info()
  
def onClick(event):
  global exe
  if not exe:
    exe = newFixedThreadPool(-1)
  if 2 == event.getClickCount():
    table = event.getSource() # a JTable
    view_index = table.rowAtPoint(event.getPoint())
    data_index = table.convertRowIndexToModel(view_index)
    filename = table.getModel().getValueAt(data_index, 0) # row, col
    exe.submit(Task(openDAT, filename))

def destroy(event):
  exe.shutdownNow()

table, frame = showTable(filenames, column_names=["filename"], dataType=String,
                         width=600, height=500, showTable=True,
                         renderCenteredColumns=[0],
                         windowClosing=destroy, onClickFn=onClick)

