(function(){
  try {
    var a = document.querySelector('.fp-btn-add a');
    if (!a) return 'no add button';
    a.click();
    return 'opened picker';
  } catch(e) { return 'EXC ' + e.message; }
})()
