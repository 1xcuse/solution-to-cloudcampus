(function(){
  try {
    var els = [].slice.call(document.querySelectorAll('input[type=submit], button'));
    for (var i=0;i<els.length;i++){ if (/^save changes$/i.test((els[i].value || els[i].innerText || '').trim())) { els[i].click(); return 'clicked save'; } }
    return 'no save button';
  } catch(e) { return 'EXC ' + e.message; }
})()
