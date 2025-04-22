import os, sys, re

from java.lang import Integer, Runnable, String
from javax.swing import JPanel, JFrame, JTable, JScrollPane, JTextField, ListSelectionModel, SwingUtilities,\
                        JLabel, BorderFactory, JPopupMenu, JMenuItem, AbstractAction, KeyStroke, JOptionPane
from javax.swing.table import AbstractTableModel, DefaultTableCellRenderer
from java.awt import GridBagLayout, GridBagConstraints, Dimension, Font, Insets, Color
from java.awt.event import KeyAdapter, MouseAdapter, KeyEvent, ActionListener, WindowAdapter
from javax.swing.event import ListSelectionListener

from ij import IJ
from ij.io import FileSaver

from ini.trakem2 import Project
from ini.trakem2.display import Display

from lib.io import readFIBSEMHeader
from lib.util import syncPrintQ, Task, numCPUs, newFixedThreadPool, newThread, ensureDirsExist
from lib.ui import duplicateInParallel, saveInParallel, ExecutorCloser
from lib.registration import saveMatrices


class SliceTableModel(AbstractTableModel):
  def __init__(self, groupNames, tileGroups):
    self.groupNames = groupNames
    self.tileGroups = tileGroups
    self.rows = []
    self.restore() # populate rows
    self.header = ["Slice index", "Group name", "Num. tiles"]
  def restore(self):
    self.rows = [[i+1, groupName, self.tileGroups[i]]
                 for i, groupName in enumerate(self.groupNames)]
  def getColumnName(self, col):
    return self.header[col]
  def getColumnClass(self, col):
    return String if 1 == col else Integer
  def getRowCount(self):
    return len(self.groupNames)
  def getColumnCount(self):
    return 3
  def getValueAt(self, row, col):
    if 2 == col:
      return len(self.rows[row][2])
    return self.rows[row][col]
  def isCellEditable(self, row, col):
    return False # none editable
  def setValueAt(self, value, row, col):
    pass # none editable
  def filterTable(self, text):
    text = text.strip()
    try:
      if 0 == len(text):
        self.restore()
      else:
        pattern = re.compile(text)
        # Search in middle column
        self.rows = [[i+1, groupName, self.tileGroups[i]]
                     for i, groupName in enumerate(self.groupNames)
                     if pattern.search(groupName)]
      return True
    except:
      print "Malformed regex pattern: " + text


class TypingInSearchField(KeyAdapter):
  def __init__(self, table, model, search_field):
    self.table = table
    self.model = model
    self.search_field = search_field
  def keyPressed(self, event):
    if KeyEvent.VK_ENTER == event.getKeyCode():
      self.model.filterTable(self.search_field.getText())
    elif KeyEvent.VK_ESCAPE == event.getKeyCode():
      self.search_field.setText("")
      self.model.restore()
    SwingUtilities.invokeLater(lambda: self.table.updateUI()) # executed by the event dispatch thread 

class OpenDAT(Runnable):
  def __init__(self, filepath, show=True):
    self.filepath = filepath
    self.show = show
  def run(self):
    try:
      syncPrintQ("OpenDAT filepath: %s" % self.filepath)
      imp = load(self.filepath)
      if self.filepath.endswith(".dat"):
        syncPrintQ(readFIBSEMHeader(self.filepath))
      imp.setTitle(os.path.basename(self.filepath))
      if self.show:
        imp.show()
    except:
      print sys.exc_info()

class Action(AbstractAction):
  def __init__(self, opener):
    self.opener = opener
  def actionPerformed(self, event):
    table = event.getSource()
    model = table.getSelectionModel()
    rowIndex = model.getLeadSelectionIndex() # first selected row
    opener.openImages(rowIndex)

