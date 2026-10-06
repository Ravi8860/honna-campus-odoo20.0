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

    // ==========================================
    // Association / Organisation Profile Scripts
    // ==========================================
    window.previewAvatar = function(input) {
        if (input.files && input.files[0]) {
            const reader = new FileReader();
            reader.onload = function(e) {
                const img = document.getElementById('avatar_preview');
                if (img) img.src = e.target.result;
            };
            reader.readAsDataURL(input.files[0]);
        }
    };

    window.submitProfileForm = function(action) {
        const form = document.getElementById('association_profile_form');
        const actionInput = document.getElementById('profile_form_action');
        if (form && actionInput) {
            actionInput.value = action || 'save';
            form.submit();
        }
    };

    window.toggleMemberAddSection = function() {
        const inlineRow = document.getElementById('inline_add_member_row');
        const detailsSection = document.getElementById('add_member_details_section');
        if (inlineRow) {
            if (inlineRow.classList.contains('d-none')) {
                inlineRow.classList.remove('d-none');
                const nameInput = document.getElementById('inline_name');
                if (nameInput) nameInput.focus();
            } else {
                inlineRow.classList.add('d-none');
            }
        }
        if (detailsSection) {
            detailsSection.scrollIntoView({ behavior: 'smooth' });
        }
    };

    window.saveInlineMember = function() {
        const name = (document.getElementById('inline_name')?.value || '').trim();
        const desig = (document.getElementById('inline_desig')?.value || '').trim();
        const email = (document.getElementById('inline_email')?.value || '').trim();
        const role = (document.getElementById('inline_role')?.value || '').trim();

        if (!name && !email) {
            alert('Please enter at least a name or email for the member.');
            return;
        }

        const fnameInput = document.getElementById('new_mem_fname');
        const lnameInput = document.getElementById('new_mem_lname');
        const roleInput = document.getElementById('new_mem_role');
        const emailInput = document.getElementById('new_mem_email');

        const parts = name.split(' ');
        if (fnameInput) fnameInput.value = parts[0] || '';
        if (lnameInput) lnameInput.value = parts.slice(1).join(' ') || '';
        if (roleInput) roleInput.value = role || desig || 'Member';
        if (emailInput) emailInput.value = email || '';

        window.submitProfileForm('save');
    };

    window.cancelInlineMember = function() {
        const inlineRow = document.getElementById('inline_add_member_row');
        if (inlineRow) inlineRow.classList.add('d-none');
    };

    window.deleteMemberRow = function(memberId) {
        if (confirm('Are you sure you want to remove this member?')) {
            const deleteInput = document.getElementById('delete_member_id_input');
            if (deleteInput) {
                deleteInput.value = memberId;
                window.submitProfileForm('save');
            }
        }
    };

    window.editMemberRow = function(memberId) {
        const row = document.getElementById('member_row_' + memberId);
        if (!row) return;
        const cells = row.querySelectorAll('td');
        if (cells.length < 5) return;

        const name = cells[0].textContent.trim();
        const desig = cells[1].textContent.trim();
        const email = cells[2].textContent.trim();
        const role = cells[3].textContent.trim();

        const inlineRow = document.getElementById('inline_add_member_row');
        if (inlineRow) {
            inlineRow.classList.remove('d-none');
            document.getElementById('inline_name').value = name;
            document.getElementById('inline_desig').value = desig;
            document.getElementById('inline_email').value = email;
            document.getElementById('inline_role').value = role;
            inlineRow.scrollIntoView({ behavior: 'smooth' });
        }
    };

    // ==========================================
    // School Multi-Step Wizard Scripts
    // ==========================================
    window.previewSchoolAvatar = function(input, targetId) {
        if (input.files && input.files[0]) {
            const reader = new FileReader();
            reader.onload = function(e) {
                const img = document.getElementById(targetId || 'school_avatar_preview');
                if (img) img.src = e.target.result;
            };
            reader.readAsDataURL(input.files[0]);
        }
    };

    window.setSchoolStep = function(step) {
        step = parseInt(step) || 1;
        const s1 = document.getElementById('school_step_1_content');
        const s2 = document.getElementById('school_step_2_content');
        const s3 = document.getElementById('school_step_3_content');

        const tab1 = document.getElementById('school_nav_step_1');
        const tab2 = document.getElementById('school_nav_step_2');
        const tab3 = document.getElementById('school_nav_step_3');

        const barFill = document.getElementById('school_progress_fill');
        const barText = document.getElementById('school_progress_text');
        const subtitle = document.getElementById('school_header_subtitle');
        const stepInput = document.getElementById('school_current_step_input');

        if (stepInput) stepInput.value = step;

        if (s1) s1.classList.toggle('d-none', step !== 1);
        if (s2) s2.classList.toggle('d-none', step !== 2);
        if (s3) s3.classList.toggle('d-none', step !== 3);

        // Update nav items
        if (tab1) {
            tab1.className = 'honna-step-item ' + (step === 1 ? 'active' : 'completed');
            tab1.innerHTML = step === 1 ? 'School Details' : 'School Details <i class="oi oi-check text-success"></i>';
        }
        if (tab2) {
            if (step === 1) {
                tab2.className = 'honna-step-item';
                tab2.innerHTML = 'Member Details';
            } else if (step === 2) {
                tab2.className = 'honna-step-item active';
                tab2.innerHTML = 'Member Details';
            } else {
                tab2.className = 'honna-step-item completed';
                tab2.innerHTML = 'Member Details <i class="oi oi-check text-success"></i>';
            }
        }
        if (tab3) {
            tab3.className = 'honna-step-item ' + (step === 3 ? 'active' : '');
            tab3.innerHTML = 'Primary Contact';
        }

        // Progress percentage
        if (barFill && barText) {
            if (step === 1) {
                barFill.style.width = '20%';
                barText.textContent = '20% complete';
                if (subtitle) subtitle.textContent = 'Add your school details below to get started.';
            } else if (step === 2) {
                barFill.style.width = '60%';
                barText.textContent = '60% complete';
                if (subtitle) subtitle.textContent = 'Add your organisation details below to get started.';
            } else if (step === 3) {
                barFill.style.width = '90%';
                barText.textContent = '90% complete';
                if (subtitle) subtitle.textContent = 'Add your organisation details below to get started.';
            }
        }

        // Scroll smooth to top of profile
        const formTop = document.getElementById('school_profile_form');
        if (formTop) {
            formTop.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
    };

    window.switchSchoolMemberTab = function(tabName) {
        const tabs = ['executive', 'academic', 'operations'];
        tabs.forEach(function(t) {
            const tableEl = document.getElementById('school_table_' + t);
            const btnEl = document.getElementById('school_tab_btn_' + t);
            if (tableEl) {
                tableEl.classList.toggle('d-none', t !== tabName);
            }
            if (btnEl) {
                btnEl.classList.toggle('active', t === tabName);
            }
        });

        const catInput = document.getElementById('school_new_member_category_input');
        if (catInput) {
            catInput.value = tabName;
        }
    };

    window.submitSchoolProfileForm = function(action, nextStep) {
        const form = document.getElementById('school_profile_form');
        const actionInput = document.getElementById('school_form_action');
        const stepInput = document.getElementById('school_current_step_input');
        if (form && actionInput) {
            actionInput.value = action || 'save';
            if (nextStep && stepInput) {
                stepInput.value = nextStep;
            }
            form.submit();
        }
    };

    window.deleteSchoolMemberRow = function(memberId, memberType) {
        if (confirm('Are you sure you want to remove this member?')) {
            const idInput = document.getElementById('school_delete_member_id_input');
            const typeInput = document.getElementById('school_delete_member_type_input');
            if (idInput && typeInput) {
                idInput.value = memberId;
                typeInput.value = memberType;
                window.submitSchoolProfileForm('save', 2);
            }
        }
    };

    window.editSchoolMemberRow = function(memberId, memberType, fname, lname, role, email, phone, isPrimary) {
        const fnameEl = document.getElementById('school_new_mem_fname');
        const lnameEl = document.getElementById('school_new_mem_lname');
        const roleEl = document.getElementById('school_new_mem_role');
        const emailEl = document.getElementById('school_new_mem_email');
        const phoneEl = document.getElementById('school_new_mem_phone');
        const primaryEl = document.getElementById('school_new_mem_primary');
        const catInput = document.getElementById('school_new_member_category_input');
        const editIdInput = document.getElementById('school_edit_member_id_input');

        if (fnameEl) fnameEl.value = fname || '';
        if (lnameEl) lnameEl.value = lname || '';
        if (roleEl) roleEl.value = role || '';
        if (emailEl) emailEl.value = email || '';
        if (phoneEl) phoneEl.value = phone || '';
        if (primaryEl) primaryEl.checked = !!isPrimary;
        if (catInput && memberType) catInput.value = memberType;
        if (editIdInput) editIdInput.value = memberId || '';

        const section = document.getElementById('school_add_member_details_section');
        if (section) {
            section.scrollIntoView({ behavior: 'smooth' });
        }
    };

    window.toggleSchoolMemberAddSection = function() {
        const section = document.getElementById('school_add_member_details_section');
        if (section) {
            section.scrollIntoView({ behavior: 'smooth' });
            const fnameInput = document.getElementById('school_new_mem_fname');
            if (fnameInput) fnameInput.focus();
        }
    };
})();
