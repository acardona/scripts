# A graphical user interface to keep track of files opened with Fiji
# and with the possibility of taking notes for each,
# which are persisted in a CSV file.
#
# Select a row to see its file path and note, if any.
# Double-click the file path to open the image corresponding to the selected table row.
# Click the "Open folder" to open the containing folder.
# Click the "Edit note" to start editing it, and "Save note" to sync to a CSV file.
#
# Albert Cardona 2020-11-22


from javax.swing import JPanel, JFrame, JTable, JScrollPane, JButton, JTextField, \
                        JTextArea, ListSelectionModel, SwingUtilities, JLabel, BorderFactory
from javax.swing.table import AbstractTableModel
from java.awt import GridBagLayout, GridBagConstraints, Dimension, Font, Insets, Color
from java.awt.event import KeyAdapter, MouseAdapter, KeyEvent
from javax.swing.event import ListSelectionListener
from java.lang import Thread, Integer, String, System
import os, csv
from datetime import datetime
from ij import ImageListener, ImagePlus, IJ, WindowManager
from ij.io import OpenDialog
from java.util.concurrent import Executors, TimeUnit
from java.util.concurrent.atomic import AtomicBoolean

# EDIT here: where you want the CSV file to live
csv_image_notes = os.path.join(System.getProperty("user.home"),
                               ".fiji-image-notes.csv") # as a hidden file in my home

# Generic read and write CSV functions
def openCSV(filepath, header_length=1):
  with open(filepath, 'r') as csvfile:
    reader = csv.reader(csvfile, delimiter=',', quotechar="\"")
    header_rows = [reader.next() for i in xrange(header_length)]  
    rows = [columns for columns in reader]
    return header_rows, rows

