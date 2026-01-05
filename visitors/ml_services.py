# visitors/ml_services.py
import numpy as np
from sklearn.preprocessing import StandardScaler
from django.utils import timezone

# In real project load from joblib / pickle
scaler = StandardScaler()
DUMMY_MEAN = np.array([0.5, 30.0, 5.0])  # example features

def compute_risk_score(visit_request):
    """
    Example feature engineering for classification model.
    Features:
      - frequent visitor (0/1)
      - hour of day
      - text length of purpose
    """
    frequent = 1.0 if visit_request.visitor.frequent_visitor else 0.0
    hour = float(visit_request.request_time.astimezone(timezone.get_current_timezone()).hour)
    purpose_len = float(len(visit_request.purpose))

    x = np.array([[frequent, hour, purpose_len]])
    # Dummy normalization
    normalized = (x - DUMMY_MEAN) / np.array([[0.5, 10.0, 20.0]])
    # Fake risk model: sigmoid-like
    raw_score = (normalized.sum(axis=1)[0] + 1.0) / 2.0
    return max(0.0, min(1.0, float(raw_score)))
