# Repair FIBSEM DAT files based on a good file
# Rescues as much data as there may be from the first channel
# into a new file.

import os, sys
sys.path.append("/net/fibserver1/raw/YY9_Gaba/scripts/python/imagej/IsoView-GCaMP/")
from jarray import zeros
from java.io import RandomAccessFile, File
from java.lang import System
from lib.io import repairTruncatedDAT, readFIBSEMdat, blankROIDAT, readFIBSEMHeader
from ij import IJ

# List of images to repair 
to_repair = sorted(["Merlin-FIBdeSEMAna_25-12-07_133352_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-07_135434_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-07_134733_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-07_131600_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-07_141249_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-07_132240_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-07_204920_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-07_205632_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-07_212505_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-07_214510_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-07_214803_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-07_221732_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-07_222854_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-07_230627_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-07_231333_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-07_233456_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-07_135434_0-0-1.dat",
"Merlin-FIBdeSEMAna_25-12-07_212505_0-0-1.dat",
"Merlin-FIBdeSEMAna_25-12-07_221732_0-0-1.dat",
"Merlin-FIBdeSEMAna_25-12-07_214803_0-0-1.dat",
"Merlin-FIBdeSEMAna_25-12-07_205632_0-0-1.dat",
"Merlin-FIBdeSEMAna_25-12-07_141249_0-0-1.dat",
"Merlin-FIBdeSEMAna_25-12-07_204920_0-0-1.dat",
"Merlin-FIBdeSEMAna_25-12-07_132240_0-0-1.dat",
"Merlin-FIBdeSEMAna_25-12-07_214510_0-0-1.dat",
"Merlin-FIBdeSEMAna_25-12-07_222854_0-0-1.dat",
"Merlin-FIBdeSEMAna_25-12-07_230627_0-0-1.dat",
"Merlin-FIBdeSEMAna_25-12-08_003144_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-08_072435_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-09_135438_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-10_144846_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-10_145423_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-10_145209_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-13_211256_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-13_211502_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-13_214112_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-07_124802_0-0-1.dat",
"Merlin-FIBdeSEMAna_25-12-07_130858_0-0-1.dat",
"Merlin-FIBdeSEMAna_25-12-07_223147_0-0-1.dat",
"Merlin-FIBdeSEMAna_25-12-07_125911_0-0-1.dat",
"Merlin-FIBdeSEMAna_25-12-07_230917_0-0-1.dat",
"Merlin-FIBdeSEMAna_25-12-07_130734_0-0-1.dat",
"Merlin-FIBdeSEMAna_25-12-07_130323_0-0-1.dat",
"Merlin-FIBdeSEMAna_25-12-07_122817_0-0-1.dat",
"Merlin-FIBdeSEMAna_25-12-07_215633_0-0-1.dat",
"Merlin-FIBdeSEMAna_25-12-13_224648_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-13_224648_0-0-1.dat",
"Merlin-FIBdeSEMAna_25-12-13_225914_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-13_230028_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-13_231028_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-13_212700_0-0-1.dat",
"Merlin-FIBdeSEMAna_25-12-13_231151_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-13_214825_0-0-1.dat",
"Merlin-FIBdeSEMAna_25-12-13_231403_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-13_220945_0-0-1.dat",
"Merlin-FIBdeSEMAna_25-12-13_225514_0-0-1.dat",
"Merlin-FIBdeSEMAna_25-12-13_223646_0-0-1.dat",
"Merlin-FIBdeSEMAna_25-12-13_222401_0-0-1.dat",
"Merlin-FIBdeSEMAna_25-12-13_221529_0-0-1.dat",
"Merlin-FIBdeSEMAna_25-12-13_224105_0-0-1.dat",
"Merlin-FIBdeSEMAna_25-12-14_000358_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-13_231839_0-0-1.dat",
"Merlin-FIBdeSEMAna_25-12-13_232426_0-0-1.dat",
"Merlin-FIBdeSEMAna_25-12-14_000501_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-13_233143_0-0-1.dat",
"Merlin-FIBdeSEMAna_25-12-14_000708_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-14_000914_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-14_010709_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-14_011115_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-14_011659_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-14_022318_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-14_022616_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-14_024831_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-14_035902_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-14_040110_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-14_024831_0-0-1.dat",
"Merlin-FIBdeSEMAna_25-12-14_040213_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-14_040420_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-14_041100_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-14_041225_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-14_011533_0-0-1.dat",
"Merlin-FIBdeSEMAna_25-12-14_042938_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-14_012538_0-0-1.dat",
"Merlin-FIBdeSEMAna_25-12-14_041100_0-0-1.dat",
"Merlin-FIBdeSEMAna_25-12-14_044243_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-14_045423_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-14_052043_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-14_052759_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-14_023507_0-0-1.dat",
"Merlin-FIBdeSEMAna_25-12-14_023211_0-0-1.dat",
"Merlin-FIBdeSEMAna_25-12-14_024411_0-0-1.dat",
"Merlin-FIBdeSEMAna_25-12-14_053642_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-14_052759_0-0-1.dat",
"Merlin-FIBdeSEMAna_25-12-14_055538_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-14_063619_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-14_043232_0-0-1.dat",
"Merlin-FIBdeSEMAna_25-12-14_064501_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-14_065216_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-14_051200_0-0-1.dat",
"Merlin-FIBdeSEMAna_25-12-14_052338_0-0-1.dat",
"Merlin-FIBdeSEMAna_25-12-14_065801_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-14_053515_0-0-1.dat",
"Merlin-FIBdeSEMAna_25-12-14_053935_0-0-1.dat",
"Merlin-FIBdeSEMAna_25-12-14_054358_0-0-1.dat",
"Merlin-FIBdeSEMAna_25-12-14_062612_0-0-1.dat",
"Merlin-FIBdeSEMAna_25-12-14_063452_0-0-1.dat",
"Merlin-FIBdeSEMAna_25-12-14_055116_0-0-1.dat",
"Merlin-FIBdeSEMAna_25-12-14_064039_0-0-1.dat",
"Merlin-FIBdeSEMAna_25-12-14_062151_0-0-1.dat",
"Merlin-FIBdeSEMAna_25-12-14_073401_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-14_070219_0-0-1.dat",
"Merlin-FIBdeSEMAna_25-12-14_073822_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-14_071934_0-0-1.dat",
"Merlin-FIBdeSEMAna_25-12-14_070803_0-0-1.dat",
"Merlin-FIBdeSEMAna_25-12-14_071514_0-0-1.dat",
"Merlin-FIBdeSEMAna_25-12-14_072101_0-0-1.dat",
"Merlin-FIBdeSEMAna_25-12-14_072814_0-0-1.dat",
"Merlin-FIBdeSEMAna_25-12-14_080549_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-14_080549_0-0-1.dat",
"Merlin-FIBdeSEMAna_25-12-14_074116_0-0-1.dat",
"Merlin-FIBdeSEMAna_25-12-14_081433_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-14_132111_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-14_075250_0-0-1.dat",
"Merlin-FIBdeSEMAna_25-12-14_080003_0-0-1.dat",
"Merlin-FIBdeSEMAna_25-12-14_132707_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-14_132811_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-14_081010_0-0-1.dat",
"Merlin-FIBdeSEMAna_25-12-14_081728_0-0-1.dat",
"Merlin-FIBdeSEMAna_25-12-14_132916_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-14_133020_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-14_133124_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-14_140442_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-14_150050_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-14_150809_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-14_150050_0-0-1.dat",
"Merlin-FIBdeSEMAna_25-12-14_151355_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-14_151642_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-14_151642_0-0-1.dat",
"Merlin-FIBdeSEMAna_25-12-14_201155_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-14_201828_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-15_083846_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-15_085335_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-15_092633_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-15_093708_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-15_093941_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-15_095334_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-14_141346_0-0-1.dat",
"Merlin-FIBdeSEMAna_25-12-15_100849_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-14_142134_0-0-1.dat",
"Merlin-FIBdeSEMAna_25-12-15_101121_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-15_101808_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-15_102541_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-15_102039_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-15_102955_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-15_103640_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-15_104507_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-15_105153_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-15_105658_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-15_112357_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-14_143742_0-0-1.dat",
"Merlin-FIBdeSEMAna_25-12-15_112629_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-15_114553_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-15_114825_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-14_151230_0-0-1.dat",
"Merlin-FIBdeSEMAna_25-12-15_115833_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-15_121756_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-15_122026_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-15_122259_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-15_125723_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-15_125953_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-15_130225_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-15_130542_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-15_132010_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-15_132602_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-15_133042_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-15_133634_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-15_134451_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-15_134720_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-15_134950_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-15_140443_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-14_153111_0-0-1.dat",
"Merlin-FIBdeSEMAna_25-12-15_141121_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-15_141438_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-15_142022_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-15_142606_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-15_144001_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-15_145357_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-15_145626_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-15_145855_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-15_150706_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-15_152202_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-15_152746_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-15_172311_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-15_172710_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-15_175431_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-15_195205_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-15_203709_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-15_205738_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-15_210104_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-15_211420_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-15_210742_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-15_214704_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-15_214328_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-15_215511_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-15_220030_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-15_215936_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-15_221447_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-15_223853_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-15_224438_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-15_225526_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-15_230023_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-15_230836_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-15_231333_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-16_074544_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-16_083838_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-16_084928_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-16_092707_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-16_103758_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-16_110317_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-16_152426_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-16_175647_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-16_182554_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-17_044921_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-17_051537_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-17_052350_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-17_075657_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-17_075421_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-17_081240_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-17_081507_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-17_081645_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-17_081734_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-17_083046_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-17_083628_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-17_084955_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-17_084121_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-17_090226_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-17_091932_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-17_085423_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-17_091651_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-17_091411_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-17_090509_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-17_092453_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-17_093201_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-17_093812_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-17_094613_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-17_101737_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-17_102356_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-17_103800_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-17_104026_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-17_104333_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-17_110111_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-17_124958_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-17_130227_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-17_131451_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-17_134649_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-17_140226_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-17_140312_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-17_142325_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-17_143507_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-17_143552_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-17_143638_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-17_145955_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-17_150214_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-17_150300_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-17_150347_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-17_150434_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-17_174639_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-17_174945_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-17_175645_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-17_180301_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-17_181131_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-17_182225_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-17_184548_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-17_184106_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-17_185946_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-17_184020_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-17_185900_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-17_185333_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-17_192103_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-17_190921_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-17_192017_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-18_081035_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-18_081436_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-18_082406_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-18_083240_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-18_083635_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-18_084846_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-18_085329_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-18_091047_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-18_091313_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-18_092158_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-18_092419_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-18_092639_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-18_092859_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-18_093119_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-18_094038_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-18_094738_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-18_094957_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-18_095353_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-18_095614_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-18_100009_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-18_100404_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-18_100912_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-18_104027_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-18_104856_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-18_105513_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-18_110630_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-18_135552_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-18_140653_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-18_142742_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-18_143431_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-18_143738_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-18_144832_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-18_144219_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-18_150452_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-18_145839_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-18_151457_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-18_151149_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-18_150759_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-18_152041_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-18_155407_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-18_155713_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-18_155847_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-18_160643_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-18_161012_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-18_161320_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-18_162725_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-18_163032_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-18_163609_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-18_163522_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-18_163917_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-18_164311_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-18_165013_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-18_165406_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-18_165713_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-18_170413_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-18_171028_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-18_171815_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-18_172123_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-18_172736_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-18_173128_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-18_184316_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-18_184908_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-18_185844_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-18_190150_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-18_190544_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-18_191114_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-18_191422_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-18_191730_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-18_192344_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-18_192651_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-18_193307_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-18_194009_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-18_194403_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-18_194711_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-18_195018_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-18_195457_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-18_200854_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-18_201201_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-18_201508_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-18_202737_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-18_205456_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-18_210332_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-18_205803_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-18_210947_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-18_212434_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-18_213356_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-18_213049_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-18_212741_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-18_214717_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-19_083111_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-19_085431_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-19_090418_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-19_092535_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-19_093752_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-19_095007_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-19_095429_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-19_100225_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-19_100629_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-19_101419_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-19_101725_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-19_102034_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-19_102734_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-19_103125_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-19_103912_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-19_104217_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-19_104744_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-19_105051_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-19_105618_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-19_111018_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-19_112703_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-19_113116_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-19_113511_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-19_114344_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-19_114947_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-19_115419_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-19_115807_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-19_120152_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-19_121017_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-19_121726_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-19_121908_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-19_122144_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-19_122327_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-19_123441_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-19_124047_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-19_124510_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-19_125346_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-19_125431_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-19_125905_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-19_130213_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-19_130954_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-19_132204_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-19_133932_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-19_134234_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-19_135015_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-19_135924_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-19_140227_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-19_141354_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-19_135621_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-19_142413_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-19_143023_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-19_142942_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-19_143838_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-19_151501_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-19_152319_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-19_152839_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-19_153223_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-19_153354_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-19_153738_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-19_154123_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-19_171018_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-19_172240_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-19_202514_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-19_203205_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-19_203452_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-19_213446_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-19_213624_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-19_213919_0-0-0.dat",
"Merlin-FIBdeSEMAna_25-12-19_214022_0-0-0.dat",])

