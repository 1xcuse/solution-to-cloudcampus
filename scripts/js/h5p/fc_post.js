(function(){
  try {
    var f = document.querySelector('iframe.h5p-iframe');
    var w = f.contentWindow, ins = w.H5P.instances[0];
    var base = JSON.parse(JSON.stringify(ins.getXAPIData().statement));
    var cid = base.object.definition.extensions['http://h5p.org/x-api/h5p-local-content-id'];
    base.result = {score:{min:0, raw:ins.getScore(), max:ins.getMaxScore(), scaled:ins.getScore()/ins.getMaxScore()}, completion:true, success:ins.getScore()===ins.getMaxScore(), duration:'PT60S'};
    window.__postResult = 'PENDING';
    w.H5P.jQuery.post(window.H5PIntegration.ajax.xAPIResult, {contentId: cid, xAPIResult: JSON.stringify({statement: base})}).done(function(r){ window.__postResult = 'OK ' + JSON.stringify(r); }).fail(function(x){ window.__postResult = 'FAIL ' + (x?x.status:''); });
    return 'posting cid=' + cid + ' score=' + ins.getScore() + '/' + ins.getMaxScore();
  } catch(e) { return 'EXCEPTION: ' + e.message; }
})()
