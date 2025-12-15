from __future__ import with_statement
import os, sys
# Add current directory to path
sys.path.append(os.path.dirname(sys.argv[0]))
# Import parameters
from step_1_montage_parameters import montageDir, first_section, last_section

from lib.montage2d import runEvaluateMontages
from lib.montage2d_table import makeMontageEvaluationTable
from ij import IJ

# Read groupNames and tileGroups from the groupNames file
groupNames = []
tileGroups = []
with open(os.path.join(montageDir, "groupNames"), 'r') as f:
  for line in f:
    p = line.split(' = ')
    groupNames.append(p[0])
    tileGroups.append(p[1].strip()[1:-1].split(', '))

frame, table, search_field, all = makeMontageEvaluationTable(groupNames[first_section:last_section+1],
                                                             tileGroups[first_section:last_section+1],
                                                             IJ.getImage(), montageDir, runEvaluateMontages, show=True)