class RowClickListener(MouseAdapter, ListSelectionListener):
  def __init__(self, model, exe, imp, csvDir, table):
    self.model = model
    self.exe = exe
    self.imp = imp
    self.csvDir = csvDir
    self.table = table
    self.firstIndex = -1
    self.lastIndex = -1
  
  def mousePressed(self, event):
    if 2 == event.getClickCount():
      # Open the raw images of the montage at that slice
      rowIndex = event.getSource().rowAtPoint(event.getPoint()) # TODO could use self.firstIndex or the whole range
      self.openImages(rowIndex)
    
  def openImages(self, rowIndex):
    for filepath in self.model.rows[rowIndex][2]:
      # Execute in a separate set of threads
      if filepath.endswith(".dat"):
        self.exe.submit(OpenDAT(filepath))
      else:
        self.exe.submit(lambda: IJ.openImage(filepath))
  
  def openImagesRows(self):
    if self.firstIndex < 0 or self.lastIndex < 0:
      return
    for rowIndex in xrange(self.firstIndex, self.lastIndex + 1):
      self.openImages(rowIndex)
  
  def openStackOfSliceMontages(self):
    if self.firstIndex > -1 and self.lastIndex > -1:
      # ij.ImageStack is 1-based, so add +1 to start and end of selection
      slice_indices = [self.model.rows[rowIndex][0] for rowIndex in xrange(self.firstIndex, self.lastIndex + 1)] # Already 1-based 
      self.exe.submit(Task(duplicateInParallel, self.imp, slice_indices, n_threads=max(1, numCPUs() -2), shallow=True, show=True, scale=1.0))

  def saveStackOfSliceMontages(self):
    if self.firstIndex > -1 and self.lastIndex > -1:
      gd = GenericDialog("Save stack")
      gd.addMessage("1-based slice indices")
      gd.addNumericField("First slice: ", self.model.rows[self.firstIndex][0], 0, 6, "")
      gd.addNumericField("Last slice: ", self.model.rows[self.lastIndex][0], 0, 6, "")
      gd.addNumericField("Scale (0 to 1): ", 1.0, 3, 7, "")
      gd.addNumericField("Number of threads: ", max(1, int(numCPUs() / 2)), 0, 4, "")
      gd.addCheckbox("Incremental (avoid overwriting image files): ", True)
      OpenDialog.setDefaultDirectory(self.csvDir)
      gd.addDirectoryField("Target directory: ", self.csvDir, 50)
      gd.showDialog()
      if not gd.wasOKed():
        return
      firstIndex, lastIndex = int(gd.getNextNumber()), int(gd.getNextNumber())
      slice_indices = range(firstIndex, lastIndex + 1) # Already 1-based
      scale = gd.getNextNumber()
      numThreads = int(gd.getNextNumber())
      incremental = gd.getNextBoolean()
      targetDir = gd.getNextString()
      # Remember the directory for next time
      if os.path.exists(targetDir):
        OpenDialog.setDefaultDirectory(targetDir)
      #print targetDir, firstIndex, lastIndex, scale, numThreads, incremental
      self.exe.submit(Task(saveInParallel(targetDir, self.imp, slice_indices, n_threads=numThreads, show=True, scale=scale, incremental=incremental)))

  def deleteMontageCSVFiles(self):
    if self.table.getSelectedRowCount() > 0:
      rowIndices = list(self.table.getSelectedRows())
      first = self.model.rows[rowIndices[0]]
      last = self.model.rows[rowIndices[-1]]
      sp = max(len(str(first[0])), len(str(last[0])))
      msg = "Delete CSV files for " + str(last[0] - first[0] + 1) + " montages\n"\
            + "from slice " + str(first[0]).rjust(sp) + " " + first[1] + "\n"\
            + "to slice   " + str(last[0]).rjust(sp)  + " " + last[1] + "\n"\
            + "\nPlease confirm."
      yn = JOptionPane.showConfirmDialog(self.table, msg, "Delete CSV montage files",
           JOptionPane.YES_NO_OPTION, JOptionPane.WARNING_MESSAGE)
      if JOptionPane.YES_OPTION == yn:
        for i in xrange(self.firstIndex, self.lastIndex +1):
          path = os.path.join(self.csvDir, "%s.csv" % self.model.rows[i][1])
          if os.path.exists(path):
            syncPrintQ("Deleting CSV file at:\n%s" % path)
            os.remove(path)
  
  def montageManually(self):
    # Open all tiles, save them as TIFF in a temporary folder, and open them in a TrakEM2 project,
    # then add a new tab to the project to export the montage coordinates as a CSV file.
    if 0 == self.table.getSelectedRowCount():
      return
    # Rows selected:
    rowIndices = list(self.table.getSelectedRows())
    newThread(self.manualMontage, self, rowIndices)
  
  def manualMontage(self, rowIndices):
    """
    Open a TrakEM2 project for the set of sections selected.
    """
    # Make a tmp directory under self.csvDir
    tmpDir = os.path.join(self.csvDir, "tmp")
    ensureDirsExist(tmpDir)
    # Check if a project for this set of sections already exists
    first = self.model.rows[rowIndices[0]][0]
    last = self.model.rows[rowIndicies[-1]][0]
    xml_path = os.path.join(folder, "montages-%i-%i.xml" % (first, last))
    if os.path.exists(xml_path):
      syncPrintQ("TrakEM2 project for sections %i-% exists already." % (first, last))
      # Check if it is open already
      for p in Project.getProjects():
        if xml_path == p.getLoader().getProjectXMLPath():
          syncPrintQ("TrakEM2 project is open: bringing its display to the front.")
          Display.getOrCreateFront(p)
          return
      # Otherwise open it
      syncPrintQ("TrakEM2 project exists, will open it now.")
      p = Project.openFSProject(xml_path)
      Display.getOrCreateFront(p)
      self.addTrakEM2Tab(p)
      return
    # Create a TrakEM2 project
    project = Project.newFSProject("blank", None, tmpDir)
    layerset = project.getRootLayerSet()
    # Open image tiles and copy them there (repeats from montage2d "load" function, but can't have circular dependencies
    for rowIndex in rowIndices:
      row = self.model.rows[rowIndex]
      groupName = row[1]
      tilePaths = self.model.tileGroups[row[0]]
      print "Will setup for montage:", groupName
      print "With tile filepaths: \n  %s" % "\n  ".join(tilePaths)
      # Create a TrakEM2 Layer for this section
      layer = layerset.getLayer(row[0], 1, True)
      # Save all tile images in the tmpDir folder and add them as Patch instances to the Layer
      pattern = re.compile("^\d+-(\d+)-(\d+)\..*$") # any extension
      for tilePath in tilePaths:
        path = os.path.join(tmpDir, os.path.basename(tilePath) + ".tif")
        if os.path.exists(path):
          syncPrintQ("Tile already as TIFF under tmpDir:\n%s" % path)
          continue
        if tilePath.endswith(".dat"):
          imp = readFIBSEMdat(tilePath, channel_index=0, asImagePlus=True)[0]
        else:
          imp = IJ.openImage(tilePath)
        FileSaver(imp).saveAsTIFF(path)
        patch = Patch.createPatch(project, path)
        patch.setProperty("groupName", groupName)
        layer.add(patch)
        # Parse i, j coordinates from the e.g., ".*_0-0-0.dat" filename
        i_row, i_col = map(int, re.match(pattern, tilePath[tilePath.rfind('_')+1:]).groups())
        # Position tiles so as to overlap tiles by 10%
        x = i_row * 0.9 * imp.getWidth()
        y = i_col * 0.9 * imp.getHeight()
        patch.setLocation(x, y)
      # Resize the display canvas
      layerset.setMinimumDimensions()
      # Update internal quadtree of the layer so it can find the Patch instances
     layer.recreateBuckets()
   # Update TrakEM2 UI
   project.getLayerTree().updateList(layerset)
   # ... and the display slider
   Display.updateLayerScroller(layerset)
   # Show the TrakEM2 display
   Display.getOrCreateFront(project)
   # Ensure the display shows the tab for exporting the CSV file of the montage
   self.addTrakEM2Tab(project)
   # Save the TrakEM2 Project
   project.saveAs(xml_path), False)
   
  def saveTrakEM2MontageCSV(self, project, printOnly):
    """
    To be executed from a button in a custom tab in the TrakEM2 Display.
    """
    display = Display.getOrCreateFront(project)
    tiles = {}
    for patch in display.getLayer().getPatches(False): # visible or invisible: all
      path = patch.getImageFilePath()
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
             "Confirm", "Write montage file\n%s.csv ?" % groupName, JOptionPane.YES_NO_OPTION)
        saveMatrices(groupName, matrices, self.csvDir)
   
  def addTrakEM2Tab(self, project):
   display = Display.getOrCreateFront(project)
   tabs = display.getTabbedPane()
   title = "Manual Montage"
   # Check if the tab is already there
   for i in xrange(tags.getTabCount()):
     if tags.getTitleAt(i) == title:
       syncPrintQ("'Manual Montage' tab already exists.")
       return
   # Add it new
   pane = JPanel()
   b1 = JButton("Save montage CSV", actionPerformed=partial(self.saveTrakEM2MontageCSV, self, project, False))
   pane.add(b1)
   b2 = JButton("Print montage CSV", actionPerformed=partial(self.saveTrakEM2MontageCSV, self, project, True))
   pane.add(b2)
   tabs.add(title, pane)
   display.pack() # repaint
    

  def mouseReleased(self, event):
    if 1 == event.getClickCount() and SwingUtilities.isRightMouseButton(event):
      popup = JPopupMenu()
      popup.add(JMenuItem("Open stack of slice montages",
                          actionPerformed=lambda event: self.openStackOfSliceMontages()))
      popup.add(JMenuItem("Save stack of slice montages...",
                          actionPerformed=lambda event: self.saveStackOfSliceMontages()))
      popup.add(JMenuItem("Open raw images",
                          actionPerformed=lambda event: self.openImagesRows()))
      popup.add(JMenuItem("Delete CSV files for montages...",
                          actionPerformed=lambda event: self.deleteMontageCSVFiles()))
      popup.add(JMenuItem("Montage manually...",
                          actionPerformed=lambda event: self.montageManually()))
      popup.show(event.getComponent(), event.getX(), event.getY())
      
  def valueChanged(self, event):
    if event.getValueIsAdjusting():
      return
    self.firstIndex = event.getFirstIndex()
    self.lastIndex = event.getLastIndex()


