from org.janelia.simview.klb import KLB # Needs 'SiMView' Fiji update site enabled

path = "/net/zstore1/data_WillBishop/KLB/SPM00_TM007151_CM00_CM01_CHN00.weightFused.TimeRegistration.klb"

klb = KLB.newInstance()
img = klb.readFull(path)
print img
print type(img)
print img.getImg()
print type(img.getImg())