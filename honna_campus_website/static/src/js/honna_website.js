/** @odoo-module **/

function initHonnaWebsite() {
    // 1. Login Modal Functionality
    const loginModal = document.getElementById('honna_login_modal');
    const loginTriggers = document.querySelectorAll('.honna-trigger-login');
    const loginClose = document.getElementById('honna_modal_close');

    if (loginModal) {
        loginTriggers.forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.preventDefault();
                loginModal.classList.add('show');
            });
        });

        if (loginClose) {
            loginClose.addEventListener('click', () => {
                loginModal.classList.remove('show');
            });
        }

        loginModal.addEventListener('click', (e) => {
            if (e.target === loginModal) {
                loginModal.classList.remove('show');
            }
        });

        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && loginModal.classList.contains('show')) {
                loginModal.classList.remove('show');
            }
        });
    }

    // 2. Partner Schools Carousel Controls
    const track = document.getElementById('honna_partner_track');
    const btnPrev = document.getElementById('btn_partner_prev');
    const btnNext = document.getElementById('btn_partner_next');

    if (track && btnPrev && btnNext) {
        btnPrev.addEventListener('click', () => {
            track.scrollBy({ left: -280, behavior: 'smooth' });
        });
        btnNext.addEventListener('click', () => {
            track.scrollBy({ left: 280, behavior: 'smooth' });
        });
    }

    // 3. Hero Image Arch Carousel
    const archImg = document.getElementById('hero_arch_display');
    const dots = document.querySelectorAll('.hero-dot');
    const images = [
        '/honna_campus_website/static/src/img/hero_arch_1.png',
        '/honna_campus_website/static/src/img/hero_arch_2.png'
    ];
    let currentIndex = 0;

    if (archImg && dots.length > 0) {
        function setArchImage(idx) {
            currentIndex = idx % images.length;
            archImg.style.opacity = '0.4';
            setTimeout(() => {
                archImg.src = images[currentIndex];
                archImg.style.opacity = '1';
            }, 200);

            dots.forEach((dot, i) => {
                if (i === currentIndex) {
                    dot.classList.add('active');
                } else {
                    dot.classList.remove('active');
                }
            });
        }

        dots.forEach((dot, idx) => {
            dot.addEventListener('click', () => setArchImage(idx));
        });

        // Auto rotate every 5s
        setInterval(() => {
            setArchImage(currentIndex + 1);
        }, 5000);
    }

    // 4. Password Visibility Toggle for Honna Login Page
    const togglePasswordBtn = document.getElementById('honna_toggle_password');
    const passwordInput = document.getElementById('password_input');

    if (togglePasswordBtn && passwordInput && togglePasswordBtn.dataset.bound !== '1') {
        togglePasswordBtn.dataset.bound = '1';
        togglePasswordBtn.addEventListener('click', (e) => {
            e.preventDefault();
            e.stopPropagation();
            const showPassword = passwordInput.getAttribute('type') === 'password';
            passwordInput.setAttribute('type', showPassword ? 'text' : 'password');
            const eyeIcon = togglePasswordBtn.querySelector('.icon-eye');
            const eyeOffIcon = togglePasswordBtn.querySelector('.icon-eye-off');
            if (eyeIcon && eyeOffIcon) {
                eyeIcon.classList.toggle('d-none', showPassword);
                eyeOffIcon.classList.toggle('d-none', !showPassword);
            }
            togglePasswordBtn.setAttribute(
                'aria-label',
                showPassword ? 'Hide password' : 'Show password'
            );
        });
    }
}

// Odoo ES modules often load after DOMContentLoaded — run immediately when ready.
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initHonnaWebsite);
} else {
    initHonnaWebsite();
}
