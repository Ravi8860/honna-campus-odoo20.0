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

        // --- Success Toast Notification & AJAX Form Submit ---
        var form = document.getElementById('honna_registration_form');
        var toastEl = document.getElementById('honna_toast_notification');
        var toastTimer = null;

        function showToastNotification(message) {
            var el = document.getElementById('honna_toast_notification');
            if (!el) return;
            if (message) {
                var msgEl = document.getElementById('honna_toast_message');
                if (msgEl) {
                    msgEl.textContent = message;
                }
            }
            if (toastTimer) {
                clearTimeout(toastTimer);
            }
            el.classList.remove('d-none');
            // Trigger reflow to restart CSS transition
            void el.offsetWidth;
            el.classList.add('show');

            // Automatically remove after 2 seconds
            toastTimer = setTimeout(function () {
                el.classList.remove('show');
                setTimeout(function () {
                    el.classList.add('d-none');
                }, 300);
            }, 2000);
        }

        // Check if page loaded with ?submitted=1
        var urlParams = new URLSearchParams(window.location.search);
        if (urlParams.get('submitted') === '1') {
            showToastNotification('Registration submitted successfully!');
            if (window.history && window.history.replaceState) {
                window.history.replaceState({}, document.title, window.location.pathname);
            }
        }

        if (form) {
            form.addEventListener('submit', function (e) {
                if (!form.checkValidity()) {
                    return;
                }
                e.preventDefault();

                var submitBtn = document.getElementById('btn_submit_approval');
                var originalBtnHtml = '';
                if (submitBtn) {
                    originalBtnHtml = submitBtn.innerHTML;
                    submitBtn.disabled = true;
                    submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span> Submitting...';
                }

                // Clear previous error messages
                var errDivs = form.querySelectorAll('.honna-ajax-error');
                errDivs.forEach(function (el) { el.remove(); });
                var globalErr = form.parentNode.querySelector('.honna-ajax-global-error');
                if (globalErr) { globalErr.remove(); }

                var formData = new FormData(form);
                fetch(form.action || '/stakeholder-portals/submit', {
                    method: 'POST',
                    body: formData,
                    headers: {
                        'X-Requested-With': 'XMLHttpRequest',
                        'Accept': 'application/json'
                    }
                })
                .then(function (res) {
                    var contentType = res.headers.get('content-type') || '';
                    if (contentType.indexOf('application/json') !== -1) {
                        return res.json();
                    }
                    return { status: res.ok ? 'success' : 'error' };
                })
                .then(function (data) {
                    if (submitBtn) {
                        submitBtn.disabled = false;
                        submitBtn.innerHTML = originalBtnHtml;
                    }
                    if (data.status === 'success') {
                        showToastNotification(data.message || 'Registration submitted successfully!');
                        form.reset();
                        setTimeout(function () {
                            window.location.href = data.redirect_url || '/web/login?registered=1';
                        }, 1000);
                    } else if (data.errors) {
                        if (data.errors.email) {
                            var emailInput = document.getElementById('reg_email') || form.querySelector('input[name="email"]');
                            if (emailInput) {
                                var errSpan = document.createElement('div');
                                errSpan.className = 'text-danger small mt-1 honna-ajax-error';
                                errSpan.textContent = data.errors.email;
                                emailInput.closest('.honna-form-group, .mb-3, div').appendChild(errSpan);
                            }
                        }
                        if (data.errors.global) {
                            var gErr = document.createElement('div');
                            gErr.className = 'alert alert-danger d-flex align-items-center mb-3 rounded-3 shadow-sm py-2 px-3 honna-ajax-global-error';
                            gErr.innerHTML = '<i class="oi oi-warning me-2 fs-5"></i><div class="fw-semibold small">' + data.errors.global + '</div>';
                            form.parentNode.insertBefore(gErr, form);
                        }
                    } else {
                        showToastNotification('Registration submitted successfully!');
                        form.reset();
                        setTimeout(function () {
                            window.location.href = '/web/login?registered=1';
                        }, 1000);
                    }
                })
                .catch(function (err) {
                    console.error('Registration submit error:', err);
                    if (submitBtn) {
                        submitBtn.disabled = false;
                        submitBtn.innerHTML = originalBtnHtml;
                    }
                    form.submit();
                });
            });
        }
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initHonnaRegistration);
    } else {
        initHonnaRegistration();
    }
})();
