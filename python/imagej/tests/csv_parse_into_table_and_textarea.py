from javax.swing import JPanel, JFrame, JTable, JScrollPane, JButton,\
                        JTextArea, ListSelectionModel, SwingUtilities
from javax.swing.table import AbstractTableModel
from java.awt import GridBagLayout, GridBagConstraints, Dimension, Font
from java.awt.event import KeyAdapter, MouseAdapter, KeyEvent
from javax.swing.event import ListSelectionListener
from java.lang import Thread, Integer, String

import csv, os

# CSV with 3 columns: ApplicantID, Preference, and Motivation
csvfilepath = "/home/albert/lab/presentations/20201130_I2K_Janelia/tutorial_2.csv"

def openCSV(filepath, header_length=0):
  with open(filepath, 'r') as csvfile:
    reader = csv.reader(csvfile, delimiter=',', quotechar="\"")
    header_rows = [reader.next() for i in xrange(header_length)]  
    rows = [columns for columns in reader]
    return header_rows, rows

# Parse input file
header_rows, applicants = openCSV(csvfilepath, header_length=2)

# Parse evaluation file, if any, otherwise create an empty list
# CSV with 2 columns: ApplicantID, Accepted -- of which we need only the second
acceptedfilepath = csvfilepath + "-accepted.csv"
accepted = [row[1] for row in openCSV(acceptedfilepath, header_length=1)[1]] \
             if os.path.exists(acceptedfilepath) \
             else [""] * len(applicants)

def writeCSV(filepath, header, rows):
   """ filepath: where to write the CSV file
       header: list of header titles
       rows: list of lists of column values
   """
   with open(filepath + ".tmp", 'wb') as csvfile:
     w = csv.writer(csvfile, delimiter=',', quotechar="\"",  
                    quoting=csv.QUOTE_NONNUMERIC)
     if header:
       w.writerow(header)
     for row in rows:
       w.writerow(row)
     # when written in full, replace the old one if any
     os.rename(filepath + ".tmp", filepath)

# Will write the evaluation file every time a table cell of the 3rd column is edited
def writeAccepted():
  """ uses the global 'table' variable. """
  model = table.getModel()
  rows = [[model.getValueAt(y, x) for x in [0, 2]]
          for y in xrange(model.getRowCount())]
  writeCSV(acceptedfilepath, ["ApplicantID", "Accepted"], rows)

column_names = ["Index"] + header_rows[1][:2] + ["Accepted"]
column_classes = [Integer, Integer, Integer, String]

# Blend both CSV files into 3 columns: ApplicantID, Preference and Accepted 
class TableModel(AbstractTableModel):
  def getColumnName(self, col):
    return column_names[col]
  def getColumnClass(self, col): # for e.g. proper numerical sorting
    return column_classes[col]
  def getRowCount(self):
    return len(applicants)
  def getColumnCount(self):
    return len(column_names)
  def getValueAt(self, row, col):
    if 0 == col:
      return row + 1 # index
    if 3 == col:
      return accepted[row]
    return int(applicants[row][col -1])
  def isCellEditable(self, row, col):
    return 3 == col
  def setValueAt(self, value, row, col):
    if 3 == col:
      old = self.getValueAt(row, col)
      if old == value:
        return
      # else, update value in the underlying data structure
      accepted[row] = value
      # ... and save the evaluation CSV file in a new thread
      # to avoid potentially slow operations in the event dispatch thread
      t = Thread(writeAccepted)
      t.setPriority(Thread.NORM_PRIORITY)
      t.start()


# Create the UI: a 3-column table and a text area next to it
# to show the Motivation column of any selected row:
all = JPanel()
gb = GridBagLayout()
all.setLayout(gb)
c = GridBagConstraints()
table = JTable(TableModel())
table.setSelectionMode(ListSelectionModel.SINGLE_SELECTION)
table.setAutoCreateRowSorter(True) # to sort the view only, not the data in the underlying TableModel
jsp = JScrollPane(table)
jsp.setPreferredSize(Dimension(200, 500))
c.anchor = GridBagConstraints.NORTHWEST
c.fill = GridBagConstraints.BOTH # resize with the frame
gb.setConstraints(jsp, c)
all.add(jsp)
c.gridx = 1
c.weightx = 1.0 # take any additionally available horizontal space
c.weighty = 1.0
textarea = JTextArea()
textarea.setLineWrap(True)
textarea.setWrapStyleWord(True) # wrap text by cutting at whitespace
textarea.setEditable(False) # avoid changing the text, as any changes wouldn't be persisted to disk
font = textarea.getFont().deriveFont(20.0)
textarea.setFont(font)
textarea.setPreferredSize(Dimension(500, 500))
gb.setConstraints(textarea, c)
all.add(textarea)
frame = JFrame("CSV")
frame.getContentPane().add(all)
frame.pack()
frame.setVisible(True)

# React to a row being selected by showing the corresponding Motivation entry
# in the textarea to the right, so that it's more readable
class TableSelectionListener(ListSelectionListener):
  def valueChanged(self, event):
    if event.getValueIsAdjusting():
      return
    # Must run later, when the event dispatch thread
    # has updated the selection
    def after():
      rowIndex = table.getSelectionModel().getLeadSelectionIndex()
      textarea.setText(applicants[rowIndex][2])
    SwingUtilities.invokeLater(after)

table.getSelectionModel().addListSelectionListener(TableSelectionListener())

# Enable changing text size in the textarea
class FontSizeAdjuster(KeyAdapter):
  def keyPressed(self, event):
    key = event.getKeyCode()
    if event.isControlDown() and event.isShiftDown(): # like in e.g. a web browser
      font = event.getSource().getFont()
      size = font.getSize2D() # floating-point: important for later use of deriveFont
                              # Otherwise deriveFont with an integer alters the style instead.
      sign = 0
      if KeyEvent.VK_MINUS == key:
        sign = -1
      elif KeyEvent.VK_PLUS or KeyEvent.VK_EQUALS == key:
        sign = 1
      if 0 != sign:
        size = max(8.0, size + sign * 0.5)
        if size != font.getSize2D():
          event.getSource().setFont(font.deriveFont(size))

textarea.addKeyListener(FontSizeAdjuster())
