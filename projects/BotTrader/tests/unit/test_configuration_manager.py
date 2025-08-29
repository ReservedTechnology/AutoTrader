"""
Test Suite for Configuration Manager
Following TDD methodology for forex bot targeting 25% annual returns
Tests for configuration loading, validation, and dynamic updates
"""
import pytest
import numpy as np
import pandas as pd
from unittest.mock import Mock, patch, MagicMock, mock_open
from datetime import datetime, timedelta
import json
import yaml
import os
from pathlib import Path


class TestConfigurationManager:
    """Test suite for configuration management"""
    
    @pytest.fixture
    def config_manager(self):
        """Initialize configuration manager"""
        from src.config.configuration_manager import ConfigurationManager
        
        manager = ConfigurationManager(
            config_dir='config/',
            environment='development'
        )
        return manager
    
    @pytest.fixture
    def sample_config(self):
        """Sample configuration data"""
        return {
            'trading': {
                'pairs': ['EUR_USD', 'GBP_USD', 'USD_JPY'],
                'max_positions': 5,
                'risk_per_trade': 0.02,
                'max_portfolio_heat': 0.05
            },
            'ml_models': {
                'transformer': {
                    'enabled': True,
                    'weight': 0.5,
                    'params': {
                        'attention_heads': 12,
                        'layers': 6,
                        'dropout': 0.1
                    }
                },
                'lstm': {
                    'enabled': True,
                    'weight': 0.3,
                    'params': {
                        'units': 256,
                        'layers': 4
                    }
                }
            },
            'apis': {
                'oanda': {
                    'environment': 'practice',
                    'timeout': 30,
                    'max_retries': 3
                }
            }
        }
    
    def test_load_yaml_config(self, config_manager, sample_config):
        """
        Test 14.1.1: Load YAML configuration
        Acceptance: Parse YAML files correctly
        """
        yaml_content = yaml.dump(sample_config)
        
        with patch('builtins.open', mock_open(read_data=yaml_content)):
            config = config_manager.load_yaml('config.yaml')
            
            assert config['trading']['pairs'] == ['EUR_USD', 'GBP_USD', 'USD_JPY']
            assert config['trading']['risk_per_trade'] == 0.02
            assert config['ml_models']['transformer']['enabled'] is True
    
    def test_load_json_config(self, config_manager, sample_config):
        """
        Test 14.1.2: Load JSON configuration
        Acceptance: Parse JSON files correctly
        """
        json_content = json.dumps(sample_config)
        
        with patch('builtins.open', mock_open(read_data=json_content)):
            config = config_manager.load_json('config.json')
            
            assert config['trading']['max_positions'] == 5
            assert config['apis']['oanda']['max_retries'] == 3
    
    def test_environment_override(self, config_manager):
        """
        Test 14.1.3: Environment-specific overrides
        Acceptance: Apply environment configs
        """
        base_config = {
            'database': {
                'host': 'localhost',
                'port': 5432,
                'name': 'bottrader'
            },
            'trading': {
                'mode': 'paper'
            }
        }
        
        prod_override = {
            'database': {
                'host': 'prod.db.server',
                'name': 'bottrader_prod'
            },
            'trading': {
                'mode': 'live'
            }
        }
        
        # Apply production overrides
        config_manager.environment = 'production'
        merged = config_manager.merge_configs(base_config, prod_override)
        
        assert merged['database']['host'] == 'prod.db.server'
        assert merged['database']['port'] == 5432  # Unchanged
        assert merged['database']['name'] == 'bottrader_prod'
        assert merged['trading']['mode'] == 'live'
    
    def test_config_validation(self, config_manager):
        """
        Test 14.1.4: Validate configuration
        Acceptance: Catch invalid configs
        """
        # Valid config
        valid_config = {
            'trading': {
                'risk_per_trade': 0.02,
                'max_positions': 5
            }
        }
        
        schema = {
            'trading': {
                'risk_per_trade': {'type': 'float', 'min': 0.001, 'max': 0.05},
                'max_positions': {'type': 'int', 'min': 1, 'max': 10}
            }
        }
        
        is_valid = config_manager.validate_config(valid_config, schema)
        assert is_valid is True
        
        # Invalid config (risk too high)
        invalid_config = {
            'trading': {
                'risk_per_trade': 0.10,  # Too high
                'max_positions': 5
            }
        }
        
        is_valid = config_manager.validate_config(invalid_config, schema)
        assert is_valid is False
        
        errors = config_manager.get_validation_errors(invalid_config, schema)
        assert 'risk_per_trade' in str(errors)
    
    def test_secure_credential_loading(self, config_manager):
        """
        Test 14.1.5: Secure credential management
        Acceptance: Load secrets safely
        """
        # Test environment variable loading
        with patch.dict(os.environ, {
            'OANDA_API_KEY': 'secret_key_123',
            'DB_PASSWORD': 'secure_pass'
        }):
            credentials = config_manager.load_credentials()
            
            assert credentials['oanda_api_key'] == 'secret_key_123'
            assert credentials['db_password'] == 'secure_pass'
        
        # Test secrets file loading (encrypted)
        encrypted_secrets = {
            'alpha_vantage_key': 'encrypted_AV123',
            'telegram_token': 'encrypted_TG456'
        }
        
        with patch.object(config_manager, 'decrypt') as mock_decrypt:
            mock_decrypt.side_effect = lambda x: x.replace('encrypted_', '')
            
            with patch('builtins.open', mock_open(read_data=json.dumps(encrypted_secrets))):
                secrets = config_manager.load_secrets_file('.secrets.json')
                
                assert secrets['alpha_vantage_key'] == 'AV123'
                assert secrets['telegram_token'] == 'TG456'


