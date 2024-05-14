# Repair FIBSEM DAT files based on a good file
# Rescues as much data as there may be from the first channel
# into a new file.

import os
from jarray import zeros
from java.io import RandomAccessFile, File
from java.lang import System

basepath = "/net/fibserver1/raw/MR1.4-3/M02/D27/"
good = "Merlin-WEMS_24-02-27_165658_0-0-0.dat"
bad  = "Merlin-WEMS_24-02-27_165658_0-1-0.dat"

repaired = "/net/zstore1/FIBSEM/MR1.4-3/repaired/" + bad


def repair(goodFilePath, badFilePath, repairedFilePath, header=1024):
  # ASSUMES 2 channels
  # Copy header and trailer from the good file
  raGood = RandomAccessFile(goodFilePath, 'r')
  try:
    # Parse width and height
    raGood.seek(100)
    width = raGood.readInt()
    raGood.seek(104)
    height = raGood.readInt()
    # Copy header
    headerBytes = zeros(header, 'b')
    raGood.seek(0)
    raGood.read(headerBytes)
    # Copy trailer
    goodLength = File(goodFilePath).length()
    start_of_trailer = 1024 + width * height * 4
    raGood.seek(1024 + width * height * 4)
    trailerBytes = zeros(goodLength - start_of_trailer, 'b')
    raGood.read(trailerBytes)
  finally:
    raGood.close()
  
  # From the bad file, copy as many pixels as there are.
  # The assumption is that the file writing was truncated, so the header exists (but may be corrupted)
  # and the pixels array is truncated, and the trailer is not there.
  raBad = RandomAccessFile(badFilePath, 'r')
  raRepaired = RandomAccessFile(repairedFilePath, 'rw')
  try:
    repairedBytes = zeros(header + width * height * 4 + len(trailerBytes), 'b') # assumes 2 channels of 16-bit
    System.arraycopy(headerBytes, 0, repairedBytes, 0, header)
    badLength = File(badFilePath).length()
    raBad.seek(header)
    raBad.read(repairedBytes, header, badLength - header)
    System.arraycopy(trailerBytes, 0, repairedBytes, goodLength - len(trailerBytes), len(trailerBytes)) 
    raRepaired.write(repairedBytes)
    raRepaired.getFD().sync()
  finally:
    raBad.close()
    raRepaired.close()


repair(os.path.join(basepath, good),
       os.path.join(basepath, bad),
       repaired)

  
  