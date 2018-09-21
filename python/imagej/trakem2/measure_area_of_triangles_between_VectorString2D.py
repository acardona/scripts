from ini.trakem2.vector import SkinMaker, VectorString2D, Editions
from jarray import array
from ini.trakem2.utils import M

delta = 1.0

vs1 = VectorString2D(array([0, 1, 2, 3, 4, 5, 6], 'd'),
                     array([0, 0, 0, 0, 0, 0, 0], 'd'),
                     0,
                     False)

vs2 = VectorString2D(array([0, 1, 2, 3, 4, 5, 6], 'd'),
                     array([0, 0, 0, 0, 0, 0, 0], 'd'),
                     1,
                     False)

print vs1.length(), vs2.length(), vs1.getPoints(0), vs1.getPoints(1)

vs1.resample(delta)
vs2.resample(delta)

print vs1.length(), vs2.length(), vs1.getPoints(0), vs1.getPoints(1)

editions = Editions(vs1, vs2, delta, False)
match = SkinMaker.Match(vs1, vs2, editions, None)
triangles = match.generateTriangles(False)

print len(triangles)


area = 0.0
for i in xrange(0, len(triangles), 3):
  a = M.measureArea(triangles[i], triangles[i+1], triangles[i+2])
  print i, a
  area += a
  

print area