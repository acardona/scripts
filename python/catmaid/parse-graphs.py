# ASSUMES python 3

import networkx as nx
import csv
from collections import defaultdict
from functools import partial

def graph0(brain_neurons_synapses_csv_path, threshold=2):
  """ Each neuron as a single node,
      and edges have as weight the number of synapses
      from one neuron to another.
      
      Header: pre_skeleton_id, pre_treenode_id, post_skeleton_id, post_treenode_id
      We ignore the treenode ids (a 'treenode' is a node of a skeleton
      in CATMAID parlance).
      
      Will ignore all edges with a synapse count (aka weight) smaller than
      threshold, which defaults to 2.
      
      NOTE that, in using brain_neurons_synapses.csv, this graph
      includes also all ascending neurons (whose morphology is not
      included in brain_neurons_skeletons.csv) and all synaptic partners
      of descending axons (whose morphology is not included either). """
  
  with open(brain_neurons_synapses_csv_path, 'r') as csv_file:
    reader = csv.reader(csv_file, delimiter=',', quotechar="\"")
    header = next(reader) # ignore
    # Each row contains a single morphological synapse,
    # and therefore we have to collapse many rows into a single edge.
    # I use here a dictionary of source node keys vs. a dictionary of
    # target node keys vs synaptic counts.
    # The defaultdict enables us to create keys on they fly if they don't exist,
    # and the partial is a technique to define how to instantiate their values
    # when they don't exist yet, in this case being another defaultdict
    # whose values are initialized to the integer zero, via executing int().
    edges = defaultdict(partial(defaultdict, int))
    for row in reader:
      pre_skeleton_id, pre_treenode_id, post_skeleton_id, post_treenode_id = map(int, row)
      edges[pre_skeleton_id][post_skeleton_id] += 1

    # As a directed graph
    g = nx.DiGraph()
    for source_node, targets in edges.items():
      for target_node, weight in targets.items():
        if weight >= threshold:
          g.add_edge(source_node, target_node, weight=weight)

    return g


def test_graph0():
  g = graph0("/home/albert/lab/manuscripts/20190329_whole_larval_brain/data/20190329_mw_brain_neurons/brain_neurons_synapses.csv", threshold=1)
  print("number of nodes: %i" % g.number_of_nodes())
  print("number of edges: %i" % g.number_of_edges())

