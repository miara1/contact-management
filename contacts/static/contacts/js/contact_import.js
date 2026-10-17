'use strict';

const importForm = document.getElementById('contact-import-form');
const importInput = importForm?.querySelector('[name="csv_file"]');
const importButton = document.getElementById('contact-import-button');

if (importInput && importButton) {
    // Keep a standard upload form usable when JavaScript is disabled.
    importInput.hidden = true;
    importButton.type = 'button';

    importButton.addEventListener('click', () => {
        importInput.value = '';
        importInput.click();
    });

    importInput.addEventListener('change', () => {
        if (importInput.files.length) {
            importButton.disabled = true;
            importButton.textContent = 'Importowanie…';
            importForm.requestSubmit();
        }
    });

    window.addEventListener('pageshow', () => {
        importButton.disabled = false;
        importButton.textContent = 'Importuj CSV';
    });
}
