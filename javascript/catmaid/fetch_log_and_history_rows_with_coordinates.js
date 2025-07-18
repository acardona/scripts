// 2025-03-07
// Script to fetch rows with the X,Y,Z position from the Log and History table
// Mind to specify the range_start and the range_length parameters.


(function() {

    // UPDATE these to desired range of rows from the table
    var range = {range_start: 0, range_length: 100};

    var saveJSON = function(rows) {
      saveAs(new Blob([JSON.stringify(rows)], {type: 'text/plain'}), "log_history_rows.json");
    };
    
    var handle = function(json) {

        var rows = new Array(json.transactions.length);

        console.log(json);
        console.log(rows);

        console.log(json.transactions.length);
        
        json.transactions.forEach(function(row, i) {
          var params = {
                'transaction_id': row.transaction_id,
                'execution_time': row.execution_time
              };
          CATMAID.fetch({
                url: project.id + '/transactions/location',  // project.id is a global variable
                method: 'GET',
                data: params,
                parallel: true,
              })
              .then(function(result) {
                  var x = parseFloat(result.x);
                  var y = parseFloat(result.y);
                  var z = parseFloat(result.z);
                  row.position = [x, y, z];
                  rows[i] = row;
                  if (i == json.transactions.length - 1) {
                      console.log(rows);
                      saveJSON(rows);
                  }
              }).catch(function(error) {
                console.log("error at ", i);
                rows[i] = row;
                row.position = [NaN, NaN, NaN];
                if (i == json.transactions.length - 1) {
                      console.log(rows);
                      saveJSON(rows);
                }
              });
        });
    };

    CATMAID.fetch({
              url: project.id +  "/transactions/",
              method: "GET",
              data: range,
              parallel: true,
            }).then(handle);

    
})();
