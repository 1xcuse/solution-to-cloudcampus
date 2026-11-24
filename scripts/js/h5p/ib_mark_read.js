(function(){
  try {
    var f = document.querySelector('iframe.h5p-iframe');
    var ins = f.contentWindow.H5P.instances[0];
    ins.setChapterRead(ins.activeChapter || 0, true);
    return JSON.stringify({completed: ins.completed, chapters: (ins.chapters||[]).map(function(c){return c.completed;})});
  } catch(e) { return JSON.stringify({error:e.message}); }
})()
