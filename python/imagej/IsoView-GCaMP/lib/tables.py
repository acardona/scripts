import sys, re, os
from lib.registration import loadMatrices
from lib.img import showAlignedImg
from lib.util import syncPrintQ
from lib.ui import RowClickListener, showTable
from net.imglib2 import FinalInterval
from functools import partial


def openChunkVolume(groupNames, montage_img, csvDir, properties, chunk_matrices_csv_filename):
  # Extract Z interval from the name of the matrices CSV file
  pattern = re.compile("^matrices_(\d+)-(\d+).csv$")
  start, end = map(int, pattern.search(chunk_matrices_csv_filename).groups())
  # Load the matrices
  matrices = loadMatrices(chunk_matrices_csv_filename[:-4], csvDir) # name without the csv
  
  return showAlignedImg(montage_img,
                 FinalInterval([montage_img.dimension(0), montage_img.dimension(1)]), # whole 2D
                 groupNames[start, end], # Only the interval within the chunk
                 properties,
                 matrices, # a list as long as the number of chunks
                 rotate=None,
                 title_addendum=chunk_matrices_csv_filename)

def uiOpenChunkVolume(groupNames, montage_img, csvDir, properties, table_model, rowIndex):
  openChunkVolume(groupNames, montage_img, csvDir, properties, table_model.getValueAt(rowIndex, 0))


def makeTableChunks(groupNames, montage_img, csvDir, properties):
  """
  Open a JTable listing one chunk per row, with a right-click menu to do:
    - open the chunk in a stack, virtual but with a preloading cache.
    - run pair-wise cosyne similarity for all subsequent pairs of sections in a chunk,
      and open it in another, sortable table.
  """
  # Find all "matrices_\d+-\d+.csv" files:
  chunks = {}
  pattern = re.compile("^matrices_(\d+)-(\d+).csv$")
  for root, dirs, filenames in os.walk(csvDir):
    for filename in filenames:
      if filename.startswith("matrices_"):
        m = pattern.search(filename)
        if m:
          start, end = map(int, m.groups())
          chunks[start] = [filename, start, end]
        else:
          syncPrintQ("No match for file: " + filename)
  
  rows = [chunks[key] for key in sorted(chunks.keys())]
  
  table, frame = showTable(rows,
      title="Table of chunks",
      column_names=["file", "start", "end"],
      dataType=String,
      width=400, height=500,
      showTable=True,
      windowClosing=None, onCellClickFn=None, onRowClickFn=None,
      singleBlockSelection=True, renderRightColumns=[1, 2])
  
  listener = RowClickListener(table,
                              double_click_fn=partial(uiOpenChunkVolume, groupNames, montage_img, csvDir, properties),
                              right_click_fns=[]) # TODO to run evaluation tools
                                                  # and tools to invalidate relevant CSVs (chunk matrices and CSVs for comparisons around particular sections)
  table.addMouseListener(listener)
  
  return table, frame, listener
  

