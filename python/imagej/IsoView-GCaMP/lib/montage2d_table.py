import os, sys, re, csv, math
from functools import partial

from java.lang import Integer, Runnable, String, Float
from javax.swing import JPanel, JFrame, JTable, JScrollPane, JTextField, ListSelectionModel, SwingUtilities,\
                        JLabel, BorderFactory, JPopupMenu, JMenuItem, AbstractAction, KeyStroke, JOptionPane, JButton
from javax.swing.table import AbstractTableModel, DefaultTableCellRenderer
from java.awt import GridBagLayout, GridBagConstraints, Dimension, Font, Insets, Color
from java.awt.geom import AffineTransform
from java.awt.event import KeyAdapter, MouseAdapter, KeyEvent, ActionListener, WindowAdapter
from javax.swing.event import ListSelectionListener
from java.util.concurrent import Callable

from ij import IJ, ImagePlus, ImageStack
from ij.io import FileSaver, OpenDialog, SaveDialog
from ij.gui import GenericDialog
from ij.process import ImageProcessor

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
from lib.util import syncPrintQ, Task, numCPUs, newFixedThreadPool, newThread, batched, printException, newScheduledExecutor, RemoveFile, WaitAndShutdown
from lib.ui import duplicateInParallel, saveInParallel, ExecutorCloser
from lib.registration import saveMatrices


