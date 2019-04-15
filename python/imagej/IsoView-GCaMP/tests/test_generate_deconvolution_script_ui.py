from __future__ import with_statement
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(sys.argv[0])))
from lib.isoview_ui import generateDeconvolutionScriptUI
from lib.util import affine3D
import pickle
from net.imglib2.realtransform import AffineTransform3D


with open("/tmp/parameters.pickle", 'r') as f:
  parameters = pickle.load(f)

  # Convert back to AffineTransform3D
  parameters[-3] = map(affine3D, parameters[-3])
  parameters[-1] = map(affine3D, parameters[-1])
  
  generateDeconvolutionScriptUI(*parameters)