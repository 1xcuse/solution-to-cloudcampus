(function(){
  try {
    var dlg = document.querySelector('.moodle-dialogue.filepicker');
    if (!dlg) return 'no dialog';
    var c = dlg.querySelector('.closebutton, .moodle-dialogue-hd button');
    if (c) { c.click(); return 'closed'; }
    return 'no close btn';
  } catch(e) { return 'EXC ' + e.message; }
})()
