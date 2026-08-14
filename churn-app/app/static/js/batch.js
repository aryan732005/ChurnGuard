(function () {
    'use strict';

    function showErrors(container, errors) {
        var el = document.getElementById(container);
        if (!el) return;
        el.classList.remove('hidden');
        el.innerHTML = '<strong>Please fix the following:</strong><ul>' +
            errors.map(function (e) { return '<li>' + e + '</li>'; }).join('') + '</ul>';
    }

    function hideErrors(container) {
        var el = document.getElementById(container);
        if (el) el.classList.add('hidden');
    }

    function parseApiErrors(res) {
        return res.json().then(function (data) {
            if (data.detail && data.detail.errors) return data.detail.errors;
            if (typeof data.detail === 'string') return [data.detail];
            return ['Request failed. Please try again.'];
        });
    }

    var csvData = null;

    document.addEventListener('DOMContentLoaded', function () {
        var zone = document.getElementById('uploadZone');
        var input = document.getElementById('csvFile');
        var progress = document.getElementById('batchProgress');
        var results = document.getElementById('batchResults');

        zone.addEventListener('click', function () { input.click(); });
        zone.addEventListener('dragover', function (e) { e.preventDefault(); zone.classList.add('dragover'); });
        zone.addEventListener('dragleave', function () { zone.classList.remove('dragover'); });
        zone.addEventListener('drop', function (e) {
            e.preventDefault();
            zone.classList.remove('dragover');
            if (e.dataTransfer.files.length) upload(e.dataTransfer.files[0]);
        });
        input.addEventListener('change', function () {
            if (input.files.length) upload(input.files[0]);
        });

        function upload(file) {
            hideErrors('batchErrors');
            var fd = new FormData();
            fd.append('file', file);
            progress.style.display = 'block';
            results.style.display = 'none';

            fetch('/api/batch-predict', { method: 'POST', body: fd })
                .then(function (r) {
                    if (!r.ok) return parseApiErrors(r).then(function (errs) { throw errs; });
                    return r.json();
                })
                .then(function (data) {
                    progress.style.display = 'none';
                    results.style.display = 'block';
                    csvData = data.csv;
                    renderTable(data.data, data.columns);
                })
                .catch(function (err) {
                    progress.style.display = 'none';
                    showErrors('batchErrors', Array.isArray(err) ? err : ['Upload failed.']);
                });
        }

        document.getElementById('downloadCsv').addEventListener('click', function () {
            if (!csvData) return;
            var blob = new Blob([csvData], { type: 'text/csv' });
            var a = document.createElement('a');
            a.href = URL.createObjectURL(blob);
            a.download = 'churn_predictions.csv';
            a.click();
        });
    });

    function renderTable(rows, cols) {
        var thead = document.querySelector('#batchTable thead');
        var tbody = document.querySelector('#batchTable tbody');
        var show = (cols || []).filter(function (c) {
            return ['customerID', 'Contract', 'tenure', 'MonthlyCharges', 'churn_probability', 'prediction', 'risk_level'].indexOf(c) >= 0;
        });
        thead.innerHTML = '<tr>' + show.map(function (c) { return '<th>' + c + '</th>'; }).join('') + '</tr>';
        tbody.innerHTML = rows.slice(0, 50).map(function (row) {
            return '<tr>' + show.map(function (c) {
                var v = row[c];
                if (c === 'risk_level') return '<td><span class="badge badge-' + String(v).toLowerCase() + '">' + v + '</span></td>';
                return '<td>' + (v != null ? v : '—') + '</td>';
            }).join('') + '</tr>';
        }).join('');
    }
})();
