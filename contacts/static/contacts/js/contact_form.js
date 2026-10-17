'use strict';

const contactForm = document.querySelector('[data-contact-form]');
const phoneInput = contactForm?.querySelector('[name="phone_number"]');

// Django still validates submissions when JavaScript or the library is unavailable.
if (phoneInput && window.libphonenumber) {
    const phoneError = 'Podaj prawidłowy numer telefonu lub polski numer alarmowy, np. 112.';
    const polishEmergencyNumbers = new Set(
        (phoneInput.dataset.polishEmergencyNumbers || '').split(' ')
    );

    function validatePhoneNumber() {
        phoneInput.setCustomValidity('');
        let value = phoneInput.value.replace(/[\s()-]/g, '');
        if (!value) {
            phoneInput.value = '';
            return;
        }
        if (!/^(?:\+|00)?[0-9]+$/.test(value)) {
            phoneInput.setCustomValidity(phoneError);
            return;
        }

        // Only Polish emergency short codes supplied by Django bypass international validation.
        if (polishEmergencyNumbers.has(value)) {
            phoneInput.value = value;
            return;
        }

        if (value.startsWith('00')) {
            value = '+' + value.slice(2);
        }

        const number = window.libphonenumber.parsePhoneNumberFromString(value, {
            defaultCountry: 'PL',
            extract: false,
        });
        if (!number || !number.isValid()) {
            phoneInput.setCustomValidity(phoneError);
            return;
        }
        phoneInput.value = number.number;
    }

    phoneInput.addEventListener('input', () => phoneInput.setCustomValidity(''));
    phoneInput.addEventListener('blur', validatePhoneNumber);
    contactForm.addEventListener('submit', (event) => {
        validatePhoneNumber();
        if (!contactForm.reportValidity()) {
            event.preventDefault();
        }
    });
}
