import os, sys, re, csv, math
from functools import partial
from itertools import batched

from java.lang import Integer, Runnable, String
from javax.swing import JPanel, JFrame, JTable, JScrollPane, JTextField, ListSelectionModel, SwingUtilities,\
                        JLabel, BorderFactory, JPopupMenu, JMenuItem, AbstractAction, KeyStroke, JOptionPane, JButton
from javax.swing.table import AbstractTableModel, DefaultTableCellRenderer
from java.awt import GridBagLayout, GridBagConstraints, Dimension, Font, Insets, Color
from java.awt.geom import AffineTransform
from java.awt.event import KeyAdapter, MouseAdapter, KeyEvent, ActionListener, WindowAdapter
from javax.swing.event import ListSelectionListener

from ij import IJ, ImagePlus, ImageStack
from ij.io import FileSaver, OpenDialog
from ij.gui import GenericDialog

from ini.trakem2 import Project
from ini.trakem2.display import Display, Patch
from ini.trakem2.imaging.filters import Invert, ResetMinAndMax, EnhanceContrast

from net.imglib2.img.array import ArrayImgs

__labkit_present__ = False
try:
  from sc.fiji.labkit.ui.inputimage import DatasetInputImage
  from sc.fiji.labkit.ui import LabkitFrame
  __labkit_present__ = True
except:
  print "WARNING Labkit isn't installed. Install it via the Fiji updater."

from lib.io import readFIBSEMHeader, readFIBSEMdat, ensureDirsExist, imageInfo, makeNonOverwritingName
from lib.util import syncPrintQ, Task, numCPUs, newFixedThreadPool, newThread
from lib.ui import duplicateInParallel, saveInParallel, ExecutorCloser
from lib.registration import saveMatrices


