# Open a text file full of file paths, one per line,
# list each path in a table row
# and provide means to specify a regex for filtering
# and a base path to prepend to each path.
#
# To generate such a list from a directory,
# run this in the command line to find all files:
# $ find . -type f -printf "%p\n" > ~/Desktop/list.txt
#
# Albert Cardona 2018-05-15

from ij import IJ
from ij.io import OpenDialog
from javax.swing import JFrame, JPanel, JLabel, JScrollPane, JTable, JTextField, JButton, \
                        SwingUtilities, AbstractAction, KeyStroke
from javax.swing.border import EmptyBorder
from javax.swing.table import AbstractTableModel
from java.awt.event import MouseAdapter, KeyAdapter, KeyEvent, WindowAdapter
from java.awt import Cursor, GridBagLayout, GridBagConstraints as GC
from java.util import ArrayList
from java.util.concurrent import Executors
from java.util.function import Predicate
from functools import partial
import re
import os
import sys

try: # try-except block allows users with default FIJI to run the script without KLB installation
  from org.janelia.simview.klb import KLB 
except ImportError:
  print "Warning: KLB format unavailable"
  KLB = None

from net.imglib2.img.display.imagej import ImageJFunctions as IL


# EDIT HERE, or leave as None (a dialog will open and ask for the .txt file)

# The path to the file listing the file paths to tabulate
txt_file = None  # Set to e.g. "/path/to/list.txt"
base_path = "/home/albert/LarvalScreen/"

# Laptop via sshfs
txt_file = "/Volumes/zfs/barnesc/flylight-backups/LarvalScreen/manifest.txt"
base_path = "/Volumes/zfs/barnesc/flylight-backups/LarvalScreen/"

# At LMB desktop:
txt_file = "/home/albert/LarvalScreen.txt"
basepath = "/home/albert/zstore1/Light_Microscopy_Library/Confocal_Images/"

# For I2K 2020 workshop
#txt_file = "/home/albert/lab/presentations/20201130_I2K_Janelia/data/list.txt"
#base_path = "/home/albert/lab/presentations/20201130_I2K_Janelia/data/"


# Ensure UTF-8 encoding
reload(sys)
sys.setdefaultencoding('utf8')

exe = Executors.newFixedThreadPool(2)

class Filter(Predicate):
  """ Convenient class for the collections streaming,
      otherwise would have to write this cryptic snippet to create one on the fly:
        type("Filter", (Predicate,), {"test": fn})()
      instead of:
        Filter(fn)
  """
  def __init__(self, fn):
    self.test = fn # shortcut, or alternative way of defining a class method named "test"



class TableModel(AbstractTableModel):
  def __init__(self, txt_file):
    self.paths = ArrayList()
    with open(txt_file, 'r') as f:
      for line in f:
        self.paths.add(line[:-1]) # remove line break
    self.filtered_paths = self.paths
  def getColumnName(self, col):
    return "Path"
  def getRowCount(self):
    return len(self.filtered_paths)
  def getColumnCount(self):
    return 1
  def getValueAt(self, row, col):
    return self.filtered_paths[row]
  def isCellEditable(self, row, col):
    return False
  def setValueAt(self, value, row, col):
    pass
  def remove(self, row):
    pass
  def filter(self, regex):
    # regex is a string
    if not regex: # null or empty string
      self.filtered_paths = self.paths # reset: show all
      IJ.showMessage("Enter a valid search text string")
      return
    fn = None
    if '/' == regex[0]:
      fn = partial(re.search, re.compile(regex[1:]))
    else:
      fn = lambda path: -1 != path.find(regex)
    try:
      self.filtered_paths = self.paths.parallelStream().filter(Filter(fn)).toArray()
    except:
      print sys.exc_info()

class RowClickListener(MouseAdapter):
  def __init__(self, base_path_field):
    self.base_path_field = base_path_field
  def mousePressed(self, event):
    if 2 == event.getClickCount():
      table = event.getSource()
      model = table.getModel()
      rowIndex = table.rowAtPoint(event.getPoint())
      def openImage():
        IJ.open(os.path.join(self.base_path_field.getText(), model.filtered_paths[rowIndex]))
      exe.submit(openImage)

