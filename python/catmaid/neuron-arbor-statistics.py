from __future__ import with_statement
import csv
from collections import defaultdict
from operator import itemgetter

def count_skeleton_nodes(filepath):
    arbors = defaultdict(int)
    with open(filepath, 'r') as csvfile:
        reader = csv.reader(csvfile, delimiter=',', quotechar='"')
        reader.next() # skip header
        for skeleton_id, treenode_id, parent_id, x, y, z in reader:
            arbors[int(skeleton_id)] += 1

    return arbors


def test_count_skeleton_nodes():
    filepath = '/tmp/0111-8/20190329_mw_brain_neurons/brain_neurons_skeleton_coordinates.csv'
    arbors = count_skeleton_nodes(filepath)
    print("Found %i arbors:" % len(arbors))
    for skeleton_id, count in sorted(arbors.items(), key=itemgetter(1), reverse=True):
        print("%s skeleton nodes for skeleton_id %i" % (str(count).rjust(5, ' '), skeleton_id))

test_count_skeleton_nodes()

    

