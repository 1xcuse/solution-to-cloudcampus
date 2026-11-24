(function(){
  try {
    var els = [].slice.call(document.querySelectorAll('button, input[type=submit], a'));
    var order = [/^\s*add submission\s*$/i, /^\s*edit submission\s*$/i];
    for (var k = 0; k < order.length; k++) {
      for (var i = 0; i < els.length; i++) {
        var t = (els[i].innerText || els[i].value || '').trim();
        if (order[k].test(t)) { els[i].click(); return 'clicked: ' + t; }
      }
    }
    return 'no add/edit button on page: ' + location.href;
  } catch(e) { return 'EXC ' + e.message; }
})()
