# Open a text file full of file paths, one per line,
# list each path in a table row
# and provide means to specify a regex for filtering
# and a base path to prepend to each path.
#
# For Jim Truman's GAL4 line folders, run:
# $ find -name "*.lsm" -printf "%h/%f\n" >> ~/Desktop/larvalscreen.txt
# Or:
# $ find -regex "^.*\.(lsm|tif|jpg|mov|bz2)$" -printf "%h/%f\n" >> ~/Desktop/larvalscreen.txt
# Or find all files:
# $ find . -type f -printf %p\n" > ~/Desktop/larvalscreen.txt
#

from ij import IJ
from javax.swing import JFrame, JPanel, JLabel, JScrollPane, JTable, JTextField, BoxLayout, SwingUtilities
from javax.swing.table import AbstractTableModel
from java.awt.event import MouseAdapter, KeyAdapter, KeyEvent, WindowAdapter
from java.awt import Cursor
from java.util.concurrent import Executors
import re
import os
import sys

reload(sys)
sys.setdefaultencoding('utf8')

exe = Executors.newFixedThreadPool(2)

class TableModel(AbstractTableModel):
  def __init__(self, txt_file):
    self.paths = []
    with open(txt_file, 'r') as f:
      for line in f:
        self.paths.append(line[:-1]) # remove line break
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
    regex = regex + "" # turn into a python string
    if not regex:
      IJ.showMessage("Enter a valid search text string")
      return
    if '/' == regex[0]:
        pattern = re.compile(regex[1:])
      self.filtered_paths = [path for path in self.paths if re.match(pattern, path)]
    else:
      self.filtered_paths = [path for path in self.paths if -1 != path.find(regex)]      
    

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
  table = JTable(model)
  jsp = JScrollPane(table)
  regex_label = JLabel("Search: ")
  regex_field = JTextField(20)
  top = JPanel()
  top.add(regex_label)
  top.add(regex_field)
  top.setLayout(BoxLayout(top, BoxLayout.X_AXIS))
  base_path_label = JLabel("Base path:")
  base_path_field = JTextField(50)
  bottom = JPanel()
  bottom.add(base_path_label)
  bottom.add(base_path_field)
  bottom.setLayout(BoxLayout(bottom, BoxLayout.X_AXIS))
  all = JPanel()
  all.add(top)
  all.add(jsp)
  all.add(bottom)
  all.setLayout(BoxLayout(all, BoxLayout.Y_AXIS))
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

txt_file = "/home/albert/Desktop/larvalscreen-2.txt"
model = TableModel(txt_file)
SwingUtilities.invokeLater(launch(model))