def writeCSV(filepath, header, rows):
   """ filepath: where to write the CSV file
       header: list of header titles
       rows: list of lists of column values
       Writes first to a temporary file, and upon successfully writing it in full,
       then rename it to the target filepath, overwriting it.
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

# Load the CSV file if it exists, otherwise use an empty data structure
if os.path.exists(csv_image_notes):
  header_rows, entries = openCSV(csv_image_notes, header_length=1)
  header = header_rows[0]
else:
  header = ["name", "first opened", "last opened", "filepath", "notes"]
  entries = []

# Map of file paths vs. index of entries
image_paths = {row[3]: i for i, row in enumerate(entries)}

# Flag to set to True to request the table model data be saved to the CSV file
requested_save_csv = AtomicBoolean(False)

def saveTable():
  def after():
    note_status.setText("Saved.")
    edit_note.setEnabled(True)
    save_note.setEnabled(False)
  while requested_save_csv.getAndSet(False):
    writeCSV(csv_image_notes, header, entries)
    SwingUtilities.invokeLater(after)

# Every 500 milliseconds, save to CSV only if it has been requested
# This background thread is shutdown when the JFrame window is closed
exe = Executors.newSingleThreadScheduledExecutor()
exe.scheduleAtFixedRate(saveTable, 0, 500, TimeUnit.MILLISECONDS)

# A model (i.e. the data) of the JTable listing all opened files
class TableModel(AbstractTableModel):
  def getColumnName(self, col):
    return header[col]
  def getColumnClass(self, col): # for e.g. proper numerical sorting
    return String # all as strings
  def getRowCount(self):
    return len(entries)
  def getColumnCount(self):
    return len(header) -2 # don't show neither the full filepath nor the notes in the table
  def getValueAt(self, row, col):
    return entries[row][col]
  def isCellEditable(self, row, col):
    return False # none editable
  def setValueAt(self, value, row, col):
    pass # none editable


# Create the UI: a 3-column table and a text area next to it
# to show and write notes for any selected row, plus some buttons:
all = JPanel()
all.setBackground(Color.white)
gb = GridBagLayout()
all.setLayout(gb)
c = GridBagConstraints()

table = JTable(TableModel())
table.setSelectionMode(ListSelectionModel.SINGLE_SELECTION)
table.setCellSelectionEnabled(True)
table.setAutoCreateRowSorter(True) # to sort the view only, not the data in the underlying TableModel

c.gridx = 0
c.gridy = 0
c.anchor = GridBagConstraints.NORTHWEST
c.fill = GridBagConstraints.BOTH # resize with the frame
c.weightx = 1.0
c.gridheight = 3
jsp = JScrollPane(table)
jsp.setMinimumSize(Dimension(400, 500))
gb.setConstraints(jsp, c)
all.add(jsp)

c.gridx = 1
c.gridy = 0
c.gridheight = 1
c.gridwidth = 2
path = JTextArea("")
path.setEditable(False)
path.setMargin(Insets(4, 4, 4, 4))
path.setLineWrap(True)
path.setWrapStyleWord(True)
gb.setConstraints(path, c)
all.add(path)

def openAtFolder(event):
  directory = os.path.dirname(path.getText())
  od = OpenDialog("Open", directory, None)
  filepath = od.getPath()
  if filepath:
    IJ.open(filepath)

c.gridx = 3
c.gridy = 0
c.gridwidth = 1
c.fill = GridBagConstraints.NONE
c.weightx = 0.0 # let the previous ('path') component stretch as much as possible
parent = JButton("Open folder", actionPerformed=openAtFolder)
gb.setConstraints(parent, c)
all.add(parent)

c.gridx = 1
c.gridy = 1
c.weighty = 1.0
c.gridwidth = 3
c.fill = GridBagConstraints.BOTH
textarea = JTextArea()
textarea.setBorder(BorderFactory.createCompoundBorder(
                    BorderFactory.createLineBorder(Color.BLACK),
                    BorderFactory.createEmptyBorder(10, 10, 10, 10)))
textarea.setLineWrap(True)
textarea.setWrapStyleWord(True) # wrap text by cutting lines at whitespace
textarea.setEditable(False)
font = textarea.getFont().deriveFont(18.0)
textarea.setFont(font)
textarea.setPreferredSize(Dimension(500, 500))
gb.setConstraints(textarea, c)
all.add(textarea)

c.gridx = 1
c.gridy = 2
c.gridwidth = 1
c.weightx = 0.5
c.weighty = 0.0
note_status = JLabel("")
gb.setConstraints(note_status, c)
all.add(note_status)

def clickEditButton(event):
  edit_note.setEnabled(False)
  save_note.setEnabled(True)
  note_status.setText("Editing...")
  textarea.setEditable(True)
  textarea.requestFocus()	

c.gridx = 2
c.gridy = 2
c.weightx = 0.0
c.anchor = GridBagConstraints.NORTHEAST
edit_note = JButton("Edit note", actionPerformed=clickEditButton)
edit_note.setEnabled(False)
gb.setConstraints(edit_note, c)
all.add(edit_note)

def requestSave(event):
  # Update table model data
  rowIndex = table.getSelectionModel().getLeadSelectionIndex()
  entries[rowIndex][-1] = textarea.getText()
  # Signal synchronize to disk
  requested_save_csv.set(True)

c.gridx = 3
c.gridy = 2
save_note = JButton("Save note", actionPerformed=requestSave)
save_note.setEnabled(False)
gb.setConstraints(save_note, c)
all.add(save_note)

def cleanup(event):
  exe.shutdown()
  ImagePlus.removeImageListener(open_imp_listener)

frame = JFrame("CSV", windowClosing=cleanup)
frame.getContentPane().add(all)
frame.pack()
frame.setVisible(True)


def addOrUpdateEntry(imp):
  """
  This function runs in response to an image being opened,
  and finds out whether a new entry should be added to the table (and CSV file)
  or whether an existing entry ought to be added,
  or whether there's nothing to do because it's a new image not opened from a file.
  
  imp: an ImagePlus
  """
  # Was the image opened from a file?
  fi = imp.getOriginalFileInfo()
  if not fi:
    # Image was created new, not from a file: ignore
    return
  filepath =  os.path.join(fi.directory, fi.fileName)
  # Had we opened this file before?
  index = image_paths.get(filepath, None)
  now = datetime.now().strftime("%Y-%m-%d %H:%M")
  if index is None:
    # File isn't yet in the table: add it
    entries.append([fi.fileName, now, now, filepath, ""])
  else:
    # File exists: edit its last seen date
    entries[index][2] = now
  # Update table to reflect changes to the underlying data model
  def repaint():
    table.updateUI()
    table.repaint()
  SwingUtilities.invokeLater(repaint) # must run in the event dispatch thread
  # Request writing changes to the CSV file
  requested_save_csv.set(True)

# A listener to react to images being opened via an ij.io.Opener from e.g. "File - Open"
class OpenImageListener(ImageListener):
  def imageClosed(self, imp):
    pass
  def imageUpdated(self, imp):
    pass
  def imageOpened(self, imp):
    addOrUpdateEntry(imp)

open_imp_listener = OpenImageListener() # keep a reference for unregistering on window closing
ImagePlus.addImageListener(open_imp_listener)

class TypingListener(KeyAdapter):
  def keyPressed(self, event):
    rowIndex = table.getSelectionModel().getLeadSelectionIndex()
    if event.getSource().getText() != entries[rowIndex][-1]:
      note_status.setText("Unsaved changes.")

textarea.addKeyListener(TypingListener())

# React to a row being selected by showing the corresponding note
# in the textarea to the right
class TableSelectionListener(ListSelectionListener):
  def valueChanged(self, event):
    if event.getValueIsAdjusting():
      return
    if note_status.getText() == "Unsaved changes.":
      if IJ.showMessageWithCancel("Alert", "Save current note?"):
        requestSave(None)
      else:
        # Stash current note in the log window
        IJ.log("Discarded note for image at:")
        IJ.log(path.getText())
        IJ.log(textarea.getText())
        IJ.log("===")
    # Must run later in the context of the event dispatch thread
    # when the latter has updated the table selection
    def after():
      rowIndex = table.getSelectionModel().getLeadSelectionIndex()
      path.setText(entries[rowIndex][-2])
      path.setToolTipText(path.getText()) # for mouse over to show full path
      textarea.setText(entries[rowIndex][-1])
      textarea.setEditable(False)
      edit_note.setEnabled(True)
      save_note.setEnabled(False)
      note_status.setText("Saved.") # as in entries and the CSV file
    SwingUtilities.invokeLater(after)

table.getSelectionModel().addListSelectionListener(TableSelectionListener())

# Open an image on double-clicking the filepath label
# but merely bring its window to the front if already opened:
class PathOpener(MouseAdapter):
  def mousePressed(self, event):
    if 2 == event.getClickCount():
      # If the file is opened, bring it to the front
      ids = WindowManager.getIDList()
      if ids: # can be null
        is_open = False # to allow bringing to front more than one window
                        # in cases where it has been opened more than once
        for ID in ids:
          imp = WindowManager.getImage(ID)
          fi = imp.getOriginalFileInfo()
          filepath = os.path.join(fi.directory, fi.fileName)
          if File(filepath).equals(File(event.getText())):
            imp.getWindow().toFront()
            is_open = True
        if is_open:
          return
      # otherwise open it
      rowIndex = table.getSelectionModel().getLeadSelectionIndex()
      IJ.open(entries[rowIndex][-2])

path.addMouseListener(PathOpener())

# Enable changing text font size in all components by control+shift+(plus|equals)/minus
components = list(all.getComponents()) + [table, table.getTableHeader()]
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
        if table.getRowCount() > 0:
          r = table.prepareRenderer(table.getCellRenderer(0, 1), 0, 1)
          table.setRowHeight(max(table.getRowHeight(), r.getPreferredSize().height))
      SwingUtilities.invokeLater(repaint)


for component in components:
  component.addKeyListener(FontSizeAdjuster())
