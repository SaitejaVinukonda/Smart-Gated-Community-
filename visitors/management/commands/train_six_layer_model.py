# visitors/management/commands/train_six_layer_model.py
from datetime import timezone
import os
from xml.parsers.expat import model

from django.core.management.base import BaseCommand
import numpy as np
import xgboost as xgb
import joblib
import json
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report
from django.conf import settings

class Command(BaseCommand):
    def handle(self, *args, **options):
        self.stdout.write('🔄 Training 6-Layer XGBoost Model...')
        
        # Load training data
        with open('training_data.json', 'r') as f:
            data = json.load(f)
        
        X = np.array([sample['features'] for sample in data])
        y = np.array([sample['label'] for sample in data])
        
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
        
        # Train XGBoost
        model = xgb.XGBClassifier(
            n_estimators=200,
            max_depth=6,
            learning_rate=0.1,
            subsample=0.8,
            colsample_bytree=0.8,
            random_state=42,
            eval_metric='logloss'
        )
        
        model.fit(X_train, y_train)
        
        # Evaluate
        train_acc = accuracy_score(y_train, model.predict(X_train))
        test_acc = accuracy_score(y_test, model.predict(X_test))
        
        self.stdout.write(self.style.SUCCESS(f'✅ Training Accuracy: {train_acc:.3f}'))
        self.stdout.write(self.style.SUCCESS(f'✅ Test Accuracy: {test_acc:.3f}'))
        
        # Feature importance
        importance = dict(zip(['face', 'tampering', 'format', 'purpose', 'resident', 'behavior'], 
                         model.feature_importances_))
        self.stdout.write(self.style.WARNING(f'📊 Feature Importance: {importance}'))
    
    model_package = {
        'model': model,
        'feature_order': ['face', 'tampering', 'format', 'purpose', 'resident', 'behavior'],
        'threshold': 0.70,
        'version': 'v2.0',
        'trained_on': str(timezone.now())
    }

    model_path = os.path.join(settings.BASE_DIR, 'media', 'ml_models', 'six_layer_model.pkl')
    os.makedirs(os.path.dirname(model_path), exist_ok=True)

    joblib.dump(model_package, model_path)

    self.stdout.write(self.style.SUCCESS(f'🎉 Model v2.0 saved successfully!'))