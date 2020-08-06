from java.awt import Frame
from org.scijava.ui.swing.script import FileSystemTree
from ij import IJ

class CustomLeafListener(FileSystemTree.LeafListener):
  def __init__(self, texteditor):
    self.texteditor = texteditor
  def leafDoubleClicked(self, fileOb):
    name = fileOb.getName()
    idot = name.rfind('.')
    if -1 == idot:
      print "File name lacks extension"
      return
    # Open depending on what it is  
    extension = name[idot+1:].lower() # in lowercase
    languages = set(["py", "clj", "js", "java", "bs", "ijm", "r", "rb", "sc", "txt", "md"])
    if extension in languages:
      self.texteditor.open(fileOb)
    else:
      # Let ImageJ handle it
      print "Asking ImageJ to open file", fileOb
      IJ.open(fileOb.getAbsolutePath())

# Find the java.awt.Frame of the ScriptEditor
for frame in Frame.getFrames():
  if frame.getClass().getSimpleName() == "TextEditor":
    # Grab its private "tree" instance of FileSystemTree
    field = frame.getClass().getDeclaredField("tree")
    field.setAccessible(True)
    tree = field.get(frame)
    # Remove any registered LeafListener
    map(tree.removeLeafListener, tree.getLeafListeners())
    # Add your own
    tree.addLeafListener(CustomLeafListener(frame))
