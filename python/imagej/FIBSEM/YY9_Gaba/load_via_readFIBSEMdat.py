import sys, os
sys.path.append("/lmb/home/acardona/lab/scripts/python/imagej/IsoView-GCaMP/")

from lib.io import readFIBSEMHeader, readFIBSEMdat
from lib.util import timeit

base_path = "/net/fibserver1/raw/YY9_Gaba/Y2025/"

filepaths = [
  # single tile:
  #"Merlin-FIBdeSEMAna_25-11-28_045840_0-0-1.dat",
  #"Merlin-FIBdeSEMAna_25-12-04_073041_0-0-0.dat", # Same artefact
  #"Merlin-FIBdeSEMAna_25-12-04_073041_0-0-1.dat",
  #"Merlin-FIBdeSEMAna_25-12-06_213718_0-0-0.dat", # Same artefact
  #"Merlin-FIBdeSEMAna_25-12-06_213718_0-0-1.dat",
  #"Merlin-FIBdeSEMAna_25-11-27_185132_0-0-0.dat", # Same artefact
  #"Merlin-FIBdeSEMAna_25-11-27_185132_0-0-1.dat",
  #"Merlin-FIBdeSEMAna_25-11-28_004440_0-0-0.dat", # Same artefact but no problem with neuropil
  #"Merlin-FIBdeSEMAna_25-11-28_004440_0-0-1.dat",
  #"Merlin-FIBdeSEMAna_25-12-15_195457_0-0-0.dat", # blurred
  #"Merlin-FIBdeSEMAna_25-12-07_133352_0-0-0.dat",
  "Merlin-FIBdeSEMAna_25-12-15_083846_0-0-0.dat", # size: 689067936
 ]


for filepath in filepaths:
  date = filepath.split("_")[1].split("-")
  path = "%sM%s/D%s/%s" % (base_path, date[1], date[2], filepath)
  imp = readFIBSEMdat(path, channel_index=0, asImagePlus=True, toUnsigned=True)[0]
  imp.setTitle(os.path.basename(filepath))
  imp.show()
  
  print readFIBSEMHeader(path)
