/**
 * Albert Cardona 2019-04012
 *
 * First, open a Graph widget, add nodes to it, split some
 * into axon and dendrite, and select some dendrite nodes.
 * Will print the node name and its number of postsynaptic sites
 * only if the node has been split into axon and dendrite
 * (aka its label has the name dendrite or its data has the
 * 'upstream_skids' variable).
 */

(function() {
  var gg = CATMAID.GroupGraph.prototype.getInstances()[0];

  gg.cy.nodes().each(function(i, node) {
    var data = node.data();
    if (node.selected()) {
      var partners = data.upstream_skids;
      if (partners) {
        var n_post = Object.keys(partners).reduce(function(s, skid) {
          return s + partners[skid].length; // count of skid's treenode_id making contacts
        }, 0);
        console.log("name:", data.label, "n_post:", n_post);
      } else {
        console.log("node ", data.label, "is not split into axon and dendrite");
      }
    }
  });
})();