# List of images with ROIs to blank out
#to_blank = [
  #{"path": "M02/D23/Merlin-WEMS_24-02-23_213519_0-0-0.dat",  # turns out it's truncated and opens funny, with a duplication
  # "rois": [[0, 9815, 12500, 2685]]}, # [x,y,width,height]
#]

base_path = "/net/fibserver1/raw/YY9_Gaba/" 
repaired_path = "/net/fibserver1/raw/YY9_Gaba/repaired/"


# Table of good images for single tile sections

# 0, 0, Merlin-FIBdeSEMAna_25-12-15_085335_0-0-0.dat, 689067936
# 0, 0, Merlin-FIBdeSEMAna_25-12-17_091651_0-0-0.dat, 597192936
# 0, 0, Merlin-FIBdeSEMAna_25-12-19_135015_0-0-0.dat, 528942936
# 0, 0, Merlin-FIBdeSEMAna_25-12-19_141354_0-0-0.dat, 399755436
# 0, 0, Merlin-FIBdeSEMAna_25-12-19_172240_0-0-0.dat, 319883024  # truncated?
# 0, 0, Merlin-FIBdeSEMAna_25-12-19_202514_0-0-0.dat, 5126024  # very truncated, unrecoverable
# 0, 0, Merlin-FIBdeSEMAna_25-12-19_213919_0-0-0.dat, 152931024
#0, 0, Merlin-FIBdeSEMAna_25-12-19_214022_0-0-0.dat, 698024 # very truncated, un recoverable


