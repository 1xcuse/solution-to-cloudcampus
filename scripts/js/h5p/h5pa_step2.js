(function(){
  try {
    var outer = document.querySelector('iframe.h5p-player');
    if (!outer) return JSON.stringify({status:'NO_PLAYER_IFRAME'});
    var n = outer.contentDocument.querySelector('iframe');
    if (!n) return JSON.stringify({status:'NO_NESTED_IFRAME'});
    var w = n.contentWindow, d = n.contentDocument;
    var ins = (w.H5P && w.H5P.instances && w.H5P.instances[0]) || null;
    if (!ins) return JSON.stringify({status:'NO_INSTANCE'});
    var body = d.body.innerText.replace(/\s+/g,' ');
    var out = {activeChapter: ins.activeChapter, completed: ins.completed};
    var pm = body.match(/(\d+) \/ (\d+) Page/);
    if (pm) { out.page = pm[1]; out.total = pm[2]; }
    // 1. read/cover
    var readBtn = [].slice.call(d.querySelectorAll('button')).filter(function(b){ return /^\s*read\s*$/i.test(b.innerText || ''); })[0];
    if (readBtn) { readBtn.click(); out.status = 'CLICKED_READ'; return JSON.stringify(out); }
    // 2. answer any SCS whose current slide is a question
    var scsList = [].slice.call(d.querySelectorAll('.h5p-single-choice-set'));
    for (var i = 0; i < scsList.length; i++) {
      var cur = scsList[i].querySelector('.h5p-sc-current-slide');
      if (cur && !cur.classList.contains('h5p-sc-set-results')) {
        var correct = cur.querySelector('.h5p-sc-alternative.h5p-sc-is-correct');
        if (correct) { correct.click(); out.status = 'ANSWERED_SCS'; out.scs = i; return JSON.stringify(out); }
      }
    }
    // 3. submit report
    var submit = [].slice.call(d.querySelectorAll('button, .h5p-joubelui-button')).filter(function(b){
      return /submit report/i.test((b.innerText || '') + ' ' + (b.getAttribute && b.getAttribute('aria-label') || ''));
    });
    if (submit.length) { submit[0].click(); out.status = 'CLICKED_SUBMIT'; return JSON.stringify(out); }
    // 4. next page
    var nexts = [].slice.call(d.querySelectorAll('.h5p-interactive-book-status-arrow.next')).filter(function(a){ return a.offsetParent !== null; });
    if (nexts.length && !(pm && pm[1] === pm[2])) { nexts[0].click(); out.status = 'NEXT'; return JSON.stringify(out); }
    out.status = 'END_OR_UNKNOWN';
    out.tail = body.slice(-300);
    return JSON.stringify(out);
  } catch(e) { return JSON.stringify({status:'ERROR', error:e.message}); }
})()
