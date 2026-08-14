(function () {
    'use strict';

    document.addEventListener('DOMContentLoaded', function () {
        fetch('/api/logs?limit=150', { credentials: 'include' }).then(function (r) {
            if (r.status === 401) {
                document.getElementById('logBody').innerHTML =
                    '<tr><td colspan="4" class="text-muted">Use browser basic auth (same as /logs page login).</td></tr>';
                return null;
            }
            return r.json();
        }).then(function (d) {
            if (!d) return;
            var lat = d.latency || {};
            document.getElementById('latencySummary').textContent =
                'Predict latency — avg: ' + (lat.avg_ms || 0) + ' ms · p95: ' + (lat.p95_ms || 0) +
                ' ms · samples: ' + (lat.sample_count || 0);
            var tbody = document.getElementById('logBody');
            var entries = d.entries || [];
            if (!entries.length) {
                tbody.innerHTML = '<tr><td colspan="4" class="text-muted">No log entries yet.</td></tr>';
                return;
            }
            tbody.innerHTML = entries.map(function (e) {
                return '<tr><td class="log-ts">' + e.timestamp + '</td><td>' + e.level +
                    '</td><td>' + e.logger + '</td><td class="log-msg">' + e.message + '</td></tr>';
            }).join('');
        });
    });
})();
