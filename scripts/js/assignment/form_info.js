(function(){
  try {
    var out = {};
    out.url = location.href;
    out.title = document.title;
    var ed = document.querySelector('#id_onlinetext_editoreditable');
    var ta = document.querySelector('#id_onlinetext_editor');
    out.online_editor = !!ed;
    out.online_textarea = !!ta;
    out.online_word_count = (document.querySelector('.word-count, [data-region=wordcount]') || {}).innerText || '';
    var fm = document.querySelector('.filemanager');
    out.filemanager = !!fm;
    out.filemanager_text = fm ? (fm.innerText || '').replace(/\s+/g,' ').slice(0, 200) : '';
    var fis = [].slice.call(document.querySelectorAll('input[type=file]'));
    out.file_inputs = fis.map(function(f){ return f.name; });
    out.save_buttons = [].slice.call(document.querySelectorAll('button, input[type=submit]'))
      .map(function(b){ return (b.innerText || b.value || '').trim(); })
      .filter(function(t){ return /save changes|submit assignment|save and show/i.test(t); });
    return JSON.stringify(out);
  } catch(e) { return JSON.stringify({error: e.message}); }
})()
