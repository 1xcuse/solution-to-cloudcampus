(function(){
  try {
    var outer = document.querySelector('iframe.h5p-player');
    var n = outer.contentDocument.querySelector('iframe');
    var w = n.contentWindow, d = n.contentDocument, ins = w.H5P.instances[0];
    return JSON.stringify({completed: ins.completed, activeChapter: ins.activeChapter, body: d.body.innerText.replace(/\s+/g,' ').slice(-500)});
  } catch(e) { return JSON.stringify({error:e.message}); }
})()
