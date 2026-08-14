(function () {
    'use strict';

    document.addEventListener('DOMContentLoaded', function () {
        document.querySelectorAll('.disclosure-trigger').forEach(function (btn) {
            btn.addEventListener('click', function () {
                var panel = document.getElementById(btn.dataset.target);
                if (!panel) return;
                var open = panel.classList.toggle('open');
                btn.setAttribute('aria-expanded', open ? 'true' : 'false');
                if (open && panel.dataset.onOpen) {
                    window.dispatchEvent(new CustomEvent('disclosure:open', {
                        detail: { id: panel.id }
                    }));
                }
                if (window.lucide) lucide.createIcons();
            });
        });

        document.querySelectorAll('[data-tab-group]').forEach(function (group) {
            var tabs = group.querySelectorAll('[data-tab]');
            tabs.forEach(function (tab) {
                tab.addEventListener('click', function () {
                    var name = tab.dataset.tab;
                    tabs.forEach(function (t) { t.classList.toggle('active', t.dataset.tab === name); });
                    group.querySelectorAll('[data-tab-panel]').forEach(function (p) {
                        p.classList.toggle('active', p.dataset.tabPanel === name);
                    });
                });
            });
        });
    });
})();
