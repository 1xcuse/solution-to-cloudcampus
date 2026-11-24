(function(){
  try {
    var f = document.querySelector('iframe.h5p-iframe');
    var w = f.contentWindow, d = f.contentDocument, ins = w.H5P.instances[0];
    return JSON.stringify({type:'QuestionSet', score: ins.getScore(), max: ins.getMaxScore(), result:(d.body.innerText.replace(/\s+/g,' ').slice(0,200))});
  } catch(e) { return JSON.stringify({error:e.message}); }
})()
