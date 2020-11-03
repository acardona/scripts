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
from javax.swing import JFrame, JPanel, JLabel, JScrollPane, JTable, JTextField, JButton, SwingUtilities
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


# EDIT HERE, or leave as None (a dialog will open and ask for the .txt file)

# The path to the file listing the file paths to tabulate
txt_file = None  # Set to e.g. "/path/to/list.txt"



# Ensure UTF-8 encoding
reload(sys)
sys.setdefaultencoding('utf8')

exe = Executors.newFixedThreadPool(2)

class Filter(Predicate):
  def __init__(self, fn):
    self.test = fn

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
    if not regex:
      IJ.showMessage("Enter a valid search text string")
      return
    fn = None
    if '/' == regex[0]:
      fn = partial(re.match, re.compile(regex[1:]))
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
      row = table.rowAtPoint(event.getPoint())
      def openImage():
        IJ.open(os.path.join(self.base_path_field.getText(), model.filtered_paths[row]))
      exe.submit(openImage)

class EnterListener(KeyAdapter):
  def __init__(self, table, table_model, frame):
    self.table_model = table_model
    self.table = table
    self.frame = frame
  def keyPressed(self, event):
    if KeyEvent.VK_ENTER == event.getKeyCode():
      self.frame.setCursor(Cursor.getPredefinedCursor(Cursor.WAIT_CURSOR))
      ins = self
      def repaint():
        ins.table.updateUI()
        ins.table.repaint()
        ins.frame.setCursor(Cursor.getPredefinedCursor(Cursor.DEFAULT_CURSOR))
      def filterRows():
        ins.table_model.filter(event.getSource().getText())
        SwingUtilities.invokeLater(repaint)
      exe.submit(filterRows)

class Closing(WindowAdapter):
  def windowClosed(self, event):
    exe.shutdownNow()

def makeUI(model):
  # Components:
  table = JTable(model)
  jsp = JScrollPane(table)
  regex_label = JLabel("Search: ")
  regex_field = JTextField(20)
  base_path_label = JLabel("Base path:")
  base_path_field = JTextField(50)
  # Panel for all components
  all = JPanel()
  all.setBorder(EmptyBorder(20, 20, 20, 20))
  layout, c = GridBagLayout(), GC()
  all.setLayout(layout)
  # First row: label and regex text field
  c.gridx = 0; c.gridy = 0; c.anchor = GC.NORTHWEST; c.fill = GC.NONE; c.weighty = 0.0
  layout.setConstraints(regex_label, c)
  all.add(regex_label)
  c.gridx = 1; c.fill = GC.HORIZONTAL; c.weightx = 1.0
  layout.setConstraints(regex_field, c)
  all.add(regex_field)
  # Second row: the table
  c.gridx = 0; c.gridy = 1; c.fill = GC.BOTH; c.gridwidth = 2; c.weightx = 1.0; c.weighty = 1.0
  layout.setConstraints(jsp, c)
  all.add(jsp)
  # Third row: the base path
  c.gridy = 2; c.fill = GC.NONE; c.gridwidth = 1; c.weightx = 0.0; c.weighty = 0.0
  layout.setConstraints(base_path_label, c)
  all.add(base_path_label)
  c.gridx = 1; c.fill = GC.HORIZONTAL; c.weightx = 1.0
  layout.setConstraints(base_path_field, c)
  all.add(base_path_field)  
  # Window frame
  frame = JFrame("File paths")
  frame.getContentPane().add(all)
  frame.setDefaultCloseOperation(JFrame.DISPOSE_ON_CLOSE)
  frame.addWindowListener(Closing())
  frame.pack()
  frame.setVisible(True)
   # Listeners
  regex_field.addKeyListener(EnterListener(table, model, frame))
  table.addMouseListener(RowClickListener(base_path_field))
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
