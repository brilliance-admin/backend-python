tinymce.PluginManager.add('customLink', function (editor, url) {
  editor.contentCSS.push(url + '/css/link.css');
  editor.addButton('customLink', {
    text: 'Custom Link',
    icon: false,
    onclick: function () {
      editor.windowManager.open({
        title: 'Insert Custom Link',
        body: [
          { type: 'textbox', name: 'url', label: 'URL', value: '' },
          { type: 'textbox', name: 'text', label: 'Text', oninput: updatePreview },
          {
            type: 'textbox',
            name: 'borderRadius',
            label: 'Border Radius',
            value: 12,
            oninput: updatePreview,
          },
          {
            type: 'textbox',
            name: 'backgroundColorHex',
            label: 'Background Color (Hex)',
            value: '#0edebe',
            oninput: (e) => {
              updateColorPicker(e);
              updatePreview(e);
            }
          },
          {
            type: 'colorpicker',
            name: 'backgroundColor',
            label: '',
            value: '#0edebe',
            onchange: (e) => {updateHexInput(e), updatePreview(e)},
          },
          {
            type: 'container',
            html: '<div id="link-preview" style="margin-top: 10px;margin-bottom:10px;display:grid; height:50px;"></div>',
          },
        ],
        buttons: [
          {
            text: 'Close',
            onclick: 'close',
          },
          {
            text: 'Insert',
            subtype: 'primary',
            onclick: function (e) {
              const data = e.control.rootControl.toJSON();
              const invalidFields = getInvalidFields(data);
              if (invalidFields.length > 0) {
                alert('Please fill in all fields correctly: ' + invalidFields.join(', '));
                return;
              }
              const textColor = getContrastYIQ(data.backgroundColorHex);
              editor.insertContent(
                `<a style="color: ${textColor}; font-family: 'SF Pro', Helvetica, Arial, sans-serif; font-size: 16px; line-height: 24px; font-weight: 600; text-decoration: none; border-radius: ${data.borderRadius}px; background-color: ${data.backgroundColor}; display: inline-block; padding: 12px 24px 12px 24px;" href="${data.url}" target="_blank" rel="noopener">${data.text}</a>`,
              );
              editor.windowManager.close();
            },
          },
        ]
      });

      const validationRules = {
        url: value => value && /^https?:\/\/(?:www\.)?[-a-zA-Z0-9@:%._+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b(?:[-a-zA-Z0-9()@:%_+.~#?&/=]*)$/.test(value),
        text: value => value && value.trim().length > 0,
        borderRadius: value => value && !isNaN(value) && Number(value) >= 0,
        backgroundColorHex: value => value && /^#[0-9A-F]{6}$/i.test(value),
      };

      function getInvalidFields(data) {
        const invalidFields = Object.keys(validationRules).filter(field => !validateField(field, data[field]));
        highlightInvalidFields(invalidFields);
        return invalidFields;
      }

      function validateField(name, value) {
        return validationRules[name](value);
      }

      function highlightInvalidFields(invalidFields) {
        const win = editor.windowManager.getWindows()[0];
        Object.keys(validationRules).forEach(field => {
          const control = win.find(`[name=${field}]`)[0];
          if (invalidFields.includes(field)) {
            control.$el[0].style.border = '1px solid red';
          } else {
            control.$el[0].style.border = '';
          }
        });
      }

      function checkDataValidityForPreview(data) {
        if (data.backgroundColorHex.length !== 7 || !data.borderRadius || data.borderRadius.length < 1) {
          return false;
        } else {
          return true;
        }
      }

      function updatePreview() {
        const win = editor.windowManager.getWindows()[0];
        const data = win.toJSON();
        if (!checkDataValidityForPreview(data)) {
          return;
        }
        const textColor = getContrastYIQ(data.backgroundColorHex);
        const previewHtml = `<a style="color: ${textColor}; font-family: 'SF Pro', Helvetica, Arial, sans-serif; font-size: 16px; line-height: 24px; font-weight: 600; text-decoration: none; border-radius: ${data.borderRadius}px; background-color: ${data.backgroundColor}; display: inline-block; padding: 12px 24px 12px 24px;text-align: center" href="${data.url}" target="_blank" rel="noopener">${data.text || 'Example'}</a>`;
        document.getElementById('link-preview').innerHTML = previewHtml;
      }

      function getContrastYIQ(hexcolor) {
        hexcolor = hexcolor.slice(1);

        const r = parseInt(hexcolor.substr(0, 2), 16);
        const g = parseInt(hexcolor.substr(2, 2), 16);
        const b = parseInt(hexcolor.substr(4, 2), 16);

        // Calculate the luminance using the YIQ formula
        const yiq = ((r * 299) + (g * 587) + (b * 114)) / 1000;

        return (yiq >= 128) ? 'black' : 'white';
      }

      function updateHexInput(e) {
        const color = e.control.value();
        const win = editor.windowManager.getWindows()[0];
        win.find('#backgroundColorHex')[0].value(color);
      }

      function updateColorPicker(e) {
        const hex = e.control.value();
        const win = editor.windowManager.getWindows()[0];

        if (hex.length === 7) {
          win.find('#backgroundColor')[0].value(hex);
          win.find('#backgroundColor')[0].postRender();
        }
      }

      updatePreview();
    }
    });
})

