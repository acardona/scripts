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
        var skids = Object.keys(skeletonIDs).map(function(skid) { return [skid, getName(skid)]; })
                    .sort(function(a, b) { return a[1] < b[1] ? -1 : 1; })
                    .map(function(a) { return a[0]; });


        /*
        var edges = {"axon-dendrite": {},
                     "axon-axon": {},
                     "dendrite-axon": {},
                     "dendrite-dendrite": {}};

        Object.keys(connectors).forEach(function(connectorID) {
          var connector = connectors[connectorID];
          if (!connector.preSkid) return;
          connector.postSkid.forEach(function(post) {
            var color = connector.location + "-" + post.location;
            var edge = edges[color];
            var key = connector.preSkid + "-" + post.skid;
            var counts = edge[key];
            if (counts) edge[key] += 1;
            else e[key] = 1;
          });
        });
        */


        var counts = skids.reduce(function(o, skid) {
                       o[skid] = {"axon": 0,
                                  "dendrite": 0 }; // skid vs count of synapses
                       return o;
                     }, {});
        var edges = skids.reduce(function(o, skid) {
            o[skid] = {"axon": $.extend({}, counts),
                       "dendrite": $.extend({}, counts) };
            return o;
        }, {});
        
        Object.keys(connectors).forEach(function(connectorID) {
           var connector = connectors[connectorID];
           if (!connector.preSkid) return;
           var edge = edges[connector.preSkid];
           if (!edge) {
               // Ignore edge that starts in a neuron that is not annotated as a brain neuron
               return;
           }
           
           var counts = edge[connector.location];

           connector.postSkid.forEach(function(post) {
               if (!edge[post.skid]) return; // ignore neuron outside the set of annotated brain neurons
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

        var exportCSV = function(loc1, loc2) {
          var rows = skids.map(function(skid_pre) {
            var outer = edges[skid_pre][loc1];
            return [skid_pre].concat(skids.map(function(skid_post) {
              return outer[skid_post][loc2];
            }));
          });
          var csv = "," + skids.join(",") + "\n" + rows.map(function(row) { return row.join(","); }).join("\n");
          CATMAID.FileExporter.saveAs(csv, loc1 + "-" + loc2 + ".csv", 'text/csv')
        };

        exportCSV("axon", "dendrite");
        exportCSV("axon", "axon");
        exportCSV("dendrite", "axon");
        exportCSV("dendrite", "dendrite");

        var namescsv = "skelelon_id, neuron_name\n" + skids.map(function(skid) {
            return [skid, getName(skid)].join(",");
        }).join("\n");
        CATMAID.FileExporter.saveAs(namescsv, "skeleton_id_vs_neuron_name.csv", 'text/csv');
    }
  );


})();
