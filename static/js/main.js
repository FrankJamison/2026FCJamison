(() => {
    'use strict';

    const doc = document;
    const win = window;
    const html = doc.documentElement;
    const backToTop = doc.querySelector('.backto-top');
    const header = doc.querySelector('.header--sticky');
    const mobileMenu = doc.getElementById('mobile-menu');
    const openMenuBtn = doc.querySelector('.humberger-menu');
    const closeMenuControls = doc.querySelectorAll('.closeTrigger, .close-menu-activation');
    const mobileMenuLinks = doc.querySelectorAll('.popup-mobile-menu .primary-menu .nav-item a');

    /* ****************************
       Mobile menu toggle + state sync.
       **************************** */
    function setMenuOpen(isOpen) {
        if (!mobileMenu) {
            return;
        }
        mobileMenu.classList.toggle('menu-open', isOpen);
        mobileMenu.setAttribute('aria-hidden', isOpen ? 'false' : 'true');
        if (openMenuBtn) {
            openMenuBtn.setAttribute('aria-expanded', isOpen ? 'true' : 'false');
        }
        html.style.overflow = isOpen ? 'hidden' : '';
    }

    if (openMenuBtn) {
        openMenuBtn.addEventListener('click', (event) => {
            event.preventDefault();
            setMenuOpen(true);
        });
    }

    closeMenuControls.forEach((control) => {
        control.addEventListener('click', (event) => {
            event.preventDefault();
            setMenuOpen(false);
        });
    });

    if (mobileMenu) {
        mobileMenu.addEventListener('click', (event) => {
            if (event.target === mobileMenu) {
                setMenuOpen(false);
            }
        });
    }

    mobileMenuLinks.forEach((link) => {
        link.addEventListener('click', () => {
            setMenuOpen(false);
        });
    });

    doc.querySelectorAll('.popup-mobile-menu .has-droupdown > a').forEach((link) => {
        link.addEventListener('click', (event) => {
            event.preventDefault();
            const submenu = link.parentElement ? link.parentElement.querySelector('.submenu') : null;
            const isOpen = link.classList.toggle('open');
            link.setAttribute('aria-expanded', isOpen ? 'true' : 'false');
            if (submenu) {
                submenu.classList.toggle('active', isOpen);
                submenu.style.display = isOpen ? 'block' : 'none';
            }
        });
    });

    /* ****************************
       Scroll-driven UI (back-to-top + sticky header).
       **************************** */
    function updateBackToTop() {
        if (!backToTop) {
            return;
        }
        const isVisible = win.scrollY > 100;
        backToTop.style.opacity = isVisible ? '1' : '0';
        backToTop.setAttribute('aria-hidden', isVisible ? 'false' : 'true');
        if (isVisible) {
            backToTop.removeAttribute('tabindex');
        } else {
            backToTop.setAttribute('tabindex', '-1');
        }
    }

    function updateStickyHeader() {
        if (!header) {
            return;
        }
        header.classList.toggle('sticky', win.scrollY > 250);
    }

    if (backToTop) {
        backToTop.addEventListener('click', () => {
            win.scrollTo({
                top: 0,
                behavior: 'smooth'
            });
        });
    }

    function smoothScrollTo(targetId, offset) {
        if (!targetId || targetId.charAt(0) !== '#') {
            return;
        }
        const target = doc.querySelector(targetId);
        if (!target) {
            return;
        }
        const top = target.getBoundingClientRect().top + win.scrollY - offset;
        win.scrollTo({
            top,
            behavior: 'smooth'
        });
    }

    doc.addEventListener('click', (event) => {
        const link = event.target.closest('.smoth-animation, .smoth-animation-two');
        if (!link) {
            return;
        }
        event.preventDefault();
        const offset = link.classList.contains('smoth-animation-two') ? 0 : 50;
        smoothScrollTo(link.getAttribute('href'), offset);
    });

    /* ****************************
       Scrollspy for one-page navigation.
       **************************** */
    function initScrollSpy() {
        const navLinks = Array.from(doc.querySelectorAll('.onepagenav .nav-link'));
        if (!navLinks.length) {
            return;
        }

        const sections = navLinks
            .map((link) => {
                const id = link.getAttribute('href');
                if (!id || !id.startsWith('#')) {
                    return null;
                }
                const section = doc.querySelector(id);
                return section ? {
                    link,
                    section,
                    id
                } : null;
            })
            .filter(Boolean);

        function setActive(id) {
            navLinks.forEach((link) => {
                const isActive = link.getAttribute('href') === id;
                link.classList.toggle('active', isActive);
                if (isActive) {
                    link.setAttribute('aria-current', 'page');
                } else {
                    link.removeAttribute('aria-current');
                }
                const parent = link.closest('li');
                if (parent) {
                    parent.classList.toggle('current', isActive);
                }
            });
        }

        const observer = new IntersectionObserver((entries) => {
            entries.forEach((entry) => {
                if (entry.isIntersecting) {
                    const match = sections.find((item) => item.section === entry.target);
                    if (match) {
                        setActive(match.id);
                    }
                }
            });
        }, {
            rootMargin: '-35% 0px -55% 0px',
            threshold: 0.01
        });

        sections.forEach((item) => observer.observe(item.section));
    }


    win.addEventListener('scroll', () => {
        updateBackToTop();
        updateStickyHeader();
    }, {
        passive: true
    });

    updateBackToTop();
    updateStickyHeader();
    initScrollSpy();

    /* ****************************
       A11y helpers for keyboard activation.
       **************************** */
    function initKeyboardActivation() {
        doc.addEventListener('keydown', (event) => {
            if (event.key !== 'Enter' && event.key !== ' ') {
                return;
            }
            const target = event.target;
            if (!target) {
                return;
            }
            const isButtonLike = target.getAttribute &&
                target.getAttribute('role') === 'button' &&
                target.getAttribute('tabindex') === '0';
            if (!isButtonLike) {
                return;
            }
            event.preventDefault();
            if (typeof target.click === 'function') {
                target.click();
            }
        });
    }

    function initModalTriggers() {
        doc.querySelectorAll('[data-bs-toggle="modal"][data-bs-target]').forEach((trigger) => {
            const tag = (trigger.tagName || '').toLowerCase();
            const isNative = tag === 'a' || tag === 'button' || tag === 'input' ||
                tag === 'select' || tag === 'textarea';

            if (!isNative) {
                if (!trigger.getAttribute('role')) {
                    trigger.setAttribute('role', 'button');
                }
                if (!trigger.getAttribute('tabindex')) {
                    trigger.setAttribute('tabindex', '0');
                }
            }

            if (!trigger.getAttribute('aria-haspopup')) {
                trigger.setAttribute('aria-haspopup', 'dialog');
            }

            if (!trigger.getAttribute('aria-controls')) {
                const targetId = (trigger.getAttribute('data-bs-target') || '').trim();
                if (targetId && targetId.charAt(0) === '#') {
                    trigger.setAttribute('aria-controls', targetId.slice(1));
                }
            }

            if (!trigger.getAttribute('aria-label')) {
                const titleEl = trigger.querySelector('h4.title, h3.title, .title');
                const titleText = titleEl ? (titleEl.textContent || '').replace(/\s+/g, ' ').trim() : '';
                if (titleText) {
                    trigger.setAttribute('aria-label', `Open details: ${titleText}`);
                }
            }
        });
    }

    /* ****************************
       Ensure safe rel values for external links.
       **************************** */
    function initExternalLinks(root = doc) {
        root.querySelectorAll('a[target="_blank"]').forEach((anchor) => {
            const rel = (anchor.getAttribute('rel') || '').trim();
            const tokens = rel ? rel.split(/\s+/) : [];
            const lowerTokens = tokens.map((token) => String(token).toLowerCase());
            if (!lowerTokens.includes('noopener')) {
                tokens.push('noopener');
            }
            if (!lowerTokens.includes('noreferrer')) {
                tokens.push('noreferrer');
            }
            anchor.setAttribute('rel', tokens.join(' ').trim());
        });
    }

    /* ****************************
       Modal ARIA enhancements and feather icon refresh.
       **************************** */
    function initModalEnhancements(root = doc) {
        root.querySelectorAll('.modal').forEach((modal) => {
            if (!modal.hasAttribute('role')) {
                modal.setAttribute('role', 'dialog');
            }
            if (!modal.hasAttribute('aria-modal')) {
                modal.setAttribute('aria-modal', 'true');
            }
            if (!modal.getAttribute('aria-labelledby')) {
                const titleEl = modal.querySelector('.news-details h2.title, .text-content h3, .modal-title, h1, h2, h3');
                if (titleEl) {
                    if (!titleEl.id) {
                        titleEl.id = modal.id ? `${modal.id}-title` : 'modal-title';
                    }
                    modal.setAttribute('aria-labelledby', titleEl.id);
                }
            }

            const mainTitle = modal.querySelector('.news-details h2.title, .modal-title, h1, h2');
            if (mainTitle) {
                const hasH3 = !!modal.querySelector('h3');
                const firstH4 = modal.querySelector('h4');
                if (firstH4 && !hasH3) {
                    const h3 = doc.createElement('h3');
                    h3.className = 'visually-hidden';
                    h3.textContent = 'Sections';
                    firstH4.parentNode.insertBefore(h3, firstH4);
                }
            }

            if (!modal.dataset.featherListener) {
                modal.addEventListener('shown.bs.modal', () => {
                    if (win.feather && typeof win.feather.replace === 'function') {
                        win.feather.replace();
                    }
                });
                modal.dataset.featherListener = 'true';
            }
        });
    }

    let modalNavigationBound = false;

    /* ****************************
       Leave-reply form helpers + modal link hardening.
       **************************** */
    function initLeaveReplyForms(root = doc) {
        root.querySelectorAll('form.js-leave-reply-form').forEach((form) => {
            const statusEl = form.querySelector('.js-leave-reply-status');
            if (statusEl) {
                if (!statusEl.getAttribute('role')) {
                    statusEl.setAttribute('role', 'status');
                }
                if (!statusEl.getAttribute('aria-live')) {
                    statusEl.setAttribute('aria-live', 'polite');
                }
                if (!statusEl.getAttribute('aria-atomic')) {
                    statusEl.setAttribute('aria-atomic', 'true');
                }
            }

            form.querySelectorAll('.rnform-group').forEach((group) => {
                const honeypot = group.querySelector('input[name="hp"]');
                if (!honeypot) {
                    return;
                }
                if (!group.getAttribute('aria-hidden')) {
                    group.setAttribute('aria-hidden', 'true');
                }
                if (!honeypot.getAttribute('tabindex')) {
                    honeypot.setAttribute('tabindex', '-1');
                }
            });

            form.querySelectorAll('input, textarea').forEach((field) => {
                const type = (field.getAttribute('type') || '').toLowerCase();
                if (type === 'hidden') {
                    return;
                }

                const ariaLabel = field.getAttribute('aria-label');
                if (!ariaLabel) {
                    const placeholder = (field.getAttribute('placeholder') || '').trim();
                    if (placeholder) {
                        field.setAttribute('aria-label', placeholder);
                    }
                }

                if (!field.getAttribute('autocomplete')) {
                    const name = (field.getAttribute('name') || '').toLowerCase();
                    if (name === 'name') {
                        field.setAttribute('autocomplete', 'name');
                    } else if (name === 'email') {
                        field.setAttribute('autocomplete', 'email');
                    } else if (name === 'website') {
                        field.setAttribute('autocomplete', 'url');
                    }
                }
            });
        });

        if (!modalNavigationBound) {
            modalNavigationBound = true;
            doc.addEventListener('click', (event) => {
                if (event.button !== 0) {
                    return;
                }
                if (event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) {
                    return;
                }

                const anchor = event.target && event.target.closest ?
                    event.target.closest('.modal a.rn-btn.thumbs-icon') :
                    null;
                if (!anchor) {
                    return;
                }

                const href = anchor.getAttribute('href');
                if (!href || href === '#' || href.toLowerCase().startsWith('javascript:')) {
                    return;
                }
                event.preventDefault();
                event.stopPropagation();

                if (anchor.target && anchor.target.toLowerCase() === '_blank') {
                    win.open(href, '_blank', 'noopener,noreferrer');
                    return;
                }

                win.location.assign(href);
            }, true);
        }

        root.querySelectorAll('form.js-leave-reply-form').forEach((form) => {
            if (form.dataset.leaveReplyBound === 'true') {
                return;
            }
            form.dataset.leaveReplyBound = 'true';
            form.addEventListener('submit', (event) => {
                event.preventDefault();

                const statusEl = form.querySelector('.js-leave-reply-status');
                const submitBtn = form.querySelector('button[type="submit"], input[type="submit"]');
                const previousBtnText = submitBtn ? submitBtn.textContent : '';

                function setStatus(message, ok) {
                    if (!statusEl) {
                        return;
                    }
                    statusEl.style.display = '';
                    statusEl.textContent = message;
                    statusEl.setAttribute('data-status', ok ? 'ok' : 'error');
                }

                if (submitBtn) {
                    submitBtn.disabled = true;
                    submitBtn.classList.add('disabled');
                }
                setStatus('Sending...', true);

                const formData = new FormData(form);

                const existingTitle = (formData.get('blog_title') || '').toString().trim();
                if (!existingTitle) {
                    const modal = form.closest ? form.closest('.modal') : null;
                    const titleEl = modal ? modal.querySelector('.news-details h2.title') : null;
                    const derivedTitle = titleEl ? (titleEl.textContent || '').trim() : '';
                    if (derivedTitle) {
                        formData.set('blog_title', derivedTitle);
                    }
                }

                fetch(form.action, {
                        method: 'POST',
                        headers: {
                            'Accept': 'application/json'
                        },
                        body: formData
                    })
                    .then((response) => response.json().then((data) => ({
                        response,
                        data
                    })).catch(() => ({
                        response,
                        data: null
                    })))
                    .then((result) => {
                        const response = result.response;
                        const data = result.data;
                        if (response.ok && data && data.ok) {
                            setStatus('Thanks! Your reply was sent.', true);
                            form.reset();
                        } else {
                            const message = (data && data.error) ? data.error : 'Sorry - could not send your reply.';
                            setStatus(message, false);
                        }
                    })
                    .catch(() => {
                        setStatus('Sorry - network error while sending.', false);
                    })
                    .finally(() => {
                        if (submitBtn) {
                            submitBtn.disabled = false;
                            submitBtn.classList.remove('disabled');
                            if (previousBtnText) {
                                submitBtn.textContent = previousBtnText;
                            }
                        }
                    });
            });
        });
    }

    /* ****************************
       Lazy-inject modal templates on first open.
       **************************** */
    function ensureModalTemplates(targetId) {
        if (!targetId || targetId.charAt(0) !== '#') {
            return;
        }

        const isPortfolio = targetId.indexOf('#portfolioModal') === 0;
        const isBlog = targetId.indexOf('#blogModal') === 0;
        if (!isPortfolio && !isBlog) {
            return;
        }

        const templateId = isPortfolio ? 'portfolio-modals-template' : 'blog-modals-template';
        const rootId = isPortfolio ? 'portfolio-modals-root' : 'blog-modals-root';
        const template = doc.getElementById(templateId);
        const root = doc.getElementById(rootId);
        if (!template || !root) {
            return;
        }
        if (root.childNodes.length > 0) {
            return;
        }

        root.appendChild(template.content.cloneNode(true));
        initExternalLinks(root);
        initModalEnhancements(root);
        initLeaveReplyForms(root);
    }

    /* ****************************
       AJAX contact form submission.
       **************************** */
    function initContactForm() {
        const contactForm = doc.querySelector('form.js-contact-form');
        if (!contactForm || contactForm.dataset.contactBound === 'true') {
            return;
        }
        contactForm.dataset.contactBound = 'true';
        contactForm.addEventListener('submit', (event) => {
            event.preventDefault();

            const statusEl = contactForm.querySelector('.js-contact-status');
            const submitBtn = contactForm.querySelector('button[type="submit"], input[type="submit"]');
            const previousBtnText = submitBtn ? submitBtn.textContent : '';

            function setStatus(message, ok) {
                if (!statusEl) {
                    return;
                }
                statusEl.style.display = '';
                statusEl.textContent = message;
                statusEl.setAttribute('data-status', ok ? 'ok' : 'error');
            }

            if (submitBtn) {
                submitBtn.disabled = true;
                submitBtn.classList.add('disabled');
            }
            setStatus('Sending...', true);

            const formData = new FormData(contactForm);

            fetch(contactForm.action, {
                    method: 'POST',
                    headers: {
                        'Accept': 'application/json'
                    },
                    body: formData
                })
                .then((response) => response.json().then((data) => ({
                    response,
                    data
                })).catch(() => ({
                    response,
                    data: null
                })))
                .then((result) => {
                    const response = result.response;
                    const data = result.data;
                    if (response.ok && data && data.ok) {
                        setStatus('Thanks! Your message was sent.', true);
                        contactForm.reset();
                    } else {
                        const message = (data && data.error) ? data.error : 'Sorry - could not send your message.';
                        setStatus(message, false);
                    }
                })
                .catch(() => {
                    setStatus('Sorry - network error while sending.', false);
                })
                .finally(() => {
                    if (submitBtn) {
                        submitBtn.disabled = false;
                        submitBtn.classList.remove('disabled');
                        if (previousBtnText) {
                            submitBtn.textContent = previousBtnText;
                        }
                    }
                });
        });
    }

    doc.addEventListener('click', (event) => {
        const trigger = event.target && event.target.closest ?
            event.target.closest('[data-bs-toggle="modal"][data-bs-target]') :
            null;
        if (!trigger) {
            return;
        }
        const targetId = (trigger.getAttribute('data-bs-target') || '').trim();
        ensureModalTemplates(targetId);
    }, true);

    initKeyboardActivation();
    initModalTriggers();
    initExternalLinks(doc);
    initModalEnhancements(doc);
    initLeaveReplyForms(doc);
    initContactForm();

    if (win.feather && typeof win.feather.replace === 'function') {
        win.feather.replace();
    }
    doc.querySelectorAll('i[data-feather]').forEach((icon) => {
        icon.setAttribute('aria-hidden', 'true');
    });
})();