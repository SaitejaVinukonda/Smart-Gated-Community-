# visitors/management/commands/generate_training_data.py
from django.core.management.base import BaseCommand
#from visitors.models import VisitPass
import numpy as np
import json
from datetime import timedelta
from django.utils import timezone

class Command(BaseCommand):
    def handle(self, *args, **options):
        self.stdout.write('🔄 Generating 2000 training samples...')
        
        # Generate realistic training data
        training_data = []
        
        for i in range(2000):
            # Simulate 6 layers (realistic distributions)
            layers = {
                'face_match': np.clip(np.random.normal(0.85, 0.1), 0, 1),
                'tampering': np.clip(np.random.normal(0.92, 0.08), 0, 1),
                'format': np.clip(np.random.normal(0.88, 0.12), 0, 1),
                'purpose': np.clip(np.random.normal(0.82, 0.15), 0, 1),
                'resident': np.random.choice([1.0, 0.4], p=[0.85, 0.15]),
                'behavior': np.clip(np.random.normal(0.90, 0.1), 0, 1)
            }
            
            # Weighted score
            weights = [0.25, 0.20, 0.18, 0.17, 0.10, 0.10]
            overall = sum(layers[k] * w for k, w in zip(layers.keys(), weights))
            
            # Label: approved if > 0.75
            label = 1 if overall > 0.75 else 0
            
            training_data.append({
                'features': list(layers.values()),
                'label': label,
                'overall_score': overall
            })
        
        # Save training data
        with open('training_data.json', 'w') as f:
            json.dump(training_data, f)
        
        self.stdout.write(self.style.SUCCESS(f'✅ Generated {len(training_data)} samples'))
        self.stdout.write(self.style.SUCCESS(f'✅ Approval rate: {np.mean([d["label"] for d in training_data]):.1%}'))
