// README:
// 1. Open the developer tools in Chrome
// 2. Paste this code below into the javascript Console
// 3. Select a skeleton node
// 4. Invoke this function in the console, for "MR1.4-3 re-registered":

// CATMAID.openInNeuroglancer("https://spelunker.cave-explorer.org/#!%7B%22dimensions%22:%7B%22x%22:%5B8e-9%2C%22m%22%5D%2C%22y%22:%5B8e-9%2C%22m%22%5D%2C%22z%22:%5B8e-9%2C%22m%22%5D%7D%2C%22position%22:%5B6888%2C7804%2C9048%5D%2C%22crossSectionScale%22:0.5%2C%22projectionOrientation%22:%5B-0.5596503019332886%2C0.16869042813777924%2C0.09972338378429413%2C0.8052268624305725%5D%2C%22projectionScale%22:1339591.339963096%2C%22layers%22:%5B%7B%22type%22:%22image%22%2C%22source%22:%22precomputed://gs://fly-larva-sf/MR1.4-3.n5-derived/clahe%22%2C%22tab%22:%22source%22%2C%22shader%22:%22#uicontrol%20float%20black%20slider%28min=0%2C%20max=1%2C%20default=0.0%29%5Cn#uicontrol%20float%20white%20slider%28min=0%2C%20max=1%2C%20default=1.0%29%5Cnfloat%20rescale%28float%20value%29%20%7B%5Cn%20%20return%20%28value%20-%20black%29%20/%20%28white%20-%20black%29%3B%5Cn%7D%5Cnvoid%20main%28%29%20%7B%5Cn%20%20float%20val%20=%20toNormalized%28getDataValue%28%29%29%3B%5Cn%20%20if%20%28val%20%3C%20black%29%20%7B%5Cn%20%20%20%20emitRGB%28vec3%280%2C0%2C0%29%29%3B%5Cn%20%20%7D%20else%20if%20%28val%20%3E%20white%29%20%7B%5Cn%20%20%20%20emitRGB%28vec3%281.0%2C%201.0%2C%201.0%29%29%3B%5Cn%20%20%7D%20else%20%7B%5Cn%20%20%20%20emitGrayscale%28rescale%28val%29%29%3B%5Cn%20%20%7D%5Cn%7D%5Cn%22%2C%22name%22:%22img%22%7D%2C%7B%22type%22:%22segmentation%22%2C%22source%22:%22graphene://middleauth+https://local.cave.braininbrain.org/segmentation/table/zlatic_mr143%22%2C%22tab%22:%22source%22%2C%22segments%22:%5B%5D%2C%22name%22:%22seg%22%7D%2C%7B%22type%22:%22annotation%22%2C%22source%22:%7B%22url%22:%22local://annotations%22%2C%22transform%22:%7B%22outputDimensions%22:%7B%22x%22:%5B8e-9%2C%22m%22%5D%2C%22y%22:%5B8e-9%2C%22m%22%5D%2C%22z%22:%5B8e-9%2C%22m%22%5D%7D%2C%22inputDimensions%22:%7B%220%22:%5B4e-9%2C%22m%22%5D%2C%221%22:%5B4e-9%2C%22m%22%5D%2C%222%22:%5B4e-8%2C%22m%22%5D%7D%7D%7D%2C%22tab%22:%22source%22%2C%22annotations%22:%5B%5D%2C%22name%22:%22ann%22%7D%5D%2C%22showSlices%22:false%2C%22selectedLayer%22:%7B%22visible%22:true%2C%22layer%22:%22seg%22%7D%2C%22layout%22:%22xy-3d%22%7D");

// You will see a new Chrome tab opening at the exact same location as the selected skeleton node in CATMAID

(function() {

    var openInNeuroglancer = function(base_url) {
      var atn = SkeletonAnnotations.atn;
      var resolution = project.focusedStackViewer.primaryStack.resolution;
      // Active node coordinates in pixels:
      var x = parseInt(atn.x / resolution.x),
          y = parseInt(atn.y / resolution.y),
          z = parseInt(atn.z / resolution.z);

      // Easier: (but not for the active skeleton node, only the center position of the stack viewer)
      //var s = project.focusedStackViewer;
      // then use s.x, s.y and s.z
        
      // Replace the base URL coordinates with x,y,z
      // Find this:
      // ...position%22:%5B\d+%2C\d+%2c\d+
      var expression = /(^.*)(position\%22:\%5B\d+\%2C\d+\%2C\d+)(.*$)/;
      var m = base_url.match(expression); // an array where 0 is whole matched input string, and 1,2,3 are the three groups
      var replacement = "position%22:%5B" + x + "%2C" + y + "%2C" + z;
      //console.log(m);
      var new_url = m[1] + replacement + m[3];
      console.log(new_url);
      console.log(x, y, z);
      // Open a new tab with this URL
      window.open(new_url, '_blank').focus()
    };

    CATMAID.openInNeuroglancer = openInNeuroglancer;
})();



