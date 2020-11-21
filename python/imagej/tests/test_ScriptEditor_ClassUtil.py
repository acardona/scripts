from org.scijava.ui.swing.script import ClassUtil

"""
m = ClassUtil.findClassDocumentationURLs("ShortAccess")
for k, v in m.iteritems():
  print k
  print "##", v.name, len(v.urls)
  for url in v.urls:
    print "---", url
"""

m = ClassUtil.findDocumentationForClass("ShortAccess")
for k, v in m.iteritems():
  print k
  for i, url in enumerate(v):
    print i, ":", url

f = ClassUtil.getDeclaredField("scijava_javadoc_URLs")
f.setAccessible(True)
scijava_javadoc_URLs = f.get(None)
print scijava_javadoc_URLs.get("imglib2")

f = ClassUtil.getDeclaredField("class_urls")
f.setAccessible(True)
class_urls = f.get(None)
jp = class_urls.get("net.imglib2.Cursor")
print jp.name
for url in jp.urls:
  print "---", url

jp = class_urls.get("ini.trakem2.Project")
print jp.name
for url in jp.urls:
  print "---", url