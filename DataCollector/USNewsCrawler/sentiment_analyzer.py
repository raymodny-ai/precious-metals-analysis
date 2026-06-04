from transformers import pipeline
import torch

class SentimentAnalyzer:
    def __init__(self):
        # Using FinBERT
        try:
            self.pipe = pipeline("text-classification", model="ProsusAI/finbert", device=0 if torch.cuda.is_available() else -1)
        except Exception as e:
            print(f"Error loading model: {e}")
            self.pipe = None

    def analyze(self, text):
        if not self.pipe:
            return {'label': 'neutral', 'score': 0.5}
        
        # Truncate text if too long (BERT limit 512 tokens)
        truncated_text = text[:512] 
        try:
            result = self.pipe(truncated_text)[0]
            return result
        except Exception as e:
            print(f"Error in analysis: {e}")
            return {'label': 'neutral', 'score': 0.5}
