# Albert Cardona 2018-09-18
# Edit font size for Jython Interpreter
from common import AbstractInterpreter
from java.awt import Font

def getField(the_class, fieldname, instance):
  field = the_class.getDeclaredField(fieldname)
  field.setAccessible(True)
  return field.get(instance)

def run(fontsize):
  # Get map of all open scripting interpreters
  instances = getField(AbstractInterpreter, "instances", None) # static
  if 0 == len(instances):
    print "No instances open!"
    return
  # Filter Jython_Interpreter instances
  jis = [instance for instance in instances.values() if instance.getClass().getName() == "Jython.Jython_Interpreter"]
  if 0 == len(jis):
    print "No Jython instances open!"
    return
  # The Jython Intepreter
  ji = jis[0]
  # Get text fields
  screen = getField(AbstractInterpreter, "screen", ji) # JTextArea
  prompt = getField(AbstractInterpreter, "prompt", ji) # JTextArea
  # Edit font size
  font = screen.getFont()
  font2 = Font(font.getName(), font.getStyle(), fontsize)
  print font
  print font2
  screen.setFont(font2)
  prompt.setFont(font2)

run(18)