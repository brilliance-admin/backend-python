'use strict';

const ADD_ACCORDION =
      `<div class="accordion-content">
<div class="accordion-item">{caption}</div>
<div class="accordion-content">{content}</div>
</div>`

tinymce.PluginManager.add('accordion', function(editor, url) {
  var $ = editor.$;
  editor.contentCSS.push(url + '/css/accordion.css');
  var caption = editor.getParam('caption', 'Accordion title');

  function addAccordion()
  {
    var selection = editor.selection;
    var node = selection.getNode();
    if (node) {
      editor.undoManager.transact(function() {
      var content = selection.getContent();
      if (!content) {
        content = 'Accordion content';
      }
        selection.setContent(ADD_ACCORDION.replace('{content}', content).replace('{caption}', caption));
      });
      editor.nodeChanged();
    }
  }

  if (tinymce.majorVersion == 4) {
    editor.addButton(
      'add-accordion',
      {
        tooltip: 'Add accordion',
        text: 'Accordion',
        onclick: addAccordion,
      });
    editor.addMenuItem(
      'add-accordion',
      {
        text: 'Add accordion',
        context: 'format',
        onclick: addAccordion
      });
  } else {
    console.exception('accordion plugin is not supported onlt for 4 version')
  }
});
