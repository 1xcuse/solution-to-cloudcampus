(function(){
  try {
    var f = document.querySelector('iframe.h5p-iframe');
    var w = f.contentWindow, ins = w.H5P.instances[0];
    var grid = ins.grid, es = grid.elementSize, g = grid.wordGrid;
    var H = g.length, W = g[0].length;
    var dirs = [[1,0],[-1,0],[0,1],[0,-1],[1,1],[-1,1],[1,-1],[-1,-1]];
    function findPaths(word){
      var paths = [], lower = String(word).toLowerCase();
      for (var r=0;r<H;r++) for (var c=0;c<W;c++) {
        if (String(g[r][c]||'').toLowerCase() !== lower[0]) continue;
        dirs.forEach(function(dir){
          var ok = true, cells = [];
          for (var k=1;k<lower.length;k++){
            var rr=r+dir[1]*k, cc=c+dir[0]*k;
            if (rr<0||rr>=H||cc<0||cc>=W|| String(g[rr][cc]||'').toLowerCase()!==lower[k]) { ok=false; break; }
            cells.push([rr,cc]);
          }
          if (ok) { cells.unshift([r,c]); paths.push(cells); }
        });
      }
      return paths;
    }
    var canvas = grid.$drawingCanvas[0], rect = canvas.getBoundingClientRect();
    var words = ins.vocabulary.words.slice();
    var results = [];
    words.forEach(function(word){
      var paths = findPaths(word);
      if (!paths.length) { results.push(word + ':NO_PATH'); return; }
      var cells = paths[0];
      function fire(type, cell, buttons) {
        var x = (cell[1] + 0.5) * es, y = (cell[0] + 0.5) * es;
        canvas.dispatchEvent(new w.MouseEvent(type, {bubbles:true, cancelable:true, view:w, clientX: rect.left + x, clientY: rect.top + y, button:0, buttons: (type==='mouseup'?0:1)}));
      }
      fire('mousedown', cells[0]);
      fire('mousemove', cells[0]);
      for (var i=1;i<cells.length;i++) fire('mousemove', cells[i]);
      fire('mouseup', cells[cells.length-1]);
      results.push(word);
    });
    var submitted = false;
    if (ins.$submitButton && ins.$submitButton.length) { ins.$submitButton.click(); submitted = true; }
    else { var b = f.contentDocument.querySelector('button'); if (b) { b.click(); submitted = true; } }
    return JSON.stringify({type:'FindTheWords', found:ins.numFound, total:ins.vocabulary.words.length, score:ins.getScore(), max:ins.getMaxScore(), submitted:submitted, results:results});
  } catch(e) { return JSON.stringify({type:'FindTheWords', error:e.message}); }
})()
