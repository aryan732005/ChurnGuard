"""Input validation for churn prediction form."""


def validate_prediction_input(data):
    """
    Validate prediction form fields.
    Returns list of user-facing error strings (empty if valid).
    """
    errors = []

    try:
        tenure = int(data.get('tenure', ''))
        if tenure < 0 or tenure > 72:
            errors.append('Tenure must be between 0 and 72 months.')
    except (TypeError, ValueError):
        errors.append('Tenure must be a whole number between 0 and 72.')

    try:
        monthly = float(data.get('MonthlyCharges', ''))
        if monthly < 0 or monthly > 200:
            errors.append('Monthly charges must be between $0 and $200.')
    except (TypeError, ValueError):
        errors.append('Monthly charges must be a valid dollar amount.')

    try:
        total = float(data.get('TotalCharges', ''))
        if total < 0:
            errors.append('Total charges cannot be negative.')
    except (TypeError, ValueError):
        errors.append('Total charges must be a valid dollar amount.')

    if not errors:
        try:
            tenure = int(data.get('tenure', 0))
            monthly = float(data.get('MonthlyCharges', 0))
            total = float(data.get('TotalCharges', 0))
            expected_min = max(0, monthly * max(tenure - 2, 0) * 0.5)
            expected_max = monthly * (tenure + 2) + 500
            if total < expected_min or total > expected_max:
                errors.append(
                    'Total charges look inconsistent with tenure and monthly charges. '
                    'Please verify billing values.'
                )
        except (TypeError, ValueError):
            pass

    phone = data.get('PhoneService', 'Yes')
    multiple_lines = data.get('MultipleLines', 'No')
    if phone == 'No' and multiple_lines not in ('No phone service', 'No'):
        errors.append('If phone service is No, multiple lines must be No phone service.')

    internet = data.get('InternetService', 'DSL')
    internet_dependent = [
        'OnlineSecurity', 'OnlineBackup', 'DeviceProtection',
        'TechSupport', 'StreamingTV', 'StreamingMovies',
    ]
    if internet == 'No':
        for field in internet_dependent:
            val = data.get(field, 'No')
            if val not in ('No internet service', 'No'):
                label = field.replace('Online', 'Online ').replace('DeviceProtection', 'Device Protection')
                errors.append(f'{label} must be "No internet service" when internet service is No.')

    return errors
