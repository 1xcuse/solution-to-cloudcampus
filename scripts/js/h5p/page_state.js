(function(){
  try {
    var m = document.querySelector('#region-main') || document.body;
    return JSON.stringify({url: location.href, ready: document.readyState, title: document.title.slice(0,80), text: (m.innerText||'').replace(/\s+/g,' ').slice(0,120)});
  } catch(e) { return JSON.stringify({url: location.href, err:e.message}); }
})()
