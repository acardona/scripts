# Export an ImageStack from a range of TrakEM2 layers
from ini.trakem2 import Project
from ini.trakem2.display import Display, Displayable, AreaList, Treeline
from ij import ImagePlus, ImageStack
import time
from java.awt.geom.Point2D import Float as Point2D
from java.awt.geom import PathIterator, Area, AffineTransform
from java.awt import Rectangle, Polygon, Color
from org.python.modules.jarray import zeros
from java.awt import Graphics2D

HIGHLIGHT_TIME = 2 #seconds
DELAY_BETWEEN_HIGHLIGHTS = 0.2

def findHoles(area):
	# get all outlines of an Area
	# This includes outer outline as well as the outline of
	# any holes in the area
  	polies = []
	pol = Polygon();
	pit = area.getPathIterator(None)
	pit.next()
	coords = zeros(6,'d')
	orig = [a for a in coords]
	k=0
	while not pit.isDone():
		seg_type = pit.currentSegment(coords)
		if seg_type == PathIterator.SEG_MOVETO: # 0
			pass
		elif seg_type == PathIterator.SEG_LINETO: # 1
			k+=1
			pol.addPoint(int(coords[0]), int(coords[1]))
		elif seg_type == PathIterator.SEG_CLOSE: # 4
			points = list(zip(pol.xpoints[:pol.npoints], pol.ypoints[:pol.npoints]))
			yield(Area(pol))
			# prepare next:
			pol = Polygon()
		else:
			print("WARNING: unhandled seg type.")
		pit.next()

def inner_holes(area):
	# Find all "holes" in the area:
	# i.e. exclude the outer outline that covers everything
	holes = [hole for hole in findHoles(area)]
	inner_holes = []
	for i in range(len(holes)):
		intersects_none = True
		for j in range(len(holes)):
			intersection = holes[i].clone()
			intersection.intersect(holes[j])
			if not intersection.isEmpty() and not intersection.equals(holes[i]):
				intersects_none = False
		if intersects_none:
			inner_holes.append(holes[i])
	return inner_holes

def all_nodes(trees, layer):
	# find all tree nodes in the current layer
	nodes = {}
	for tree in trees:
		tree_bounds = tree.getBoundingBox()
		for node in tree.getNodesAt(layer):
			nodes[Point2D(node.getX() + tree_bounds.x,
						  node.getY() + tree_bounds.y)] = tree.id
	return nodes

def valid_membrane(cell_membrane, nodes):
	# Check if a membrane is valid,
	# i.e. it contains nodes belonging to only one tree
	tree_ids = set()
	for node in nodes:
		if cell_membrane.contains(node):
			tree_ids.add(nodes[node])
	if len(tree_ids) < 2:
		return (True, cell_membrane)
	else:
		return (False, cell_membrane)

def valid_membranes(all_membranes, nodes):
	# check if a list of membranes are valid
	cell_membranes = inner_holes(all_membranes)
	validated_membranes = [valid_membrane(cell_membrane, nodes) for cell_membrane in cell_membranes]
	return (all([valid for valid, membrane in validated_membranes]), validated_membranes)

def highlight_missing_region(arealist, layer, missing_region):
	# highlight the invalid membrane areas
	bounds = arealist.getBoundingBox()
	canvas = Display.getFront().getCanvas()
	graphic = canvas.getGraphics()
	mag = canvas.getMagnification()
	src = canvas.getSrcRect()
	shift = AffineTransform(mag, 0, 0, mag, src.x, src.y)
	missing_region.transform(shift)
	graphic.setColor(Color.RED)
	graphic.fill(missing_region)
	graphic.transform(shift)
	arealist.paint(graphic, None, 1, False, 0, layer, [])
	time.sleep(HIGHLIGHT_TIME)
	Display.repaint()
	time.sleep(DELAY_BETWEEN_HIGHLIGHTS)

def membranes_enclose_one_tree():
	# Check that all membranes are valid
	current_layer = Display.getFrontLayer()
	arealists = Display.getSelected(AreaList)
	trees = Display.getFront().getLayer().getParent().getZDisplayables(Treeline)
	projects = Project.getProjects()
	only_project = projects[0]

	layer_nodes = all_nodes(trees, current_layer)
	for arealist in arealists:
		bounds = arealist.getBoundingBox()
		print(bounds.x, bounds.y)
		valid_arealist, cell_membranes = valid_membranes(arealist.getAreaAt(current_layer), layer_nodes)
		if not valid_arealist:
			for valid, membrane in cell_membranes:
				if not valid:
					highlight_missing_region(arealist, current_layer, membrane)
					
			print("Area list with id {} contains invalid membranes".format(arealist.id))
		else:
			print("Area list with id {} contains all valid membranes".format(arealist.id))

membranes_enclose_one_tree()