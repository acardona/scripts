import sys, re, os
from lib.registration import loadMatrices
from lib.img import showAlignedImg
from lib.util import syncPrintQ, printException, newThread
from lib.ui import RowClickListener, showTable
from lib.pixels import pairwiseCosyneSimilarity
from net.imglib2 import FinalInterval
from functools import partial
from java.lang import String, Number, Integer, Double
from net.imglib2.view import Views
from collections import defaultdict


def openVolume(groupNames, img, matrices, properties, matrices_csv_filename):
  # Alias showAlignedImg to also return the first and last slice indices
  imgA, impA = showAlignedImg(img,
                 FinalInterval([img.dimension(0), img.dimension(1)]), # whole 2D
                 groupNames,
                 properties,
                 matrices, # a list as long as the number of slices
                 rotate=None,
                 title_addendum=" - %s" % matrices_csv_filename)
  return imgA, impA, 0, img.dimension(2) - 1

def openChunkVolume(groupNames, montage_img, csvDir, properties, chunk_matrices_csv_filename):
  # Extract Z interval from the name of the matrices CSV file
  pattern = re.compile("^matrices_(\d+)-(\d+).csv$")
  start, end = map(int, pattern.search(chunk_matrices_csv_filename).groups())
  # Load the matrices
  matrices = loadMatrices(chunk_matrices_csv_filename[:-4], csvDir) # name without the csv
  # Crop
  dim2d = [montage_img.dimension(0), montage_img.dimension(1)]
  img = Views.zeroMin(Views.interval(montage_img, [0, 0, start], [dim2d[0] -1, dim2d[1] -1, end - 1]))
  
  imgA, impA = showAlignedImg(img,
                 FinalInterval(dim2d), # whole 2D
                 groupNames[start:end], # Only the interval within the chunk
                 properties,
                 matrices, # a list as long as the number of slices in a chunk
                 rotate=None,
                 title_addendum=" - %s" % chunk_matrices_csv_filename)
   
  # Fix stack labels
  stack = impA.getStack()
  for i in xrange(stack.size()):
    stack.setSliceLabel(str(start + i), i + 1) # 1-based
   
  return imgA, impA, start, end

def uiOpenChunkVolume(groupNames, montage_img, csvDir, properties, table_model, rowIndex):
  try:
    newThread(openChunkVolume, groupNames, montage_img, csvDir, properties, table_model.getValueAt(rowIndex, 0))
  except:
    printException()


def makeTableCosyneSimilarity(openVolumeFn):
  # Load a virtual aligned volume
  imgA, impA, start, end = openVolumeFn()
  # Compute for all pairs of adjacent sections, in parallel
  cs = pairwiseCosyneSimilarity(imgA)
  
  table, frame = showTable(zip(("%i-%i" % (i, i+1) for i in xrange(start, end)), cs), # two columns: indices and score
      title="Cosyne similarities for sections %i-%i" % (start, end),
      column_names=["pair", "score"],
      dataType=String,
      width=400, height=500,
      showTable=True,
      windowClosing=None, onCellClickFn=None, onRowClickFn=None,
      singleBlockSelection=True, renderRightColumns=[0, 1])
  

def makeTableChunks(groupNames, montage_img, csvDir, properties):
  """
  Open a JTable listing one chunk per row, with a right-click menu to do:
    - open the chunk in a stack, virtual but with a preloading cache.
    - run pair-wise cosyne similarity for all subsequent pairs of sections in a chunk,
      and open it in another, sortable table.
  """
  # Find all "matrices_\d+-\d+.csv" files:
  chunks = defaultdict(lambda: [None] * 6)
  pattern1 = re.compile("^matrices_(\d+)-(\d+).csv$")
  pattern2 = re.compile("^matrices_(\d+)-(\d+)_optimizer_stats.csv$")
  for root, dirs, filenames in os.walk(csvDir):
    for filename in filenames:
      if filename.startswith("matrices_"):
        # Test against chunk matrix filename pattern
        m = pattern1.search(filename)
        if m:
          start, end = map(int, m.groups())
          entry = chunks[start]
          entry[0] = filename
          entry[1] = start
          entry[2] = end
          continue
        # Test against chunk matrix optimizer stats CSV filename pattern
        m = pattern2.search(filename)
        if m:
          start, end = map(int, m.groups())
          try:
            with open(filename, 'r') as csvfile:
              reader = csv.reader(csvfile, delimiter=',', quotechar='"')
              # First line contains parameter names
              headerParams = reader.next()
              # Second line the values
              maxIterations, stats_min, stats_max = reader.next() # as strings
              #
              entry = chunks[start]
              entry[3] = int(maxIterations)
              entry[4] = float(stats_min)
              entry[5] = float(stats_max)
              continue
          except:
            syncPrintQ("Failed to parse CSV file %s" % filename)
        # Else
        syncPrintQ("No match for file: " + filename)
  
  rows = [chunks[key] for key in sorted(chunks.keys())]
  
  table, frame = showTable(rows,
      title="Table of chunks",
      column_names=["file", "start", "end", "maxIterations", "stats_min", "stats_max"],
      dataType=[String, Integer, Integer, Integer, Double, Double]
      width=800, height=500,
      showTable=True,
      windowClosing=None, onCellClickFn=None, onRowClickFn=None,
      singleBlockSelection=True, renderRightColumns=[1, 2])
  
  def launchCosSimForChunk(table_model, rowIndex):
    newThread(makeTableCosyneSimilarity, partial(openChunkVolume, groupNames, montage_img, csvDir, properties, table_model.getValueAt(rowIndex, 0)))
  
  def launchCosSimForAll(table_model, rowIndex):
    newThread(makeTableCosyneSimilarity, partial(openVolume, groupNames, montage_img, csvDir, properties, "matrices.csv"))

  commands = [("Compute cosyne similarity", launchCosSimForChunk),
               "Compute cosyne similrity (all)", launchCosSimForAll)]
  
  listener = RowClickListener(table,
                              double_click_fn=partial(uiOpenChunkVolume, groupNames, montage_img, csvDir, properties),
                              right_click_fns=commands) # TODO to run evaluation tools
                                                        # and tools to invalidate relevant CSVs (chunk matrices and CSVs for comparisons around particular sections)
  table.addMouseListener(listener)
  
  return table, frame, listener
  

