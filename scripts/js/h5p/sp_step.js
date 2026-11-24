(function(){
  try {
    var f = document.querySelector('iframe.h5p-iframe');
    var w = f.contentWindow, ins = w.H5P.instances[0], c = ins.content, d = f.contentDocument;
    function norm(s){ return String(s).replace(/<[^>]+>/g,' ').replace(/\s+/g,' ').trim(); }
    if (!ins.params) return JSON.stringify({status:'NO_PARAMS'});
    var targets = ins.params.paragraphs.map(norm);
    var els = c.getDraggables();
    var cur = els.map(function(el){ var cc = el.querySelector('.h5p-sort-paragraphs-paragraph-container'); return norm((cc||el).innerText||'').slice(0,50); });
    var tgt = targets.map(function(t){ return t.slice(0,50); });
    var i = -1;
    for (var k=0;k<cur.length;k++) { if (cur[k] !== tgt[k]) { i = k; break; } }
    if (i < 0) {
      var cb = d.querySelector('.h5p-question-check-answer');
      if (cb) cb.click();
      return JSON.stringify({status:'SORTED_AND_CHECKED', score:ins.getScore(), max:ins.getMaxScore()});
    }
    var j = -1;
    for (var m=i;m<cur.length;m++) { if (cur[m] === tgt[i]) { j = m; break; } }
    if (j < 0) return JSON.stringify({status:'NOMATCH', cur:cur, tgt:tgt});
    c.handleDraggableMoved(els[j], 'up');
    return JSON.stringify({status:'MOVED', j:j, target:tgt[i].slice(0,30)});
  } catch(e) { return JSON.stringify({status:'ERROR', error:e.message}); }
})()
