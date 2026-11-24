(function(){
  try {
    var f = document.querySelector('iframe.h5p-iframe');
    var w = f.contentWindow, d = f.contentDocument, ins = w.H5P.instances[0];
    function norm(s){ return String(s).replace(/\u00a0/g,' ').replace(/\s+/g,' ').trim(); }
    function loose(s){ return norm(s).toLowerCase().replace(/[^a-z0-9]/g,''); }
    function decode(s){ var ta = d.createElement('textarea'); ta.innerHTML = String(s).replace(/<[^>]+>/g,''); return ta.value.trim(); }
    function visible(el){ return !!el && el.offsetParent !== null; }
    var PLAN = window.__PLAN;
    if (!PLAN) return JSON.stringify({status:'NO_PLAN'});
    var all = [].slice.call(d.querySelectorAll('.question-container'));
    var vis = all.filter(function(c){ return c.style.display !== 'none'; });
    if (!vis.length) {
      var bodyTxt = d.body.innerText.replace(/\s+/g,' ');
      if (bodyTxt.indexOf('Your result') >= 0 || bodyTxt.indexOf('Show solution') >= 0) return JSON.stringify({status:'FINISHED', score: ins.getScore(), max: ins.getMaxScore()});
      return JSON.stringify({status:'NO_VISIBLE'});
    }
    var visEl = vis[0], idx = all.indexOf(visEl);
    var qs = ins.getQuestions ? ins.getQuestions() : [];
    var q = qs[idx] || null;
    var lib = q && q.libraryInfo ? q.libraryInfo.machineName.replace('H5P.','') : null;
    if (!lib) {
      if (visEl.classList.contains('h5p-multichoice')) lib = 'MultiChoice';
      else if (visEl.classList.contains('h5p-true-false')) lib = 'TrueFalse';
      else if (visEl.classList.contains('h5p-drag-text')) lib = 'DragText';
      else if (visEl.classList.contains('h5p-blanks')) lib = 'Blanks';
      else if (visEl.classList.contains('h5p-essay')) lib = 'Essay';
    }
    var qIntro = visEl.querySelector('.h5p-question-introduction');
    var qtext = norm(qIntro ? qIntro.innerText : '');
    var answered = false;
    try { if (q && q.getAnswerGiven) answered = !!q.getAnswerGiven(); } catch(e) {}
    var finishBtn = visEl.querySelector('.h5p-question-finish');
    var nextBtn = visEl.querySelector('.h5p-question-next');
    if (answered) {
      if (visible(finishBtn)) { finishBtn.click(); return JSON.stringify({status:'CLICKED_FINISH', score: ins.getScore(), max: ins.getMaxScore()}); }
      if (visible(nextBtn)) { nextBtn.click(); return JSON.stringify({status:'ADVANCE', score: ins.getScore(), max: ins.getMaxScore()}); }
      try { if (q && q.showButton) { q.showButton('finish'); q.showButton('next'); } } catch(e) {}
      return JSON.stringify({status:'SHOW_BUTTONS', lib:lib, idx:idx});
    }
    // MC / TF
    if (lib === 'MultiChoice' || lib === 'TrueFalse') {
      var opts = [].slice.call(visEl.querySelectorAll('li.h5p-answer, .h5p-true-false-answer'));
      var optTexts = opts.map(function(o){ return norm(o.innerText); });
      var entry = null;
      PLAN.questions.forEach(function(p){
        if (entry) return;
        if (p.type !== 'MultiChoice' && p.type !== 'TrueFalse') return;
        var pq = norm(p.q || '').slice(0,50);
        if (pq && qtext.indexOf(pq) === 0) entry = p;
      });
      if (lib === 'MultiChoice') {
        var key = function(arr){ return arr.map(loose).sort().join('||'); };
        if (!entry || key(entry.opts || []) !== key(optTexts)) {
          entry = null;
          PLAN.questions.forEach(function(p){
            if (entry) return;
            if (p.type !== 'MultiChoice') return;
            if (key(p.opts || []) === key(optTexts)) entry = p;
          });
        }
      }
      if (!entry) return JSON.stringify({status:'NO_ENTRY', lib:lib, qtext:qtext.slice(0,80), opts:optTexts.map(function(x){return x.slice(0,30);})});
      var want = entry.type === 'TrueFalse' ? (String(entry.correct) === 'true' ? 'True' : 'False') : entry.correct[0];
      var target = null;
      opts.forEach(function(o, i){ if (!target && loose(optTexts[i]) === loose(want)) target = o; });
      if (!target) opts.forEach(function(o, i){ if (!target && loose(want) && loose(optTexts[i]).indexOf(loose(want)) >= 0) target = o; });
      if (!target) return JSON.stringify({status:'OPT_NOT_FOUND', want:want, have:optTexts});
      target.click();
      var chk = visEl.querySelector('.h5p-question-check-answer');
      if (chk && visible(chk)) chk.click();
      return JSON.stringify({status:'ANSWERED', type:lib, want:want, score: ins.getScore()});
    }
    if (lib === 'DragText' && q) {
      var used = {}, placed = 0;
      (q.droppables||[]).forEach(function(z){
        var txt = String(z.text || '').trim();
        for (var j = 0; j < q.draggables.length; j++) {
          var dr = q.draggables[j];
          var t = String(dr.text || (dr.getAnswerText ? dr.getAnswerText() : '') || '').trim();
          if (!used[dr.getIndex()] && t === txt) { q.drop(dr, z); used[dr.getIndex()] = true; placed++; break; }
        }
      });
      var cb = visEl.querySelector('.h5p-question-check-answer, .h5p-question-submit-answer');
      if (cb) cb.click();
      return JSON.stringify({status:'ANSWERED', type:'DragText', placed:placed, total:(q.droppables||[]).length});
    }
    if (lib === 'Blanks' && q) {
      var answers = [];
      var texts = (q.params && q.params.questions) || [];
      texts.forEach(function(t){
        var re = /\*([^*]+)\*/g, m;
        while ((m = re.exec(t)) !== null) answers.push(decode(m[1].split('/')[0]));
      });
      if (!answers.length) {
        var bp = PLAN.questions.filter(function(p){ return p.type === 'Blanks'; })[0];
        if (bp) answers = bp.answers.map(function(a){ return a[0]; });
      }
      var inputs = [].slice.call(visEl.querySelectorAll('input'));
      for (var i = 0; i < inputs.length && i < answers.length; i++) {
        inputs[i].focus(); inputs[i].value = answers[i];
        ['input','keyup','change','blur'].forEach(function(ev){ inputs[i].dispatchEvent(new w.Event(ev,{bubbles:true})); });
      }
      var cb2 = visEl.querySelector('.h5p-question-check-answer, .h5p-question-submit-answer');
      if (cb2) cb2.click();
      return JSON.stringify({status:'ANSWERED', type:'Blanks', filled:inputs.length, answers:answers.length});
    }
    if (lib === 'Essay' && q) {
      var et = PLAN.questions.filter(function(p){ return p.type === 'Essay'; })[0] || {};
      var sample = et.sample || '';
      var ta = visEl.querySelector('textarea');
      if (!ta) return JSON.stringify({status:'NO_TEXTAREA'});
      ta.focus(); ta.value = sample;
      ['input','keyup','change','blur'].forEach(function(ev){ ta.dispatchEvent(new w.Event(ev,{bubbles:true})); });
      var cb3 = visEl.querySelector('.h5p-question-check-answer, .h5p-question-submit-answer');
      if (cb3) cb3.click();
      return JSON.stringify({status:'ANSWERED', type:'Essay', len:sample.length});
    }
    return JSON.stringify({status:'UNHANDLED', lib:lib, qtext:qtext.slice(0,100), idx:idx});
  } catch(e) { return JSON.stringify({status:'ERROR', error:e.message + ' @ ' + (e.stack||'').split('\n')[1]}); }
})()
