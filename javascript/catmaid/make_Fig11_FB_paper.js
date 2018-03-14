/** Recreate Figure 11 for each FB2IN
 */
(function(gg, layout) {
  "use strict";

	// 0. The spatial layout of the column-based graph
	if (!layout) {
		layout = {
			offsetX: 100,
			offsetY: 100,
			column_height: 600,
			column_spacing: 151.3,
		};
	}

	// 1. The skids for all neurons in Fig. 11, grouped by neuron type
	var MBON_skids = [3299214,4022539,4195012,4230749,4234009,4241237,4401350,4598109,4598363,5395823,6699205,6703240,7055857,7802210,7840791,7897469,7910624,8094859,8297018,8338584,8798010,8877158,8922644,8980589,9074101,9109799,9469519,10163418,11017761,11524047,14082322,15253921,15398730,15421363,15617305,15810983,16178283,16223537,16782830,16797672,16846805,16868923,16883909,17013073,17016974,17147698,17355757,18028397];
	var FBN_skids = [11003660, 16594509, 7594047, 2966602, 10682660, 5480553, 17437719, 10209260, 9423829, 14077615, 8075484, 15741865, 5321459, 6290724, 9062992, 9141404, 16691937, 5934511, 11909406, 9064208, 15588620, 8864785, 4617479, 8118947, 16856539, 5516552, 7026287, 7540581, 15480928, 5681132, 4190567, 10809383, 11013351, 11018254, 11889676, 7980369, 12704069, 13197236, 14313750, 9527522, 16427492, 17854345, 13743125, 10202724, 4144377, 9251793, 15766806, 14083681, 9057043, 8792477, 7574701, 5870071, 4180774, 13863331];
	var FAN_skids = [4199033,4408397,4514494,5738449,8078096,8712361,8752697,9103732,9238937,3157405,4473922,9848760,12262910,14000746,14260575,14540633,15668309,16475849,16699958,16823703,16987409,17150791,17165711,17300165];
	var FB2IN_skids = [3945246,4103336,4114133,4152272,4201555,4337398,4411688,5091874,6591182,6597872,8052161,8019816,8540770,8814922,9083312,9252296,9287906,9457719,11528017,12233237,12398622,13852833,14077179,15343835,15488316,15623649,15629281,16160495,16848475,17176767,17176781,17177005,17280216,17980792,18035864,19271710];
	// Only a subset of all MBINs
	var MBIN_skids = [2506050,3813487,3886356,3890028,4235139,4381377,4884579,5966099,6611894,7616956,7983899,7901791,7057894,10673895,11525714,12475432,12805363,12871993,14541927,17068730];

	// Specify colors (as in Akira's Fig. 11)
	var colors = {
		MBON: new THREE.Color(161, 53, 160),
		FBN: new THREE.Color(105, 182, 229),
		FAN: new THREE.Color(57, 114, 194),
		FB2IN: new THREE.Color(249, 167, 45),
		MBIN: new THREE.Color(41, 139, 61),
	};

	colors["DAN"] = colors["MBIN"];
	colors["OAN"] = colors["MBIN"];


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
								 position: new THREE.Vector3(-1, -1, -1)};
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

	// Map of skid vs the group it belongs to
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
			group.position.x = offsetX + column_index * column_spacing;
			group.position.y = offsetY + (i / (order.length -1)) * column_height;
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
			};
		});
	};

	intoColumn(MBON_order, MBON_groups, 0);
	intoColumn(FBN_FAN_order, FBN_FAN_groups, 1);
	intoColumn(FB2IN_order, FB2IN_groups, 2);
	intoColumn(MBIN_order, MBIN_groups, 3);


	// 5. Place nodes into position within the graph 
	gg.cy.nodes().show();

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
	var showRelevantEdges = function(gg, edge_weight_threshold) {
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
	var makeFig11Panel = function(gg, edge_weight_threshold, FB2IN_skid) {
		// Unselect all, select only the given node
		gg.cy.nodes().each(function(i, node) {
			node.unselect();
			if (node.data().skeletons[FB2IN_skid]) {
				node.select();
			}
		});

		setTimeout(function() {
			showRelevantEdges(gg, edge_weight_threshold);
			setTimeout(function() {
				exportFigurePanel(gg);
			}, 2000);
		}, 2000);
	};

	var exportFigurePanel = function(gg) {

		var svgfactory = gg.generateSVG();

		var MBON_bar = [
			{name: "CA", span: 2},
			{name: "IP", span: 1},
			{name: "LP", span: 1},
			{name: "LA", span: 3},
			{name: "UVL", span: 2},
			{name: "LVL", span: 2},
			{name: "LA/VL", span: 4},
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
		var bounds = {topleft: null, bottomright: null};
		gg.cy.nodes().each(function(i, node) {
			var position = node.position();
			if (null == bounds.topleft) bounds.topleft = {x: position.x, y: position.y};
			else {
				bounds.topleft.x = Math.min(bounds.topleft.x, position.x);
				bounds.topleft.y = Math.min(bounds.topleft.y, position.y);
			}
			if (null == bounds.bottomright) bounds.bottomright = {x: position.x, y: position.y};
			else {
				bounds.bottomright.x = Math.max(bounds.bottomright.x, position.x);
				bounds.bottomright.y = Math.max(bounds.bottomright.y, position.y);
			}
		});

		var width  = bounds.bottomright.x - bounds.topleft.x;
		var height = bounds.bottomright.y - bounds.topleft.y;

		var neuron_name_width = 50;
		var neuron_name_spacing = 5;
		var MBON_row_height = height / MBON_order.length;
		var MBIN_row_height = height / MBIN_order.length;

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
			opacity: "0",
		};

		var MBON_text_style = $.extend({"text-align": "end"}, text_style);
		var MBIN_text_style = $.extend({"text-align": "start"}, text_style);

		MBON_bar.forEach(function(compartment, i) {
			var x = bounds.topleft.x - neuron_name_width;
			var y1 = bounds.topleft.y + (i + 0.2) * MBON_row_height;
			var y2 = bounds.topleft.y + (i + compartment.span - 0.2) * MBON_row_height;
			svgfactory.drawLine(x, y1, x, y2, line_style, line_options);
			svgfactory.drawText(x - neuron_name_spacing, (y1 + y2) / 2, compartment.name, MBON_text_style);
		});

		MBIN_bar.forEach(function(compartment, i) {
			var x = bounds.topleft.x + width + neuron_name_spacing;
			var y1 = bounds.topleft.y + (i + 0.2) * MBIN_row_height;
			var y2 = bounds.topleft.y + (i + compartment.span - 0.2) * MBIN_row_height;
			svgfactory.drawLine(x, y1, x, y2, line_style, line_options);
			svgfactory.drawText(x + neuron_name_spacing, (y1 + y2) / 2, compartment.name, text_style);
		});

		svgfactory.save("fig11-panel-.svg");
	};


	CATMAID.Fig11 = {};
	CATMAID.Fig11.all_in_skids = all_in_skids;
	CATMAID.Fig11.showRelevantEdges = showRelevantEdges;
	CATMAID.Fig11.makeFig11Panel = makeFig11Panel;

})();
