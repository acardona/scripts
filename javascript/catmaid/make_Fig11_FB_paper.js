/** Recreate Figure 11 for each FB2IN
 *
 * Start by:
 *  1. Load all neurons into a Selection Table.
 *  2. Load them into the Graph widget.
 *  3. Ensure the "MB nomenclature" is used for nanimg neurons, exclusively.
 *  4. Push "Group equally named".
 *  5. Then execute this file.
 *  6. Then select an FB2IN node
 *  7. Then run CATMAID.Fig11.showRelevantEdges(5);
 *  8. Then run CATMAID.Fig11.exportFigurePanel();
 */
var prepareFig11 = function(gg, layout) {
  "use strict";

  // 0. The spatial layout of the column-based graph
  if (!layout) {
    layout = {
      offsetX: 100,
      offsetY: 100,
      column_height: 273.3 * 2, // 588,
      column_spacing: (231 / 3) * 2, // 151.3,
    };
  }

  // 1. The skids for all neurons in Fig. 11, grouped by neuron type
  var MBON_skids = [3299214,4022539,4195012,4230749,4234009,4241237,4401350,4598363,5395823,6699205,6703240,7055857,7802210,7840791,7897469,7910624,8297018,8338584,8798010,8877158,8922644,8980589,9074101,9109799,10163418,11017761,11524047,12233237,14082322,15398730,15421363,15617305,15810983,16178283,16223537,16797672,16846805,16868923,16883909,17013073,17016974,17355757,18028397];
  // All FBNs except FBN-(3|10|11|15|18|22), which do not synapse onto FB2INs consistently or with more than 5 synapses
  var FBN_skids = [7980369, 7026287, 9062992, 8792477, 9251793, 4190567, 5934511, 9064208, 14077615, 8118947, 7540581, 5516552, 4617479, 8864785, 15588620, 7594047, 11003660, 16594509, 14083681, 9527522, 9141404, 16691937, 13197236, 8075484, 10809383, 5321459, 11013351, 11909406, 11889676, 14313750, 15480928, 11018254, 2966602, 12704069];
  // All FBNs
  //var FBN_skids = [2966602,4190567,4617479,5321459,5480553,5516552,5934511,6290724,7026287,7540581,7594047,7980369,8075484,8118947,8792477,8864785,9057043,9062992,9064208,9141404,9251793,9423829,9527522,10202724,10209260,10682660,10809383,11003660,11013351,11018254,11889676,11909406,12704069,13197236,13863331,14077615,14083681,14313750,15480928,15588620,15741865,15766806,16594509,16691937,16856539,17437719];
  var FAN_skids = [4199033,4408397,4514494,5738449,8078096,8712361,8752697,9103732,9238937,3157405,4473922,9848760,12262910,14000746,14260575,14540633,15668309,16475849,16699958,16823703,16987409,17150791,17165711,17300165];
  var FB2IN_skids = [3945246,4103336,4114133,4152272,4201555,4337398,4411688,5091874,6591182,6597872,8052161,8019816,8540770,8814922,9083312,9252296,9287906,9457719,11528017,12233237,12398622,13852833,14077179,15343835,15488316,15623649,15629281,16160495,16848475,17176767,17176781,17177005,17280216,17980792,18035864,19271710];
  // Only a subset of all MBINs
  var MBIN_skids = [2506050,3813487,3886356,3890028,4235139,4381377,4884579,5966099,6611894,7616956,7983899,7901791,7057894,10673895,11525714,12475432,12805363,12871993,14541927,17068730]; 

  // Specify colors (as in Akira's Fig. 11)
  var colors = {
    MBON: new THREE.Color(163/255, 78/255, 158/255),
    FBN: new THREE.Color(90/255, 178/255, 225/255),
    FAN: new THREE.Color(27/255, 118/255, 188/255),
    FB2IN: new THREE.Color(251/255, 176/255, 66/255),
    MBIN: new THREE.Color(16/255, 138/255, 68/255),
  };

  colors["DAN"] = colors["MBIN"];
  colors["OAN"] = colors["MBIN"];

  // Edge type: by neurotransmitter
  var GABA = /(MBON-(b1|b2|d1|h1|h2|g1|g2|m1)|FAN-(7|9))/;
  var Glut = /(MBON-(e2|j1|i1|k1)|FBN-(12|17)|FAN-10|FB2IN-(3))/;
  var ChAT = /(MBON-(a1|a2|c1|e1)|FBN-(3|7|10|20|25))/;

  var determineEdgeEndType = function(neuron) {
    var name = neuron.name;
    if (!name) {
      console.log("No name?", neuron);
      return "circle";
    }
    var r = name.match(GABA);
    if (r) return "tee";
    r = name.match(Glut);
    if (r) return "tee";
    r = name.match(ChAT);
    if (r) return "triangle";
    // unknown:
    return "circle";
  };

  // 2. Group them by name (settings: "MB nomenclature"), to capture left-right homologs
  // Will retain only the relevant part of the name
  var groupByName = function(skids, retain) {
    // WARNING: getting the name will only work if all the skeletons are pre-loaded in another widget
    var getName = CATMAID.NeuronNameService.getInstance().getName;
    return skids.map(function(skid) {
      var tokens = getName(skid).split(",");
      var name;
      if (1 === tokens.length) {
        name = tokens[0];
      } else {
        for (var i=0; i<tokens.length; ++i) {
          if (tokens[i].search(retain) > -1) {
            name = tokens[i].trim();
            break;
          }
        }
      }
      return {skid: skid,
              name: name};
    }).reduce(function(groups, neuron) {
      var group = groups[neuron.name];
      if (group) {
        group.skids[neuron.skid] = true;
      } else {
        group = {name: neuron.name,
                 skids: {},
                 position: new THREE.Vector3(-1, -1, -1),
                 edgeEndType: determineEdgeEndType(neuron)};
        group.skids[neuron.skid] = true;
        groups[neuron.name] = group;
      }
      return groups;
    }, {});
  };

  var MBON_groups = groupByName(MBON_skids, /MBON-[a-z]\d+/);
  var FBN_groups = groupByName(FBN_skids, /FBN-\d+/);
  var FAN_groups = groupByName(FAN_skids, /FAN-\d+/);
  var FBN_FAN_groups = $.extend({}, FBN_groups, FAN_groups);
  var FB2IN_groups = groupByName(FB2IN_skids, /FB2IN-\d+/);
  var MBIN_groups = groupByName(MBIN_skids, /([OD]A|MBI)N-[a-z]\d+/);

  // Map of type name vs group object
  var all_groups = $.extend({},
                            MBON_groups,
                            FBN_groups,
                            FAN_groups,
                            FB2IN_groups,
                            MBIN_groups);


  // 3. Specify neuron group order within each type
  //    Will also filter out neurons not to be included
  var MBON_order = ["MBON-a1", "MBON-a2", // CA
                    "MBON-b3", // IP
                    "MBON-c1", // LP
                    "MBON-d1", "MBON-d2", "MBON-d3", // LA
                    "MBON-e1", "MBON-e2", // UVL
                    "MBON-g1", "MBON-g2", // LVL
                    "MBON-m1", "MBON-n1", "MBON-o1", "MBON-p1", "MBON-q1", // LA/LV 
                    "MBON-h1", "MBON-h2", // SHA
                    "MBON-i1", // UT
                    "MBON-j1", // IT
                    "MBON-k1", // LT
                    ];

  // Works only for e.g. "FBN-10" and "FB2IN-5", would fail for e.g. "MBON-e1".
  var sortGroupsFn = function(g1, g2) {
    var n1 = Number(g1.split("-")[1]),
        n2 = Number(g2.split("-")[1]);
    return n1 < n2 ? -1 : 1;
  };

  var FBN_FAN_order = Object.keys(FBN_groups)
                            .sort(sortGroupsFn)
                            .concat(Object.keys(FAN_groups)
                                          .sort(sortGroupsFn));

  var FB2IN_order = Object.keys(FB2IN_groups).sort(sortGroupsFn);

  var MBIN_order = ["OAN-a1", "OAN-a2", // CA 
                    "DAN-d1", // LA
                    "OAN-e1", "MBIN-e1", "MBIN-e2", // UVL
                    "DAN-f1", // IVL
                    "DAN-g1", "OAN-g1", // UVL
                    "DAN-i1", // UT
                    "DAN-k1", // LT
                    ];

  // 4. Organize the 4 columns
  //    Will also specify the node text label and its relative position to the node.
  var n_columns = 4;

  // Sets the position of each group within a column according to the given order
  // Groups whose name is not in the order are ignored
  var intoColumn = function(order, groups, column_index) {
    order.forEach(function(name, i) {
      var group = groups[name];
      group.column_index = column_index;
      group.position.x = layout.offsetX + column_index * layout.column_spacing;
      group.position.y = layout.offsetY + (i / (order.length -1)) * layout.column_height;
      var halign;
      if (0 === column_index) {
        // First column 
        halign = "left";
        group.node_label = group.name;
      }
      else if (n_columns -1 === column_index) {
        // Last column 
        halign = "right";
        group.node_label = group.name;
      }
      else {
        // Middle columns
        halign = "center";
        // Number only
        group.node_label = group.name.split("-")[1];
      }
      group.style = {
        "text-halign": halign,
        "text-valign": "center",
        "shape": "hexagon",
        "width": "20px", // smaller: default is 30
        "height": "20px",
        "font-size": "12px",
        "color": name.startsWith("FAN") ? "white" : "black",
      };
    });
  };

  // Need zoom 100% for any dimension numbers to make sense,
  // and for arrows to be placed correctly in the exported SVG
  gg.cy.zoom(1.0);

  intoColumn(MBON_order, MBON_groups, 0);
  intoColumn(FBN_FAN_order, FBN_FAN_groups, 1);
  intoColumn(FB2IN_order, FB2IN_groups, 2);
  intoColumn(MBIN_order, MBIN_groups, 3);


  // Map of skid vs the group it belongs to
  // NOTE: uses whether the position is set in the group to accept it or not.
  var all_in_skids = Object.keys(all_groups).reduce(function(sks, name) {
    // Skip groups for which no position was specified
    var group = all_groups[name];
    if (-1 === group.position.x) {
      console.log("Ignoring: ", name);
      return sks;
    }
    Object.keys(group.skids).forEach(function(skid) {
      sks[skid] = group;
    });
    return sks;
  }, {});


  // 5. Place nodes into position within the graph 
  gg.cy.nodes().show();

  // Hide edges: re-renders nodes a lot faster
  gg.cy.edges().hide();

  // Define the "arrow" of each edge, and color the edge, according to the source node
  gg.cy.edges().each(function(i, edge) {
    var group = all_in_skids[edge.source().data().skeletons[0].id];
    if (group) {
      var color = edge.source().style()["background-color"];
      edge.style({"target-arrow-shape": group.edgeEndType,
                  "line-color": color,
                  "target-arrow-color": color});
    } else {
      console.log("No group for: ", edge.source(), edge.source().data());
    }
  });

  gg.cy.nodes().each(function(i, node) {
    var group = all_in_skids[node.data().skeletons[0].id];
    if (!group) {
      console.log("Group not present for " + node.data().label);
      node.hide();
      return;
    }
    node.renderedPosition({x: group.position.x,
                           y: group.position.y});
    if (group.name) {
      node.data("label", group.node_label);
      var color = colors[group.name.substring(0, group.name.indexOf("-"))];
      node.style("background-color", "#" + color.getHexString());
      node.css(group.style);
      node.data("shape", "hexagon"); // needed for SVGFactory to recognize it
    } else {
      console.log("group.name failed for", group, CATMAID.NeuronNameService.getInstance().getName(Object.keys(group.skids)[0]));
    }
  });

  gg.cy.center();

  // 6. Functions to show only edges
  var getColumnIndex = function(node) {
    if (! all_in_skids[node.data().skeletons[0].id]) {
      console.log(node);
      console.log("a");
    }
    return all_in_skids[node.data().skeletons[0].id].column_index;
  };

  // Show edges from nodes on the column to the left of the node's column
  var showIncommingEdges = function(node, threshold) {
    if (!node.visible()) return;
    var column_index = getColumnIndex(node);
    node.connectedEdges().each(function(i, edge) {
      if (!edge.source().visible()) return;
      if (getColumnIndex(edge.source()) === column_index - 1
       && edge.data().weight >= threshold) {
         edge.show();
         if (column_index - 1 > 0) {
           // Recurse
           showIncommingEdges(edge.source(), threshold);
         }
       }
    });
  };

  // Show edges onto nodes on the column to the right of the node's column 
  var showOutgoingEdges = function(node, threshold) {
    if (!node.visible()) return;
    var column_index = getColumnIndex(node);
    node.connectedEdges().each(function(i, edge) {
      if (!edge.target().visible()) return;
      if (edge.data().weight >= threshold
       && getColumnIndex(edge.target()) === column_index + 1) {
         edge.show();
         if (column_index + 1 < n_columns -1) {
           // Recurse
           showOutgoingEdges(edge.target(), threshold);
         }
       }
    });
  };

  /**
   * A function to hide all edges and show only those relevant to the selected node.
   */
  var showRelevantEdges = function(edge_weight_threshold) {
    gg.cy.edges().hide();
    gg.cy.$(':selected').each(function(i, node) {
      showIncommingEdges(node, edge_weight_threshold);
      showOutgoingEdges(node, edge_weight_threshold);
   });
  };

  // 7. Functions to generate a panel of Fig11

  /**
   * Make a single panel of the Fig11 by selecting one FB2IN skid,
   * running the showRelevantEdges on it, and then export to SVG
   * and decorate the SVG with the MB compartment annotations.
   */
  var makeFig11Panel = function(edge_weight_threshold, FB2IN_skid) {
    // Unselect all, select only the given node
    gg.cy.nodes().each(function(i, node) {
      node.unselect();
      if (node.data().skeletons[FB2IN_skid]) {
        node.select();
      }
    });

    setTimeout(function() {
      showRelevantEdges(edge_weight_threshold);
      setTimeout(function() {
        exportFigurePanel();
      }, 2000);
    }, 2000);
  };

  var exportNodes = function(svgfactory, templateTextStyle, templateShapeStyle) {
    var renderer = gg.cy.renderer();

    // Export nodes
    gg.cy.nodes().each(function(i, node) {
      // Modified from GroupGraph.generateSVG
      if (node.hidden()) {
        return;
      }
      var data = node.data();
      var pos = node.position();
      var style = node.style();

      // clone:
      templateTextStyle = $.extend({}, templateTextStyle);

      templateTextStyle['fill'] = style['color'];
      templateTextStyle['opacity'] = CATMAID.tools.getDefined(style['text-opacity'], '1');
      templateShapeStyle['fill'] = style['background-color'];
      templateShapeStyle['stroke'] = style['border-color'];
      templateShapeStyle['stroke-width'] = style['border-width'];
      templateShapeStyle['opacity'] = CATMAID.tools.getDefined(style['opacity'], '1');


      if (data.shape === 'ellipse') {
        var r = node.width() / 2.0;
        svgfactory.drawLabeledCircle(pos.x, pos.y, r, templateShapeStyle,
            data.label, 0, -1.5 * r, templateTextStyle);
      } else if (data.shape in renderer.nodeShapes) {
        var w = node.width();
        var h = node.height();
        var shape = renderer.nodeShapes[data.shape].points;
        // Determine label position and style
        var valign = style["text-valign"];
        var halign = style["text-halign"];
        var labelHeight = node._private.rstyle.labelHeight;
        // Label position relative to node position
        var dx = 0;
        var dy = 0;
        if      ("center" === halign) { dx = 0;          templateTextStyle["text-anchor"] = "middle"; }
        else if ("right"  === halign) { dx =   w/2 + 1;  templateTextStyle["text-anchor"] = "start";  }
        else if ("left"   === halign) { dx = -(w/2 + 1); templateTextStyle["text-anchor"] = "end";   }
        if      ("center" === valign) { dy = labelHeight/3; }
        else if ("bottom" === valign) { dy =   h/2 + 1 + labelHeight; }
        else if ("top"    === valign) { dy = -(h/2 + 1);  }
        svgfactory.drawLabeledPolygonPath(pos.x, pos.y, w, h, shape,
           templateShapeStyle, data.label, dx, dy, templateTextStyle);
      } else {
        CATMAID.warn('Could not export graph element. Unknown shape: ' + data.shape);
      }
    });
  };

  var exportEdges = function(svgfactory, templateTextStyle, templateLineStyle, templateLineOptions) {
    gg.cy.edges().each(function(i, edge) {
      if (edge.hidden()) {
        return;
      }
      var data = edge.data();
      var startId = data.start;
      var style = edge.style();
      var color = edge.source().style()["background-color"];
      var edgeEndType = all_in_skids[edge.source().data().skeletons[0].id].edgeEndType;

      var rscratch = edge._private.rscratch;

      // clone:
      templateTextStyle = $.extend({}, templateTextStyle);

      templateTextStyle['fill'] = data.label_color;
      templateTextStyle['font-size'] = style['font-size'];
      templateTextStyle['opacity'] = 0; // CATMAID.tools.getDefined(style['text-opacity'], '1');
      templateLineStyle['stroke'] = edge.source().style()["background-color"]; // style['line-color'];
      templateLineStyle['opacity'] = CATMAID.tools.getDefined(style['opacity'], '1');

      var strokeWidth = 'width' in data ? data.width : 1.0;
      templateLineStyle['stroke-width'] = strokeWidth + 'px';

      templateLineOptions['strokeWidth'] = strokeWidth;

      templateLineOptions['edgeType'] = rscratch.edgeType;
      switch (rscratch.edgeType) {
        case 'bezier':
        case 'self':
        case 'compound':
        case 'multibezier':
          templateLineOptions['controlPoints'] = rscratch.ctrlpts;
          break;
      }
      if (data.label) {
        templateLineOptions['label'] = data.label;
        templateLineOptions['labelOffsetX'] = 0;
        templateLineOptions['labelOffsetY'] = 0;
        templateLineOptions['labelStyle'] = templateTextStyle;
        templateLineOptions['labelX'] = rscratch.labelX;
        templateLineOptions['labelY'] = rscratch.labelY;
      } else {
        templateLineOptions['label'] = undefined;
      }

      // Cytoscape.js luckily keeps render locations cached, so we don't need
      // to do the math ourselves. Arrow locations are available even without
      // arrows in use.
      var x1 = rscratch.startX,
          y1 = rscratch.startY,
          x2 = rscratch.arrowEndX,
          y2 = rscratch.arrowEndY;

      if (data.arrow && data.arrow !== 'none') {
        templateLineOptions['arrow'] = edgeEndType; // data.arrow; // TODO ??
        templateLineOptions['arrowStyle'] = templateLineStyle;
        templateLineStyle['target-arrow-shape'] = edgeEndType;
        templateLineStyle['line-color'] = color;
        templateLineStyle['target-arrow-color'] = color;
        /*
        if (data.arrow === 'triangle') {
          // Since our arrows width are in a reather narrow ranger, setting the
          // arrow dimensions in absolute pixels is easier.
          var d = strokeWidth; // 3 * (0.5 * strokeWidth + 1.5);
          templateLineOptions['arrowUnit'] = 'userSpaceOnUse';
          templateLineOptions['arrowWidth'] = d;
        } else {
          CATMAID.warn('Could not export graph element. Unknown arrow: ' + data.arrow);
        }
        */
      } else {
        templateLineOptions['arrow'] = undefined;
      }

      svgfactory.drawLine(x1, y1, x2, y2, templateLineStyle, templateLineOptions);
    });
  }

  var exportFigurePanel = function(options) {
    options = options || {};

    var div= $('#graph_widget' + gg.widgetID),
        width = div.width(),
        height = div.height(),
        extent = gg.cy.extent(),
        viewX = extent.x1,
        viewY = extent.y1,
        viewWidth = extent.x2 - extent.x1,
        viewHeight = extent.y2 - extent.y1;

    var svgfactory = new CATMAID.SVGFactory(width, height, viewX, viewY, viewWidth, viewHeight);

    var templateTextStyle = {
      'fill': null,
      'stroke-width': '0px',
      'font-family': 'Verdana',
      'font-size': '12px'
    };

    var templateLineStyle = {
      'stroke': null,
      'stroke-width': '1px',
      'fill': 'none',
      //'marker-end': "url(#Arrow1Send)",
    };

    var templateShapeStyle = {
      'fill': null,
      'stroke': null,
      'stroke-width': null
    };

    var templateLineOptions = {
      'edgeType': 'haystack',
      'arrowOnSeperateLine': CATMAID.getOption(options, 'arrowOnSeperateLine', false),
      'arrowLineShrinking': CATMAID.getOption(options, 'arrowLineShrinking', true),
      'refX': CATMAID.getOption(options, 'arrowRefX', 0), // default: undefined
    };

    // Find selected node, keep it, and deselect it
    var selected_node = null;
    gg.cy.nodes().each(function(i, node) {
      if (node.selected()) {
        selected_node = node;
        node.unselect();
      }
    });
    
    exportEdges(svgfactory, templateTextStyle, templateLineStyle, templateLineOptions);
    exportNodes(svgfactory, templateTextStyle, templateShapeStyle);

    // Restore
    selected_node.select();


    var MBON_bar = [
      {name: "CA", span: 2},
      {name: "IP", span: 1},
      {name: "LP", span: 1},
      {name: "LA", span: 3},
      {name: "UVL", span: 2},
      {name: "LVL", span: 2},
      {name: "LA/VL", span: 5},
      {name: "SHA", span: 2},
      {name: "UT", span: 1},
      {name: "IT", span: 1},
      {name: "LT", span: 1},
    ];

    var MBIN_bar = [
      {name: "CA", span: 2},
      {name: "LA", span: 1},
      {name: "UVL", span: 3},
      {name: "IVL", span: 1},
      {name: "LVL", span: 2},
      {name: "UT", span: 1},
      {name: "LT", span: 1},
    ];

    // Determine bounding box of node centers
    var bounds = {topleft: null,
                  bottomright: null};
    gg.cy.nodes().each(function(i, node) {
      var position = node.position();
      if (null == bounds.topleft) {
        bounds.topleft = {x: position.x,
                          y: position.y};
      } else {
        bounds.topleft.x = Math.min(bounds.topleft.x, position.x);
        bounds.topleft.y = Math.min(bounds.topleft.y, position.y);
      }
      if (null == bounds.bottomright) {
        bounds.bottomright = {x: position.x,
                              y: position.y};
      } else {
        bounds.bottomright.x = Math.max(bounds.bottomright.x, position.x);
        bounds.bottomright.y = Math.max(bounds.bottomright.y, position.y);
      }
    });

    // Correction for node height: half the node height
    //bounds.topleft.y -= 10;
    //bounds.bottomright.y += 10;

    var width  = bounds.bottomright.x - bounds.topleft.x;
    var height = bounds.bottomright.y - bounds.topleft.y;

    var neuron_name_width = 70;
    var neuron_name_spacing = 5;
    var MBON_row_height = height / (MBON_order.length -1);
    var MBIN_row_height = height / (MBIN_order.length -1);

    var line_style = {
      stroke: "#000",
      "stroke-width": "4px",
      fill: "none",
      opacity: "1", 
    };
    var line_options = {
      edgeType: "straight",
    };
    var text_style = {
      fill: "#000",
      "stroke-width": "0px",
      "font-family": "Verdana",
      "font-size": "16px",
      opacity: "1",
    };

    var MBON_text_style = $.extend({"text-anchor": "end"}, text_style);
    var MBIN_text_style = $.extend({"text-anchor": "start"}, text_style);

    var node_height = 20;
    var bar_label_height = 14;

    var accum_span = 0;
    MBON_bar.forEach(function(compartment) {
      var x = bounds.topleft.x - neuron_name_width - 5;
      var y = bounds.topleft.y + accum_span * MBON_row_height;
      var y1 = y - node_height/2;
      var y2 = y + (compartment.span -1) * MBON_row_height + node_height/2;
      svgfactory.drawLine(x, y1, x, y2, line_style, line_options);
      svgfactory.drawText(x - neuron_name_spacing, (y1 + y2) / 2 + bar_label_height/2, compartment.name, MBON_text_style);
      accum_span += compartment.span;
    });

    accum_span = 0;
    MBIN_bar.forEach(function(compartment) {
      var x = bounds.topleft.x + width + neuron_name_width;
      var y = bounds.topleft.y + accum_span * MBIN_row_height;
      var y1 = y - node_height/2;
      var y2 = y + (compartment.span -1) * MBIN_row_height + node_height/2;
      svgfactory.drawLine(x, y1, x, y2, line_style, line_options);
      svgfactory.drawText(x + neuron_name_spacing, (y1 + y2) / 2 + bar_label_height/2, compartment.name, MBIN_text_style);
      accum_span += compartment.span;
    });

    // Add column titles and main title: the FB2IN

    var title_style = {
      "stroke-width": "0px",
      "font-family": "Verdana",
      "font-size": "20px",
      "opacity": "1",
    };

    var hex = function(color) {
      return '#' + color.getHexString();
    };

    var dy = -30;

    svgfactory.drawText(
      bounds.topleft.x - 35,
      bounds.topleft.y + dy,
      "MBONs",
      $.extend({}, title_style, {"fill": hex(colors["MBON"]), "text-anchor": "middle"})
    );

    svgfactory.drawText(
      bounds.topleft.x + layout.column_spacing,
      bounds.topleft.y + dy,
      "FBNs",
      $.extend({}, title_style, {"fill": hex(colors["FBN"]), "text-anchor": "end"})
    );

    svgfactory.drawText(
      bounds.topleft.x + layout.column_spacing,
      bounds.topleft.y + dy,
      "/FANs",
      $.extend({}, title_style, {"fill": hex(colors["FAN"]), "text-anchor": "start"})
    );

    svgfactory.drawText(
      bounds.topleft.x + 2 * layout.column_spacing,
      bounds.topleft.y + dy,
      "FB2INs",
      $.extend({}, title_style, {"fill": hex(colors["FB2IN"]), "text-anchor": "middle"})
    );

    svgfactory.drawText(
      bounds.topleft.x + 3 * layout.column_spacing - 20,
      bounds.topleft.y + dy,
      "DANs/OANs",
      $.extend({}, title_style, {"fill": hex(colors["MBIN"]), "text-anchor": "start"})
    );

    // Title of the whole panel: the name of the selected FB2IN
    var group = all_in_skids[selected_node.data().skeletons[0].id];

    svgfactory.drawText(
      bounds.topleft.x + 1.5 * layout.column_spacing,
      bounds.topleft.y - 60,
      group.name,
      $.extend({}, title_style, {"fill": "black", "text-anchor": "middle"})
    );

    svgfactory.save("fig11_" + group.name + ".svg");
  };



  CATMAID.Fig11 = {};
  CATMAID.Fig11.all_in_skids = all_in_skids;
  CATMAID.Fig11.showRelevantEdges = showRelevantEdges;
  CATMAID.Fig11.exportFigurePanel = exportFigurePanel;

};


prepareFig11(CATMAID.GroupGraph.prototype.getInstances()[0]);

