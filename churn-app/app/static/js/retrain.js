(function () {
    'use strict';

    function basicAuthHeader() {
        var user = document.getElementById('adminUser').value.trim();
        var pass = document.getElementById('adminPass').value;
        if (!user || !pass) {
            return null;
        }
        return 'Basic ' + btoa(unescape(encodeURIComponent(user + ':' + pass)));
    }

    document.addEventListener('DOMContentLoaded', function () {
        var zone = document.getElementById('retrainUploadZone');
        var input = document.getElementById('retrainFile');

        zone.addEventListener('click', function () { input.click(); });
        zone.addEventListener('keydown', function (e) {
            if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                input.click();
            }
        });
        input.addEventListener('change', function () {
            if (input.files.length) upload(input.files[0]);
        });

        function showErrors(errs) {
            var el = document.getElementById('retrainErrors');
            el.classList.remove('hidden');
            el.innerHTML = '<ul>' + errs.map(function (e) { return '<li>' + e + '</li>'; }).join('') + '</ul>';
        }

        function upload(file) {
            var auth = basicAuthHeader();
            if (!auth) {
                showErrors(['Enter admin username and password before uploading.']);
                return;
            }

            document.getElementById('retrainErrors').classList.add('hidden');
            document.getElementById('retrainProgress').classList.remove('hidden');
            document.getElementById('retrainResults').classList.add('hidden');

            var fd = new FormData();
            fd.append('file', file);

            fetch('/api/retrain-simulation', {
                method: 'POST',
                body: fd,
                headers: { Authorization: auth },
            })
                .then(function (r) {
                    if (r.status === 401) {
                        throw ['Invalid admin credentials — check ADMIN_USER / ADMIN_PASSWORD in .env.local'];
                    }
                    if (!r.ok) {
                        return r.json().then(function (d) {
                            throw (d.detail && d.detail.errors) || [d.detail || 'Retrain failed'];
                        });
                    }
                    return r.json();
                })
                .then(function (data) {
                    document.getElementById('retrainProgress').classList.add('hidden');
                    document.getElementById('retrainResults').classList.remove('hidden');
                    document.getElementById('retrainNote').textContent = data.note;

                    function card(label, m, rows) {
                        return '<div class="card"><h3>' + label + '</h3><p class="text-sm text-muted">' + rows + ' rows</p>' +
                            '<div style="margin-top:16px;line-height:2" class="text-sm">' +
                            '<div>Accuracy: <strong>' + (m.accuracy * 100).toFixed(1) + '%</strong></div>' +
                            '<div>F1: <strong>' + (m.f1_score * 100).toFixed(1) + '%</strong></div>' +
                            '<div>ROC AUC: <strong>' + (m.roc_auc * 100).toFixed(1) + '%</strong></div></div></div>';
                    }

                    document.getElementById('retrainCompare').innerHTML =
                        card(data.before.label, data.before, data.before.rows) +
                        card(data.after.label, data.after, data.after.rows) +
                        '<div class="card full-width" style="grid-column:1/-1"><h3>Delta (after − before)</h3>' +
                        '<p class="text-sm">Accuracy: ' + (data.delta.accuracy >= 0 ? '+' : '') + (data.delta.accuracy * 100).toFixed(2) + '% · ' +
                        'F1: ' + (data.delta.f1_score >= 0 ? '+' : '') + (data.delta.f1_score * 100).toFixed(2) + '% · ' +
                        'ROC AUC: ' + (data.delta.roc_auc >= 0 ? '+' : '') + (data.delta.roc_auc * 100).toFixed(2) + '%</p>' +
                        (data.experiments_url ? '<a href="' + data.experiments_url + '" class="btn btn-primary btn-sm" style="margin-top:12px">View in Experiments →</a>' : '') +
                        '</div>';
                })
                .catch(function (err) {
                    document.getElementById('retrainProgress').classList.add('hidden');
                    showErrors(Array.isArray(err) ? err : [String(err)]);
                });
        }
    });
})();
