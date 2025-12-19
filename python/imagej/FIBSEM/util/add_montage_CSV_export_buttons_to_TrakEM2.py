import os, sys
libDir = "/data/code/scripts/python/imagej/IsoView-GCaMP/"
sys.path.append(libDir)
from ini.trakem2.display import Display
from lib.util import syncPrintQ
from lib.registration import saveMatrices
from javax.swing import JOptionPane, JButton, JPanel
from functools import partial
from ij import IJ

def saveTrakEM2MontageCSV(project, csvDir, printOnly, event): # used as actionPerformed for a button
    """
    To be executed from a button in a custom tab in the TrakEM2 Display.
    """
    display = Display.getOrCreateFront(project)
    tiles = {}
    for patch in display.getLayer().getPatches(False): # visible or invisible: all
      # Path doesn't exist, was generated from a script
      #path = patch.getImageFilePath()
      path = patch.getPreprocessorScriptPath() # same as tilePath but with a .bsh extension
      tiles[os.path.basename(path)] = patch # the folder can be different if the file was repaired. The basename suffices and will sort well.
    matrices = []
    groupName = None
    for path in sorted(tiles.keys()):
      patch = tiles[path]
      x, y = patch.getX(), patch.getY()
      matrices.append([1, 0, x, 0, 1, y])
      groupName = patch.getProperty("groupName")
    if printOnly:
      IJ.log("Matrices describing tile montage for section %s" % groupName)
      IJ.log("\n".join(map(str, matrices)))
    else:
      # Write or overwrite montage matrices CSV file
      if JOptionPane.YES_OPTION == JOptionPane.showConfirmDialog(None,
             "Confirm", "Write montage file\n%s.csv ?" % groupName, JOptionPane.YES_NO_OPTION):
        saveMatrices(groupName, matrices, csvDir)
   

def addTrakEM2Tab(project, csvDir):
   display = Display.getOrCreateFront(project)
   tabs = display.getTabbedPane()
   title = "FIBSEM section montage"
   # Check if the tab is already there
   for i in xrange(tabs.getTabCount()):
     if tabs.getTitleAt(i) == title:
       syncPrintQ("'FIBSEM section montage' tab already exists.")
       return
   # Add it new
   pane = JPanel()
   b1 = JButton("Save montage CSV", actionPerformed=partial(saveTrakEM2MontageCSV, project, csvDir, False))
   pane.add(b1)
   b2 = JButton("Print montage CSV", actionPerformed=partial(saveTrakEM2MontageCSV, project, csvDir, True))
   pane.add(b2)
   tabs.add(title, pane)
   display.pack() # repaint


# VOLUME
name = "Nicolo_S9_02122024" # Name of the folder containing the .dat files, e.g., "MR1.4-3"
targetServer = "/net/fibserver1/raw/"
tgtDir = targetServer + name + "/registration/"
montageDir = tgtDir + "montage-csv/" # for in-section montaging

front = Display.getFront()
if front:
  addTrakEM2Tab(front.getProject(), montageDir)