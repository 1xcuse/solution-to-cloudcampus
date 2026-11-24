(function(){
  try {
    var f = document.querySelector('iframe.h5p-iframe');
    var w = f.contentWindow, d = f.contentDocument, ins = w.H5P.instances[0];
    var used = {}, placed = 0, missing = [];
    ins.droppables.forEach(function(z){
      var txt = String(z.text || '').trim();
      var found = false;
      for (var j = 0; j < ins.draggables.length; j++) {
        var dr = ins.draggables[j];
        var t = String(dr.text || (dr.getAnswerText ? dr.getAnswerText() : '') || '').trim();
        if (!used[dr.getIndex()] && t === txt) { ins.drop(dr, z); used[dr.getIndex()] = true; placed++; found = true; break; }
      }
      if (!found) missing.push(txt);
    });
    var btn = d.querySelector('.h5p-question-check-answer, .h5p-question-submit-answer, .h5p-question-check');
    var clicked = false;
    if (btn) { btn.click(); clicked = true; }
    return JSON.stringify({type:'DragText', placed:placed, total:ins.droppables.length, missing:missing, clicked:clicked, score:ins.getScore(), max:ins.getMaxScore(), answered:ins.answered});
  } catch(e) { return JSON.stringify({type:'DragText', error:e.message}); }
})()