# Convert from row index in the view (could e.g. be sorted)  
# to the index in the underlying table model  
#def getSelectedRowIndex(table):
#  viewIndex = table.getSelectionModel().getLeadSelectionIndex()
#  modelIndex = table.convertRowIndexToModel(viewIndex)
#  return modelIndex


def makeMontageTable(groupNames, tileGroups, imp, volumeImg, csvDir, show=True):
  model = SliceTableModel(groupNames, tileGroups)
  # GUI:
  all = JPanel()
  all.setBackground(Color.white)
  gb = GridBagLayout()
  all.setLayout(gb)
  c = GridBagConstraints()
  # Top-left element: search box
  c.gridx = 0
  c.gridy = 0
  c.anchor = GridBagConstraints.CENTER
  c.fill = GridBagConstraints.HORIZONTAL
  search_field = JTextField("")
  gb.setConstraints(search_field, c)
  all.add(search_field)
  # Bottom left, the table, wrapped in a scrollable component
  table = JTable(model)
  table.setAutoCreateRowSorter(True) # to sort the view only, not the data in the underlying TableModel
  table.setRowSelectionAllowed(True);
  table.setSelectionMode(ListSelectionModel.SINGLE_INTERVAL_SELECTION);
  centerRenderer = DefaultTableCellRenderer();
  centerRenderer.setHorizontalAlignment(JLabel.CENTER);
  table.getColumnModel().getColumn(0).setCellRenderer(centerRenderer)
  table.getColumnModel().getColumn(2).setCellRenderer(centerRenderer)
  c.gridx = 0
  c.gridy = 1
  c.anchor = GridBagConstraints.NORTHWEST
  c.fill = GridBagConstraints.BOTH # resize with the frame
  c.weightx = 1.0
  c.gridheight = 2
  jsp = JScrollPane(table)
  jsp.setMinimumSize(Dimension(400, 500))
  gb.setConstraints(jsp, c)
  all.add(jsp)

  # To open images and run operations outside the event dispatch thread
  exe = newFixedThreadPool(min(32, numCPUs() / 2))

  # Enable search by regular expression matching
  search_field.addKeyListener(TypingInSearchField(table, model, search_field)) 

  # Enable opening raw DAT files when double-clicking a row
  opener = RowClickListener(model, exe, imp, csvDir, table)
  table.addMouseListener(opener)

  # Enable pushing enter instead of clicking
  # Instead of a KeyListener, use the input vs action map
  table.getInputMap().put(KeyStroke.getKeyStroke(KeyEvent.VK_ENTER, 0), "enter")
  table.getActionMap().put("enter", Action(opener))
  
  # Enable popup menu on right click over a multi-row selection
  table.getSelectionModel().addListSelectionListener(opener)
  
  frame = JFrame("Slice montages")
  frame.addWindowListener(ExecutorCloser(exe))
  frame.getContentPane().add(all)
  frame.pack()
  frame.setVisible(True)

