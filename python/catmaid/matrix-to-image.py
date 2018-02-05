# Albert Cardona 2018

import sys
import os
from lib.util.matrix import createIntImage
from lib.util.csv import parseLabeledMatrix

if 1 == len(sys.argv):
    print("""

Usage:
$ python matrix-to-image.py path/to/file.csv

""")
    sys.exit(0)

filename = sys.argv[1]

row_names, col_names, matrix = parseLabeledMatrix(filename)
image = createIntImage(matrix)
image.save(os.path.basename(filename) + ".png")

