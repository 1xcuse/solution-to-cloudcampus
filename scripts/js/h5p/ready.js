(function(){
  try {
    var f = document.querySelector('iframe.h5p-iframe');
    if (!f) return JSON.stringify({ready:false, why:'no iframe'});
    var w = f.contentWindow;
    var ins = (w.H5P && w.H5P.instances && w.H5P.instances[0]) || null;
    if (!ins || !ins.libraryInfo) return JSON.stringify({ready:false, why:'no instance'});
    return JSON.stringify({ready:true, lib: ins.libraryInfo.machineName, ver: ins.libraryInfo.majorVersion+'.'+ins.libraryInfo.minorVersion});
  } catch(e) { return JSON.stringify({ready:false, why:e.message}); }
})()
