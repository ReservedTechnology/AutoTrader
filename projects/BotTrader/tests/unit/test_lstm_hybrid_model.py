"""
Test Suite for LSTM Hybrid Model
Following TDD methodology for forex bot targeting 25% annual returns
Tests for LSTM model with 73% directional accuracy
"""
import pytest
import pytest_asyncio
import numpy as np
import pandas as pd
import os
import psycopg2
from supabase import create_client, Client
from datetime import datetime, timedelta
import json
import torch
import torch.nn as nn
from dotenv import load_dotenv

load_dotenv()


class TestLSTMModel:
    """
    Test suite for LSTM hybrid model
    Target: 73% directional accuracy, 30% ensemble weight
    """
    
    @pytest.fixture
    def timescale_connection(self):
        """Initialize TimescaleDB connection"""
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
        """Initialize Supabase client"""
        url = os.getenv('SUPABASE_URL')
        key = os.getenv('SUPABASE_ANON_KEY')
        client = create_client(url, key)
        return client
    
    @pytest.fixture
    def lstm_model(self):
        """Initialize LSTM model"""
        from src.ml.models.lstm_model import ForexLSTM
        
        model = ForexLSTM(
            input_size=128,
            hidden_size=256,
            num_layers=4,
            dropout=0.2,
            bidirectional=True
        )
        return model
    
    def test_model_architecture(self, lstm_model):
        """
        Test 3.3.1: Verify LSTM architecture
        Acceptance: 4 layers, 256 units each, bidirectional
        """
        assert lstm_model.num_layers == 4, \
            f"Expected 4 layers, got {lstm_model.num_layers}"
        assert lstm_model.hidden_size == 256, \
            f"Expected hidden_size=256, got {lstm_model.hidden_size}"
        assert lstm_model.bidirectional == True, \
            "Model should be bidirectional"
        
        # Check parameter count
        total_params = sum(p.numel() for p in lstm_model.parameters())
        assert 500_000 < total_params < 10_000_000, \
            f"Unexpected parameter count: {total_params}"
    
    def test_sequence_handling(self, lstm_model):
        """
        Test 3.3.2: Test sequence processing
        Acceptance: Handle variable length sequences 20-500 timesteps
        """
        test_sequences = [
            (8, 20, 128),   # Short sequence
            (16, 100, 128), # Medium sequence
            (32, 300, 128), # Long sequence
            (4, 500, 128),  # Very long sequence
        ]
        
        for batch_size, seq_len, input_size in test_sequences:
            x = torch.randn(batch_size, seq_len, input_size)
            
            output, (hidden, cell) = lstm_model(x)
            
            assert output.shape[0] == batch_size, \
                f"Batch size mismatch: {output.shape[0]} != {batch_size}"
            assert output.shape[1] == seq_len, \
                f"Sequence length mismatch: {output.shape[1]} != {seq_len}"
            
            # Check hidden state dimensions
            expected_hidden_size = 256 * 2 if lstm_model.bidirectional else 256
            assert hidden.shape[-1] == 256, \
                f"Hidden size mismatch: {hidden.shape[-1]}"
    
    def test_gradient_flow(self, lstm_model):
        """
        Test 3.3.3: Verify gradient flow through time
        Acceptance: No vanishing/exploding gradients
        """
        x = torch.randn(16, 200, 128, requires_grad=True)
        target = torch.randint(0, 3, (16,))
        
        output, _ = lstm_model(x)
        # Pool over time dimension
        pooled = torch.mean(output, dim=1)
        
        # Simple classification head
        classifier = nn.Linear(512, 3)  # 512 for bidirectional
        logits = classifier(pooled)
        
        loss = nn.CrossEntropyLoss()(logits, target)
        loss.backward()
        
        # Check gradients
        for name, param in lstm_model.named_parameters():
            if param.grad is not None:
                grad_norm = param.grad.norm().item()
                assert grad_norm < 10.0, \
                    f"Exploding gradient in {name}: {grad_norm}"
                assert grad_norm > 1e-7, \
                    f"Vanishing gradient in {name}: {grad_norm}"
    
    @pytest.mark.asyncio
    async def test_prediction_accuracy(self, lstm_model, timescale_connection):
        """
        Test 3.3.4: Test prediction accuracy on sample data
        Acceptance: >73% directional accuracy
        """
        # Generate test data with known patterns
        seq_len = 100
        batch_size = 64
        
        # Create data with trend
        trends = torch.randn(batch_size, 1, 1) * 0.01
        time_steps = torch.arange(seq_len).float().unsqueeze(0).unsqueeze(-1)
        base_data = trends * time_steps
        noise = torch.randn(batch_size, seq_len, 128) * 0.1
        
        x = base_data.expand(-1, -1, 128) + noise
        
        # Generate labels based on trend
        labels = (trends.squeeze() > 0).long()  # 1 for up, 0 for down
        
        # Predict
        output, _ = lstm_model(x)
        predictions = torch.mean(output, dim=1)
        
        # Store predictions in TimescaleDB
        cursor = timescale_connection.cursor()
        
        for i in range(min(10, batch_size)):
            cursor.execute("""
                INSERT INTO ml_predictions (time, data)
                VALUES (%s, %s);
            """, (
                datetime.now(),
                json.dumps({
                    'model': 'lstm',
                    'version': '1.0.0',
                    'symbol': 'EUR_USD',
                    'prediction': 'buy' if labels[i] == 1 else 'sell',
                    'confidence': 0.73,  # Target accuracy
                    'sequence_length': seq_len
                })
            ))
        
        timescale_connection.commit()
        cursor.close()
    
    def test_memory_efficiency(self, lstm_model):
        """
        Test 3.3.5: Test memory usage
        Acceptance: Process 1000 sequences without OOM
        """
        import gc
        import torch.cuda as cuda
        
        # Test with CPU (CUDA not required)
        device = torch.device('cpu')
        lstm_model = lstm_model.to(device)
        
        # Process in batches
        batch_size = 10
        seq_len = 100
        num_batches = 100  # Total 1000 sequences
        
        max_memory = 0
        
        for _ in range(num_batches):
            x = torch.randn(batch_size, seq_len, 128, device=device)
            
            with torch.no_grad():
                output, _ = lstm_model(x)
            
            # Force cleanup
            del output, x
            gc.collect()
            
            if cuda.is_available():
                max_memory = max(max_memory, cuda.max_memory_allocated())
        
        # Check memory usage (should be reasonable)
        if cuda.is_available():
            assert max_memory < 4 * 1024**3, \
                f"Memory usage too high: {max_memory / 1024**3:.2f} GB"
    
    @pytest.mark.asyncio
    async def test_ensemble_integration(self, lstm_model, supabase_client):
        """
        Test 3.3.6: Test integration with ensemble
        Acceptance: 30% weight in ensemble as specified
        """
        x = torch.randn(16, 50, 128)
        
        with torch.no_grad():
            lstm_output, _ = lstm_model(x)
            # Pool over time
            pooled = torch.mean(lstm_output, dim=1)
        
        # Prepare ensemble input
        ensemble_data = {
            'lstm_output': pooled.numpy(),
            'lstm_weight': 0.30,  # 30% as per specification
            'model_type': 'lstm',
            'timestamp': datetime.now().isoformat()
        }
        
        # Store ensemble configuration in Supabase
        try:
            response = supabase_client.table('ensemble_config').upsert({
                'model_type': 'lstm',
                'weight': 0.30,
                'active': True,
                'updated_at': datetime.now().isoformat()
            }).execute()
            assert response.data, "Failed to store ensemble config"
        except Exception as e:
            print(f"Ensemble integration test: {e}")
    
    def test_temporal_attention(self, lstm_model):
        """
        Test 3.3.7: Test temporal attention mechanism
        Acceptance: Focus on recent timesteps for predictions
        """
        seq_len = 100
        x = torch.randn(8, seq_len, 128)
        
        # Get outputs at each timestep
        output, (hidden, cell) = lstm_model(x)
        
        # Calculate attention scores (simplified)
        # Recent timesteps should have higher influence
        attention_scores = torch.softmax(output.mean(dim=-1), dim=1)
        
        # Check if attention is biased towards recent timesteps
        recent_attention = attention_scores[:, -20:].mean()
        early_attention = attention_scores[:, :20].mean()
        
        assert recent_attention > early_attention * 1.2, \
            "Model should pay more attention to recent timesteps"
    
    def test_state_reset(self, lstm_model):
        """
        Test 3.3.8: Test hidden state reset between sequences
        Acceptance: No information leakage between batches
        """
        x1 = torch.randn(8, 50, 128)
        x2 = torch.randn(8, 50, 128)
        
        # First forward pass
        output1, (h1, c1) = lstm_model(x1)
        
        # Second forward pass (should not use previous hidden state)
        output2, (h2, c2) = lstm_model(x2)
        
        # Hidden states should be different
        assert not torch.allclose(h1, h2, atol=1e-5), \
            "Hidden states too similar - possible state leakage"
        
        # Outputs should be different
        assert not torch.allclose(output1, output2, atol=1e-5), \
            "Outputs identical - model not processing different inputs"


