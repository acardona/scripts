/**
 * Export all arbors from the first SelectionTable into a CSV file,
 * ignoring the treenode radius.
 * 
 * Albert Cardona 2019-03-13
 * 
 * Requires pasting the contents of this file to the console before running:
 * https://github.com/jimmywarting/StreamSaver.js/blob/master/StreamSaver.js
 */

(function() {

  const fileStream = streamSaver.createWriteStream('skeleton_coordinates.csv');
  const writer = fileStream.getWriter();
  const encoder = new TextEncoder();

  // CSV header
  writer.write(encoder.encode(["skeleton_id", "treenode_id", "parent_id", "x", "y", "z"].join(',') + "\n"));

  fetchSkeletons(
    CATMAID.NeuronSearch.prototype.getFirstInstance().getSelectedSkeletons(),
    function(skid) {
      return CATMAID.makeURL(project.id + '/' + skid + '/0/0/compact-skeleton'); // Without connectors or tags  
    },
    function(skid) {
        return {}; // POST
    },
    function(skid, json) {
        var ap = new CATMAID.ArborParser().tree(json[0]);
        var edges = ap.arbor.edges;
        var positions = ap.positions;
        edges[ap.arbor.root] = ''; // rather than null
        var rows = [];
        ap.arbor.nodesArray().forEach(function(tnid) {
          var v = ap.positions[tnid];
          rows.push(skid + "," + tnid + "," + edges[tnid]  + "," + v.x + "," + v.y + "," + v.z + "\n");
        });
        writer.write(encoder.encode(rows.join("")));
    },
    function(skid) {
        console.log("Failed to export arbor skid " + skid);
    },
    function() {
        writer.close();
    }
  );

})();
