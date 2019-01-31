// Compute distances from each dendritic node with a postsynatic site
// to the root of the dendritic arbor, here defined as the dendritic node 
// that is the nearest common ancestor to all dendritic arbor nodes with
// a postsynaptic site.

// ASSUMES axon and dendrite coloring mode, so that the "axon" variable exists.

// Exports measurements as one CSV file for each arbor in the 3D viewer.


var w = CATMAID.WebGLApplication.prototype.getInstances()[0];
var sks = w.space.content.skeletons;


Object.keys(sks).forEach(function(skid) {
  var sk = sks[skid];
  var arbor = sk.createArbor();
  var smooth_positions = arbor.smoothPositions(sk.getPositions(), 200); // sigma of 200 nm
  var distanceFn = (function(child, paren) {
     return this[child].distanceTo(this[paren]);
  }).bind(smooth_positions);

  // Find dendritic nodes hosting at least one postsynaptic site
  var synapses = sk.createSynapseMap();
  var postsynaptic_nodes = Object.keys(synapses).reduce(function(o, nodeID) {
    if (!sk.axon.hasOwnProperty(nodeID)) {
      // nodeID is in the dendritic arbor
      synapses[nodeID].forEach(function(synapse) {
        if (1 === synapse.type) {
          // postsynaptic
          o[nodeID] = true;
          return o;
        }
      });
    }
    return o;
  }, {});
  
  // Find denritic root: find the node parent to all dendritic postsynaptic nodes
  var dendritic_root = arbor.nearestCommonAncestor(postsynaptic_nodes);

  var distances_to_root = arbor.nodesDistanceTo(arbor.root, distanceFn).distances;

  // Distance from dendritic_root to root:
  var offset = distances_to_root[dendritic_root];

  // Distances from each dendritic postsynaptic node to the dendritic_root
  var distances_to_dendritic_root = Object.keys(postsynaptic_nodes).reduce(function(o, nodeID) {
    o[nodeID] = distances_to_root[nodeID] - offset;
    return o;
  }, {});

  // Export CSV file
  var name = CATMAID.NeuronNameService.getInstance().getName(skid) + "-" + skid;
  var rows = [["skid", "nodeID", "connectorID", "distance_to_dendritic_root"].join(",")];

  Object.keys(synapses).forEach(function(nodeID) {
    synapses[nodeID].forEach(function(synapse) {
      if (1 === synapse.type) {
        rows.push([skid, nodeID, synapse.connector_id, distances_to_dendritic_root[nodeID]].join(","));
      }
    });
  });

  saveAs(new Blob([rows.join("\n")], {type : 'text/plain'}), name + ".csv");
});

