(function () {
    'use strict';

    var rows = [];
    var selected = new Set();
    var currentPage = 1;
    var totalPages = 1;
    var totalCount = 0;
    var PAGE_SIZE = 20;

    function pct(v) { return (Number(v) * 100).toFixed(1) + '%'; }

    function statusBadge(s) {
        var c = s === 'failed' ? 'badge-high' : s === 'running' ? 'badge-medium' : 'badge-low';
        return '<span class="badge ' + c + '">' + (s || 'completed') + '</span>';
    }

    function showError(msg) {
        var el = document.getElementById('expAlert');
        el.textContent = msg;
        el.classList.remove('hidden');
    }

    function loadExperiments() {
        var model = document.getElementById('filterModel').value.trim();
        var dateFrom = document.getElementById('filterDate').value;
        var q = '?model_type=' + encodeURIComponent(model) + '&date_from=' + encodeURIComponent(dateFrom) +
            '&page=' + currentPage + '&page_size=' + PAGE_SIZE;

        document.getElementById('expLoading').hidden = false;
        document.getElementById('expTableWrap').hidden = true;
        document.getElementById('expEmpty').classList.add('hidden');
        document.getElementById('expAlert').classList.add('hidden');

        fetch('/api/experiments' + q)
            .then(function (r) {
                if (!r.ok) throw new Error('Failed to load experiments (' + r.status + ')');
                return r.json();
            })
            .then(function (d) {
                document.getElementById('expLoading').hidden = true;
                rows = d.runs || [];
                totalCount = d.count || rows.length;
                totalPages = d.total_pages || 1;
                currentPage = d.page || 1;
                selected.clear();
                updateCompareBtn();
                updatePagination();
                if (!rows.length && totalCount === 0) {
                    document.getElementById('expEmpty').classList.remove('hidden');
                    document.getElementById('expTableWrap').hidden = true;
                    document.getElementById('expPagination').hidden = true;
                    return;
                }
                document.getElementById('expEmpty').classList.add('hidden');
                document.getElementById('expTableWrap').hidden = false;
                renderTable();
            })
            .catch(function (e) {
                document.getElementById('expLoading').hidden = true;
                showError(e.message || 'Could not load experiments.');
            });
    }

    function renderTable() {
        var tbody = document.getElementById('expBody');
        tbody.innerHTML = rows.map(function (r) {
            var id = r.full_run_id || r.run_id;
            var checked = selected.has(id) ? ' checked' : '';
            return '<tr data-run="' + id + '" class="exp-row" style="cursor:pointer">' +
                '<td><input type="checkbox" class="exp-select" data-id="' + id + '"' + checked + ' aria-label="Select run ' + r.model_type + '"></td>' +
                '<td><strong>' + r.model_type + '</strong>' + (r.is_best ? ' <span class="badge badge-low">best</span>' : '') + '</td>' +
                '<td>' + r.date + '</td>' +
                '<td>' + pct(r.roc_auc) + '</td>' +
                '<td>' + pct(r.pr_auc || 0) + '</td>' +
                '<td>' + pct(r.precision) + '</td>' +
                '<td>' + pct(r.recall) + '</td>' +
                '<td>' + pct(r.f1_score) + '</td>' +
                '<td>' + statusBadge(r.status) + '</td>' +
                '<td><button type="button" class="btn btn-secondary btn-sm exp-view" data-id="' + id + '">View</button></td></tr>';
        }).join('');

        tbody.querySelectorAll('.exp-select').forEach(function (cb) {
            cb.addEventListener('click', function (e) { e.stopPropagation(); toggleSelect(cb.dataset.id, cb.checked); });
        });
        tbody.querySelectorAll('.exp-view').forEach(function (btn) {
            btn.addEventListener('click', function (e) { e.stopPropagation(); openDetail(btn.dataset.id); });
        });
        tbody.querySelectorAll('.exp-row').forEach(function (tr) {
            tr.addEventListener('click', function () { openDetail(tr.dataset.run); });
        });
    }

    function toggleSelect(id, on) {
        if (on) {
            if (selected.size >= 3) { return; }
            selected.add(id);
        } else {
            selected.delete(id);
        }
        if (selected.size > 3) {
            selected.delete(id);
        }
        updateCompareBtn();
        renderTable();
    }

    function updatePagination() {
        var nav = document.getElementById('expPagination');
        if (totalCount <= PAGE_SIZE) {
            nav.hidden = true;
            return;
        }
        nav.hidden = false;
        document.getElementById('expPageInfo').textContent =
            'Page ' + currentPage + ' of ' + totalPages + ' (' + totalCount + ' runs)';
        document.getElementById('expPrev').disabled = currentPage <= 1;
        document.getElementById('expNext').disabled = currentPage >= totalPages;
    }

    function updateCompareBtn() {
        var btn = document.getElementById('compareBtn');
        btn.textContent = 'Compare selected (' + selected.size + ')';
        btn.disabled = selected.size < 2;
    }

    function openDetail(runId) {
        fetch('/api/experiments/' + encodeURIComponent(runId))
            .then(function (r) {
                if (!r.ok) throw new Error('Run not found');
                return r.json();
            })
            .then(showDetail)
            .catch(function () { showError('Could not load experiment detail.'); });
    }

    function showDetail(d) {
        document.getElementById('detailPanel').hidden = false;
        document.getElementById('detailTitle').textContent = d.model_type;
        document.getElementById('detailSubtitle').textContent = d.date + ' · ' + (d.source || 'mlflow') + ' · ' + d.status;
        document.getElementById('detailMetrics').innerHTML =
            ['roc_auc', 'pr_auc', 'precision', 'recall', 'f1_score'].map(function (k) {
                var label = k === 'pr_auc' ? 'PR-AUC' : k.replace('_', ' ');
                return '<div class="card flat"><div class="card-title">' + label + '</div><div class="card-value">' + pct(d[k] || 0) + '</div></div>';
            }).join('');
        document.getElementById('detailParams').textContent = JSON.stringify(d.hyperparameters || d.params || {}, null, 2);
        var pc = d.per_class || {};
        document.getElementById('detailPerClass').innerHTML = pc.retained ?
            '<div>Retained F1: ' + pct(pc.retained.f1_score) + '</div><div>Churned F1: ' + pct(pc.churned.f1_score) + '</div>' : '—';
        document.getElementById('detailNote').textContent = d.note || '';

        if (d.roc_curve && d.roc_curve.fpr) {
            Plotly.newPlot('detailRoc', [{
                x: d.roc_curve.fpr, y: d.roc_curve.tpr, type: 'scatter', mode: 'lines',
                line: { color: ChurnCharts.mono(), width: 2 }
            }], ChurnCharts.layout({ margin: { t: 8 } }), { displayModeBar: false, responsive: true });
        } else {
            document.getElementById('detailRoc').innerHTML = '<p class="text-sm text-muted">ROC not available for this run.</p>';
        }

        if (d.pr_curve && d.pr_curve.recall) {
            Plotly.newPlot('detailPr', [{
                x: d.pr_curve.recall, y: d.pr_curve.precision, type: 'scatter', mode: 'lines',
                line: { color: ChurnCharts.mono(), width: 2 }
            }], ChurnCharts.layout({ margin: { t: 8 }, xaxis: { title: 'Recall' }, yaxis: { title: 'Precision' } }),
            { displayModeBar: false, responsive: true });
        } else {
            document.getElementById('detailPr').innerHTML = '<p class="text-sm text-muted">PR curve not available for this run.</p>';
        }

        if (d.confusion_matrix) {
            var cm = d.confusion_matrix;
            Plotly.newPlot('detailCm', [{
                z: cm, x: ['Pred stay', 'Pred churn'], y: ['Actual stay', 'Actual churn'],
                type: 'heatmap', colorscale: [[0, '#F3F4F6'], [0.5, '#93C5FD'], [1, '#2563EB']],
                showscale: false, text: cm.map(function (row) { return row.map(String); }), texttemplate: '%{text}'
            }], ChurnCharts.layout({ margin: { l: 90, b: 50, t: 8 } }), { displayModeBar: false, responsive: true });
        } else {
            document.getElementById('detailCm').innerHTML = '<p class="text-sm text-muted">Confusion matrix not available.</p>';
        }
        document.getElementById('detailPanel').scrollIntoView({ behavior: 'smooth', block: 'start' });
    }

    function runCompare() {
        if (selected.size < 2) return;
        fetch('/api/experiments/compare', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ run_ids: Array.from(selected) }),
        }).then(function (r) { return r.json(); }).then(function (d) {
            var runs = d.runs || [];
            document.getElementById('comparePanel').hidden = false;
            for (var i = 0; i < 3; i++) {
                document.getElementById('cmpCol' + i).textContent = runs[i] ? runs[i].model_type : '—';
            }
            var metrics = ['roc_auc', 'pr_auc', 'precision', 'recall', 'f1_score', 'accuracy'];
            document.getElementById('compareBody').innerHTML = metrics.map(function (m) {
                var label = m === 'pr_auc' ? 'PR-AUC' : m;
                var cells = runs.map(function (r) { return '<td>' + (r ? pct(r[m]) : '—') + '</td>'; });
                while (cells.length < 3) cells.push('<td>—</td>');
                return '<tr><td>' + label + '</td>' + cells.join('') + '</tr>';
            }).join('');
        });
    }

    document.addEventListener('DOMContentLoaded', function () {
        fetch('/api/metrics').then(function (r) { return r.json(); }).then(function (m) {
            var meth = m.methodology || m.validation || {};
            document.getElementById('expMethodology').textContent =
                'Methodology: ' + (meth.train_test_split || '80/20 stratified') + ' · ' +
                (meth.cv_folds || 5) + '-fold stratified CV · imbalance: ' +
                (meth.imbalance_method || 'class_weight') + ' (not SMOTE) · PR-AUC shown for imbalanced churn';
        });
        loadExperiments();
        document.getElementById('applyFilters').addEventListener('click', function () {
            currentPage = 1;
            loadExperiments();
        });
        document.getElementById('expPrev').addEventListener('click', function () {
            if (currentPage > 1) { currentPage -= 1; loadExperiments(); }
        });
        document.getElementById('expNext').addEventListener('click', function () {
            if (currentPage < totalPages) { currentPage += 1; loadExperiments(); }
        });
        document.getElementById('compareBtn').addEventListener('click', runCompare);
        document.getElementById('selectAll').addEventListener('change', function () {
            selected.clear();
            if (this.checked) {
                rows.slice(0, 3).forEach(function (r) { selected.add(r.full_run_id || r.run_id); });
            }
            updateCompareBtn();
            renderTable();
        });

        document.querySelectorAll('#expTable th[data-sort]').forEach(function (th) {
            th.style.cursor = 'pointer';
            th.addEventListener('click', function () {
                var key = th.dataset.sort;
                var asc = th.dataset.asc !== 'true';
                rows.sort(function (a, b) {
                    var va = a[key], vb = b[key];
                    if (typeof va === 'string') return asc ? va.localeCompare(vb) : vb.localeCompare(va);
                    return asc ? va - vb : vb - va;
                });
                th.dataset.asc = asc;
                renderTable();
            });
        });

        var params = new URLSearchParams(window.location.search);
        var run = params.get('run');
        if (run) openDetail(run);
    });
})();