class SliceTableModel(AbstractTableModel):
  def __init__(self, groupNames, tileGroups, failed, montage_stats):
    self.groupNames = groupNames
    self.tileGroups = tileGroups
    self.rows = []
    self.restore() # populate rows
    self.header = ["Slice index", "Group name", "Num. tiles", "Failed", "Least inliers", "Num. inliers"]
    self.column_class = [Integer, String, Integer, String, Integer, String]
    self.failed = failed
    self.montage_stats = montage_stats # list of [least inliers, "<comma-separated list of inliers>"] 
  def restore(self):
    self.rows = [[i+1, groupName, self.tileGroups[i], self.failed.get(groupName, "")] + self.montage_stats[i]
                 for i, groupName in enumerate(self.groupNames)]
  def getColumnName(self, col):
    return self.header[col]
  def getColumnClass(self, col):
    return self.column_class[col]
  def getRowCount(self):
    return len(self.rows)
  def getColumnCount(self):
    return 6
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
        if text.startswith("section "):
          pattern = re.compile(text[8:])
          match = lambda i, groupName: pattern.search(str(i))
        else:
          pattern = re.compile(text)
          match = lambda i, groupName: pattern.search(groupName)
        self.rows = [[i+1, groupName, self.tileGroups[i]]
                     for i, groupName in enumerate(self.groupNames)
                     if match(i, groupName)]
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
      imp = readFIBSEMdat(self.filepath, channel_index=0, asImagePlus=True, toUnsigned=True)[0]
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
    
  def getRow(self, index):
    # To convert from a table index (which could be sorted differently) to the model index
    return self.model.rows[self.table.convertRowIndexToModel(index)]
  
  def mousePressed(self, event):
    if 2 == event.getClickCount():
      # Open the raw images of the montage at that slice
      rowIndex = event.getSource().rowAtPoint(event.getPoint()) # TODO could use self.firstIndex or the whole range
      self.openImages(rowIndex)
    
  def openImages(self, rowIndex):
    for filepath in self.getRow(rowIndex)[2]:
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
      slice_indices = [self.getRow(rowIndex)[0] for rowIndex in xrange(self.firstIndex, self.lastIndex + 1)] # Already 1-based 
      self.exe.submit(Task(duplicateInParallel, self.imp, slice_indices, n_threads=max(1, numCPUs() -2), shallow=True, show=True, scale=1.0))

  def saveStackOfSliceMontages(self):
    if self.firstIndex > -1 and self.lastIndex > -1:
      gd = GenericDialog("Save stack")
      gd.addMessage("1-based slice indices")
      gd.addNumericField("First slice: ", self.getRow(firstIndex)[0], 0, 6, "")
      gd.addNumericField("Last slice: ", self.getRow(lastIndex)[0], 0, 6, "")
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
      #rowIndices = list(self.table.getSelectedRows())  # Can be wrong if sorting by some other column that the first
      rowIndices = [self.table.convertRowIndexToModel(i) for i in self.table.getSelectedRows()]
      affected = "\n".join(", ".join(map(str, batch)) for batch in batched(rowIndices, 8))
      msg = "Delete CSV files for %i montages:\n%s\nPlease confirm" % (len(rowIndices), affected)
      yn = JOptionPane.showConfirmDialog(self.table, msg, "Delete CSV montage files",
           JOptionPane.YES_NO_OPTION, JOptionPane.WARNING_MESSAGE)
      if JOptionPane.YES_OPTION == yn:
        for i in rowIndices:
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
    newThread(self.manualMontage, rowIndices)
  
  def manualMontage(self, rowIndices):
    """
    Open a TrakEM2 project for the set of sections selected.
    """
    # Make a tmp directory under self.csvDir
    tmpDir = os.path.join(self.csvDir, "tmp")
    ensureDirsExist(tmpDir)
    # Check if a project for this set of sections already exists
    first = self.getRow(rowIndices[ 0])[0] # 1-based
    last  = self.getRow(rowIndices[-1])[0]
    xml_path = os.path.join(tmpDir, "montages-%i-%i.xml" % (first, last))
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
    for rowIndex in xrange(first-1, last): # xrange in 0-based, first and last in 1-based
      row = self.model.rows[rowIndex]
      groupName = row[1]
      tilePaths = self.model.tileGroups[row[0]]
      print "Will setup for montage:", groupName
      print "With tile filepaths: \n  %s" % "\n  ".join(tilePaths)
      # Create a TrakEM2 Layer for this section
      layer = layerset.getLayer(row[0], 0, True)
      # Save all tile images in the tmpDir folder and add them as Patch instances to the Layer
      pattern = re.compile("^\d+-(\d+)-(\d+)\..*$") # any extension
      for tilePath in tilePaths:
        path = os.path.join(tmpDir, os.path.basename(tilePath) + ".tif")
        # Save TIFF versions of the original DAT image tiles
        if os.path.exists(path):
          syncPrintQ("Tile already as TIFF under tmpDir:\n%s" % path)
          info = imageInfo(path)
        else:
          if tilePath.endswith(".dat"):
            imp = readFIBSEMdat(tilePath, channel_index=0, asImagePlus=True)[0]
          else:
            imp = IJ.openImage(tilePath)
          FileSaver(imp).saveAsTiff(path)
          info = {"width": imp.getWidth(),
                  "height": imp.getHeight()}
        # Add Patches to Layer
        # Can't use, loads the image from the path before setting the filters, would have to flush TrakEM2's image cache and reload
        #patch = Patch.createPatch(project, path)
        # Create the Patch manually, which avoids loading the image
        patch = Patch(project, os.path.basename(path),
             info["width"], info["height"],
             info["width"], info["height"],
             ImagePlus.GRAY16, 1.0,
             Color.yellow, False,
             0, pow(2, 16) -1,
             AffineTransform(),
             path)
        patch.setFilters([Invert(), ResetMinAndMax(), EnhanceContrast()])
        project.getLoader().addedPatchFrom(path, patch);
        patch.setProperty("groupName", groupName)
        layer.add(patch)
        # Parse i, j coordinates from the e.g., ".*_0-0-0.dat" filename
        i_row, i_col = map(int, re.match(pattern, tilePath[tilePath.rfind('_')+1:]).groups())
        # Position tiles so as to overlap tiles by 10%
        x = i_col * 0.9 * info["width"]
        y = i_row * 0.9 * info["height"]
        patch.setLocation(x, y)
      # Update internal quadtree of the layer so it can find the Patch instances
      layer.recreateBuckets()
      # Start off mipmap regeneration
      project.getLoader().generateMipMaps(layer.getPatches(True), True)
      # Resize the display canvas
      layerset.setMinimumDimensions()
    # Update TrakEM2 UI
    project.getLayerTree().updateList(layerset)
    # ... and the display slider
    Display.updateLayerScroller(layerset)
    # Show the TrakEM2 display
    Display.getOrCreateFront(project)
    # Ensure the display shows the tab for exporting the CSV file of the montage
    self.addTrakEM2Tab(project)
    # Save the TrakEM2 Project
    project.saveAs(xml_path, False)
  
  def saveTrakEM2MontageCSV(self, project, printOnly, event): # used as actionPerformed for a button
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
             "Confirm", "Write montage file\n%s.csv ?" % groupName, JOptionPane.YES_NO_OPTION):
        saveMatrices(groupName, matrices, self.csvDir)
   
  def addTrakEM2Tab(self, project):
   display = Display.getOrCreateFront(project)
   tabs = display.getTabbedPane()
   title = "FIBSEM section montage"
   # Check if the tab is already there
   for i in xrange(tabs.getTabCount()):
     if tabs.getTitleAt(i) == title:
       syncPrintQ("'Manual Montage' tab already exists.")
       return
   # Add it new
   pane = JPanel()
   b1 = JButton("Save montage CSV", actionPerformed=partial(self.saveTrakEM2MontageCSV, project, False))
   pane.add(b1)
   b2 = JButton("Print montage CSV", actionPerformed=partial(self.saveTrakEM2MontageCSV, project, True))
   pane.add(b2)
   tabs.add(title, pane)
   display.pack() # repaint
  
  
  def openSampledStackForLabkit(self):
    if not __labkit_present__:
      msg = "Labkit needs to be installed from the Fiji updater."
      print msg
      IJ.error(msg)
      return
    gd = GenericDialog("Sample for Labkit")
    gd.addNumericField("Number of sections:", 6, 0)
    gd.addNumericField("Target width:", 400, 0)
    gd.showDialog()
    if gd.wasCanceled():
      return
    num = int(gd.getNextNumber())
    width = int(gd.getNextNumber())
    spacing = int(self.imp.getNSlices() / (num + 1))
    #
    def sampleStack(imp, spacing, width, csvDir):
      stack = ImageStack()
      for i in xrange(spacing, imp.getNSlices(), spacing):
        syncPrintQ("Adding slice %i" % (i+1))
        stack.addSlice(imp.getStack().getProcessor(i).resize(width))
      sample = ImagePlus(imp.getTitle() + " sample for Labkit", stack)
      sample.show() # become the current image
      labkitDir = os.path.join(csvDir, "labkit")
      ensureDirsExist(labkitDir)
      syncPrintQ("Saving sample stack for Labkit under %s" % labkitDir)
      sample_path = os.path.join(labkitDir, makeNonOverwritingName(labkitDir, "sample_sections.tif"))
      FileSaver(sample).saveAsTiff(sample_path)
      OpenDialog.setLastDirectory(labkitDir) # make it easy to then save the classifier and labels into the labkit folder
      syncPrintQ("Opening sample sections with Labkit")
      # Does not respect the 'sample' as argument, takes the current image anyway
      # IJ.run(sample, "Open Current Image With Labkit", "dataset=sample_sections.tif")
      # Make an ImgLib2 image so there's no issues with additional dimensions
      #img = Views.stack([ArrayImgs.unsignedBytes(stack.getProcessor(i+1).getPixels(), [stack.getWidth(), stack.getHeight()])
      #                   for i in xrange(stack.getSize())])
      #LabKitFrame.showForImage(DatasetInputImage(img)) # works
      # Just tell Labkit to load the file, so the folder for saving labels and the classifier will be the same
      LabkitFrame.showForFile(None, sample_path)

    #
    newThread(sampleStack, self.imp, spacing, width, self.csvDir)
  

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
      popup.addSeparator()
      popup.add(JMenuItem("Open sampled stack for Labkit...",
                          actionPerformed=lambda event: self.openSampledStackForLabkit()))
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


