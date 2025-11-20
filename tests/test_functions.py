"""
Tests for data_utils.py and model_runner.py (simplified, no external Yahoo calls).
"""
import pandas as pd
import numpy as np
import data_utils
import model_runner


def test_validate_symbol():
    """Test symbol validation."""
    # Invalid symbols should return None
    df, ticker = data_utils.fetch_stock('!!!INVALID!!!')
    assert df is None and ticker is None


def test_fetch_returns_types():
    """Test that fetch_stock returns correct types when it fails."""
    result = data_utils.fetch_stock('NOTEXIST12345')  
    assert isinstance(result, tuple)
    assert len(result) == 2


def test_create_supervised_data():
    """Test supervised data creation."""
    s = pd.Series([100.0 + i * 0.5 for i in range(200)])
    X, y = model_runner.create_dataset(s, window_size=30)
    
    assert X.shape[0] == len(s) - 30
    assert X.shape[1] == 30
    assert X.shape[2] == 1
    assert y.shape[0] == len(s) - 30


def test_predict_output_shape():
    """Test prediction shapes (synthetic data)."""
    # Create synthetic sine series
    x = np.arange(300)
    vals = np.sin(x * 0.05) * 10 + 100
    s = pd.Series(vals)
    
    # Train quickly
    model, scaler = model_runner.train_model(s, window_size=30, epochs=1)
    preds = model_runner.predict_future(model, scaler, s, days=5, window_size=30)
    conf = model_runner.mc_dropout_confidence(model, scaler, s, days=5, window_size=30, runs=10)
    
    assert len(preds) == 5
    assert isinstance(conf, float)
    assert 0 <= conf <= 100
