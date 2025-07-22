# Replace NaNs in csv1 with correct values in csv2

import os, sys, csv, math

folder = "/net/zstore1/FIBSEM/MR1.4-3/registration/"
csv1 = os.path.join(folder, "bridge.csv")
csv2 = os.path.join(folder, "bridge-nans.csv")

csv_output = os.path.join(folder, "bridge-correct.csv")

translations = []
with open(csv1, 'r') as csvfile:
  reader = csv.reader(csvfile, delimiter=',', quotechar="\"")
  for line in reader:
    translations.append(map(float, line))

with open(csv2, 'r') as csvfile:
  reader = csv.reader(csvfile, delimiter=',', quotechar="\"")
  for line in reader:
    index = int(line[0])
    tx, ty = float(line[1]), float(line[2])
    if math.isnan(translations[index][0]) or math.isnan(translations[index][1]):
      print "Correcting index: ", index, "with", tx, ", ", ty
      translations[index] = (tx, ty)
    else:
      print "No NaN at index", index, "but there is a correction for it"

"""
with open(csv_output, 'a') as csvfile:
  for i, t in enumerate(translations):
    if math.isnan(t[0]) or math.isnan(t[1]):
      print "WARNING still a NaN at index", i
    csvfile.write("%f, %f\n" % (t[0], t[1]))
"""