class TestDynamicConfiguration:
    """Test suite for dynamic configuration updates"""
    
    @pytest.fixture
    def dynamic_config(self):
        """Initialize dynamic configuration manager"""
        from src.config.dynamic_config import DynamicConfigManager
        
        manager = DynamicConfigManager()
        return manager
    
    def test_hot_reload(self, dynamic_config):
        """
        Test 14.2.1: Hot reload configuration
        Acceptance: Apply changes without restart
        """
        initial_config = {
            'trading': {'risk_per_trade': 0.02}
        }
        
        dynamic_config.load_config(initial_config)
        assert dynamic_config.get('trading.risk_per_trade') == 0.02
        
        # Simulate config file change
        updated_config = {
            'trading': {'risk_per_trade': 0.015}
        }
        
        # Trigger hot reload
        dynamic_config.reload(updated_config)
        
        assert dynamic_config.get('trading.risk_per_trade') == 0.015
        assert dynamic_config.reload_count == 1
    
    def test_config_change_callbacks(self, dynamic_config):
        """
        Test 14.2.2: Configuration change callbacks
        Acceptance: Notify on config changes
        """
        callback_called = False
        callback_args = None
        
        def on_risk_change(old_value, new_value):
            nonlocal callback_called, callback_args
            callback_called = True
            callback_args = (old_value, new_value)
        
        # Register callback
        dynamic_config.register_callback(
            'trading.risk_per_trade',
            on_risk_change
        )
        
        # Load initial config
        dynamic_config.load_config({'trading': {'risk_per_trade': 0.02}})
        
        # Update config
        dynamic_config.set('trading.risk_per_trade', 0.015)
        
        assert callback_called is True
        assert callback_args == (0.02, 0.015)
    
    def test_config_versioning(self, dynamic_config):
        """
        Test 14.2.3: Configuration versioning
        Acceptance: Track config history
        """
        # Load multiple versions
        configs = [
            {'version': '1.0.0', 'trading': {'pairs': ['EUR_USD']}},
            {'version': '1.1.0', 'trading': {'pairs': ['EUR_USD', 'GBP_USD']}},
            {'version': '1.2.0', 'trading': {'pairs': ['EUR_USD', 'GBP_USD', 'USD_JPY']}}
        ]
        
        for config in configs:
            dynamic_config.load_config(config)
        
        # Check version history
        history = dynamic_config.get_version_history()
        assert len(history) == 3
        assert history[-1]['version'] == '1.2.0'
        
        # Rollback to previous version
        dynamic_config.rollback_to_version('1.1.0')
        assert dynamic_config.get('trading.pairs') == ['EUR_USD', 'GBP_USD']
    
    def test_config_persistence(self, dynamic_config):
        """
        Test 14.2.4: Persist configuration changes
        Acceptance: Save runtime changes
        """
        config = {
            'trading': {
                'risk_per_trade': 0.02,
                'max_positions': 5
            }
        }
        
        dynamic_config.load_config(config)
        
        # Make runtime changes
        dynamic_config.set('trading.risk_per_trade', 0.025)
        dynamic_config.set('trading.stop_loss_atr_multiplier', 2.0)
        
        # Save to file
        with patch('builtins.open', mock_open()) as mock_file:
            dynamic_config.save_to_file('runtime_config.yaml')
            
            # Verify save was called
            mock_file.assert_called_once_with('runtime_config.yaml', 'w')
            
            # Check saved content
            handle = mock_file()
            written_content = ''.join(call.args[0] for call in handle.write.call_args_list)
            
            assert '0.025' in written_content
            assert 'stop_loss_atr_multiplier' in written_content


