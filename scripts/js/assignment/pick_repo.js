(function(){
  try {
    var reps = [].slice.call(document.querySelectorAll('.fp-repo'));
    var u = reps.filter(function(r){ return /upload/i.test(r.innerText); })[0];
    if (!u) return 'no upload repo';
    (u.querySelector('a') || u).click();
    return 'picked upload repo';
  } catch(e) { return 'EXC ' + e.message; }
})()
