(function () {
    'use strict';

    function showFormErrors(errors) {
        var el = document.getElementById('predictErrors');
        if (!el) return;
        el.classList.remove('hidden');
        el.innerHTML = '<ul>' + errors.map(function (e) { return '<li>' + e + '</li>'; }).join('') + '</ul>';
    }

    function hideFormErrors() {
        var el = document.getElementById('predictErrors');
        if (el) el.classList.add('hidden');
    }

    function formPayload(form) {
        var data = {};
        new FormData(form).forEach(function (v, k) {
            if (k === 'SeniorCitizen' || k === 'tenure') data[k] = parseInt(v, 10);
            else if (k === 'MonthlyCharges' || k === 'TotalCharges') data[k] = parseFloat(v);
            else data[k] = v;
        });
        return data;
    }

    function showResult(res) {
        hideFormErrors();
        document.getElementById('resultPlaceholder').style.display = 'none';
        var card = document.getElementById('resultCard');
        card.style.display = 'block';

        var prob = res.churn_probability;
        document.getElementById('probValue').textContent = prob + '%';
        document.getElementById('confValue').textContent = res.confidence + '%';
        document.getElementById('probBar').style.width = prob + '%';

        var circ = 2 * Math.PI * 52;
        document.getElementById('gaugeFill').setAttribute('stroke-dasharray', (prob / 100 * circ) + ' ' + circ);

        var badge = document.getElementById('riskBadge');
        badge.textContent = res.risk_level + ' risk';
        badge.className = 'badge badge-' + res.risk_level.toLowerCase();

        var list = document.getElementById('factorList');
        list.innerHTML = (res.top_factors || []).map(function (f) {
            return '<li style="padding:4px 0">' + f.feature + ' <span style="float:right">' + f.impact + '</span></li>';
        }).join('') || '<li>No factors available</li>';

        var actionEl = document.getElementById('recommendedAction');
        if (actionEl) actionEl.textContent = res.recommended_action || '—';

        var noteEl = document.getElementById('explainNote');
        if (noteEl && res.explainability_note) noteEl.textContent = res.explainability_note;

        fetch('/api/predict/explain', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                risk_level: res.risk_level,
                churn_probability: res.churn_probability,
                top_factors: res.top_factors || [],
                attributes: formPayload(document.getElementById('predictForm')),
            }),
        }).then(function (r) { return r.json(); }).then(function (ex) {
            var wrap = document.getElementById('nlExplainWrap');
            wrap.hidden = false;
            document.getElementById('nlExplainText').textContent = ex.text || '';
            document.getElementById('nlExplainLabel').textContent = ex.ai_label || '';
        }).catch(function () {});
    }

    function predict(payload) {
        return fetch('/api/predict', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload),
        }).then(function (r) {
            if (!r.ok) {
                return r.json().then(function (d) {
                    var errs = (d.detail && d.detail.errors) || [d.detail || 'Validation failed'];
                    throw errs;
                });
            }
            return r.json();
        });
    }

    document.addEventListener('DOMContentLoaded', function () {
        var form = document.getElementById('predictForm');
        form.addEventListener('submit', function (e) {
            e.preventDefault();
            predict(formPayload(form)).then(showResult).catch(function (err) {
                showFormErrors(Array.isArray(err) ? err : [String(err)]);
            });
        });

        var simTenure = document.getElementById('simTenure');
        var simMonthly = document.getElementById('simMonthly');
        var debounce;

        function liveSim() {
            clearTimeout(debounce);
            debounce = setTimeout(function () {
                var t = parseInt(simTenure.value, 10);
                var m = parseInt(simMonthly.value, 10);
                document.getElementById('simTenureVal').textContent = t;
                document.getElementById('simMonthlyVal').textContent = m;
                document.getElementById('tenure').value = t;
                document.getElementById('monthly').value = m;
                document.getElementById('total').value = Math.round(m * Math.max(t, 1));

                predict(formPayload(form)).then(function (res) {
                    document.getElementById('simProb').textContent = res.churn_probability;
                    var b = document.getElementById('simRisk');
                    b.textContent = res.risk_level;
                    b.className = 'badge badge-' + res.risk_level.toLowerCase();
                    showResult(res);
                }).catch(function () {});
            }, 300);
        }

        simTenure.addEventListener('input', liveSim);
        simMonthly.addEventListener('input', liveSim);
    });
})();
