(function(){
  try {
    var btns = [].slice.call(document.querySelectorAll('.filepicker button, .filepicker input[type=submit], .moodle-dialogue button'));
    for (var i=0;i<btns.length;i++){ if (/upload this file/i.test(btns[i].innerText || btns[i].value || '')) { btns[i].click(); return 'clicked upload'; } }
    return 'no upload button';
  } catch(e) { return 'EXC ' + e.message; }
})()
