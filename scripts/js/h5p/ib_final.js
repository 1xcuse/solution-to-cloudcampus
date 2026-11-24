(function(){
  try {
    var f = document.querySelector('iframe.h5p-iframe');
    var w = f.contentWindow, ins = w.H5P.instances[0];
    var body = f.contentDocument.body.innerText.replace(/\s+/g,' ');
    return JSON.stringify({completed: ins.completed, activeChapter: ins.activeChapter, score: (ins.getScore?ins.getScore():'?'), max: (ins.getMaxScore?ins.getMaxScore():'?'), text: body.slice(-300)});
  } catch(e) { return JSON.stringify({error:e.message}); }
})()
