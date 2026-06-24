(() => {
    'use strict';

    const doc = document;
    const win = window;
    const html = doc.documentElement;
    const backToTop = doc.querySelector('.backto-top');
    const header = doc.querySelector('.site-header--sticky');
    const mobileMenu = doc.querySelector('.mobile-menu');
    const openMenuBtn = doc.querySelector('.site-header__toggle');
    const closeMenuControls = doc.querySelectorAll('.site-header__close, .mobile-menu__close-button');
    const mobileMenuLinks = doc.querySelectorAll('.mobile-menu__menu-link');

    let isMobileMenuOpen = false;
    let lastFocusedBeforeMenuOpen = null;

    function getFocusableElements(container) {
        if (!container) {
            return [];
        }
        const selectors = [
            'a[href]:not([tabindex="-1"])',
            'button:not([disabled]):not([tabindex="-1"])',
            'input:not([disabled]):not([type="hidden"]):not([tabindex="-1"])',
            'select:not([disabled]):not([tabindex="-1"])',
            'textarea:not([disabled]):not([tabindex="-1"])',
            '[tabindex]:not([tabindex="-1"])'
        ];

        return Array.from(container.querySelectorAll(selectors.join(',')))
            .filter((el) => {
                if (!el || typeof el.focus !== 'function') {
                    return false;
                }
                if (el.getAttribute('aria-hidden') === 'true') {
                    return false;
                }
                if (el.hasAttribute('hidden')) {
                    return false;
                }
                return !!(el.offsetWidth || el.offsetHeight || el.getClientRects().length);
            });
    }

    function focusFirstMobileMenuControl() {
        if (!mobileMenu) {
            return;
        }
        const closeButton = mobileMenu.querySelector('.mobile-menu__close-button');
        if (closeButton) {
            closeButton.focus();
            return;
        }
        const focusables = getFocusableElements(mobileMenu);
        if (focusables.length) {
            focusables[0].focus();
        }
    }

    function handleMobileMenuKeydown(event) {
        if (!isMobileMenuOpen || !mobileMenu) {
            return;
        }

        if (event.key === 'Escape') {
            event.preventDefault();
            setMenuOpen(false);
            return;
        }

        if (event.key !== 'Tab') {
            return;
        }

        const focusables = getFocusableElements(mobileMenu);
        if (!focusables.length) {
            event.preventDefault();
            return;
        }

        const first = focusables[0];
        const last = focusables[focusables.length - 1];
        const active = doc.activeElement;

        if (event.shiftKey) {
            if (active === first || !mobileMenu.contains(active)) {
                event.preventDefault();
                last.focus();
            }
        } else {
            if (active === last) {
                event.preventDefault();
                first.focus();
            }
        }
    }

    /* ****************************
       Mobile menu toggle + state sync.
       **************************** */
    function setMenuOpen(isOpen) {
        if (!mobileMenu) {
            return;
        }
        const wasOpen = isMobileMenuOpen;
        isMobileMenuOpen = isOpen;

        if (isOpen && !wasOpen) {
            lastFocusedBeforeMenuOpen = doc.activeElement;
        }

        mobileMenu.classList.toggle('mobile-menu--open', isOpen);
        mobileMenu.setAttribute('aria-hidden', isOpen ? 'false' : 'true');
        if (openMenuBtn) {
            openMenuBtn.setAttribute('aria-expanded', isOpen ? 'true' : 'false');
        }
        html.style.overflow = isOpen ? 'hidden' : '';

        if (isOpen) {
            doc.addEventListener('keydown', handleMobileMenuKeydown, true);
            win.setTimeout(() => {
                focusFirstMobileMenuControl();
            }, 0);
        } else {
            doc.removeEventListener('keydown', handleMobileMenuKeydown, true);
            const toRestore = lastFocusedBeforeMenuOpen;
            lastFocusedBeforeMenuOpen = null;
            if (toRestore && typeof toRestore.focus === 'function') {
                win.setTimeout(() => {
                    toRestore.focus();
                }, 0);
            }
        }
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

    doc.querySelectorAll('.mobile-menu__menu-item--dropdown > a').forEach((link) => {
        link.addEventListener('click', (event) => {
            event.preventDefault();
            const submenu = link.parentElement ? link.parentElement.querySelector('.mobile-menu__submenu') : null;
            const isOpen = link.classList.toggle('mobile-menu__menu-link--open');
            link.setAttribute('aria-expanded', isOpen ? 'true' : 'false');
            if (submenu) {
                submenu.classList.toggle('mobile-menu__submenu--open', isOpen);
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
        header.classList.toggle('site-header--scrolled', win.scrollY > 250);
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
                    event.target.closest('.modal a.rn-btn') :
                    null;
                if (!anchor) {
                    return;
                }

                const href = anchor.getAttribute('href');
                if (!href || href === '#' || href.toLowerCase().startsWith('javascript:')) {
                    event.preventDefault();
                    return;
                }

                const target = (anchor.getAttribute('target') || '').toLowerCase();
                if (target === '_blank') {
                    event.preventDefault();
                    event.stopPropagation();

                    win.open(href, '_blank', 'noopener,noreferrer');
                }
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
       Read-time indicators for articles.

       Populates .js-read-time spans using word count of each article's
       .news-details content (excluding the meta row).
       **************************** */
    function initReadTimeIndicators(root) {
        const scope = root && root.querySelectorAll ? root : doc;
        scope.querySelectorAll('.news-details').forEach((newsDetails) => {
            const indicator = newsDetails.querySelector('.js-read-time');
            if (!indicator) {
                return;
            }

            // Gather text from top-level nodes except the meta row.
            // This includes text nodes so legacy articles that still have raw
            // text inside .news-details get accurate read-time estimates.
            const parts = [];
            Array.from(newsDetails.childNodes).forEach((node) => {
                // Element
                if (node.nodeType === 1) {
                    if (node.classList && node.classList.contains('article-meta')) {
                        return;
                    }
                    parts.push((node.textContent || '').trim());
                    return;
                }

                // Text
                if (node.nodeType === 3) {
                    const text = (node.textContent || '').trim();
                    if (text) {
                        parts.push(text);
                    }
                }
            });

            const text = parts.join(' ').replace(/\s+/g, ' ').trim();
            const words = (text.match(/[A-Za-z0-9]+(?:[’'\-][A-Za-z0-9]+)*/g) || []).length;
            const minutes = Math.max(1, Math.ceil(words / 200));

            indicator.textContent = `${minutes} min read`;
            indicator.setAttribute('aria-label', `Estimated read time: ${minutes} minute${minutes === 1 ? '' : 's'}`);
            indicator.dataset.minutes = String(minutes);
            indicator.dataset.words = String(words);
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
        initReadTimeIndicators(root);
    }

    /* ****************************
       Chained modal buttons (dismiss one, open another).

       Bootstrap data-attributes don't reliably open a second modal
       on the same click that dismisses the first, so we do it
       explicitly.
       **************************** */
    function initChainedModalButtons() {
        doc.addEventListener('click', (event) => {
            const target = event.target;
            if (!target || !target.closest) {
                return;
            }

            const trigger = target.closest('[data-bs-toggle="modal"][data-bs-target][data-bs-dismiss="modal"]');
            if (!trigger) {
                return;
            }

            const currentModalEl = trigger.closest('.modal');
            if (!currentModalEl) {
                return;
            }

            const targetId = (trigger.getAttribute('data-bs-target') || '').trim();
            if (!targetId || targetId.charAt(0) !== '#') {
                return;
            }

            // If Bootstrap isn't available for some reason, fall back to native behavior.
            const bs = win.bootstrap;
            if (!bs || !bs.Modal) {
                return;
            }

            const targetModalEl = doc.querySelector(targetId);
            if (!targetModalEl) {
                // The template may be lazy-injected.
                ensureModalTemplates(targetId);
            }

            const ensuredTargetEl = doc.querySelector(targetId);
            if (!ensuredTargetEl) {
                return;
            }

            event.preventDefault();
            event.stopPropagation();
            event.stopImmediatePropagation();

            const currentInstance = bs.Modal.getInstance(currentModalEl) || bs.Modal.getOrCreateInstance(currentModalEl);

            const showTarget = () => {
                const targetInstance = bs.Modal.getOrCreateInstance(ensuredTargetEl);
                targetInstance.show();
            };

            currentModalEl.addEventListener('hidden.bs.modal', showTarget, {
                once: true
            });

            currentInstance.hide();
        }, true);
    }

    /* ****************************
       AJAX contact form submission.
       **************************** */
    function postAnalyticsEvent(eventName, payload) {
        if (!eventName) {
            return;
        }

        const eventPayload = Object.assign({
            event: eventName,
            client_timestamp: new Date().toISOString()
        }, payload || {});

        const endpoint = '/analytics/event';
        const body = JSON.stringify(eventPayload);

        if (win.navigator && typeof win.navigator.sendBeacon === 'function' && typeof win.Blob !== 'undefined') {
            try {
                const blob = new Blob([body], {
                    type: 'application/json'
                });
                if (win.navigator.sendBeacon(endpoint, blob)) {
                    return;
                }
            } catch (_error) {
                // Fall through to fetch when beacon fails.
            }
        }

        fetch(endpoint, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            },
            body,
            keepalive: true
        }).catch(() => {
            // No-op: analytics delivery should never block UX.
        });
    }

    function trackConversionEvent(eventName, label, extras) {
        if (!eventName) {
            return;
        }

        const payload = {
            event_category: 'portfolio_conversion',
            event_label: label || 'unspecified',
            page_path: win.location ? win.location.pathname : ''
        };

        if (extras && typeof extras === 'object') {
            Object.keys(extras).forEach((key) => {
                payload[key] = extras[key];
            });
        }

        postAnalyticsEvent(eventName, payload);

        if (typeof win.gtag === 'function') {
            win.gtag('event', eventName, payload);
            return;
        }

        if (Array.isArray(win.dataLayer)) {
            win.dataLayer.push(Object.assign({
                event: eventName
            }, payload));
            return;
        }

        if (!Array.isArray(win.__fcAnalyticsQueue)) {
            win.__fcAnalyticsQueue = [];
        }
        win.__fcAnalyticsQueue.push({
            event: eventName,
            payload,
            ts: Date.now()
        });
    }

    function initScrollDepthTracking() {
        const milestones = [25, 50, 75, 100];
        const sent = {};
        let ticking = false;

        function emitMilestones() {
            ticking = false;
            const root = doc.documentElement;
            const maxScrollable = Math.max((root ? root.scrollHeight : 0) - win.innerHeight, 0);

            if (maxScrollable <= 0) {
                if (!sent[100]) {
                    sent[100] = true;
                    trackConversionEvent('scroll_depth_milestone', 'scroll_100', {
                        scroll_percent: 100
                    });
                }
                return;
            }

            const progress = Math.min(100, Math.round((win.scrollY / maxScrollable) * 100));
            milestones.forEach((milestone) => {
                if (progress >= milestone && !sent[milestone]) {
                    sent[milestone] = true;
                    trackConversionEvent('scroll_depth_milestone', `scroll_${milestone}`, {
                        scroll_percent: milestone
                    });
                }
            });
        }

        function onScroll() {
            if (ticking) {
                return;
            }
            ticking = true;
            win.requestAnimationFrame(emitMilestones);
        }

        win.addEventListener('scroll', onScroll, {
            passive: true
        });
        win.addEventListener('resize', onScroll, {
            passive: true
        });
        emitMilestones();
    }

    function initSectionEngagementTracking() {
        if (typeof win.IntersectionObserver !== 'function') {
            return;
        }

        const sectionIds = ['home', 'featured-projects', 'resume', 'portfolio', 'contacts'];
        const sections = sectionIds
            .map((id) => doc.getElementById(id))
            .filter(Boolean);

        if (!sections.length) {
            return;
        }

        const seen = new Set();
        const markSeen = (sectionId) => {
            if (!sectionId || seen.has(sectionId)) {
                return;
            }
            seen.add(sectionId);
            trackConversionEvent('section_visible', sectionId, {
                section_id: sectionId
            });
        };

        const emitFromViewportProbe = () => {
            const probeY = win.innerHeight * 0.45;
            sections.forEach((section) => {
                const rect = section.getBoundingClientRect();
                if (rect.top <= probeY && rect.bottom >= probeY) {
                    markSeen(section.id || '');
                }
            });
        };

        let probeTicking = false;
        const onViewportChange = () => {
            if (probeTicking) {
                return;
            }
            probeTicking = true;
            win.requestAnimationFrame(() => {
                probeTicking = false;
                emitFromViewportProbe();
            });
        };

        const observer = new win.IntersectionObserver((entries) => {
            entries.forEach((entry) => {
                if (!entry.isIntersecting || entry.intersectionRatio < 0.45) {
                    return;
                }

                const section = entry.target;
                const sectionId = section.id || '';
                if (!sectionId) {
                    return;
                }

                markSeen(sectionId);
                observer.unobserve(section);
            });
        }, {
            threshold: [0.45, 0.6, 0.8]
        });

        sections.forEach((section) => {
            observer.observe(section);
        });

        win.addEventListener('scroll', onViewportChange, {
            passive: true
        });
        win.addEventListener('resize', onViewportChange, {
            passive: true
        });
        emitFromViewportProbe();
    }

    function initFooterKpiRefresh() {
        const valueNodes = Array.from(doc.querySelectorAll('.portfolio-kpi-value[data-kpi-key]'));
        if (!valueNodes.length) {
            return;
        }

        fetch('/analytics/summary?days=30', {
                headers: {
                    Accept: 'application/json'
                }
            })
            .then((response) => response.json())
            .then((result) => {
                const summary = result && result.summary ? result.summary : null;
                if (!summary) {
                    return;
                }

                valueNodes.forEach((node) => {
                    const key = (node.getAttribute('data-kpi-key') || '').trim();
                    if (!key) {
                        return;
                    }

                    if (key === 'contact_success_rate') {
                        const value = Number(summary.contact_success_rate || 0);
                        node.textContent = `${value.toFixed(1)}%`;
                        return;
                    }

                    const value = summary[key];
                    if (value === undefined || value === null) {
                        return;
                    }
                    node.textContent = String(value);
                });
            })
            .catch(() => {
                // Keep server-rendered values when refresh is unavailable.
            });
    }

    function initConversionClickTracking() {
        doc.addEventListener('click', (event) => {
            const trigger = event.target && event.target.closest ?
                event.target.closest('[data-track-event]') :
                null;

            if (!trigger) {
                return;
            }

            const eventName = (trigger.getAttribute('data-track-event') || '').trim();
            if (!eventName) {
                return;
            }

            const label = (trigger.getAttribute('data-track-label') || trigger.textContent || '').trim();
            const href = (trigger.getAttribute('href') || '').trim();

            trackConversionEvent(eventName, label, {
                link_url: href
            });
        }, true);
    }

    function initContactForm() {
        const contactForm = doc.querySelector('form.js-contact-form');
        if (!contactForm || contactForm.dataset.contactBound === 'true') {
            return;
        }
        contactForm.dataset.contactBound = 'true';
        contactForm.addEventListener('submit', (event) => {
            event.preventDefault();
            trackConversionEvent('contact_submit_attempt', 'contact_form');

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
                        trackConversionEvent('contact_submit_success', 'contact_form');
                        setStatus('Thanks! Your message was sent.', true);
                        contactForm.reset();
                    } else {
                        const message = (data && data.error) ? data.error : 'Sorry - could not send your message.';
                        trackConversionEvent('contact_submit_error', 'contact_form', {
                            error_type: 'application_or_validation'
                        });
                        setStatus(message, false);
                    }
                })
                .catch(() => {
                    trackConversionEvent('contact_submit_error', 'contact_form', {
                        error_type: 'network'
                    });
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

    /* ****************************
       Make entire portfolio card clickable.
       **************************** */
    function initPortfolioCardClicks() {
        doc.addEventListener('click', (event) => {
            if (event.button !== 0) {
                return;
            }
            if (event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) {
                return;
            }

            const target = event.target;
            if (!target || !target.closest) {
                return;
            }

            if (target.closest('[data-bs-toggle="modal"][data-bs-target]')) {
                return;
            }

            const item = target.closest('.portfolio-item');
            if (!item) {
                return;
            }

            const trigger = item.querySelector('[data-bs-toggle="modal"][data-bs-target]');
            if (!trigger) {
                return;
            }

            const interactive = target.closest('a, button, input, select, textarea, label');
            if (interactive) {
                return;
            }

            trigger.click();
        }, true);
    }

    /* ****************************
       Auto-add compact tech chips to portfolio grid cards.
       **************************** */
    function initPortfolioGridTechChips() {
        const grid = doc.querySelector('#portfolio .portfolio-grid');
        if (!grid) {
            return;
        }

        const portfolioTemplate = doc.getElementById('portfolio-modals-template');
        const repoStackOverrides = {
            'FrankJamison/2-Day-Shower-Specialists': ['JavaScript', 'HTML', 'CSS'],
            'FrankJamison/RoboFriends': ['React', 'JavaScript', 'CSS', 'REST API'],
            'FrankJamison/2026SimpleFolio': ['HTML', 'SCSS', 'JavaScript'],
            'FrankJamison/2026RandomThoughtsInTraffic': ['PHP', 'JavaScript', 'Vue', 'TypeScript'],
            'FrankJamison/PassionateTeachingJourney.com': ['PHP', 'JavaScript', 'Vue', 'TypeScript'],
            'FrankJamison/FrankJamison.com-v2025': ['PHP', 'JavaScript', 'CSS'],
            'FrankJamison/Mi-Familia-Taco-Catering': ['HTML', 'CSS', 'JavaScript'],
            'FrankJamison/Angular-CLI-Application': ['Angular', 'TypeScript', 'SCSS', 'JavaScript'],
            'FrankJamison/The-Budget-Application': ['JavaScript', 'HTML', 'CSS'],
            'FrankJamison/AncientWhiteArmyVets-RPG-Tools-v2019': ['HTML', 'Sass', 'JavaScript', 'CSS'],
            'FrankJamison/AncientWhiteArmyVets-RPG-Tools-v2020.2': ['Node.js', 'MySQL', 'JavaScript', 'CSS'],
            'FrankJamison/2016VirtualWorld': ['Java', 'JavaScript', 'HTML', 'CSS'],
            'FrankJamison/FrankJamison.com-v2017': ['JavaScript', 'HTML', 'CSS'],
            'FrankJamison/2018FranksClassicCars': ['PHP', 'CSS', 'XSLT'],
            'FrankJamison/Typing-Speed-Test': ['JavaScript', 'HTML', 'CSS'],
            'FrankJamison/Zita-Worleys-Website': ['HTML', 'CSS'],
            'FrankJamison/Jamison-Stamps-and-Books': ['PHP', 'JavaScript', 'CSS', 'Shell'],
            'FrankJamison/Globe-Bank': ['PHP', 'CSS', 'Hack'],
            'FrankJamison/FrankJamison.com-v2006': ['JavaScript', 'HTML', 'CSS'],
            'FrankJamison/Password-Exposure-Checker': ['Python', 'PHP', 'REST API', 'CSS'],
            'FrankJamison/2026HackerNews': ['Python', 'PHP', 'REST API', 'CSS']
        };

        const techMatchers = [{
                label: 'React',
                test: /\breact\b/i
            },
            {
                label: 'Vue',
                test: /\bvue\b/i
            },
            {
                label: 'Angular',
                test: /\bangular\b/i
            },
            {
                label: 'Flask',
                test: /\bflask\b/i
            },
            {
                label: 'WordPress',
                test: /\bwordpress\b/i
            },
            {
                label: 'Node.js',
                test: /(node\.js|\bnode\b|\bexpress\b)/i
            },
            {
                label: 'TypeScript',
                test: /\btypescript\b/i
            },
            {
                label: 'SCSS',
                test: /\bscss\b/i
            },
            {
                label: 'Sass',
                test: /\bsass\b/i
            },
            {
                label: 'MySQL',
                test: /\bmysql\b/i
            },
            {
                label: 'MongoDB',
                test: /\bmongodb\b/i
            },
            {
                label: 'PayPal API',
                test: /\bpaypal\b/i
            },
            {
                label: 'REST API',
                test: /\b(rest|api|json)\b/i
            },
            {
                label: 'Canvas API',
                test: /\bcanvas api\b/i
            },
            {
                label: 'Parcel',
                test: /\bparcel\b/i
            },
            {
                label: 'Bootstrap',
                test: /\bbootstrap\b/i
            },
            {
                label: 'PHP',
                test: /\bphp\b/i
            },
            {
                label: 'Python',
                test: /\bpython\b/i
            },
            {
                label: 'Java',
                test: /\bjava\b/i
            },
            {
                label: 'JavaScript',
                test: /(\bjavascript\b|vanilla js|vanilla javascript)/i
            },
            {
                label: 'HTML',
                test: /(\bhtml\b|semantic html)/i
            },
            {
                label: 'CSS',
                test: /(\bcss\b|responsive)/i
            },
            {
                label: 'Shell',
                test: /\bshell\b/i
            },
            {
                label: 'XSLT',
                test: /\bxslt\b/i
            },
            {
                label: 'Hack',
                test: /\bhack\b/i
            }
        ];

        function getModalById(modalId) {
            const direct = doc.getElementById(modalId);
            if (direct) {
                return direct;
            }
            if (!portfolioTemplate || !portfolioTemplate.content) {
                return null;
            }
            return portfolioTemplate.content.querySelector(`#${modalId}`);
        }

        function normalizeAndRankTags(rawTags) {
            const tags = [...rawTags];

            // Framework-to-language coupling so stack chips stay semantically complete.
            if (tags.includes('Flask') && !tags.includes('Python')) {
                tags.push('Python');
            }

            const priority = [
                'Flask',
                'Python',
                'React',
                'Vue',
                'Angular',
                'Node.js',
                'PHP',
                'TypeScript',
                'JavaScript',
                'Java',
                'WordPress',
                'MySQL',
                'MongoDB',
                'SCSS',
                'Sass',
                'HTML',
                'CSS',
                'Bootstrap',
                'Parcel',
                'Canvas API',
                'REST API',
                'PayPal API',
                'Shell',
                'XSLT',
                'Hack'
            ];

            const ranked = tags.sort((a, b) => {
                const aIndex = priority.indexOf(a);
                const bIndex = priority.indexOf(b);
                const aRank = aIndex === -1 ? Number.MAX_SAFE_INTEGER : aIndex;
                const bRank = bIndex === -1 ? Number.MAX_SAFE_INTEGER : bIndex;
                return aRank - bRank;
            });

            return ranked.slice(0, 4);
        }

        function deriveTechTags(sourceText, repoKey) {
            if (repoKey && repoStackOverrides[repoKey]) {
                return normalizeAndRankTags(repoStackOverrides[repoKey]);
            }

            const tags = [];
            techMatchers.forEach((matcher) => {
                if (matcher.test.test(sourceText) && !tags.includes(matcher.label)) {
                    tags.push(matcher.label);
                }
            });
            if (!tags.length) {
                return ['Web'];
            }
            return normalizeAndRankTags(tags);
        }

        grid.querySelectorAll('.portfolio-item').forEach((item) => {
            const content = item.querySelector('.content');
            const trigger = item.querySelector('[data-bs-toggle="modal"][data-bs-target]');
            if (!content || !trigger) {
                return;
            }

            const existing = content.querySelector('.portfolio-tech-chips');
            if (existing) {
                existing.remove();
            }

            const targetId = (trigger.getAttribute('data-bs-target') || '').trim();
            if (!targetId || targetId.charAt(0) !== '#') {
                return;
            }

            const modalId = targetId.slice(1);
            const modal = getModalById(modalId);
            const descriptionEl = modal ? modal.querySelector('.text-content p.margin-bottom-30') : null;
            const linksText = modal ? Array.from(modal.querySelectorAll('.text-content .button-group a')).map((a) => a.getAttribute('href') || '').join(' ') : '';
            const sourceText = `${descriptionEl ? descriptionEl.textContent || '' : ''} ${linksText}`.toLowerCase();
            const repoMatch = linksText.match(/https:\/\/github\.com\/([A-Za-z0-9_.-]+\/[A-Za-z0-9_.-]+)/i);
            const repoKey = repoMatch ? repoMatch[1] : '';

            const chips = deriveTechTags(sourceText, repoKey);
            const chipsWrap = doc.createElement('div');
            chipsWrap.className = 'portfolio-tech-chips';
            chipsWrap.setAttribute('aria-label', 'Technology stack');

            chips.forEach((chipText) => {
                const chip = doc.createElement('span');
                chip.className = 'portfolio-tech-chip';
                chip.textContent = chipText;
                chipsWrap.appendChild(chip);
            });

            content.appendChild(chipsWrap);
        });
    }

    /* ****************************
       Fix: taps inside scroll-snap carousels can be consumed by
       horizontal scrolling/inertia (or focus/scroll handling), requiring a second click.
       **************************** */
    function initScrollSnapCarouselTapActivation() {
        const TAP_DELTA_PX = 10;
        const TAP_MAX_MS = 500;

        let active = null;
        const suppressTrustedClickUntil = new WeakMap();

        doc.addEventListener('pointerdown', (event) => {
            if (!event.isPrimary) {
                return;
            }
            if (event.button != null && event.button !== 0) {
                return;
            }

            const target = event.target;
            if (!target || !target.closest) {
                return;
            }

            const carousel = target.closest('.scroll-snap-carousel');
            if (!carousel) {
                return;
            }

            active = {
                pointerId: event.pointerId,
                carousel,
                startX: event.clientX,
                startY: event.clientY,
                startTime: Date.now()
            };
        }, {
            capture: true,
            passive: true
        });

        // We force a click on pointerup to guarantee "one push".
        // Suppress the browser's subsequent trusted click so Bootstrap doesn't open twice.
        doc.addEventListener('click', (event) => {
            const target = event.target;
            if (!target || !target.closest) {
                return;
            }
            const trigger = target.closest('[data-bs-toggle="modal"][data-bs-target]');
            if (!trigger) {
                return;
            }

            if (event.isTrusted) {
                const until = suppressTrustedClickUntil.get(trigger) || 0;
                if (until > Date.now()) {
                    suppressTrustedClickUntil.delete(trigger);
                    event.preventDefault();
                    event.stopImmediatePropagation();
                    event.stopPropagation();
                }
                return;
            }

            // Ignore synthetic clicks.
            if (suppressTrustedClickUntil.has(trigger)) {
                event.preventDefault();
                event.stopImmediatePropagation();
                event.stopPropagation();
            }
        }, true);

        doc.addEventListener('pointerup', (event) => {
            if (!active) {
                return;
            }
            if (!event.isPrimary || event.pointerId !== active.pointerId) {
                return;
            }

            const target = event.target;
            const carousel = active.carousel;
            const startX = active.startX;
            const startY = active.startY;
            const startTime = active.startTime;
            active = null;

            if (!target || !target.closest || !carousel || !carousel.contains(target)) {
                return;
            }

            const dx = Math.abs(event.clientX - startX);
            const dy = Math.abs(event.clientY - startY);
            const dt = Date.now() - startTime;
            if (dx > TAP_DELTA_PX || dy > TAP_DELTA_PX || dt > TAP_MAX_MS) {
                return;
            }

            // Prefer the exact trigger clicked; otherwise fall back to the card's trigger.
            let trigger = target.closest('[data-bs-toggle="modal"][data-bs-target]');
            if (!trigger) {
                const item = target.closest('.portfolio-item, .blog-item');
                trigger = item ? item.querySelector('[data-bs-toggle="modal"][data-bs-target]') : null;
            }
            if (!trigger) {
                return;
            }

            suppressTrustedClickUntil.set(trigger, Date.now() + 750);
            trigger.click();
        }, true);
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
    initReadTimeIndicators(doc);
    initSectionEngagementTracking();
    initScrollDepthTracking();
    initConversionClickTracking();
    initFooterKpiRefresh();
    initContactForm();
    initChainedModalButtons();
    initPortfolioCardClicks();
    initPortfolioGridTechChips();
    initScrollSnapCarouselTapActivation();

    if (win.feather && typeof win.feather.replace === 'function') {
        win.feather.replace();
    }
    doc.querySelectorAll('i[data-feather]').forEach((icon) => {
        icon.setAttribute('aria-hidden', 'true');
    });
})();