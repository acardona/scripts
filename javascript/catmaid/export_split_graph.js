/**
 * A CATMAID script to export the connectivity graph with multiple edge colors,
 * namely axo-dendritic, axo-axonic, dendro-dendritic and dendro-axonic.
 *
 * Uses two SkeletonSource:
 * 1. "skids": the neuron skeleton IDs to include in the graph.
 * 2. "unsplittable": the list of neuron skeleton IDs that cannot be split into
      axon and dendrite. These are considered as dendrite-only.
 *
 * ... and a text tag "splitTag", at which point the axon is split into
   axon (downstream, inclusive) and dendrite (upstream, exclusive).
 * There can be more than one "splitTag", for example for neurons with two axons.
 *
 * A total of 6 CSV files are exported:
 * 1. "input_counts.csv" with 3 columns: skeleton_id, axon_inputs, dendrite_inputs.
      These input counts are the total, so they will be equal or larger than
  the sum of inputs of the edges in the exported graph, because some inputs
  may originate in neurons not to include in the graph. The purpose of this CSV
  file is to enable normalization of inputs by computing the input fractions
  for each neuron, as the way to estimate edge weights.
 * 2. "skeleton_id_vs_neuron_name.csv" with 2 columns: skeleton_id, neuron_name.
 * 3. "axon-dendrite.csv": all-to-all matrix of axo-dendritic edges.
 * 4. "axon-axon.csv": all-to-all matrix of axo-axonic edges.
 * 5. "dendrite-axon.csv": all-to-all matrix of dendro-axonic edges.
 * 6. "dendrite-dendrite.csv": all-to-all matrix of dendro-dendritic edges.
 */

(function() {

  var ins = CATMAID.NeuronSearch.prototype.getInstances();
  var skids = ins[0].getSelectedSkeletons().slice(0, 100);
  var unsplittable = ins[1].getSelectedSkeletons();
  var splitTag = "mw axon split";

  var getName = CATMAID.NeuronNameService.getInstance().getName;


  // Connectors by presynaptic site location:
  var connectors = {};
  var skeletonIDs = {};

  var all_inputs = skids.reduce(function(o, skid) {
                    o[skid] = {"axon": 0,
                               "dendrite": 0};
                    return o;
                   }, {});

  fetchSkeletons(
    skids,
    function(skid) {
      return CATMAID.makeURL(project.id + '/' + skid + '/1/1/compact-skeleton');  
    },
    function(skid) {
      return {}; // POST
    }, 
    function(skid, json) {
        // json[0]: skeleton as one node per row
        // json[1]: connectors as half a connector per row
        // json[2]: map of tag string vs list of nodes
        var splits = json[2][splitTag];

        // Check soma: only one
        var somas = json[2]["soma"];
        if (!somas) {
            console.log("Missing SOMA tag '" + splitTag + "' for skid #" + skid + " " + getName(skid));
            return;
        }
        if (somas.length != 1) {
            console.log("More than one SOMA tag '" + splitTag + "' for skid #" + skid + " " + getName(skid));
            return;
        }

        // Accumulate valid, included skeletons
        skeletonIDs[skid] = true;

        // Parse the arbor
        var ap = new CATMAID.ArborParser().init("compact-skeleton", json);
        var arbor = ap.arbor;

        // Ensure soma is the root node
        if (somas[0] != arbor.root) {
            arbor.reroot(somas[0]);
        }

        // All nodes downstream of splits[0] included will be the axon.
        var dendrite = arbor;
        if (!splits) {
            if (!unsplittable[skid]) {
                console.log("MISSING split tag '" + splitTag + "' for skid #" + skid + " " + getName(skid));
                return;
            }
            // Unsplittable neuron: all of it is a dendrite
        } else {
            var cuts = splits.reduce(function(o, node) { o[node] = true; return o; }, {});
            arbor.pruneAt(cuts);
        }

        var inputs = all_inputs[skid];

        // Parse connectors of this arbor
        json[1].forEach(function(row) {
            // Every row has:
            // row[0]: arbor treenode ID
            // row[1]: connector ID
            // row[2]: relation, 0=presynaptic 1=postsynaptic
            var relation = row[2];
            if (0 != relation && 1 != relation) return; // ignore non-synaptic relation
            var node = row[0];
            var connectorID = row[1];

            var connector = connectors[connectorID];
            if (!connector) {
                connector = {preSkid: null,
                             postSkid: [],
                             location: null};
                connectors[connectorID] = connector;
            }
            
            var location = dendrite.contains(node) ? "dendrite" : "axon";
            inputs[location] += 1;

            if (0 == relation) {
                // Presynaptic relation
                connector.preSkid = skid;
                connector.location = location;
            } else if (1 == relation) {
                connector.postSkid.push({location: location,
                                         skid: skid});
            }
        });

    },
    function(skid) {
       console.log("Failed to export arbor skid " + skid);
    },
    function() {
        // Write 5 CSV files
        //var skids = Object.keys(skeletonIDs).map(Number).sort();
        // Sorted by name
        var skids = Object.keys(skeletonIDs).map(function(skid) { return [skid, getName(skid)]; })
                    .sort(function(a, b) { return a[1] < b[1] ? -1 : 1; })
                    .map(function(a) { return a[0]; });

        var makeCounts = function() {
          return skids.reduce(function(o, skid) {
                 o[skid] = {"axon": 0,
                           "dendrite": 0 }; // skid vs count of synapses
                 return o;
          }, {});
        };

        var edges = skids.reduce(function(o, skid) {
            o[skid] = {"axon": makeCounts(),
                       "dendrite": makeCounts() }
            return o;
        }, {});
        
        Object.keys(connectors).forEach(function(connectorID) {
           var connector = connectors[connectorID];
           if (!connector.preSkid) return; // preSkid not part of neurons to include
           var edge = edges[connector.preSkid];
           if (!edge) {
               // Ignore edge that starts in a neuron that is not annotated as a neuron to include
               return;
           }
           
           var counts = edge[connector.location];

           connector.postSkid.forEach(function(post) {
               if (!skeletonIDs[post.skid]) return; // ignore neuron outside the set of neurons to include
               counts[post.skid][post.location] += 1;
           });
        });

        // CSV of synapse counts (denominators for computing synapse fractions)
        var rows = skids.map(function(skid) {
           var inputs = all_inputs[skid];
           return [skid, inputs["axon"], inputs["dendrite"]].join(",");
        });
        var csv = "skeleton_id, axon_inputs, dendrite_inputs\n" + rows.join("\n");
        CATMAID.FileExporter.saveAs(csv, "input_counts.csv", 'text/csv');

        // Function to export all 4 colors of edges, one per CSV file
        var exportCSV = function(loc1, loc2) {
          var rows = skids.map(function(skid_pre) {
            var outer = edges[skid_pre][loc1];
            return [skid_pre].concat(skids.map(function(skid_post) {
              return outer[skid_post][loc2];
            })).join(",");
          });
          var csv = "," + skids.join(",") + "\n" // header
                  + rows.join("\n");
          CATMAID.FileExporter.saveAs(csv, loc1 + "-" + loc2 + ".csv", 'text/csv')
        };

        exportCSV("axon", "dendrite");
        exportCSV("axon", "axon");
        exportCSV("dendrite", "axon");
        exportCSV("dendrite", "dendrite");

        var namescsv = "skelelon_id, neuron_name\n" // header
                     + skids.map(function(skid) {
                                   return [skid, getName(skid)].join(",");
                                 }).join("\n");
        CATMAID.FileExporter.saveAs(namescsv, "skeleton_id_vs_neuron_name.csv", 'text/csv');
    }
  );


})();