class TestConfigurationTemplates:
    """Test suite for configuration templates"""
    
    @pytest.fixture
    def template_manager(self):
        """Initialize template manager"""
        from src.config.template_manager import ConfigTemplateManager
        
        manager = ConfigTemplateManager()
        return manager
    
    def test_conservative_template(self, template_manager):
        """
        Test 14.3.1: Conservative trading template
        Acceptance: Low-risk configuration
        """
        config = template_manager.get_template('conservative')
        
        assert config['trading']['risk_per_trade'] == 0.01
        assert config['trading']['max_positions'] == 3
        assert config['trading']['max_portfolio_heat'] == 0.03
        assert config['ml_models']['confidence_threshold'] == 0.7
        assert config['execution']['algorithm'] == 'TWAP'
    
    def test_aggressive_template(self, template_manager):
        """
        Test 14.3.2: Aggressive trading template
        Acceptance: High-risk/reward configuration
        """
        config = template_manager.get_template('aggressive')
        
        assert config['trading']['risk_per_trade'] == 0.03
        assert config['trading']['max_positions'] == 7
        assert config['trading']['max_portfolio_heat'] == 0.08
        assert config['ml_models']['confidence_threshold'] == 0.55
        assert config['execution']['algorithm'] == 'MARKET'
    
    def test_scalping_template(self, template_manager):
        """
        Test 14.3.3: Scalping strategy template
        Acceptance: High-frequency configuration
        """
        config = template_manager.get_template('scalping')
        
        assert config['timeframes']['primary'] == '1m'
        assert config['indicators']['rsi']['period'] == 9
        assert config['trading']['holding_time_target'] == 300  # 5 minutes
        assert config['execution']['max_slippage_pips'] == 1
        assert config['pairs'] == ['EUR_USD', 'GBP_USD']  # High liquidity pairs
    
    def test_swing_trading_template(self, template_manager):
        """
        Test 14.3.4: Swing trading template
        Acceptance: Multi-day holding configuration
        """
        config = template_manager.get_template('swing')
        
        assert config['timeframes']['primary'] == '4h'
        assert config['timeframes']['confirmation'] == '1d'
        assert config['indicators']['rsi']['period'] == 14
        assert config['trading']['holding_time_target'] == 172800  # 2 days
        assert config['risk']['use_trailing_stop'] is True


