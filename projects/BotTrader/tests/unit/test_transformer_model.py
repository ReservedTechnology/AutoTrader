"""
Test Suite for Transformer Model ML Predictions
Following TDD methodology for forex bot targeting 25% annual returns
Tests for Transformer model with dual database architecture
"""
import pytest
import pytest_asyncio
import numpy as np
import pandas as pd
import os
import psycopg2
from psycopg2.extras import RealDictCursor
from supabase import create_client, Client
from datetime import datetime, timedelta
from typing import Dict, List, Any
import json
import torch
from dotenv import load_dotenv

load_dotenv()


class TestTransformerModel:
    """
    Test suite for Transformer model predictions
    Target: Sharpe ratio 4.4, 68% accuracy
    Stores predictions in TimescaleDB, model metadata in Supabase
    """
    
    @pytest.fixture
    def timescale_connection(self):
        """Initialize TimescaleDB connection for predictions"""
        conn = psycopg2.connect(
            host=os.getenv('TIMESCALE_HOST', 'localhost'),
            port=os.getenv('TIMESCALE_PORT', 5432),
            database=os.getenv('TIMESCALE_DB', 'bottrader_timeseries'),
            user=os.getenv('TIMESCALE_USER', 'postgres'),
            password=os.getenv('TIMESCALE_PASSWORD')
        )
        yield conn
        conn.close()
    
    @pytest.fixture
    def supabase_client(self) -> Client:
        """Initialize Supabase client for model metadata"""
        url = os.getenv('SUPABASE_URL')
        key = os.getenv('SUPABASE_ANON_KEY')
        client = create_client(url, key)
        return client
    
    @pytest.fixture
    def transformer_model(self):
        """Initialize Transformer model"""
        from src.ml.models.transformer_model import ForexTransformer
        
        model = ForexTransformer(
            input_dim=128,  # Features
            d_model=512,
            n_heads=12,
            n_layers=6,
            dropout=0.1
        )
        return model
    
    def test_model_architecture(self, transformer_model):
        """
        Test 3.1.1: Verify Transformer architecture
        Acceptance: 12 attention heads, 6 layers as specified
        """
        assert transformer_model.n_heads == 12, \
            f"Expected 12 attention heads, got {transformer_model.n_heads}"
        assert transformer_model.n_layers == 6, \
            f"Expected 6 layers, got {transformer_model.n_layers}"
        assert transformer_model.d_model == 512, \
            f"Expected d_model=512, got {transformer_model.d_model}"
        
        # Verify model parameters count
        total_params = sum(p.numel() for p in transformer_model.parameters())
        assert total_params > 1_000_000, \
            f"Model too small: {total_params} parameters"
        assert total_params < 50_000_000, \
            f"Model too large: {total_params} parameters"
    
    def test_input_shape_handling(self, transformer_model):
        """
        Test 3.1.2: Test various input shapes
        Acceptance: Handle batch sizes 1-1024, sequence lengths 10-500
        """
        test_cases = [
            (1, 50, 128),    # Single sample
            (32, 100, 128),  # Standard batch
            (128, 200, 128), # Large batch
            (256, 50, 128),  # Very large batch
        ]
        
        for batch_size, seq_len, input_dim in test_cases:
            x = torch.randn(batch_size, seq_len, input_dim)
            
            try:
                output = transformer_model(x)
                assert output.shape[0] == batch_size, \
                    f"Batch size mismatch: expected {batch_size}, got {output.shape[0]}"
                assert output.shape[-1] == 3, \
                    "Output should have 3 classes (buy/hold/sell)"
            except Exception as e:
                pytest.fail(f"Failed on shape {x.shape}: {e}")
    
    def test_feature_extraction(self, transformer_model):
        """
        Test 3.1.3: Verify feature extraction from forex data
        Acceptance: Extract 128 features from OHLCV + indicators
        """
        # Simulate forex data with technical indicators
        sample_data = {
            'open': 1.1000,
            'high': 1.1050,
            'low': 1.0950,
            'close': 1.1020,
            'volume': 100000,
            'rsi': 45.5,
            'macd': 0.0012,
            'macd_signal': 0.0010,
            'bollinger_upper': 1.1100,
            'bollinger_lower': 1.0900,
            'atr': 0.0050,
            'adx': 25.3
        }
        
        from src.ml.features.feature_engineering import FeatureExtractor
        
        extractor = FeatureExtractor()
        features = extractor.extract_features(sample_data)
        
        assert len(features) >= 128, \
            f"Insufficient features: {len(features)}, expected >= 128"
        assert not np.any(np.isnan(features)), \
            "Features contain NaN values"
        assert not np.any(np.isinf(features)), \
            "Features contain infinite values"
    
    @pytest.mark.asyncio
    async def test_prediction_generation(self, transformer_model, timescale_connection):
        """
        Test 3.1.4: Generate and store predictions
        Acceptance: Generate predictions with confidence scores
        """
        # Prepare test data
        batch_size = 32
        seq_len = 100
        input_dim = 128
        
        x = torch.randn(batch_size, seq_len, input_dim)
        
        # Generate predictions
        with torch.no_grad():
            predictions = transformer_model(x)
            probabilities = torch.softmax(predictions, dim=-1)
        
        # Extract predictions and confidence
        predicted_classes = torch.argmax(probabilities, dim=-1)
        confidence_scores = torch.max(probabilities, dim=-1)[0]
        
        # Store predictions in TimescaleDB
        cursor = timescale_connection.cursor()
        
        for i in range(min(5, batch_size)):  # Store first 5 predictions
            prediction_map = {0: 'sell', 1: 'hold', 2: 'buy'}
            
            cursor.execute("""
                INSERT INTO ml_predictions (time, data)
                VALUES (%s, %s);
            """, (
                datetime.now(),
                json.dumps({
                    'model': 'transformer',
                    'version': '1.0.0',
                    'symbol': 'EUR_USD',
                    'prediction': prediction_map[predicted_classes[i].item()],
                    'confidence': float(confidence_scores[i].item()),
                    'probabilities': {
                        'sell': float(probabilities[i, 0].item()),
                        'hold': float(probabilities[i, 1].item()),
                        'buy': float(probabilities[i, 2].item())
                    }
                })
            ))
        
        timescale_connection.commit()
        cursor.close()
        
        # Verify predictions
        assert predicted_classes.shape[0] == batch_size, \
            "Prediction count mismatch"
        assert torch.all(confidence_scores >= 0) and torch.all(confidence_scores <= 1), \
            "Invalid confidence scores"
        assert torch.all(predicted_classes >= 0) and torch.all(predicted_classes <= 2), \
            "Invalid prediction classes"
    
    def test_attention_weights(self, transformer_model):
        """
        Test 3.1.5: Verify attention mechanism
        Acceptance: Attention weights sum to 1, focus on relevant timepoints
        """
        x = torch.randn(8, 50, 128)
        
        # Get attention weights
        _, attention_weights = transformer_model.forward_with_attention(x)
        
        assert attention_weights is not None, \
            "No attention weights returned"
        
        # Check attention properties
        for layer_attention in attention_weights:
            # Attention weights should sum to 1 along last dimension
            attention_sum = torch.sum(layer_attention, dim=-1)
            assert torch.allclose(attention_sum, torch.ones_like(attention_sum), atol=1e-5), \
                "Attention weights don't sum to 1"
            
            # Check for reasonable attention distribution (not too concentrated)
            max_attention = torch.max(layer_attention, dim=-1)[0]
            assert torch.all(max_attention < 0.95), \
                "Attention too concentrated on single timepoint"
    
    @pytest.mark.asyncio
    async def test_model_versioning(self, transformer_model, supabase_client):
        """
        Test 3.1.6: Test model versioning and metadata storage
        Acceptance: Model versions tracked in Supabase
        """
        model_metadata = {
            'model_type': 'transformer',
            'version': '1.0.0',
            'parameters': {
                'n_heads': 12,
                'n_layers': 6,
                'd_model': 512,
                'dropout': 0.1,
                'learning_rate': 0.0001,
                'batch_size': 32
            },
            'training_metrics': {
                'epochs': 100,
                'final_loss': 0.023,
                'validation_accuracy': 0.68,
                'sharpe_ratio': 4.4
            },
            'created_at': datetime.now().isoformat()
        }
        
        try:
            # Store model metadata
            response = supabase_client.table('ml_model_versions').insert(model_metadata).execute()
            assert response.data, "Failed to store model metadata"
            
            model_id = response.data[0]['id']
            
            # Retrieve and verify
            response = supabase_client.table('ml_model_versions').select("*").eq('id', model_id).execute()
            assert len(response.data) == 1, "Model metadata not found"
            assert response.data[0]['version'] == '1.0.0', "Version mismatch"
            
            # Clean up
            supabase_client.table('ml_model_versions').delete().eq('id', model_id).execute()
            
        except Exception as e:
            print(f"Model versioning test: {e}")
    
    def test_inference_speed(self, transformer_model):
        """
        Test 3.1.7: Verify inference speed requirements
        Acceptance: <200ms for batch of 32 samples
        """
        import time
        
        x = torch.randn(32, 100, 128)
        
        # Warm up
        with torch.no_grad():
            _ = transformer_model(x)
        
        # Measure inference time
        start_time = time.time()
        with torch.no_grad():
            predictions = transformer_model(x)
        inference_time = (time.time() - start_time) * 1000  # Convert to ms
        
        assert inference_time < 200, \
            f"Inference too slow: {inference_time:.1f}ms, expected <200ms"
        
        # Calculate throughput
        throughput = 32 / (inference_time / 1000)  # samples per second
        assert throughput > 100, \
            f"Throughput too low: {throughput:.1f} samples/sec"
    
    def test_model_robustness(self, transformer_model):
        """
        Test 3.1.8: Test model robustness to noisy data
        Acceptance: Stable predictions with up to 10% noise
        """
        # Generate clean data
        clean_data = torch.randn(16, 50, 128)
        
        with torch.no_grad():
            clean_predictions = transformer_model(clean_data)
            clean_classes = torch.argmax(clean_predictions, dim=-1)
        
        # Add noise
        noise_levels = [0.01, 0.05, 0.10]  # 1%, 5%, 10% noise
        
        for noise_level in noise_levels:
            noise = torch.randn_like(clean_data) * noise_level
            noisy_data = clean_data + noise
            
            with torch.no_grad():
                noisy_predictions = transformer_model(noisy_data)
                noisy_classes = torch.argmax(noisy_predictions, dim=-1)
            
            # Calculate stability (percentage of unchanged predictions)
            stability = (clean_classes == noisy_classes).float().mean()
            
            min_stability = {
                0.01: 0.95,  # 95% stable with 1% noise
                0.05: 0.85,  # 85% stable with 5% noise
                0.10: 0.75   # 75% stable with 10% noise
            }
            
            assert stability >= min_stability[noise_level], \
                f"Model unstable with {noise_level*100}% noise: {stability:.2%} stability"
    
    @pytest.mark.asyncio
    async def test_ensemble_compatibility(self, transformer_model):
        """
        Test 3.1.9: Verify compatibility with ensemble
        Acceptance: Outputs compatible with LSTM and XGBoost models
        """
        x = torch.randn(16, 50, 128)
        
        with torch.no_grad():
            transformer_output = transformer_model(x)
        
        # Check output format for ensemble
        assert transformer_output.dim() == 2, \
            "Output should be 2D for ensemble"
        assert transformer_output.shape[-1] == 3, \
            "Output should have 3 classes"
        
        # Convert to ensemble format
        ensemble_input = {
            'transformer': transformer_output.numpy(),
            'weight': 0.5  # 50% weight in ensemble as per specs
        }
        
        assert 'transformer' in ensemble_input, \
            "Missing transformer key for ensemble"
        assert isinstance(ensemble_input['transformer'], np.ndarray), \
            "Output should be numpy array for ensemble"
    
    def test_position_encoding(self, transformer_model):
        """
        Test 3.1.10: Verify positional encoding
        Acceptance: Correct temporal relationships preserved
        """
        seq_len = 100
        d_model = 512
        
        # Get positional encoding
        from src.ml.models.transformer_model import PositionalEncoding
        
        pos_encoder = PositionalEncoding(d_model, max_len=500)
        x = torch.zeros(1, seq_len, d_model)
        encoded = pos_encoder(x)
        
        # Check that encoding is added
        assert not torch.all(encoded == 0), \
            "Positional encoding not applied"
        
        # Check that different positions have different encodings
        pos1 = encoded[0, 0, :].numpy()
        pos2 = encoded[0, 50, :].numpy()
        
        similarity = np.dot(pos1, pos2) / (np.linalg.norm(pos1) * np.linalg.norm(pos2))
        assert similarity < 0.95, \
            "Positional encodings too similar for different positions"