class EnterListener(KeyAdapter):
  def __init__(self, table):
    self.table = table
  def keyPressed(self, event):
    if KeyEvent.VK_ENTER == event.getKeyCode():
      regex_field = event.getSource()
      frame = regex_field.getTopLevelAncestor() # the JFrame window
      frame.setCursor(Cursor.getPredefinedCursor(Cursor.WAIT_CURSOR))
      def repaint():
        self.table.updateUI()
        self.table.repaint()
        frame.setCursor(Cursor.getPredefinedCursor(Cursor.DEFAULT_CURSOR))
      def filterRows():
        self.table.getModel().filter(regex_field.getText())
        SwingUtilities.invokeLater(repaint)
      exe.submit(filterRows)

class OpenImageFromTableCell(AbstractAction):
  def actionPerformed(self, event):
    table = event.getSource()
    rowIndex = table.getSelectionModel().getLeadSelectionIndex() # first selected row
    rel_path = table.getModel().filtered_paths[rowIndex]
    # UI component hierarchy: JTable -> JViewPort -> JScrollPane -> JPanel
    base_path_field = table.getParent().getParent().getParent().getComponents()[-1] # last one
    base_path = base_path_field.getText()
    def openImage():
      print rel_path
      if rel_path.endswith(".klb"):
        if(KLB==None):
          print "Cannot open KLB due to missing module"
        try:
          klb = KLB.newInstance()
          img = klb.readFull(os.path.join(base_path, rel_path))
          IL.wrap(img, rel_path).show()
        except:
          print sys.exc_info()
      else:
        print "via IJ.open"
        IJ.open(os.path.join(base_path, rel_path))
    exe.submit(openImage)
    

class ArrowListener(KeyAdapter):
  def __init__(self, table, regex_field):
    self.table = table
    self.regex_field = regex_field
  def keyPressed(self, event):
    # If at the top of the table, focus the regex_field when pushing arrow up
    if event.getSource() == self.table and KeyEvent.VK_UP == event.getKeyCode():
      if 0 == self.table.getSelectedRow():
        self.regex_field.requestFocusInWindow()
    # If at the regex_field, focus the first row of the table when pushing arrow down
    elif event.getSource() == self.regex_field and KeyEvent.VK_DOWN == event.getKeyCode():
      self.table.requestFocusInWindow()
      sm = self.table.getSelectionModel()
      sm.clearSelection()
      sm.setLeadSelectionIndex(0)

class Closing(WindowAdapter):
  def windowClosing(self, event):
    exe.shutdownNow() # free resources: otherwise the exe thread pool remains alive
    event.getSource().dispose()

# Verbose, but simple to read:
def add(parent, child,
        gridx=0, gridy=0,
        anchor=GC.NORTHWEST, fill=GC.NONE,
        weightx=0.0, weighty=0.0,
        gridwidth=1):
  c = GC()
  c.gridx = gridx
  c.gridy = gridy
  c.anchor = anchor
  c.fill = fill
  c.weightx = weightx
  c.weighty = weighty
  c.gridwidth = gridwidth
  """
  # Same, more flexible, less verbose: BUT FAILS at parent, child args
  kv = locals() # dict of local variables including the function arguments
  c = GC()
  for key, value in kv.iteritems():
    setattr(c, key, value)
  """
  #
  parent.getLayout().setConstraints(child, c)
  parent.add(child)

"""
# Too clever
def add(parent, child, **constraints):
  "Add a child component to a parent component that has a GridBagLayout,
   with a defined set of default constraints that are updated using the given ones. "
  # Desirable defaults
  params = {"gridx": 0, "gridy": 0, "gridwidth": 1,
            "anchor": GC.NORTHWEST, "fill": GC.NONE,
            "weightx": 0.0, "weighty": 0.0}
  # Adjust entries as necessary
  params.update(constraints)
  # Set each constraint
  c = GC()
  for k, v in params.iteritems():
    setattr(c, k, v) # i.e. c.gridx = params["gridx"]
  # Add the child component with constraints
  parent.getLayout().setConstraints(child, c)
  parent.add(child)
"""

