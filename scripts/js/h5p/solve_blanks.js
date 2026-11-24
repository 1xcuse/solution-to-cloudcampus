(function(){
  try {
    var f = document.querySelector('iframe.h5p-iframe');
    var w = f.contentWindow, d = f.contentDocument, ins = w.H5P.instances[0];
    function decode(s){
      s = String(s).replace(/<[^>]+>/g, '');
      var ta = d.createElement('textarea'); ta.innerHTML = s; return ta.value.trim();
    }
    var answers = [];
    var texts = (ins.params && ins.params.questions) || [];
    texts.forEach(function(t){
      var re = /\*([^*]+)\*/g, m;
      while ((m = re.exec(t)) !== null) {
        var alts = m[1].split('/');
        answers.push(decode(alts[0]));
      }
    });
    var inputs = [].slice.call(d.querySelectorAll('input.h5p-text-input, input.h5p-textinput, .h5p-text-input'));
    if (!inputs.length) inputs = [].slice.call(d.querySelectorAll('input[type=text]'));
    var filled = 0;
    for (var i = 0; i < inputs.length && i < answers.length; i++) {
      var inp = inputs[i];
      inp.focus();
      inp.value = answers[i];
      ['input','keyup','change','blur'].forEach(function(ev){ inp.dispatchEvent(new w.Event(ev, {bubbles:true})); });
      filled++;
    }
    var btn = d.querySelector('.h5p-question-check-answer, .h5p-question-submit-answer');
    var clicked = false;
    if (btn) { btn.click(); clicked = true; }
    return JSON.stringify({type:'Blanks', inputs:inputs.length, answers:answers.length, filled:filled, clicked:clicked, score:ins.getScore(), max:ins.getMaxScore(), answered:ins.getAnswerGiven ? ins.getAnswerGiven() : null});
  } catch(e) { return JSON.stringify({type:'Blanks', error:e.message}); }
})()