class TestConfigurationMonitoring:
    """Test suite for configuration monitoring"""
    
    @pytest.fixture
    def config_monitor(self):
        """Initialize configuration monitor"""
        from src.config.config_monitor import ConfigurationMonitor
        
        monitor = ConfigurationMonitor()
        return monitor
    
    def test_config_drift_detection(self, config_monitor):
        """
        Test 14.4.1: Detect configuration drift
        Acceptance: Alert on unexpected changes
        """
        baseline_config = {
            'trading': {
                'risk_per_trade': 0.02,
                'max_positions': 5
            }
        }
        
        config_monitor.set_baseline(baseline_config)
        
        # No drift
        current_config = baseline_config.copy()
        drift = config_monitor.detect_drift(current_config)
        assert drift is None
        
        # Detect drift
        drifted_config = {
            'trading': {
                'risk_per_trade': 0.025,  # Changed
                'max_positions': 5
            }
        }
        
        drift = config_monitor.detect_drift(drifted_config)
        assert drift is not None
        assert 'trading.risk_per_trade' in drift
        assert drift['trading.risk_per_trade']['old'] == 0.02
        assert drift['trading.risk_per_trade']['new'] == 0.025
    
    def test_config_audit_trail(self, config_monitor):
        """
        Test 14.4.2: Maintain configuration audit trail
        Acceptance: Track all config changes
        """
        # Record changes
        changes = [
            {
                'timestamp': datetime.now() - timedelta(hours=2),
                'user': 'system',
                'change': {'trading.risk_per_trade': {'old': 0.02, 'new': 0.025}},
                'reason': 'Increased risk after positive performance'
            },
            {
                'timestamp': datetime.now() - timedelta(hours=1),
                'user': 'trader1',
                'change': {'trading.max_positions': {'old': 5, 'new': 4}},
                'reason': 'Reduced positions due to volatility'
            }
        ]
        
        for change in changes:
            config_monitor.record_change(change)
        
        # Query audit trail
        audit_log = config_monitor.get_audit_trail(hours=24)
        
        assert len(audit_log) == 2
        assert audit_log[0]['user'] == 'system'
        assert 'risk_per_trade' in str(audit_log[0]['change'])
    
    def test_config_compliance_check(self, config_monitor):
        """
        Test 14.4.3: Configuration compliance validation
        Acceptance: Ensure regulatory compliance
        """
        compliance_rules = {
            'max_leverage': 30,  # ESMA regulation
            'min_margin': 0.033,  # 3.3% minimum
            'max_risk_per_trade': 0.05,
            'required_risk_warning': True
        }
        
        # Compliant config
        config = {
            'trading': {
                'leverage': 20,
                'margin_requirement': 0.05,
                'risk_per_trade': 0.02,
                'risk_warning_enabled': True
            }
        }
        
        is_compliant = config_monitor.check_compliance(config, compliance_rules)
        assert is_compliant is True
        
        # Non-compliant config
        bad_config = {
            'trading': {
                'leverage': 50,  # Too high
                'margin_requirement': 0.02,  # Too low
                'risk_per_trade': 0.02,
                'risk_warning_enabled': False
            }
        }
        
        is_compliant = config_monitor.check_compliance(bad_config, compliance_rules)
        assert is_compliant is False
        
        violations = config_monitor.get_compliance_violations(bad_config, compliance_rules)
        assert 'leverage' in violations
        assert 'margin_requirement' in violations
        assert 'risk_warning_enabled' in violations
    
    def test_config_performance_impact(self, config_monitor):
        """
        Test 14.4.4: Track config impact on performance
        Acceptance: Correlate config changes with results
        """
        # Record config change
        config_monitor.record_change({
            'timestamp': datetime(2025, 1, 20, 10, 0),
            'change': {'trading.risk_per_trade': {'old': 0.02, 'new': 0.025}}
        })
        
        # Record performance metrics
        performance_before = {
            'date_range': (datetime(2025, 1, 1), datetime(2025, 1, 20)),
            'sharpe_ratio': 1.2,
            'win_rate': 0.58,
            'avg_daily_return': 0.001
        }
        
        performance_after = {
            'date_range': (datetime(2025, 1, 20), datetime(2025, 1, 29)),
            'sharpe_ratio': 1.4,
            'win_rate': 0.62,
            'avg_daily_return': 0.0015
        }
        
        impact = config_monitor.analyze_config_impact(
            config_change_date=datetime(2025, 1, 20, 10, 0),
            performance_before=performance_before,
            performance_after=performance_after
        )
        
        assert impact['sharpe_ratio_change'] == 0.2
        assert impact['win_rate_change'] == 0.04
        assert impact['return_change'] == 0.0005
        assert impact['assessment'] == 'positive'


if __name__ == "__main__":
    pytest.main([__file__, '-v'])