good_singles = {
  689067936: "Merlin-FIBdeSEMAna_25-12-15_085233_0-0-0.dat", # same size
  597192936: "Merlin-FIBdeSEMAna_25-12-17_091557_0-0-0.dat", # same size
  528942936: "Merlin-FIBdeSEMAna_25-12-19_134930_0-0-0.dat", # same size
  399755436: "Merlin-FIBdeSEMAna_25-12-19_141313_0-0-0.dat", # same size
  319883024: "Merlin-FIBdeSEMAna_25-12-19_172158_0-0-0.dat", # truncated
  152931024: "Merlin-FIBdeSEMAna_25-12-19_213827_0-0-0.dat", # truncated
  521312524: "Merlin-FIBdeSEMAna_25-12-17_110022_0-0-0.dat", # truncated
}

# This works for 2-tiled because there is always one good
for img_fname in to_repair:
  items =  img_fname.split('_')
  year, month, day = items[1].split('-')
  
  if str(1) in items[-1]:
    good = '/'.join([base_path, 'Y2025', 'M' + month, 'D' + day, img_fname[:-9] + '0-0-0.dat'])
    bad = '/'.join([base_path, 'Y2025', 'M' + month, 'D' + day, img_fname[:-9] + '0-0-1.dat'])
  else:
    good = '/'.join([base_path, 'Y2025', 'M' + month, 'D' + day, img_fname[:-9] + '0-0-1.dat']) 
    bad = '/'.join([base_path, 'Y2025', 'M' + month, 'D' + day, img_fname[:-9] + '0-0-0.dat'])

  if not os.path.exists(good):
    ref_good = good_singles.get(os.path.getsize(bad), None)
    if ref_good is None:
      print "No good reference for:\n%s" % img_fname
      continue
    date = ref_good.split("_")[1].split("-")
    good = "%sY20%s/M%s/D%s/%s" % (base_path, date[0], date[1], date[2], ref_good)
    IJ.log("synthetic good: %s" % good)

  if os.path.exists(good):
    try:
      repairTruncatedDAT(good, bad, os.path.join(repaired_path, img_fname))
    except:
      print sys.exc_info()
      IJ.log("Failed to repair: %s" % img_fname)
      break
  else:
    try:
      header = readFIBSEMHeader(bad)
      IJ.log("Missing a good file for:\n%i, %i, %s" % (header.xRes, header.yRes, img_fname))
    except:
      IJ.log("Failed to read header the standard way for\n%s" % img_fname)
      # try to read the header directly
      ra = RandomAccessFile(bad, 'r')
      try:
        # Parse width and height
        ra.seek(100)
        width = ra.readInt()
        ra.seek(104)
        height = ra.readInt()
        IJ.log("Failed header parsing and missing a good file for:\n%i, %i, %s, %i" % (width, height, img_fname, os.path.getsize(bad)))
      except:
        IJ.log("Beyond recovery:\n%s" % img_fname)
      finally:
        ra.close()



# For single tiles we can assume it's a problem at the footer







#for p in to_blank:
#  blankROIDAT(os.path.join(sourcePath, p["path"]),
#              os.path.join(repairedPath, p["path"][p["path"].rfind('/')+1:]),
#              p["rois"])


