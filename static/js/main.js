/**
 * ChurnGuard AI — Theme system & shared chart color tokens
 */
(function () {
    'use strict';

    const STORAGE_KEY = 'churnguard-theme';

    function getSystemTheme() {
        return window.matchMedia('(prefers-color-scheme: light)').matches ? 'light' : 'dark';
    }

    function getTheme() {
        return document.documentElement.getAttribute('data-theme') || 'dark';
    }

    function getCssVar(name) {
        return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
    }

    function getChartColors() {
        return {
            primary: getCssVar('--accent'),
            retained: getCssVar('--chart-retained'),
            churned: getCssVar('--chart-churned'),
            risk: getCssVar('--chart-risk'),
            success: getCssVar('--success'),
            danger: getCssVar('--danger'),
            warning: getCssVar('--warning'),
            info: getCssVar('--info'),
            grid: getCssVar('--chart-grid'),
            font: getCssVar('--chart-font'),
            onAccent: getCssVar('--text-on-accent'),
            palette: [
                getCssVar('--chart-palette-1'),
                getCssVar('--chart-palette-2'),
                getCssVar('--chart-palette-3'),
                getCssVar('--chart-palette-4'),
                getCssVar('--chart-palette-5'),
            ],
        };
    }

    function getPlotlyLayout(overrides) {
        const colors = getChartColors();
        const base = {
            paper_bgcolor: 'transparent',
            plot_bgcolor: 'transparent',
            font: { color: colors.font },
            margin: { t: 10, b: 40, l: 50, r: 10 },
            xaxis: { gridcolor: colors.grid, color: colors.font, zerolinecolor: colors.grid },
            yaxis: { gridcolor: colors.grid, color: colors.font, zerolinecolor: colors.grid },
        };
        return Object.assign({}, base, overrides || {});
    }

    function getFeatureImportanceColors(count) {
        const palette = getChartColors().palette;
        return Array.from({ length: count }, function (_, index) {
            return palette[Math.min(index, palette.length - 1)];
        });
    }

    function syncToggleInputs(theme) {
        document.querySelectorAll('.theme-toggle-input').forEach(function (input) {
            input.checked = theme === 'light';
            input.setAttribute('aria-checked', theme === 'light' ? 'true' : 'false');
        });
    }

    function applyTheme(theme, animate) {
        if (animate) {
            document.documentElement.classList.add('theme-transition');
        }

        document.documentElement.setAttribute('data-theme', theme);
        localStorage.setItem(STORAGE_KEY, theme);
        syncToggleInputs(theme);

        window.dispatchEvent(new CustomEvent('themechange', { detail: { theme: theme } }));

        if (animate) {
            window.setTimeout(function () {
                document.documentElement.classList.remove('theme-transition');
            }, 400);
        }
    }

    function initThemeFromStorage() {
        const stored = localStorage.getItem(STORAGE_KEY);
        const theme = stored || getSystemTheme();
        applyTheme(theme, false);
    }

    function bindThemeToggles() {
        document.querySelectorAll('.theme-toggle-input').forEach(function (input) {
            input.addEventListener('change', function () {
                applyTheme(input.checked ? 'light' : 'dark', true);
            });
        });
    }

    function onThemeChange(callback) {
        window.addEventListener('themechange', function (event) {
            callback(event.detail.theme);
        });
    }

    window.ChurnGuardTheme = {
        STORAGE_KEY: STORAGE_KEY,
        getTheme: getTheme,
        getChartColors: getChartColors,
        getPlotlyLayout: getPlotlyLayout,
        getFeatureImportanceColors: getFeatureImportanceColors,
        applyTheme: applyTheme,
        onThemeChange: onThemeChange,
    };

    document.addEventListener('DOMContentLoaded', function () {
        initThemeFromStorage();
        bindThemeToggles();
        initNavigation();
        initScrollReveal();
        initStatCounters();
    });

    function initNavigation() {
        var trigger = document.getElementById('profileTrigger');
        var menu = document.getElementById('profileMenu');
        if (trigger && menu) {
            trigger.addEventListener('click', function (e) {
                e.stopPropagation();
                menu.classList.toggle('open');
                trigger.setAttribute('aria-expanded', menu.classList.contains('open'));
            });
            document.addEventListener('click', function () { menu.classList.remove('open'); });
        }

        var mobileToggle = document.getElementById('navMobileToggle');
        var mobileOverlay = document.getElementById('navMobileOverlay');
        if (mobileToggle && mobileOverlay) {
            mobileToggle.addEventListener('click', function () {
                mobileOverlay.classList.toggle('open');
            });
            mobileOverlay.addEventListener('click', function (e) {
                if (e.target === mobileOverlay) mobileOverlay.classList.remove('open');
            });
        }

        var header = document.getElementById('siteHeader');
        if (header) {
            window.addEventListener('scroll', function () {
                header.classList.toggle('scrolled', window.scrollY > 8);
            }, { passive: true });
        }
    }

    function initScrollReveal() {
        var items = document.querySelectorAll('.reveal');
        if (!items.length) return;
        var observer = new IntersectionObserver(function (entries) {
            entries.forEach(function (entry) {
                if (entry.isIntersecting) {
                    entry.target.classList.add('visible');
                    observer.unobserve(entry.target);
                }
            });
        }, { threshold: 0.12, rootMargin: '0px 0px -40px 0px' });
        items.forEach(function (el) { observer.observe(el); });
    }

    function initStatCounters() {
        var statSection = document.querySelector('.stat-strip');
        if (!statSection) return;
        var started = false;
        var observer = new IntersectionObserver(function (entries) {
            if (!entries[0].isIntersecting || started) return;
            started = true;
            document.querySelectorAll('.stat-number[data-count]').forEach(function (el) {
                var target = parseFloat(el.dataset.count);
                var suffix = el.dataset.suffix || '';
                var decimals = parseInt(el.dataset.decimals || '0', 10);
                var duration = 1500;
                var start = Date.now();
                (function tick() {
                    var p = Math.min((Date.now() - start) / duration, 1);
                    var eased = 1 - Math.pow(1 - p, 3);
                    var val = target * eased;
                    el.textContent = (decimals ? val.toFixed(decimals) : Math.floor(val).toLocaleString()) + suffix;
                    if (p < 1) requestAnimationFrame(tick);
                })();
            });
        }, { threshold: 0.3 });
        observer.observe(statSection);
    }
})();