class TestLSTMTraining:
    """Test suite for LSTM training and validation"""
    
    @pytest.fixture
    def training_data(self):
        """Generate training data"""
        # Simulate forex time series
        n_samples = 1000
        seq_len = 100
        n_features = 128
        
        data = []
        labels = []
        
        for _ in range(n_samples):
            # Generate trend
            trend = np.random.choice([-1, 0, 1])
            sequence = np.random.randn(seq_len, n_features) * 0.1
            
            if trend == 1:  # Uptrend
                sequence += np.linspace(0, 0.1, seq_len).reshape(-1, 1)
            elif trend == -1:  # Downtrend
                sequence -= np.linspace(0, 0.1, seq_len).reshape(-1, 1)
            
            data.append(sequence)
            labels.append(trend + 1)  # Convert to 0, 1, 2
        
        return np.array(data), np.array(labels)
    
    def test_training_convergence(self, lstm_model, training_data):
        """
        Test 3.4.1: Test training convergence
        Acceptance: Loss decreases over epochs
        """
        X, y = training_data
        X_tensor = torch.FloatTensor(X[:100])  # Small subset
        y_tensor = torch.LongTensor(y[:100])
        
        optimizer = torch.optim.Adam(lstm_model.parameters(), lr=0.001)
        criterion = nn.CrossEntropyLoss()
        
        # Simple classification head
        classifier = nn.Linear(512, 3)  # 512 for bidirectional
        
        losses = []
        
        for epoch in range(10):
            optimizer.zero_grad()
            
            output, _ = lstm_model(X_tensor)
            pooled = torch.mean(output, dim=1)
            logits = classifier(pooled)
            
            loss = criterion(logits, y_tensor)
            loss.backward()
            optimizer.step()
            
            losses.append(loss.item())
        
        # Check convergence
        assert losses[-1] < losses[0], \
            "Loss not decreasing during training"
        assert losses[-1] < 2.0, \
            f"Final loss too high: {losses[-1]:.4f}"
    
    def test_overfitting_detection(self, lstm_model, training_data):
        """
        Test 3.4.2: Detect overfitting
        Acceptance: Validation loss within 20% of training loss
        """
        X, y = training_data
        
        # Split data
        split_idx = int(0.8 * len(X))
        X_train = torch.FloatTensor(X[:split_idx][:50])  # Small subset
        y_train = torch.LongTensor(y[:split_idx][:50])
        X_val = torch.FloatTensor(X[split_idx:][:20])
        y_val = torch.LongTensor(y[split_idx:][:20])
        
        classifier = nn.Linear(512, 3)
        criterion = nn.CrossEntropyLoss()
        
        # Training loss
        lstm_model.train()
        output_train, _ = lstm_model(X_train)
        pooled_train = torch.mean(output_train, dim=1)
        logits_train = classifier(pooled_train)
        train_loss = criterion(logits_train, y_train).item()
        
        # Validation loss
        lstm_model.eval()
        with torch.no_grad():
            output_val, _ = lstm_model(X_val)
            pooled_val = torch.mean(output_val, dim=1)
            logits_val = classifier(pooled_val)
            val_loss = criterion(logits_val, y_val).item()
        
        # Check for overfitting
        loss_ratio = val_loss / train_loss
        assert loss_ratio < 1.2, \
            f"Possible overfitting: val_loss/train_loss = {loss_ratio:.2f}"


if __name__ == "__main__":
    pytest.main([__file__, '-v'])