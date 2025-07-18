from __future__ import with_statement
import os, csv

csvpath = "/net/zstore1/FIBSEM/MR1.4-3/registration/csvZ/Merlin-WEMS_24-03-15_042323_.Merlin-WEMS_24-03-15_042706_.pointmatches.csv"

with open(csvpath, 'r') as f:
  reader = csv.reader(f, delimiter=',', quotechar='"')
  names = reader.next()
  values = reader.next()
  print names
  print values