(function () {
    'use strict';

    var tableData = [];

    function badgeClass(risk) {
        return 'badge badge-' + (risk || 'low').toLowerCase();
    }

    function renderTable(rows) {
        tableData = rows || [];
        var tbody = document.getElementById('riskBody');
        if (!rows.length) {
            tbody.innerHTML = '<tr><td colspan="7" class="text-muted">No data</td></tr>';
            return;
        }
        tbody.innerHTML = rows.map(function (r) {
            return '<tr><td>' + r.customer_id + '</td><td>' + r.contract + '</td><td>' + r.tenure +
                '</td><td>$' + r.monthly_charges + '</td><td>' + r.churn_probability + '%</td><td><span class="' +
                badgeClass(r.risk_level) + '">' + r.risk_level + '</span></td><td class="text-sm">' +
                (r.recommended_action || '—') + '</td></tr>';
        }).join('');
    }

    function renderSummary(s, rev) {
        document.getElementById('summaryCards').innerHTML =
            '<div class="card"><div class="card-title">Customers</div><div class="card-value">' + s.total + '</div></div>' +
            '<div class="card"><div class="card-title">Churn rate</div><div class="card-value">' + s.churn_rate + '%</div></div>' +
            '<div class="card"><div class="card-title">High risk</div><div class="card-value">' + s.high_risk_count + '</div></div>' +
            '<div class="card"><div class="card-title">Revenue at risk</div><div class="card-value">$' + rev.toLocaleString() + '</div></div>';
        document.getElementById('roiAtRisk').value = s.high_risk_count || 10;
        updateRoi();
    }

    function updateRoi() {
        var body = {
            at_risk_count: parseInt(document.getElementById('roiAtRisk').value, 10) || 0,
            avg_monthly_revenue: parseFloat(document.getElementById('roiRevenue').value) || 0,
            offer_cost: parseFloat(document.getElementById('roiOffer').value) || 0,
            lifetime_months: parseFloat(document.getElementById('roiLifetime').value) || 24,
            success_rate_pct: parseFloat(document.getElementById('roiSuccess').value) || 25,
        };
        fetch('/api/roi', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body),
        }).then(function (r) { return r.json(); }).then(function (d) {
            document.getElementById('roiRetained').textContent = d.estimated_retained;
            document.getElementById('roiGross').textContent = '$' + d.gross_revenue_saved.toLocaleString();
            document.getElementById('roiNet').textContent = '$' + d.net_savings.toLocaleString();
            var note = 'Decision threshold: ' + (d.threshold || 0.5).toFixed(2) +
                ' · FP cost $' + (d.fp_cost_assumption || body.offer_cost) +
                ' · FN cost $' + (d.fn_cost_assumption || 0).toLocaleString();
            if (d.calibration_note) note += '. ' + d.calibration_note;
            document.getElementById('roiCalibNote').textContent = note;
        });
    }

    function renderDrift(drift) {
        var pill = document.getElementById('driftPill');
        var status = drift.overall_status || 'unknown';
        pill.textContent = status.charAt(0).toUpperCase() + status.slice(1);
        pill.className = 'drift-pill drift-' + status;
        document.getElementById('driftNote').textContent = drift.note || '';
        var tbody = document.getElementById('driftBody');
        var feats = drift.features || [];
        if (!feats.length) {
            tbody.innerHTML = '<tr><td colspan="4" class="text-muted">No drift data — upload batch CSV on /batch</td></tr>';
            return;
        }
        tbody.innerHTML = feats.map(function (f) {
            return '<tr><td>' + f.feature + '</td><td>' + f.psi + '</td><td>' +
                (f.ks_statistic != null ? f.ks_statistic : '—') + '</td><td><span class="drift-pill drift-' +
                f.status + '">' + f.status + '</span></td></tr>';
        }).join('');
    }

    function loadDrift() {
        fetch('/api/drift-status').then(function (r) { return r.json(); }).then(renderDrift);
    }

    function loadDashboard() {
        var contract = document.getElementById('filterContract').value;
        var tMin = document.getElementById('filterTenureMin').value;
        var tMax = document.getElementById('filterTenureMax').value;
        var q = '?contract=' + encodeURIComponent(contract) + '&tenure_min=' + tMin + '&tenure_max=' + tMax;

        fetch('/api/dashboard-data' + q).then(function (r) { return r.json(); }).then(function (data) {
            renderSummary(data.summary, data.revenue_at_risk);
            renderTable(data.risk_table);
            document.querySelectorAll('.skeleton').forEach(function (el) { el.classList.remove('skeleton'); });

            Plotly.newPlot('trendChart', [{
                x: data.churn_trend.map(function (t) { return t.period; }),
                y: data.churn_trend.map(function (t) { return t.churn_rate; }),
                type: 'scatter', mode: 'lines+markers',
                line: { color: ChurnCharts.mono(), width: 2 },
                marker: { size: 6, color: ChurnCharts.mono() }
            }], ChurnCharts.layout({ yaxis: { title: 'Churn rate (%)' } }), { displayModeBar: false, responsive: true });
        });

        fetch('/api/feature-importance').then(function (r) { return r.json(); }).then(function (data) {
            var feats = (data.features || []).slice().reverse();
            Plotly.newPlot('importanceChart', [{
                y: feats.map(function (f) { return f.feature; }),
                x: feats.map(function (f) { return f.importance; }),
                type: 'bar', orientation: 'h',
                marker: { color: ChurnCharts.mono(), opacity: 0.85 }
            }], ChurnCharts.layout({ margin: { l: 160 } }), { displayModeBar: false, responsive: true });
        });
    }

    document.addEventListener('DOMContentLoaded', function () {
        fetch('/api/metrics').then(function (r) { return r.json(); }).then(function (m) {
            var ds = m.dataset || {};
            var records = ds.records || m.total_customers || 7043;
            document.getElementById('dashDataSource').textContent =
                'Data source: ' + (ds.name || 'Telco Customer Churn') + ' (' + records.toLocaleString() +
                ' records) — public benchmark, not live production data';
        });
        loadDashboard();
        loadDrift();
        document.getElementById('applyFilters').addEventListener('click', loadDashboard);

        ['roiAtRisk', 'roiRevenue', 'roiOffer', 'roiLifetime'].forEach(function (id) {
            document.getElementById(id).addEventListener('input', updateRoi);
        });
        document.getElementById('roiSuccess').addEventListener('input', function () {
            document.getElementById('roiSuccessVal').textContent = this.value;
            updateRoi();
        });

        document.querySelectorAll('#riskTable th[data-sort]').forEach(function (th) {
            th.style.cursor = 'pointer';
            th.addEventListener('click', function () {
                var key = th.dataset.sort;
                var asc = th.dataset.asc !== 'true';
                tableData.sort(function (a, b) {
                    var va = a[key], vb = b[key];
                    if (typeof va === 'string') return asc ? va.localeCompare(vb) : vb.localeCompare(va);
                    return asc ? va - vb : vb - va;
                });
                th.dataset.asc = asc;
                renderTable(tableData);
            });
        });

        var cohortSlider = document.getElementById('cohortPct');
        function updateCohort() {
            var pct = parseInt(cohortSlider.value, 10);
            document.getElementById('cohortPctVal').textContent = pct;
            fetch('/api/cohort-simulation', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ retain_pct: pct, months: 6, success_rate_pct: 25 }),
            }).then(function (r) { return r.json(); }).then(function (d) {
                Plotly.newPlot('cohortChart', [
                    { x: d.months, y: d.do_nothing, name: 'Do nothing', type: 'scatter', mode: 'lines', line: { color: '#9CA3AF', dash: 'dot' } },
                    { x: d.months, y: d.retain, name: 'Retain top ' + pct + '%', type: 'scatter', mode: 'lines', line: { color: ChurnCharts.mono(), width: 2 } },
                ], ChurnCharts.layout({ xaxis: { title: 'Month' }, yaxis: { title: 'Cumulative revenue at risk ($)' }, legend: { orientation: 'h' } }),
                { displayModeBar: false, responsive: true });
            });
        }
        if (cohortSlider) {
            cohortSlider.addEventListener('input', updateCohort);
            updateCohort();
        }
    });
})();
