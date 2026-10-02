(function () {
    'use strict';

    function initHonnaRegistration() {
        var dropdown = document.getElementById('honna_role_dropdown');
        var roleBtn = document.getElementById('honna_role_btn');
        var roleMenu = document.getElementById('honna_role_menu');
        var hiddenInput = document.getElementById('hidden_portal_type');
        var labelText = document.getElementById('honna_selected_role_label');

        if (!dropdown || !roleBtn || !roleMenu || !hiddenInput) {
            return; // Not on the registration page
        }

        // Toggle dropdown open/close
        function toggleDropdown(show) {
            var isOpen = typeof show === 'boolean' ? show : roleMenu.classList.contains('d-none');
            if (isOpen) {
                roleMenu.classList.remove('d-none');
                dropdown.classList.add('is-open');
                roleBtn.setAttribute('aria-expanded', 'true');
            } else {
                roleMenu.classList.add('d-none');
                dropdown.classList.remove('is-open');
                roleBtn.setAttribute('aria-expanded', 'false');
            }
        }

        roleBtn.addEventListener('click', function (e) {
            e.stopPropagation();
            toggleDropdown();
        });

        // Handle role option selection
        var options = roleMenu.querySelectorAll('.honna-role-option');
        options.forEach(function (opt) {
            opt.addEventListener('click', function (e) {
                e.stopPropagation();
                var val = this.getAttribute('data-value');
                var text = this.querySelector('span') ? this.querySelector('span').textContent.trim() : this.textContent.trim();

                hiddenInput.value = val;
                if (labelText) {
                    labelText.textContent = text;
                }

                // Update active class
                options.forEach(function (o) { o.classList.remove('active'); });
                this.classList.add('active');

                toggleDropdown(false);
            });
        });

        // Close on click outside
        document.addEventListener('click', function (e) {
            if (!dropdown.contains(e.target)) {
                toggleDropdown(false);
            }
        });

        // Close on Escape key
        document.addEventListener('keydown', function (e) {
            if (e.key === 'Escape' || e.keyCode === 27) {
                toggleDropdown(false);
            }
        });

        // Sync with existing value on load
        if (hiddenInput.value) {
            var currentVal = hiddenInput.value;
            options.forEach(function (opt) {
                if (opt.getAttribute('data-value') === currentVal) {
                    options.forEach(function (o) { o.classList.remove('active'); });
                    opt.classList.add('active');
                    if (labelText) {
                        labelText.textContent = opt.querySelector('span') ? opt.querySelector('span').textContent.trim() : opt.textContent.trim();
                    }
                }
            });
        }
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initHonnaRegistration);
    } else {
        initHonnaRegistration();
    }
})();
