(function(){
  try {
    var fi = document.querySelector('input[name=repo_upload_file]');
    var form = fi && fi.form;
    var inp = form ? form.querySelector('input[name=itemid]') : null;
    var inp2 = document.querySelector('input[name=files_filemanager]');
    return JSON.stringify({repoForm: !!form, itemid: inp ? inp.value : null, hiddenDraft: inp2 ? inp2.value : null});
  } catch(e) { return 'EXC ' + e.message; }
})()
