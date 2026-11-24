(function(){
  try {
    var f = document.querySelector('iframe.h5p-iframe');
    var w = f.contentWindow, d = f.contentDocument, ins = w.H5P.instances[0];
    var cards = ins.options.cards;
    var inputs = [].slice.call(d.querySelectorAll('.h5p-textinput'));
    var checks = [].slice.call(d.querySelectorAll('.h5p-check-button'));
    for (var i=0;i<cards.length;i++){
      var inp = inputs[i]; if (!inp) continue;
      inp.focus(); inp.value = cards[i].answer;
      ['input','change','blur'].forEach(function(ev){ inp.dispatchEvent(new w.Event(ev, {bubbles:true})); });
    }
    for (var k=0;k<checks.length;k++) checks[k].click();
    var next = d.querySelector('.h5p-next');
    for (var n=0;n<cards.length+1 && next;n++) next.click();
    var sr = d.querySelector('.h5p-show-results-label');
    if (sr) sr.click();
    return JSON.stringify({type:'Flashcards', score:ins.getScore(), max:ins.getMaxScore(), numAnswered:ins.numAnswered, result:(d.querySelector('.h5p-results-score')||{}).innerText || ''});
  } catch(e) { return JSON.stringify({type:'Flashcards', error:e.message}); }
})()
