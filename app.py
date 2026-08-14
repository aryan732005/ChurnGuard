"""
Customer Churn Prediction System - Main Flask Application
Provides dashboard, prediction, analytics, dataset explorer, and methodology pages.
"""

import os
import json
import pickle
import traceback
import pandas as pd
from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash, send_file
from functools import wraps

from config import Config
from auth import verify_user, ensure_default_user
from validation import validate_prediction_input

app = Flask(__name__)
app.config.from_object(Config)


def load_artifacts():
    """Load model, scaler, feature names, encoders, and stats."""
    model_dir = Config.MODEL_PATH
    data_dir = Config.DATA_PATH

    model = scaler = feature_names = label_encoders = None

    try:
        model = pickle.load(open(os.path.join(model_dir, 'churn_model.pkl'), 'rb'))
        scaler = pickle.load(open(os.path.join(model_dir, 'scaler.pkl'), 'rb'))
        feature_names = pickle.load(open(os.path.join(model_dir, 'feature_names.pkl'), 'rb'))
        enc_path = os.path.join(model_dir, 'label_encoders.pkl')
        if os.path.exists(enc_path):
            label_encoders = pickle.load(open(enc_path, 'rb'))
    except FileNotFoundError:
        print("Model not found. Please run train_model.py first.")

    try:
        with open(os.path.join(data_dir, 'stats.json'), 'r') as f:
            stats = json.load(f)
    except FileNotFoundError:
        stats = {}

    try:
        df = pd.read_csv(os.path.join(data_dir, 'telco_churn.csv'))
    except FileNotFoundError:
        df = None

    return model, scaler, feature_names, label_encoders, stats, df


model, scaler, feature_names, label_encoders, stats, df = load_artifacts()
ensure_default_user()


