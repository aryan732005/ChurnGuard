(function () {
    'use strict';

    var chartColor = function () {
        return getComputedStyle(document.documentElement).getPropertyValue('--chart-line').trim() || '#2563EB';
    };

    var chartGrid = function () {
        return getComputedStyle(document.documentElement).getPropertyValue('--chart-grid').trim() || '#F3F4F6';
    };

    var chartFont = function () {
        return getComputedStyle(document.documentElement).getPropertyValue('--text-secondary').trim() || '#6B7280';
    };

    window.ChurnCharts = {
        layout: function (overrides) {
            return Object.assign({
                paper_bgcolor: 'transparent',
                plot_bgcolor: 'transparent',
                font: { family: 'Inter, system-ui', color: chartFont(), size: 12 },
                margin: { t: 24, b: 40, l: 48, r: 16 },
                xaxis: { gridcolor: chartGrid(), zeroline: false },
                yaxis: { gridcolor: chartGrid(), zeroline: false }
            }, overrides || {});
        },
        mono: chartColor
    };

    document.addEventListener('DOMContentLoaded', function () {
        if (window.lucide) lucide.createIcons();

        /* Theme toggle */
        var toggle = document.getElementById('themeToggle');
        var html = document.documentElement;
        var stored = localStorage.getItem('churn-theme');
        if (stored) html.setAttribute('data-theme', stored);

        if (toggle) {
            toggle.addEventListener('click', function () {
                var next = html.getAttribute('data-theme') === 'dark' ? 'light' : 'dark';
                html.setAttribute('data-theme', next);
                localStorage.setItem('churn-theme', next);
            });
        }

        /* Scroll reveal */
        var reveals = document.querySelectorAll('.reveal');
        if (reveals.length && 'IntersectionObserver' in window) {
            var obs = new IntersectionObserver(function (entries) {
                entries.forEach(function (e) {
                    if (e.isIntersecting) { e.target.classList.add('visible'); obs.unobserve(e.target); }
                });
            }, { threshold: 0.1 });
            reveals.forEach(function (el) { obs.observe(el); });
        } else {
            reveals.forEach(function (el) { el.classList.add('visible'); });
        }

        /* Command palette */
        var palette = document.getElementById('cmdPalette');
        var cmdToggle = document.getElementById('cmdToggle');
        var cmdBackdrop = document.getElementById('cmdBackdrop');
        var cmdInput = document.getElementById('cmdInput');

        function openCmd() {
            if (!palette) return;
            palette.hidden = false;
            if (cmdInput) cmdInput.focus();
        }
        function closeCmd() {
            if (palette) palette.hidden = true;
        }

        if (cmdToggle) cmdToggle.addEventListener('click', openCmd);
        if (cmdBackdrop) cmdBackdrop.addEventListener('click', closeCmd);
        document.addEventListener('keydown', function (e) {
            if ((e.metaKey || e.ctrlKey) && e.key === 'k') { e.preventDefault(); openCmd(); }
            if (e.key === 'Escape') closeCmd();
        });

        if (cmdInput) {
            cmdInput.addEventListener('input', function () {
                var q = cmdInput.value.toLowerCase();
                document.querySelectorAll('.cmd-list a').forEach(function (a) {
                    a.parentElement.style.display = a.textContent.toLowerCase().indexOf(q) >= 0 ? '' : 'none';
                });
            });
        }
    });
})();
