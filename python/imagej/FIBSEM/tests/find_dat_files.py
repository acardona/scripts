import os

srcDir = "/home/albert/ark/raw/fibsem/pygmy-squid/2021-12_popeye/Popeye2/"

dats = []

for root, dirs, filenames in os.walk(srcDir):
 for filename in filenames:
   if filename.endswith(".dat"):
     dats.append(os.path.join(root, filename))

dats.sort()

for path in dats:
  print path

print "found", len(dats)