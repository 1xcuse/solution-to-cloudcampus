(function(){
  try {
    var f = document.querySelector('iframe.h5p-iframe');
    var w = f.contentWindow, ins = w.H5P.instances[0];
    if (ins.resetTask) { ins.resetTask(); return 'RESET_OK'; }
    return 'NO_RESET';
  } catch(e) { return 'RESET_ERR ' + e.message; }
})()