class SliceTableModel(AbstractTableModel):
  def __init__(self, groupNames, tileGroups, failed, montage_stats):
    self.groupNames = groupNames
    self.tileGroups = tileGroups
    self.rows = []
    self.header = ["Slice index", "Group name", "Num. tiles", "Failed", "Least inliers", "Num. inliers"]
    self.column_class = [Integer, String, Integer, String, Integer, String]
    self.failed = failed # a set of groupName
    self.montage_stats = montage_stats # list of [least inliers, "<comma-separated list of inliers>"]
    self.restore() # populate rows
    
  def restore(self):
    self.rows = [[i+1, groupName, self.tileGroups[i], "failed" if groupName in self.failed else ""] + self.montage_stats[i]
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
        self.rows = [[i+1, groupName, self.tileGroups[i],  "failed" if groupName in self.failed else ""] + self.montage_stats[i]
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
    def filterTable(event, self):
      if KeyEvent.VK_ENTER == event.getKeyCode():
        self.model.filterTable(self.search_field.getText())
      elif KeyEvent.VK_ESCAPE == event.getKeyCode():
        self.search_field.setText("")
        self.model.restore()
      def repaint():
        self.table.updateUI()
        self.table.repaint()
      SwingUtilities.invokeLater(repaint) # executed by the event dispatch thread
    newThread(filterTable, event, self)

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
      printException()

class Action(AbstractAction):
  def __init__(self, opener):
    self.opener = opener
  def actionPerformed(self, event):
    table = event.getSource()
    model = table.getSelectionModel()
    rowIndex = model.getLeadSelectionIndex() # first selected row
    opener.openImages(rowIndex)

class RowClickListener(MouseAdapter, ListSelectionListener):
  def __init__(self, model, exe, imp, volumeImg, csvDir, table, overlap, offset, params_pixels, runEvaluateMontages):
    self.model = model
    self.exe = exe
    self.imp = imp
    self.volumeImg = volumeImg
    self.csvDir = csvDir
    self.table = table
    self.overlap = overlap
    self.offset = offset
    self.params_pixels = params_pixels
    self.runEvaluateMontages = runEvaluateMontages
    self.firstIndex = -1
    self.lastIndex = -1
    
  def getRow(self, index):
    # To convert from a table index (which could be sorted differently) to the model index
    return self.model.rows[self.table.convertRowIndexToModel(index)]
  
  def mousePressed(self, event):
    if 2 == event.getClickCount():
      # Set the imp slice to that of the row
      rowIndex = event.getSource().rowAtPoint(event.getPoint())
      row = self.getRow(rowIndex)
      if self.imp and self.imp.getWindow():
        self.imp.setSlice(row[0]) # TODO use an ScheduledExecutorService

  def openImages(self, rowIndex):
    """
    Will map rowIndex from the table to the model data rows using self.getRow
    """
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
      self.exe.submit(Task(saveInParallel, targetDir, self.imp, slice_indices, n_threads=numThreads, show=True, scale=scale, incremental=incremental))

  def deleteMontageCSVFiles(self):
    if self.table.getSelectedRowCount() > 0:
      #rowIndices = list(self.table.getSelectedRows())  # Can be wrong if sorting by some other column that the first
      rowIndices = [self.getRow(i)[0] for i in self.table.getSelectedRows()]
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
    modelRowIndices = [self.table.convertRowIndexToModel(i) for i in self.table.getSelectedRows()]
    newThread(self.manualMontage, modelRowIndices)
  
  def manualMontage(self, modelRowIndices):
    """
    Open a TrakEM2 project for the set of sections selected.
    """
    # Make a tmp directory under self.csvDir
    tmpDir = os.path.join(self.csvDir, "tmp")
    ensureDirsExist(tmpDir)
    # Check if a project for this set of sections already exists
    modelRowIndices = list(sorted(modelRowIndices))
    first = modelRowIndices[0] # 0-based
    last  = modelRowIndices[-1] # 0-based
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
    for rowIndex in modelRowIndices:
      row = self.model.rows[rowIndex]
      groupName = row[1]
      tilePaths = self.model.tileGroups[row[0]]
      print "Will setup for montage:", groupName
      print "With tile filepaths: \n  %s" % "\n  ".join(tilePaths)
      # Load the montage CSV file if it exists
      montage_csv = os.path.join(self.csvDir, groupName + ".csv")
      coords = []
      if os.path.exists(montage_csv):
        with open(montage_csv, 'r') as csvfile:
          reader = csv.reader(csvfile, delimiter=',', quotechar='"')
          reader.next() # skip header
          for v in reader:
            coords.append([float(v[2]), float(v[5])])
      # Create a TrakEM2 Layer for this section
      layer = layerset.getLayer(row[0], 0, True)
      # Save all tile images in the tmpDir folder and add them as Patch instances to the Layer
      pattern = re.compile("^\d+-(\d+)-(\d+)\..*$") # any extension
      for i, tilePath in enumerate(tilePaths):
        # Create a Patch preprocessor script in BeanShell to laod the data directly from the DAT file,
        # avoiding having to save intermediate TIFF files.
        # A recipe for opening channel at index 0 of the DAT file:
        if tilePath.lower().endswith(".dat"):
          script = """
import sc.fiji.io.FIBSEM_Reader;
import java.io.FileInputStream;
import ij.ImagePlus;
var path = "%s";
var reader = new FIBSEM_Reader();
var header = reader.parseHeader(new FileInputStream(path));
imp2 = reader.readFIBSEM(header, new FileInputStream(path), FIBSEM_Reader.openAsFloat);
// imp and patch exist as injected variables
imp.setProcessor(path, imp2.getStack().getProcessor(1)); // channel index zero, 1-based
          """ % tilePath
        else:
          script = """
import ij.IJ;
path = "%s";
imp.setProcessor(path, IJ.openImage(path).getProcessor());
          """ % tilePath
        # Write the script to disk with a unique name for each image
        script_path = os.path.join(tmpDir, os.path.basename(tilePath) + ".bsh")
        with open(script_path, 'w') as sf:
          sf.write(script)
          # Ensure file is written to disk now
          sf.flush()
          os.fsync(sf.fileno())
        # Add Patches to Layer
        # Can't use, loads the image from the path before setting the filters, would have to flush TrakEM2's image cache and reload
        #patch = Patch.createPatch(project, path)
        # Create the Patch manually, which avoids loading the image
        patch = Patch(project, os.path.basename(tilePath),
             0, 0, 0, 0, # dimensions will be populated upon setting the script path
             ImagePlus.GRAY16, 1.0,
             Color.yellow, False,
             0, pow(2, 16) -1,
             AffineTransform(),
             tilePath + ".nope") # bogus file path: script will generate the image
        patch.setFilters([Invert(), ResetMinAndMax(), EnhanceContrast()])
        patch.setPreprocessorScriptPath(script_path)
        patch.setProperty("groupName", groupName)
        layer.add(patch)
        # Position the Patch like in te CSV file if possible, since some tiles may be correctly positioned
        if len(coords) > 0:
          x, y = coords[i]
        else:
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
    # Delete the layer at Z=0 if empty
    layer0 = layerset.getLayers().get(0)
    if layer0.isEmpty():
      project.findLayerThing(layer0).remove(False)
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
        saveMatrices(groupName, matrices, self.csvDir)
   
  def addTrakEM2Tab(self, project):
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
        ip = imp.getStack().getProcessor(i)
        ip.setInterpolationMethod(ImageProcessor.BILINEAR)
        stack.addSlice(ip.resize(width))
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
  
  def evaluateSelectedMontages(self):
    if self.firstIndex > -1 and self.lastIndex > -1:
      slice_indices = [self.getRow(index)[0] for index in xrange(self.firstIndex, self.lastIndex + 1)]
      gd = GenericDialog("Evaluate selected montages")
      gd.addMessage("Will evaluate %i montages" % len(slice_indices))
      gd.addNumericField("Number of threads: ", max(1, numCPUs()), 0, 4, "")
      gd.addNumericField("PhaseCorrelation scale: ", 0.5, 2, 6, "")
      gd.showDialog()
      if not gd.wasOKed():
        return
      numThreads = int(gd.getNextNumber())
      PCscale = gd.getNextNumber()
      self.evaluateMontageRange(slice_indices=slice_indices, numThreads=numThreads, PCscale=PCscale)
 
  def evaluateMontageRange(self, slice_indices=None, numThreads=None, PCscale=0.5):
    if self.firstIndex > -1 and self.lastIndex > -1:
      if slice_indices is None or numThreads is None or PCscale is None):
        # Choose a range
        gd = GenericDialog("Evaluate range of montages")
        gd.addMessage("1-based slice indices")
        gd.addNumericField("First slice: ", self.getRow(self.firstIndex)[0], 0, 6, "")
        gd.addNumericField("Last slice: ", self.getRow(self.lastIndex)[0], 0, 6, "")
        gd.addNumericField("Number of threads: ", max(1, numCPUs()), 0, 4, "")
        gd.addNumericField("PhaseCorrelation scale: ", 0.5, 2, 6, "")
        gd.showDialog()
        if not gd.wasOKed():
          return
        firstIndex, lastIndex = int(gd.getNextNumber()), int(gd.getNextNumber())
        slice_indices = range(firstIndex, lastIndex + 1) # Already 1-based
        numThreads = int(gd.getNextNumber())
        PCscale = gd.getNextNumber()
      # run
      task = Task(self.runEvaluateMontages, self.model.groupNames, self.model.tileGroups, self.csvDir, slice_indices, self.overlap, self.offset, self.params_pixels, self.imp, PCscale=PCscale, n_threads=numThreads)
      # When done, open the table
      task.continuation = Task(makeMontageEvaluationTable, self.model.groupNames, self.model.tileGroups, self.imp, self.csvDir, self.overlap, self.offset, self.params_pixels, self.runEvaluateMontages, show=True)
      self.exe.submit(task)
    

  def evaluateAllMontages(self):
    self.exe.submit(Task(self.runEvaluateMontages, self.model.groupNames, self.model.tileGroups, self.csvDir, range(1, self.imp.getNSlices() + 1), self.overlap, self.offset, self.params_pixels, self.imp, n_threads=numCPUs()))

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
      popup.addSeparator()
      popup.add(JMenuItem("Evaluate selected montages...",
                          actionPerformed=lambda event: self.evaluateSelectedMontages()))
      popup.add(JMenuItem("Evaluate montage range...",
                          actionPerformed=lambda event: self.evaluateMontageRange()))
      popup.add(JMenuItem("Evaluate all montages",
                          actionPerformed=lambda event: self.evaluateAllMontages()))
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
    else:
      label.setBackground(Color.white)
    return label

def makeMontageTable(groupNames, tileGroups, imp, volumeImg, csvDir, overlap, offset, params_pixels, runEvaluateMontages, show=True):
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
  for i, groupName in enumerate(groupNames):
    try:
      path = os.path.join(csvDir, groupName + ".montage_stats.csv")
      if 1 == len(tileGroups[i]):
        montage_stats.append([0, ""]) # single tile, no montage necessary
      elif os.path.exists(path):
        with open(path, 'r') as csvfile:
          reader = csv.reader(csvfile, delimiter=',', quotechar='"')
          reader.next() # skip the header
          inlier_counts = [n_inliers for _, _, n_inliers in reader] # all as strings
          montage_stats.append([min(int(s) for s in inlier_counts), ", ".join(inlier_counts)])
      else:
        # Either it was deleted or was never written, from a prior version of this software
        montage_stats.append([0, "no stats file"])
    except:
      syncPrintQ("Reading stats failed for groupName: " + groupName)
      montage_stats.append([0, "no stats file"])
      printException()
  #
  model = SliceTableModel(groupNames, tileGroups, failed_groupNames, montage_stats)
  # GUI:
  frame, table, search_field, all = makeFrame(model, "Slice montages", show=show)

  centerRenderer = DefaultTableCellRenderer()
  centerRenderer.setHorizontalAlignment(JLabel.CENTER)
  table.getColumnModel().getColumn(0).setCellRenderer(centerRenderer)
  table.getColumnModel().getColumn(2).setCellRenderer(centerRenderer)
  table.getColumnModel().getColumn(3).setCellRenderer(ColorCellRenderer(lambda v: (Color.red if "failed" == v else None)))

  # To open images and run operations outside the event dispatch thread
  exe = newFixedThreadPool(min(32, numCPUs() / 2))
  frame.addWindowListener(ExecutorCloser(exe))

  # Enable search by regular expression matching
  search_field.addKeyListener(TypingInSearchField(table, model, search_field)) 

  # Enable opening raw DAT files when double-clicking a row
  opener = RowClickListener(model, exe, imp, volumeImg, csvDir, table, overlap, offset, params_pixels, runEvaluateMontages)
  table.addMouseListener(opener)

  # Enable pushing enter instead of clicking
  # Instead of a KeyListener, use the input vs action map
  table.getInputMap().put(KeyStroke.getKeyStroke(KeyEvent.VK_ENTER, 0), "enter")
  table.getActionMap().put("enter", Action(opener))
  
  # Enable popup menu on right click over a multi-row selection
  table.getSelectionModel().addListSelectionListener(opener)
  

def makeFrame(model, title, show=True):
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
  table.setRowSelectionAllowed(True)
  table.setSelectionMode(ListSelectionModel.SINGLE_INTERVAL_SELECTION)
  #table.setPreferredSize(Dimension(400, 500))
  c.gridx = 0
  c.gridy = 1
  c.anchor = GridBagConstraints.NORTHWEST
  c.fill = GridBagConstraints.BOTH # resize with the frame
  c.weightx = 1.0
  c.weighty = 1.0
  c.gridheight = 1
  jsp = JScrollPane(table)
  jsp.setMinimumSize(Dimension(400, 500))
  gb.setConstraints(jsp, c)
  all.add(jsp)

  frame = JFrame(title)
  frame.getContentPane().add(all)
  frame.pack()
  if show:
    frame.setVisible(True)

  return frame, table, search_field, all


class EvaluateMontageModel(AbstractTableModel):
  def __init__(self, groupNames, tileGroups, imp, csvDir, montage_scores):
    self.groupNames = groupNames
    self.tileGroups = tileGroups
    self.imp = imp
    if self.imp:
      # From groupNames the index can be wrong: some slices might have been ignored
      self.labels = {self.imp.getStack().getSliceLabel(index): index for index in xrange(1, self.imp.getNSlices() + 1)}
    else:
      self.labels = {}
    self.csvDir = csvDir
    self.montage_scores = montage_scores
    self.header = ["Slice", "Group name", "pair", "CC", "dx", "dy", "d", "CC2"]
    self.column_class = [Integer, String, String, Float, Float, Float, Float, Float]
    self.rows = []
    self.restore() # populate rows

  def restore(self):
    self.rows = self.makeRows()

  def makeRows(self):
    # Add one row for each tile-vs-tile registration,
    # so a section with 2 tiles will have 1 row
    # and a section with 4 tiles will have 4 rows.
    rows = []
    for i, groupName in enumerate(self.groupNames): # sorted
      scores = self.montage_scores.get(groupName, None)
      if scores:
        for score in scores:
          rows.append([self.model.labels.get(groupName, i+1), groupName] + score) # slice index as 1-based
    if 0 == len(rows):
      syncPrintQ("No rows found for EvaluateMontageModels. groupName keys in montage_scores were:")
      for key in self.montage_scores:
        syncPrintQ(key)
    return rows

  def getColumnName(self, col):
    return self.header[col]
  def getColumnClass(self, col):
    return self.column_class[col]
  def getRowCount(self):
    return len(self.rows)
  def getColumnCount(self):
    return len(self.header)
  def getValueAt(self, row, col):
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
        # Filtering what's displayed, so incremental filtering is possible with multiple consecutive searches
        textOriginal = text
        # First: by column name
        text = text.lower()
        iless = text.find("<")
        imore = text.find(">")
        iequal = text.find("=")
        if iless > -1 or imore > -1 or iequal > -1:
          i = filter(lambda x: x > -1, [iless, imore, iequal])[0]
          col_name = text[0:i].strip()
          for k, name in enumerate(self.header):
            if name.lower() == col_name:
              s = text[i+1:].strip()
              self.rows = filter(lambda row: str(row[k]).startswith(s), self.rows)
              return
        # Second: by regular expression across the first 3 columns
        pattern = re.compile(textOriginal)
        self.rows = filter(lambda row: pattern.search(str(row[0])) or pattern.search(row[1]) or pattern.search(row[2]), self.rows)
    except:
      self.restore()
      printException()


class ScheduledTask(Runnable):
  def __init__(self, ob):
    self.ob = ob
  def run(self):
    task = self.ob.task
    if task:
      try:
        task.call()
      except:
        printException()
      # prevent running the task more than once
      if self.ob.task == task:
        self.ob.task = None # no synchronisation but risk is very low

class EvaluationRowClickListener(MouseAdapter, ListSelectionListener):
  def __init__(self, table, model, imp, overlap, offset, params_pixels, runEvaluateMontages, scheduler):
    self.table = table
    self.model = model
    self.imp = imp
    self.overlap = overlap
    self.offset = offset
    self.params_pixels = params_pixels
    self.runEvaluateMontages = runEvaluateMontages
    self.firstIndex = -1 # in rendered table, not in model rows. Use self.getRow to get the model row.
    self.lastIndex = -1  # idem
    #
    self.task = None
    scheduler.scheduleAtFixedRate(ScheduledTask(self), 0, 500) # check every 0.5 seconds
 
  def getRow(self, index):
    # To convert from a table index (which could be sorted differently) to the model index
    return self.model.rows[self.table.convertRowIndexToModel(index)]
  
  def mousePressed(self, event):
    if 2 == event.getClickCount():
      # Set the imp slice to that of the row
      rowIndex = event.getSource().rowAtPoint(event.getPoint())
      row = self.getRow(rowIndex)
      if self.imp and self.imp.getWindow():
        self.task = Task(self.imp.setSlice, row[0]) # will be run by the scheduler

  def showOverlaps(self):
    if -1 == self.firstIndex:
      syncPrintQ("No rows selected.")
      return
    sliceIndex = self.getRow(self.firstIndex)[0] # 1-based
    self.task = Task(self.runEvaluateMontages, self.model.groupNames, self.model.tileGroups, self.model.csvDir, [sliceIndex], self.overlap, self.offset, self.params_pixels, debug=True, debugJustShowOverlaps=True) # will be run by the scheduler

  def exportCSV(self):
    sd = SaveDialog("Save table to CSV", "montage-evaluation", ".csv")
    folder = sd.getDirectory()
    if not folder:
      return # user cancelled
    path = os.path.join(folder, sd.getFileName())
    with open(path, 'w') as f:
     f.write(", ".join(self.model.header))
     f.write("\n")
     f.write("\n".join(", ".join(str(v) for v in row) for row in self.model.makeRows()))
     # Ensure it's written
     f.flush()
     os.fsync(f.fileno())

  def removeMontageCSVFiles(self):
    exe = newFixedThreadPool(numCPUs())
    yn = JOptionPane.showConfirmDialog(self.table, "Delete %i montage CSV files?" % self.table.getSelectedRowCount(), "Delete CSV montage files", JOptionPane.YES_NO_OPTION, JOptionPane.WARNING_MESSAGE)
    if JOptionPane.YES_OPTION != yn:
      return
    try:
      futures = []
      for i in self.table.getSelectedRows():
        futures.append(exe.submit(RemoveFile(os.path.join(self.model.csvDir, self.getRow(i)[1] + ".csv"))))
      exe.submit(WaitAndShutdown(futures, exe))
    except:
      printException()
    finally:
      exe.shutdown()

  def mouseReleased(self, event):
    if 1 == event.getClickCount() and SwingUtilities.isRightMouseButton(event):
      #popup = JPopupMenu()
      #popup.add(JMenuItem("Open stack of slice montages",
      #                    actionPerformed=lambda event: self.openStackOfSliceMontages()))
      popup = JPopupMenu()
      popup.add(JMenuItem("Show montage overlaps", actionPerformed=lambda event: self.showOverlaps()))
      popup.add(JMenuItem("Export CSV...", actionPerformed=lambda event: self.exportCSV()))
      popup.add(JMenuItem("Remove montage CSV files", actionPerformed=lambda event: self.removeMontageCSVFiles()))
      popup.show(event.getComponent(), event.getX(), event.getY())
      
  def valueChanged(self, event):
    if event.getValueIsAdjusting():
      return
    self.firstIndex = event.getFirstIndex()
    self.lastIndex = event.getLastIndex()


def makeMontageEvaluationTable(groupNames, tileGroups, imp, csvDir, overlap, offset, params_pixels, runEvaluateMontages, show=True):
  # Load evaluation data if any
  score_files = filter(lambda filename: filename.endswith(".montage_scores.csv"), os.listdir(csvDir))
  montage_scores = {}
  for filename in score_files: # order doesn't matter, later will be sorted
    try:
      with open(os.path.join(csvDir, filename), 'r') as csvfile:
        reader = csv.reader(csvfile, delimiter=',', quotechar='"')
        reader.next() # skip header
        # Keyed by groupName as parsed from the filename
        groupName = filename[0:-19]
        rows = [row[0:1] + map(float, row[1:]) for row in reader]
        if len(rows[0]) < 6:
          syncPrintQ("Obsolete montage evaluation file:\n%s" % filename)
          continue
        montage_scores[groupName] = rows
    except:
      syncPrintQ("Failed to load file %s" % filename)
      printException()
  
  syncPrintQ("montage_scores: %i entries" % len(montage_scores))
  #
  try:
    scheduler = newScheduledExecutor()
    model = EvaluateMontageModel(groupNames, tileGroups, imp, csvDir, montage_scores)
    # GUI
    frame, table, search_field, all = makeFrame(model, "Slice montage evaluation", show=show)
    frame.addWindowListener(ExecutorCloser(scheduler.exe))
    # Enable search by regular expression matching
    search_field.addKeyListener(TypingInSearchField(table, model, search_field)) 
    # Add mouse events
    opener = EvaluationRowClickListener(table, model, imp, overlap, offset, params_pixels, runEvaluateMontages, scheduler)
    table.addMouseListener(opener)
    # Enable pushing enter instead of clicking
    # Instead of a KeyListener, use the input vs action map
    table.getInputMap().put(KeyStroke.getKeyStroke(KeyEvent.VK_ENTER, 0), "enter")
    table.getActionMap().put("enter", Action(opener))
    # Enable popup menu on right click over a multi-row selection
    table.getSelectionModel().addListSelectionListener(opener)


    return frame, table, search_field, all
  except:
    printException()




