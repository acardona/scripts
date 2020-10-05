# Script to print every image stack slice, one per page.

from javax.print import PrintService, PrintServiceLookup
from java.awt.print import PrinterJob, Paper
from javax.print.attribute import HashPrintRequestAttributeSet
from javax.print.attribute.standard import Copies, Sides, MediaSizeName, Chromaticity, \
                                           OrientationRequested, NumberUp, PrintQuality
from ij.plugin.filter import Printer
from ij import IJ, ImagePlus

# The name of the printer as it appears in the operating system settings
# If you don't know it, run first:
# for printer in PrintServiceLookup.lookupPrintServices(None, attr):
#   print printer.getName()
printer_name = "TS5100"

# Attributes for the desired printing service
attr = HashPrintRequestAttributeSet()
attr.add(Copies(1)) # if more than 1, use in combination with attributes SheetCollate and MultipleDocumentHandling
attr.add(MediaSizeName.ISO_A4) # or .NA_LETTER or .ISO_C6 (which is the same as .NA_LETTER)
attr.add(Sides.ONE_SIDED) # or .DUPLEX or .TUMBLE
attr.add(Chromaticity.COLOR) # or .MONOCHROME
attr.add(OrientationRequested.PORTRAIT) # or .LANDSCAPE
attr.add(NumberUp(1)) # just one per page, but could ask for e.g. 4 (tiled as 2x2)
attr.add(PrintQuality.HIGH) # or .DRAFT (lowest) or .NORMAL (whatever that means)

# To define the margins, use attribute MediaPrintableArea which defines a rectangle

# Find the printer and print each image stack slice
pj = PrinterJob.getPrinterJob()
for printer in PrintServiceLookup.lookupPrintServices(None, attr):
  if printer.getName() == printer_name:
    print printer
    pj.setPrintService(printer)
    # Print every slice of an ImagePlus:
    p = Printer()
    pj.setPrintable(p)
    f = p.getClass().getDeclaredField("imp")
    f.setAccessible(True)
    stack = IJ.getImage().getStack()
    for i in xrange(1, stack.getSize() + 1):
      f.set(p, ImagePlus("", stack.getProcessor(i)))
      pj.print()
    break

# To change the paper size, do:
#format = pj.defaultPage()
#paper = format.getPaper()
#print paper.getWidth() / 72.0, paper.getHeight() / 72.0
## default is letter, at 8.5 x 11 inches 
#paper.setSize(394.936, 841.536) # A4, units are 1/72 of an inch

# ... and then define your own Printable ... a pain.