def get_stats():
    """Load latest stats from disk (avoids stale in-memory data after retraining)."""
    try:
        with open(os.path.join(Config.DATA_PATH, 'stats.json'), 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return stats if stats else {}


def reload_artifacts():
    global model, scaler, feature_names, label_encoders, stats, df
    model, scaler, feature_names, label_encoders, stats, df = load_artifacts()


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in'):
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function


def build_feature_vector(form_data):
    """Transform form input into scaled feature vector using saved encoders."""
    input_df = pd.DataFrame([form_data])

    binary_cols = ['gender', 'Partner', 'Dependents', 'PhoneService', 'PaperlessBilling']
    if label_encoders:
        for col in binary_cols:
            input_df[col] = label_encoders[col].transform(input_df[col])
    else:
        from sklearn.preprocessing import LabelEncoder
        for col in binary_cols:
            le = LabelEncoder()
            input_df[col] = le.fit_transform(input_df[col])

    multi_cols = [
        'MultipleLines', 'InternetService', 'OnlineSecurity', 'OnlineBackup',
        'DeviceProtection', 'TechSupport', 'StreamingTV', 'StreamingMovies',
        'Contract', 'PaymentMethod',
    ]
    input_df = pd.get_dummies(input_df, columns=multi_cols, drop_first=True)

    for feat in feature_names:
        if feat not in input_df.columns:
            input_df[feat] = 0
    input_df = input_df[feature_names]

    return scaler.transform(input_df.values)


def get_top_factors(X_scaled_row, n=5):
    """Top contributing features for prediction display (presentation only)."""
    if model is None or feature_names is None:
        return []
    row = X_scaled_row[0] if len(X_scaled_row.shape) > 1 else X_scaled_row
    if hasattr(model, 'coef_'):
        contribs = [(feature_names[i], float(model.coef_[0][i] * row[i])) for i in range(len(feature_names))]
    elif hasattr(model, 'feature_importances_'):
        contribs = [(feature_names[i], float(model.feature_importances_[i] * abs(row[i]))) for i in range(len(feature_names))]
    else:
        return []
    contribs.sort(key=lambda x: abs(x[1]), reverse=True)
    return [{'feature': f.replace('_', ' '), 'impact': round(v, 4)} for f, v in contribs[:n]]


def get_risk_level(probability):
    if probability >= 70:
        return 'High', 'danger'
    if probability >= 40:
        return 'Medium', 'warning'
    return 'Low', 'success'


@app.route('/')
def landing():
    return render_template('landing.html', stats=get_stats())


@app.route('/login', methods=['GET', 'POST'])
def login():
    if session.get('logged_in'):
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        if verify_user(username, password):
            session['logged_in'] = True
            session['username'] = username
            return redirect(url_for('dashboard'))
        flash('Invalid credentials. Please try again.', 'error')
    return render_template('login.html')


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html', stats=get_stats())


@app.route('/export/report')
@login_required
def export_report():
    try:
        from export_summary import generate_executive_pdf
        pdf = generate_executive_pdf()
        return send_file(
            pdf,
            mimetype='application/pdf',
            as_attachment=True,
            download_name='ChurnGuardAI_Executive_Report.pdf',
        )
    except Exception as exc:
        flash(f'Export failed: {exc}', 'error')
        return redirect(url_for('dashboard'))


@app.route('/predict', methods=['GET', 'POST'])
@login_required
def predict():
    prediction = None
    probability = None
    form_data = {}
    validation_errors = []
    top_factors = []
    risk_level = None
    risk_class = None

    if request.method == 'POST':
        if model is None or label_encoders is None:
            reload_artifacts()
        if model is None:
            flash('Prediction unavailable: model not loaded. Please run training first.', 'error')
        else:
            form_data = {
                'gender': request.form.get('gender', 'Male'),
                'SeniorCitizen': int(request.form.get('SeniorCitizen', 0)),
                'Partner': request.form.get('Partner', 'No'),
                'Dependents': request.form.get('Dependents', 'No'),
                'tenure': request.form.get('tenure', '1'),
                'PhoneService': request.form.get('PhoneService', 'Yes'),
                'MultipleLines': request.form.get('MultipleLines', 'No'),
                'InternetService': request.form.get('InternetService', 'DSL'),
                'OnlineSecurity': request.form.get('OnlineSecurity', 'No'),
                'OnlineBackup': request.form.get('OnlineBackup', 'No'),
                'DeviceProtection': request.form.get('DeviceProtection', 'No'),
                'TechSupport': request.form.get('TechSupport', 'No'),
                'StreamingTV': request.form.get('StreamingTV', 'No'),
                'StreamingMovies': request.form.get('StreamingMovies', 'No'),
                'Contract': request.form.get('Contract', 'Month-to-month'),
                'PaperlessBilling': request.form.get('PaperlessBilling', 'Yes'),
                'PaymentMethod': request.form.get('PaymentMethod', 'Electronic check'),
                'MonthlyCharges': request.form.get('MonthlyCharges', '50'),
                'TotalCharges': request.form.get('TotalCharges', '500'),
            }

            validation_errors = validate_prediction_input(form_data)

            if not validation_errors:
                try:
                    numeric_data = dict(form_data)
                    numeric_data['tenure'] = int(form_data['tenure'])
                    numeric_data['MonthlyCharges'] = float(form_data['MonthlyCharges'])
                    numeric_data['TotalCharges'] = float(form_data['TotalCharges'])

                    X_input = build_feature_vector(numeric_data)
                    pred = model.predict(X_input)[0]
                    prob = model.predict_proba(X_input)[0]

                    prediction = 'Churn' if pred == 1 else 'No Churn'
                    probability = round(float(prob[1]) * 100, 2)
                    risk_level, risk_class = get_risk_level(probability)
                    top_factors = get_top_factors(X_input)
                except Exception:
                    flash('Prediction failed due to an unexpected error. Please check your inputs and try again.', 'error')

    return render_template(
        'predict.html',
        prediction=prediction,
        probability=probability,
        form_data=form_data,
        validation_errors=validation_errors,
        top_factors=top_factors,
        risk_level=risk_level,
        risk_class=risk_class,
    )


@app.route('/analytics')
@login_required
def analytics():
    return render_template('analytics.html', stats=get_stats())


@app.route('/dataset')
@login_required
def dataset():
    page = int(request.args.get('page', 1))
    per_page = 20
    search = request.args.get('search', '').strip()
    contract_filter = request.args.get('contract', '')
    churn_filter = request.args.get('churn', '')

    if df is not None:
        filtered = df.copy()
        if search:
            filtered = filtered[filtered['customerID'].str.contains(search, case=False, na=False)]
        if contract_filter:
            filtered = filtered[filtered['Contract'] == contract_filter]
        if churn_filter:
            filtered = filtered[filtered['Churn'] == churn_filter]

        total = len(filtered)
        total_pages = max(1, (total + per_page - 1) // per_page)
        page = max(1, min(page, total_pages))
        start = (page - 1) * per_page
        end = start + per_page
        data = filtered.iloc[start:end].to_dict('records')
        columns = list(df.columns)
        contract_options = sorted(df['Contract'].unique().tolist())
    else:
        data = []
        columns = []
        total = 0
        total_pages = 0
        contract_options = []

    return render_template(
        'dataset.html',
        data=data,
        columns=columns,
        page=page,
        total_pages=total_pages,
        total=total,
        search=search,
        contract_filter=contract_filter,
        churn_filter=churn_filter,
        contract_options=contract_options,
    )


@app.route('/methodology')
def methodology():
    return render_template('methodology.html', stats=get_stats())


@app.route('/api/predict', methods=['POST'])
@login_required
def api_predict():
    if model is None:
        return jsonify({'error': 'Model not available. Run train_model.py first.'}), 503

    payload = request.get_json(silent=True) or {}
    errors = validate_prediction_input(payload)
    if errors:
        return jsonify({'error': 'Validation failed', 'details': errors}), 400

    try:
        numeric_data = dict(payload)
        numeric_data['tenure'] = int(payload['tenure'])
        numeric_data['SeniorCitizen'] = int(payload.get('SeniorCitizen', 0))
        numeric_data['MonthlyCharges'] = float(payload['MonthlyCharges'])
        numeric_data['TotalCharges'] = float(payload['TotalCharges'])

        X_input = build_feature_vector(numeric_data)
        pred = model.predict(X_input)[0]
        prob = model.predict_proba(X_input)[0]
        return jsonify({
            'prediction': 'Churn' if pred == 1 else 'No Churn',
            'probability': round(float(prob[1]) * 100, 2),
        })
    except Exception as exc:
        return jsonify({'error': 'Prediction failed', 'details': str(exc)}), 500


@app.route('/api/chart-data/<chart_type>')
@login_required
def chart_data(chart_type):
    """API endpoint for dynamic chart data."""
    current_stats = get_stats()
    try:
        if chart_type == 'churn_distribution':
            if df is None:
                return jsonify({'error': 'No data available'}), 404
            counts = df['Churn'].value_counts()
            return jsonify({
                'labels': counts.index.tolist(),
                'values': counts.values.tolist(),
            })

        if chart_type == 'tenure_distribution':
            if df is None:
                return jsonify({'error': 'No data available'}), 404
            churned = df[df['Churn'] == 'Yes']['tenure']
            not_churned = df[df['Churn'] == 'No']['tenure']
            return jsonify({
                'churned': churned.tolist(),
                'not_churned': not_churned.tolist(),
            })

        if chart_type == 'contract_churn':
            if df is None:
                return jsonify({'error': 'No data available'}), 404
            cross = pd.crosstab(df['Contract'], df['Churn'])
            return jsonify({
                'labels': cross.index.tolist(),
                'churn_yes': cross.get('Yes', pd.Series([0] * len(cross))).tolist(),
                'churn_no': cross.get('No', pd.Series([0] * len(cross))).tolist(),
            })

        if chart_type == 'monthly_charges':
            if df is None:
                return jsonify({'error': 'No data available'}), 404
            churned = df[df['Churn'] == 'Yes']['MonthlyCharges']
            not_churned = df[df['Churn'] == 'No']['MonthlyCharges']
            return jsonify({
                'churned': churned.describe().to_dict(),
                'not_churned': not_churned.describe().to_dict(),
            })

        if chart_type == 'internet_service':
            if df is None:
                return jsonify({'error': 'No data available'}), 404
            cross = pd.crosstab(df['InternetService'], df['Churn'])
            return jsonify({
                'labels': cross.index.tolist(),
                'churn_yes': cross.get('Yes', pd.Series([0] * len(cross))).tolist(),
                'churn_no': cross.get('No', pd.Series([0] * len(cross))).tolist(),
            })

        if chart_type == 'payment_method':
            if df is None:
                return jsonify({'error': 'No data available'}), 404
            cross = pd.crosstab(df['PaymentMethod'], df['Churn'])
            return jsonify({
                'labels': cross.index.tolist(),
                'churn_yes': cross.get('Yes', pd.Series([0] * len(cross))).tolist(),
                'churn_no': cross.get('No', pd.Series([0] * len(cross))).tolist(),
            })

        if chart_type == 'feature_importance':
            if current_stats.get('top_features'):
                features = current_stats['top_features']
                return jsonify({
                    'labels': [f['feature'] for f in features],
                    'values': [f['importance'] for f in features],
                })
            return jsonify({'error': 'Feature importance not available'}), 404

        if chart_type == 'model_comparison':
            if current_stats.get('model_results'):
                results = current_stats['model_results']
                return jsonify({
                    'models': list(results.keys()),
                    'accuracy': [results[m]['accuracy'] for m in results],
                    'precision': [results[m]['precision'] for m in results],
                    'recall': [results[m]['recall'] for m in results],
                    'f1_score': [results[m]['f1_score'] for m in results],
                    'roc_auc': [results[m]['roc_auc'] for m in results],
                })
            return jsonify({'error': 'Model results not available'}), 404

        if chart_type == 'roc_curve':
            if current_stats.get('roc_curve'):
                return jsonify(current_stats['roc_curve'])
            return jsonify({'error': 'ROC curve data not available'}), 404

        return jsonify({'error': 'Unknown chart type'}), 400
    except Exception:
        app.logger.error(traceback.format_exc())
        return jsonify({'error': 'Failed to load chart data. Please retry.'}), 500


if __name__ == '__main__':
    if model is None:
        print("\n[!] Model not found. Training model first...\n")
        from train_model import train_and_evaluate
        train_and_evaluate()
        reload_artifacts()

    print("\nStarting Customer Churn Prediction System...")
    print("   Dashboard: http://127.0.0.1:5000")
    print("   Login: admin / admin123\n")
    app.run(debug=True, port=5000)
