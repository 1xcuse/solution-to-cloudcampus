(function(){
  try {
    var f = document.querySelector('iframe.h5p-iframe');
    if (!f) return JSON.stringify({status:'NO_IFRAME'});
    var w = f.contentWindow, d = f.contentDocument;
    var ins = (w.H5P && w.H5P.instances && w.H5P.instances[0]) || null;
    if (!ins) return JSON.stringify({status:'NO_INSTANCE'});
    var body = d.body.innerText.replace(/\s+/g,' ');
    var info = {activeChapter: ins.activeChapter, completed: ins.completed};
    // cover page?
    var coverBtn = [].slice.call(d.querySelectorAll('button, .h5p-joubelui-button')).filter(function(b){
      return /begin|start|continue|start reading/i.test((b.innerText || '') + ' ' + (b.getAttribute && b.getAttribute('aria-label') || ''));
    });
    if (coverBtn.length && /cover|begin/i.test(body.slice(0,200))) {
      coverBtn[0].click(); info.status = 'CLICKED_COVER'; return JSON.stringify(info);
    }
    // summary/submit/finish
    var fin = [].slice.call(d.querySelectorAll('button, .h5p-joubelui-button')).filter(function(b){
      return /mark as finished|submit report|submit$|finish/i.test((b.innerText || b.getAttribute('aria-label') || '').trim());
    });
    if (fin.length) { fin[0].click(); info.status = 'CLICKED_FINISH'; info.text = fin[0].innerText.trim(); return JSON.stringify(info); }
    var pm = body.match(/Page (\d+) of (\d+)/);
    if (!pm) {
      var chm = body.match(/(\d+) \/ (\d+)/);
      if (chm) pm = [null, chm[1], chm[2]];
    }
    if (pm) {
      info.page = pm[1]; info.total = pm[2];
      if (parseInt(pm[1],10) < parseInt(pm[2],10)) {
        var nexts = [].slice.call(d.querySelectorAll('.h5p-interactive-book-status-arrow.next')).filter(function(a){ return a.offsetParent !== null; });
        if (nexts.length) { nexts[0].click(); info.status = 'NEXT'; return JSON.stringify(info); }
      }
      info.status = 'AT_LAST_PAGE';
      info.tail = body.slice(-200);
      return JSON.stringify(info);
    }
    var nexts2 = [].slice.call(d.querySelectorAll('.h5p-interactive-book-status-arrow.next')).filter(function(a){ return a.offsetParent !== null; });
    if (nexts2.length) { nexts2[0].click(); info.status = 'NEXT_NOPAGE'; return JSON.stringify(info); }
    info.status = 'UNKNOWN';
    info.bodyStart = body.slice(0, 250);
    return JSON.stringify(info);
  } catch(e) { return JSON.stringify({status:'ERROR', error:e.message}); }
})()
