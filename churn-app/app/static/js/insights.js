(function () {
    'use strict';

    function pct(v) { return (v * 100).toFixed(1) + '%'; }
    function metricDisplay(m) {
        if (!m) return '—';
        if (typeof m === 'object' && m.display) return m.display;
        return pct(m);
    }
    function metricMean(m) {
        if (!m) return 0;
        return typeof m === 'object' ? (m.mean || 0) : m;
    }
    var errorsLoaded = false;

    function renderPerClass(pc) {
        var tbody = document.getElementById('perClassBody');
        if (!pc || !pc.retained) {
            tbody.innerHTML = '<tr><td colspan="5">Run train_model.py</td></tr>';
            return;
        }
        tbody.innerHTML = ['retained', 'churned'].map(function (cls) {
            var r = pc[cls];
            var label = cls === 'retained' ? 'Retained' : 'Churned';
            return '<tr><td><strong>' + label + '</strong></td><td>' + pct(r.precision) + '</td><td>' +
                pct(r.recall) + '</td><td>' + pct(r.f1_score) + '</td><td>' + r.support + '</td></tr>';
        }).join('');
    }

    function renderBaselineCompare(m) {
        var base = m.baseline || {};
        var best = m.best_test_metrics || {};
        document.getElementById('selectionNote').textContent = m.model_selection_note || '';
        document.getElementById('baselineCompare').innerHTML =
            '<div class="card flat"><div class="card-title">Baseline (majority class)</div>' +
            '<div class="card-value" style="font-size:24px">' + pct(base.accuracy || 0.7) + '</div>' +
            '<p class="text-sm text-muted">Accuracy only · always predicts "stay"</p></div>' +
            '<div class="card flat"><div class="card-title">' + (m.best_model || 'Best model') + '</div>' +
            '<div class="card-value" style="font-size:24px">' + metricDisplay(best.roc_auc) + '</div>' +
            '<p class="text-sm text-muted">ROC AUC (mean ± std) · ' + metricDisplay(best.f1_score) + ' F1</p></div>';
    }

    function renderCalibration(cal) {
        if (!cal || !cal.before) return;
        var method = cal.method || 'isotonic';
        document.getElementById('calibrationNote').textContent =
            'Calibration method: ' + method + '. Brier score: ' +
            (cal.brier_before || 0).toFixed(4) + ' → ' + (cal.brier_after || 0).toFixed(4) + '.';
        document.getElementById('calibrationRoiNote').textContent = cal.roi_note || '';

        Plotly.newPlot('calibrationChart', [
            {
                x: cal.before.predicted_mean, y: cal.before.observed_rate,
                name: 'Before', type: 'scatter', mode: 'lines+markers',
                line: { color: '#9CA3AF', dash: 'dot' }
            },
            {
                x: cal.after.predicted_mean, y: cal.after.observed_rate,
                name: 'After (' + method + ')', type: 'scatter', mode: 'lines+markers',
                line: { color: ChurnCharts.mono(), width: 2 }
            },
            { x: [0, 1], y: [0, 1], name: 'Perfect', type: 'scatter', mode: 'lines', line: { dash: 'dash', color: '#D1D5DB' } }
        ], ChurnCharts.layout({ xaxis: { title: 'Predicted probability' }, yaxis: { title: 'Observed churn rate' }, legend: { orientation: 'h' } }),
        { displayModeBar: false, responsive: true });
    }

    function renderFairness(fairness) {
        document.getElementById('fairnessNote').textContent = fairness.note || '';
        var wrap = document.getElementById('fairnessTables');
        var segments = ['gender', 'contract', 'senior_citizen', 'tenure'];
        var labels = { gender: 'Gender', contract: 'Contract type', senior_citizen: 'Senior status', tenure: 'Tenure band' };
        wrap.innerHTML = segments.filter(function (s) { return fairness[s]; }).map(function (seg) {
            var rows = Object.keys(fairness[seg]).map(function (k) {
                var g = fairness[seg][k];
                return '<tr><td>' + k + '</td><td>' + g.count + '</td><td>' + pct(g.accuracy) +
                    '</td><td>' + pct(g.f1_score) + '</td><td>' + pct(g.error_rate) + '</td></tr>';
            }).join('');
            return '<div class="card flat" style="margin-bottom:16px"><h3>' + labels[seg] + '</h3>' +
                '<div class="table-wrap"><table><thead><tr><th>Segment</th><th>N</th><th>Accuracy</th><th>F1</th><th>Error rate</th></tr></thead>' +
                '<tbody>' + rows + '</tbody></table></div></div>';
        }).join('');
    }

    function renderRoc(roc) {
        if (!roc.fpr) return;
        Plotly.newPlot('rocChart', [
            { x: roc.fpr, y: roc.tpr, type: 'scatter', mode: 'lines', name: roc.model || 'Model', line: { color: ChurnCharts.mono(), width: 2 } },
            { x: [0, 1], y: [0, 1], type: 'scatter', mode: 'lines', name: 'Random', line: { dash: 'dash', color: '#9CA3AF' } }
        ], ChurnCharts.layout({ xaxis: { title: 'FPR' }, yaxis: { title: 'TPR' }, legend: { orientation: 'h' } }), { displayModeBar: false, responsive: true });
    }

    function renderErrorCases(cases, note) {
        document.getElementById('errorExplainNote').textContent = note || '';
        var wrap = document.getElementById('errorCases');
        if (!cases.length) {
            wrap.innerHTML = '<p class="text-muted">No error analysis data.</p>';
            return;
        }
        wrap.innerHTML = cases.map(function (c, i) {
            var typeLabel = c.case_type === 'false_positive' ? 'False positive' : 'False negative';
            var badge = c.case_type === 'false_positive' ? 'badge-medium' : 'badge-high';
            return '<div class="card error-case-card"><span class="badge ' + badge + '">' + typeLabel + '</span>' +
                '<p class="text-sm" style="margin:12px 0">' + c.explanation + '</p>' +
                '<p class="text-sm text-muted">Prob ' + c.probability + '% · ' + c.attributes.contract + ' · ' + c.attributes.tenure + ' mo</p>' +
                '<div id="errChart' + i + '" class="chart-container" style="min-height:140px;margin-top:8px"></div></div>';
        }).join('');
        cases.forEach(function (c, i) {
            var el = document.getElementById('errChart' + i);
            if (!el || !c.shap_factors.length) return;
            Plotly.newPlot(el, [{
                y: c.shap_factors.map(function (f) { return f.feature; }).reverse(),
                x: c.shap_factors.map(function (f) { return Math.abs(f.impact); }).reverse(),
                type: 'bar', orientation: 'h', marker: { color: ChurnCharts.mono(), opacity: 0.85 }
            }], ChurnCharts.layout({ margin: { l: 130, t: 4, b: 20, r: 4 }, showlegend: false }), { displayModeBar: false, responsive: true });
        });
    }

    function loadErrors() {
        if (errorsLoaded) return;
        errorsLoaded = true;
        fetch('/api/error-analysis').then(function (r) { return r.json(); }).then(function (d) {
            renderErrorCases(d.cases || [], d.explainability_note || d.note);
        });
    }

    document.addEventListener('DOMContentLoaded', function () {
        fetch('/api/metrics').then(function (r) { return r.json(); }).then(function (m) {
            var best = m.best_test_metrics || {};
            var lat = m.latency || {};
            var mv = m.model_version || {};
            document.getElementById('modelVersionBadge').textContent = 'Live: ' + (mv.version || '—') + ' · ' + (mv.date || '');
            var hist = mv.history || (mv.version ? [mv] : []);
            document.getElementById('versionBody').innerHTML = hist.length ? hist.slice().reverse().map(function (v) {
                var delta = v.roc_auc_delta != null ? (v.roc_auc_delta >= 0 ? '+' : '') + v.roc_auc_delta : '—';
                return '<tr><td>' + v.version + '</td><td>' + v.date + '</td><td>' + v.roc_auc + '</td><td>' + delta + '</td></tr>';
            }).join('') : '<tr><td colspan="4" class="text-muted">No version history</td></tr>';

            document.getElementById('metricCards').innerHTML =
                '<div class="card"><div class="card-title">ROC AUC</div><div class="card-value">' + metricDisplay(best.roc_auc) + '</div><p class="text-sm text-muted">mean ± std</p></div>' +
                '<div class="card"><div class="card-title">PR-AUC</div><div class="card-value">' + metricDisplay(best.pr_auc) + '</div><p class="text-sm text-muted">better at ~30% churn</p></div>' +
                '<div class="card"><div class="card-title">Churn recall</div><div class="card-value">' + metricDisplay(best.recall) + '</div></div>' +
                '<div class="card"><div class="card-title">Churn F1</div><div class="card-value">' + metricDisplay(best.f1_score) + '</div></div>';

            document.getElementById('dataIntegrityNote').textContent = m.data_integrity_note || m.leakage_audit_summary || 'Run train_model.py for leakage audit.';

            renderBaselineCompare(m);
            renderCalibration(m.calibration || {});

            var th = m.threshold_optimization || {};
            document.getElementById('thresholdReasoning').textContent = th.reasoning || '';
            document.getElementById('optThreshVal').textContent = th.optimal_threshold != null ? th.optimal_threshold.toFixed(2) : '—';
            if (th.optimal_threshold) {
                document.getElementById('threshSlider').value = Math.round(th.optimal_threshold * 100);
            }

            var meth = m.methodology || {};
            var v = m.validation || {};
            document.getElementById('methodologyList').innerHTML = [
                '<li><strong>Train/test split:</strong> ' + (meth.train_test_split || v.train_test_split || '80/20 stratified hold-out') + '</li>',
                '<li><strong>Cross-validation:</strong> ' + (meth.cv_folds || v.cv_folds || 5) + '-fold stratified CV on training set</li>',
                '<li><strong>Class imbalance (~30% churn):</strong> ' + (meth.imbalance_method || v.imbalance_method || 'class_weight') + ' — ' + (meth.imbalance_rationale || v.imbalance_rationale || '') + '</li>',
                '<li><strong>Variance check:</strong> ' + ((m.variance && m.variance.note) || 'Multi-seed hold-out splits') + '</li>',
                '<li><strong>Threshold:</strong> Cost-based optimisation (not fixed 0.5)</li>',
            ].join('');

            document.getElementById('imbalanceText').textContent = (v.imbalance_rationale || '') +
                (v.class_distribution ? ' (' + v.class_distribution.retained_pct + '% retained / ' + v.class_distribution.churned_pct + '% churned)' : '');
            renderPerClass(m.per_class);

            document.getElementById('modelBody').innerHTML = Object.keys(m.model_results || {}).map(function (name) {
                var r = m.model_results[name];
                var hl = name === m.best_model ? ' style="font-weight:600"' : '';
                return '<tr' + hl + '><td>' + name + '</td><td>' + pct(r.accuracy) + '</td><td>' + pct(r.precision) +
                    '</td><td>' + pct(r.recall) + '</td><td>' + pct(r.f1_score) + '</td><td>' + pct(r.roc_auc) +
                    '</td><td>' + pct(r.pr_auc || 0) + '</td></tr>';
            }).join('');

            var cm = m.confusion_matrix;
            Plotly.newPlot('cmChart', [{
                z: cm, x: ['Pred stay', 'Pred churn'], y: ['Actual stay', 'Actual churn'],
                type: 'heatmap', colorscale: [[0, '#F3F4F6'], [0.5, '#93C5FD'], [1, '#2563EB']],
                showscale: false, text: cm.map(function (row) { return row.map(String); }), texttemplate: '%{text}'
            }], ChurnCharts.layout({ margin: { l: 90, b: 50 } }), { displayModeBar: false, responsive: true });

            renderRoc(m.roc_curve || {});
            renderFairness(m.fairness || {});

            fetch('/api/feature-importance').then(function (r) { return r.json(); }).then(function (fi) {
                var feats = (fi.features || []).slice(0, 12).reverse();
                if (!feats.length || !document.getElementById('featureImportanceChart')) return;
                Plotly.newPlot('featureImportanceChart', [{
                    y: feats.map(function (f) { return f.feature; }),
                    x: feats.map(function (f) { return f.importance; }),
                    type: 'bar', orientation: 'h',
                    marker: { color: ChurnCharts.mono(), opacity: 0.85 }
                }], ChurnCharts.layout({ margin: { l: 180 } }), { displayModeBar: false, responsive: true });
            });

            if (th.cost_curve && th.cost_curve.length) {
                Plotly.newPlot('costChart', [{
                    x: th.cost_curve.map(function (p) { return p.threshold; }),
                    y: th.cost_curve.map(function (p) { return p.expected_cost; }),
                    type: 'scatter', mode: 'lines', name: 'Expected cost',
                    line: { color: ChurnCharts.mono() }
                }], ChurnCharts.layout({ xaxis: { title: 'Threshold' }, yaxis: { title: 'Expected cost ($)' } }),
                { displayModeBar: false, responsive: true });
            }
        });

        var slider = document.getElementById('threshSlider');
        function updateThresh() {
            var t = slider.value / 100;
            document.getElementById('threshVal').textContent = t.toFixed(2);
            fetch('/api/threshold?threshold=' + t).then(function (r) { return r.json(); }).then(function (data) {
                Plotly.newPlot('threshChart', [
                    { x: data.curve.map(function (p) { return p.threshold; }), y: data.curve.map(function (p) { return p.precision; }), name: 'Precision', type: 'scatter', line: { color: ChurnCharts.mono() } },
                    { x: data.curve.map(function (p) { return p.threshold; }), y: data.curve.map(function (p) { return p.recall; }), name: 'Recall', type: 'scatter', line: { color: '#9CA3AF', dash: 'dot' } }
                ], ChurnCharts.layout({ legend: { orientation: 'h' } }), { displayModeBar: false, responsive: true });
            });
        }
        slider.addEventListener('input', updateThresh);
        updateThresh();

        window.addEventListener('disclosure:open', function (e) {
            if (e.detail.id === 'disc-errors') loadErrors();
        });
    });
})();