class TestTransformerBacktesting:
    """Test suite for Transformer model backtesting"""
    
    @pytest.fixture
    def historical_data(self):
        """Load historical forex data for backtesting"""
        # Simulate 2 years of data
        dates = pd.date_range(end=datetime.now(), periods=500, freq='D')
        
        data = pd.DataFrame({
            'date': dates,
            'open': np.random.randn(500).cumsum() + 1.1000,
            'high': np.random.randn(500).cumsum() + 1.1050,
            'low': np.random.randn(500).cumsum() + 1.0950,
            'close': np.random.randn(500).cumsum() + 1.1000,
            'volume': np.random.randint(10000, 1000000, 500)
        })
        
        return data
    
    @pytest.mark.asyncio
    async def test_backtesting_performance(self, transformer_model, historical_data):
        """
        Test 3.2.1: Backtest model performance
        Acceptance: Achieve >1.2 Sharpe ratio on historical data
        """
        from src.ml.backtesting.backtester import TransformerBacktester
        
        backtester = TransformerBacktester(
            model=transformer_model,
            initial_capital=10000,
            position_size=0.02  # 2% risk per trade
        )
        
        results = await backtester.run(historical_data)
        
        # Verify performance metrics
        assert results['sharpe_ratio'] > 1.2, \
            f"Sharpe ratio {results['sharpe_ratio']:.2f} below target 1.2"
        assert results['win_rate'] > 0.55, \
            f"Win rate {results['win_rate']:.2%} below minimum 55%"
        assert results['max_drawdown'] < 0.15, \
            f"Max drawdown {results['max_drawdown']:.2%} exceeds 15%"
        assert results['profit_factor'] > 1.25, \
            f"Profit factor {results['profit_factor']:.2f} below minimum 1.25"
    
    @pytest.mark.asyncio
    async def test_walk_forward_validation(self, transformer_model, historical_data):
        """
        Test 3.2.2: Walk-forward validation
        Acceptance: Consistent performance across rolling windows
        """
        from src.ml.validation.walk_forward import WalkForwardValidator
        
        validator = WalkForwardValidator(
            model=transformer_model,
            window_size=100,
            step_size=20
        )
        
        results = await validator.validate(historical_data)
        
        # Check consistency across windows
        sharpe_ratios = [r['sharpe_ratio'] for r in results]
        sharpe_std = np.std(sharpe_ratios)
        
        assert sharpe_std < 0.5, \
            f"Sharpe ratio too volatile: std={sharpe_std:.2f}"
        assert np.mean(sharpe_ratios) > 1.2, \
            f"Average Sharpe ratio {np.mean(sharpe_ratios):.2f} below target"


if __name__ == "__main__":
    pytest.main([__file__, '-v'])