class ColorCellRenderer(DefaultTableCellRenderer):
  def __init__(self, colorFn):
    self.colorFn = colorFn
  def getTableCellRendererComponent(self, table, value, isSelected, hasFocus, row, col):
    # Invoke super to get the JLabel of the table cell
    label = DefaultTableCellRenderer.getTableCellRendererComponent(self, table, value, isSelected, hasFocus, row, col)
    # Get a color for the cell background, if any, as a function of cell value
    color = self.colorFn(value)
    if color:
      label.setBackground(color)
    return label

def makeMontageTable(groupNames, tileGroups, imp, volumeImg, csvDir, show=True):
  # Load data for all failed montages
  failed = filter(lambda filename: filename.startswith("failed_montages_"), os.listdir(csvDir))
  failed_groupNames = set()
  if len(failed) > 0:
    failed.sort() # descending, so newest last
    with open(os.path.join(csvDir, failed[-1]), 'r') as f:
      for line in f:
        failed_groupNames.add(line.rstrip()) # without the ending newline character
  # Load stats of pairwise tile connections in each montage
  montage_stats = [] # as long as groupNames
  for groupName in groupNames:
    path = os.path.join(self.csvDir, groupName + ".montage_stats.csv")
    if os.path.exists(path):
      with open(path, 'r') as csvfile:
        reader = csv.reader(csvfile, delimiter=',', quotechar='"')
        reader.next() # skip the header
        inlier_counts = [n_inliers for _, _, n_inliers in reader]
        montage_stats.append(min(inlier_counts), ", ".join(n_inliers))
    else:
      # Either it was deleted or was never written, from a prior version of this software
      montage_stats.append([float('nan'), ""])
  #
  model = SliceTableModel(groupNames, tileGroups, failed_groupNames, montage_stats)
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
  table.getColumnModel().getColumn(3).setCellRenderer(ColorCellRenderer(lambda v: (Color.red if "failed" == v else None)))
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

