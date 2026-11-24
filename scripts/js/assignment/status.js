(function(){
  try {
    var m = document.querySelector('#region-main') || document.body;
    var txt = (m.innerText||'').replace(/\s+/g, ' ');
    var i = txt.indexOf('Submission status');
    return JSON.stringify({url: location.href, status: txt.slice(i, i+600)});
  } catch(e) { return 'EXC ' + e.message; }
})()
