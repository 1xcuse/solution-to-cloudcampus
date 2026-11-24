(function(){
  /* Build window.__PLAN for a QuestionSet from the page's own H5PIntegration JSON. */
  try {
    var I = window.H5PIntegration;
    if (!I || !I.contents) return JSON.stringify({error: 'no H5PIntegration'});
    var key = Object.keys(I.contents)[0];
    var c = I.contents[key];
    var jc = JSON.parse(c.jsonContent);
    function norm(s){ return String(s).replace(/<[^>]+>/g, ' ').replace(/&nbsp;/g,' ').replace(/\s+/g,' ').trim(); }
    var plan = [];
    (jc.questions || []).forEach(function(q){
      var lib = (q.library || '').split(' ')[0].replace('H5P.','');
      var qp = q.params || {};
      if (lib === 'MultiChoice') {
        var opts = (qp.answers || []).map(function(a){ return norm(a.text || ''); });
        var corr = (qp.answers || []).filter(function(a){ return a.correct; }).map(function(a){ return norm(a.text || ''); });
        plan.push({type:'MultiChoice', q: norm(qp.question || ''), opts: opts, correct: corr});
      } else if (lib === 'TrueFalse') {
        plan.push({type:'TrueFalse', q: norm(qp.question || ''), correct: qp.correct});
      } else if (lib === 'DragText') {
        plan.push({type:'DragText', answers: (qp.textField || '').match(/\*([^*]+)\*/g) ? (qp.textField || '').match(/\*[^*]+\*/g).map(function(x){ return x.slice(1,-1); }) : []});
      } else if (lib === 'Blanks') {
        var txt = (qp.questions || []).join('');
        var answers = [];
        var re = /\*([^*]+)\*/g, m;
        while ((m = re.exec(txt)) !== null) answers.push([m[1].split('/')[0]]);
        plan.push({type:'Blanks', answers: answers});
      } else if (lib === 'Essay') {
        var sample = norm((qp.solution || {}).sample || '');
        plan.push({type:'Essay', q: norm(qp.taskDescription || ''), sample: sample});
      } else {
        plan.push({type: lib});
      }
    });
    window.__PLAN = {questions: plan};
    return JSON.stringify({ok: true, count: plan.length, types: plan.map(function(p){ return p.type; })});
  } catch(e) { return JSON.stringify({error: e.message}); }
})()