def makeUI(model):
  # Components:
  table = JTable(model)
  jsp = JScrollPane(table)
  regex_label = JLabel("Search: ")
  regex_field = JTextField(20)
  base_path_label = JLabel("Base path:")
  base_path_field = JTextField(50)
  if base_path is not None:
    base_path_field.setText(base_path)
  # Panel for all components
  all = JPanel()
  all.setBorder(EmptyBorder(20, 20, 20, 20))
  layout, c = GridBagLayout(), GC()
  all.setLayout(layout)
  # First row: label and regex text field
  add(all, regex_label, gridx=0, gridy=0) # with default constraints
  add(all, regex_field, gridx=1, gridy=0, fill=GC.HORIZONTAL, weightx=1.0)
  # Second row: the table
  add(all, jsp, gridx=0, gridy=1, fill=GC.BOTH, gridwidth=2, weightx=1.0, weighty=1.0) # full weights so it stretches when resizing
  # Third row: the base path
  add(all, base_path_label, gridx=0, gridy=2)
  add(all, base_path_field, gridx=1, gridy=2, fill=GC.HORIZONTAL, weightx=1.0)
  # Window frame
  frame = JFrame("File paths")
  frame.getContentPane().add(all)
  #frame.setDefaultCloseOperation(JFrame.DISPOSE_ON_CLOSE)
  frame.addWindowListener(Closing())
  frame.pack()
  frame.setVisible(True)
   # Listeners
  regex_field.addKeyListener(EnterListener(table))
  table.addMouseListener(RowClickListener(base_path_field))
  al = ArrowListener(table, regex_field)
  table.addKeyListener(al)
  regex_field.addKeyListener(al)
  # Instead of a KeyListener, use the input vs action map
  table.getInputMap().put(KeyStroke.getKeyStroke(KeyEvent.VK_ENTER, 0), "enter")
  table.getActionMap().put("enter", OpenImageFromTableCell())
  #
  return model, table, regex_field, frame

def launch(model):
  def run():
    makeUI(model)
  return run


if txt_file is None:
  od = OpenDialog("Choose a text file listing file paths")
  txt_file = od.getPath()
  
if txt_file:
  model = TableModel(txt_file)
  SwingUtilities.invokeLater(launch(model))


# FOR THE I2K WORKSHOP:
# Enable changing text font size in all components by control+shift+(plus|equals)/minus
components = []
tables = []
frames = []
def addFontResizing():
  global frames
  containers = [frame for frame in JFrame.getFrames()
                if frame.getTitle() == "File paths" and frame.isVisible()]
  frames = containers[:]
  from java.awt import Container
  while len(containers) > 0:
    for component in containers.pop(0).getComponents():
      if isinstance(component, JTable):
        tables.append(component)
        components.append(component)
        components.append(component.getTableHeader())
      elif isinstance(component, Container):
        containers.append(component)
      components.append(component)
  #
  for component in components:
    #print type(component).getSimpleName()
    component.addKeyListener(FontSizeAdjuster())

class FontSizeAdjuster(KeyAdapter):
  def keyPressed(self, event):
    if event.isControlDown() and event.isShiftDown(): # like in e.g. a web browser
      sign = {KeyEvent.VK_MINUS: -1,
              KeyEvent.VK_PLUS: 1,
              KeyEvent.VK_EQUALS: 1}.get(event.getKeyCode(), 0)
      if 0 == sign: return
      # Adjust font size of all UI components
      for component in components:
        font = component.getFont()
        if not font: continue
        size = max(8.0, font.getSize2D() + sign * 0.5)
        if size != font.getSize2D():
          component.setFont(font.deriveFont(size))
      def repaint():
        # Adjust the height of a JTable's rows (why it doesn't do so automatically is absurd)
        for table in tables:
          if table.getRowCount() > 0:
            r = table.prepareRenderer(table.getCellRenderer(0, 0), 0, 0)
            table.setRowHeight(max(table.getRowHeight(), r.getPreferredSize().height))
        for frame in frames:
          if frame.isVisible():
            frame.pack()
            frame.repaint()
      SwingUtilities.invokeLater(repaint)

SwingUtilities.invokeLater(addFontResizing)
