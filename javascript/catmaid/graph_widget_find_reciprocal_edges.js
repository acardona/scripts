/**
 * Albert Cardona 2019-04-03
 * In a CATMAID Graph Widget, do, sequentially:
 * 1. Hide edges with weight lower than a threshold.
 * 2. Hide nodes without edges.
 * 3. Print out a list of node pairs that have reciprocal edges.
 * 4. Remove all selections.
 * 5. Add each pair as a new selection.
 */

(function() {
  var gg = CATMAID.front();

  try {
    gg.cy.startBatch();

    // Remove edges under threshold
    var threshold = 3;
    gg.cy.edges().each(function(i, edge) {
      if (edge.data("weight") < threshold) {
        edge.remove();
      }
    });

    // Hide nodes without edges
    gg.cy.nodes().each(function(i, node) {
      if (node.connectedEdges().empty()) {
        node.hide();
      }
    });

    // Find nodes with reciprocal connections
    var edges = {};
    gg.cy.edges().each(function(i, edge) {
      var src = edge.source();
      var tgt = edge.target();
      var targets = edges[src];
      if (!targets) {
        edges[src.id()] = {[tgt.id()]: true};
      } else {
        targets[tgt.id()] = true;
      }
    });
    var reciprocal = Object.keys(edges).reduce(function(a, src) {
      return Object.keys(edges[src]).reduce(function(a, tgt1) {
        var targets2 = edges[tgt1];
        if (targets2 && targets2[src]) {
          // Check if it has already been seen in reverse
          // WARNING O(n) over seen reciprocal edges
          if (!a.some(function(e) {
                 return src == e[1] && tgt1 == e[0];
               }))
          {
            a.push([src, tgt1]); // reciprocal edge
          }
        }
        return a;
      }, a);
      return a;
    }, []);

    console.log(reciprocal);

    // Store each pair as a Selection, and print the pair's names
    gg.resetSelections();

    var getName = CATMAID.NeuronNameService.getInstance().getName;
    reciprocal.forEach(function(pair, i) {
      var node1 = gg.cy.nodes().filter("[id='" + pair[0] + "']"),
          node2 = gg.cy.nodes().filter("[id='" + pair[1] + "']");
      var name1 = node1.id() < 0 ? node1.data().label : getName(node1.data().skeletons[0].id),
          name2 = node2.id() < 0 ? node2.data().label : getName(node2.data().skeletons[0].id);
      console.log(name1, name2);
      // New Selection
      var name = (i + 1) + "";
      gg.selections[name] = {[node1.id()]: true,
                             [node2.id()]: true};
      var select = $("#gg_selections" + gg.widgetID)[0];
      select.append(new Option(name, name));
    });

  } finally {
    gg.cy.endBatch();
  }

})();
