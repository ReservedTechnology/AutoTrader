"""
Integration Test for Trading Halt Systems
Following TDD methodology for forex bot targeting 25% annual returns
Tests circuit breakers, risk limits, and emergency stops
"""
import pytest
import numpy as np
import pandas as pd
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
import json
import os
from typing import Dict, List, Optional
from enum import Enum


class HaltReason(Enum):
    DAILY_LOSS_LIMIT = "daily_loss_limit"
    CONSECUTIVE_LOSSES = "consecutive_losses"
    TECHNICAL_ERROR = "technical_error"
    RISK_BREACH = "risk_breach"
    VOLATILITY_SPIKE = "volatility_spike"
    CORRELATION_BREAKDOWN = "correlation_breakdown"
    SYSTEM_OVERLOAD = "system_overload"
    REGULATORY = "regulatory"


class TestTradingHaltSystems:
    """Integration test for trading halt and circuit breaker systems"""
    
    @pytest.fixture
    def halt_manager(self):
        """Initialize trading halt manager"""
        from src.risk.trading_halt_manager import TradingHaltManager
        
        manager = TradingHaltManager(
            daily_loss_limit=0.03,  # 3% daily loss limit
            consecutive_loss_limit=5,
            max_positions=5,
            volatility_threshold=0.03  # 3% volatility spike
        )
        return manager
    
    @pytest.fixture
    def trading_state(self):
        """Current trading state"""
        return {
            'account_equity': 100000,
            'starting_equity': 100000,
            'open_positions': 3,
            'daily_pnl': -500,
            'consecutive_losses': 2,
            'last_trade_time': datetime.now() - timedelta(minutes=5),
            'system_health': 'healthy'
        }
    
    @pytest.mark.integration
    def test_daily_loss_circuit_breaker(self, halt_manager, trading_state):
        """
        Test IT.7.1: Daily loss limit circuit breaker
        Acceptance: Halt trading at 3% daily loss
        """
        # Update with significant loss
        trading_state['daily_pnl'] = -3100  # -3.1% loss
        
        # Check if should halt
        halt_check = halt_manager.check_daily_loss_limit(trading_state)
        
        assert halt_check['should_halt'] is True
        assert halt_check['reason'] == HaltReason.DAILY_LOSS_LIMIT
        assert halt_check['severity'] == 'critical'
        
        # Calculate time until reset
        reset_time = halt_manager.calculate_reset_time(halt_check['reason'])
        assert reset_time > datetime.now()
        
        # Should close all positions
        actions = halt_manager.get_halt_actions(halt_check['reason'])
        assert 'close_all_positions' in actions
        assert actions['close_all_positions'] is True
        assert actions['allow_new_trades'] is False
        
        # Test warning level (approaching limit)
        trading_state['daily_pnl'] = -2500  # -2.5% loss
        warning_check = halt_manager.check_daily_loss_limit(trading_state)
        
        assert warning_check['should_halt'] is False
        assert warning_check['warning_level'] == 'high'
        assert warning_check['remaining_risk'] == 500  # $500 until halt
    
    @pytest.mark.integration
    def test_consecutive_loss_halt(self, halt_manager):
        """
        Test IT.7.2: Consecutive losses circuit breaker
        Acceptance: Halt after 5 consecutive losses
        """
        trades = [
            {'result': 'loss', 'amount': -100},
            {'result': 'loss', 'amount': -150},
            {'result': 'loss', 'amount': -80},
            {'result': 'loss', 'amount': -120},
            {'result': 'loss', 'amount': -90}
        ]
        
        # Check consecutive losses
        halt_check = halt_manager.check_consecutive_losses(trades)
        
        assert halt_check['should_halt'] is True
        assert halt_check['reason'] == HaltReason.CONSECUTIVE_LOSSES
        assert halt_check['consecutive_count'] == 5
        
        # Suggested cooldown period
        cooldown = halt_manager.get_cooldown_period(HaltReason.CONSECUTIVE_LOSSES)
        assert cooldown['duration_hours'] >= 1
        assert cooldown['allow_close_only'] is True
        
        # Test with mixed results (no halt)
        mixed_trades = [
            {'result': 'loss', 'amount': -100},
            {'result': 'win', 'amount': 150},
            {'result': 'loss', 'amount': -80}
        ]
        
        no_halt = halt_manager.check_consecutive_losses(mixed_trades)
        assert no_halt['should_halt'] is False
    
    @pytest.mark.integration
    def test_volatility_spike_halt(self, halt_manager):
        """
        Test IT.7.3: Volatility spike circuit breaker
        Acceptance: Halt on extreme volatility
        """
        # Normal volatility
        normal_data = {
            'current_volatility': 0.015,
            'average_volatility': 0.012,
            'volatility_percentile': 75
        }
        
        normal_check = halt_manager.check_volatility_halt(normal_data)
        assert normal_check['should_halt'] is False
        
        # Extreme volatility spike
        spike_data = {
            'current_volatility': 0.045,  # 4.5% volatility
            'average_volatility': 0.012,
            'volatility_percentile': 99,
            'volatility_ratio': 3.75  # Current/Average
        }
        
        spike_check = halt_manager.check_volatility_halt(spike_data)
        
        assert spike_check['should_halt'] is True
        assert spike_check['reason'] == HaltReason.VOLATILITY_SPIKE
        assert spike_check['action'] == 'reduce_exposure'
        
        # Gradual position reduction
        reduction_plan = halt_manager.calculate_position_reduction(
            current_positions=5,
            volatility_ratio=spike_data['volatility_ratio']
        )
        
        assert reduction_plan['target_positions'] < 5
        assert reduction_plan['close_count'] >= 2
        assert reduction_plan['priority'] == 'highest_risk_first'
    
    @pytest.mark.integration
    def test_technical_error_halt(self, halt_manager):
        """
        Test IT.7.4: Technical error circuit breaker
        Acceptance: Halt on system failures
        """
        # Data feed error
        feed_error = {
            'error_type': 'data_feed_disconnected',
            'affected_pairs': ['EUR_USD', 'GBP_USD'],
            'duration_seconds': 65,
            'error_count': 3
        }
        
        feed_halt = halt_manager.check_technical_halt(feed_error)
        
        assert feed_halt['should_halt'] is True
        assert feed_halt['reason'] == HaltReason.TECHNICAL_ERROR
        assert feed_halt['affected_trading'] == ['EUR_USD', 'GBP_USD']
        
        # Database connection error
        db_error = {
            'error_type': 'database_connection_lost',
            'affected_service': 'timescale',
            'retry_count': 5,
            'last_success': datetime.now() - timedelta(minutes=2)
        }
        
        db_halt = halt_manager.check_technical_halt(db_error)
        
        assert db_halt['should_halt'] is True
        assert db_halt['severity'] == 'critical'
        assert db_halt['recovery_action'] == 'attempt_reconnection'
    
    @pytest.mark.integration
    def test_risk_breach_halt(self, halt_manager):
        """
        Test IT.7.5: Risk limit breach circuit breaker
        Acceptance: Halt on risk parameter violations
        """
        risk_metrics = {
            'portfolio_heat': 0.062,  # 6.2% (limit 5%)
            'var_95': 0.045,  # 4.5% VaR
            'correlation_exposure': 0.85,
            'largest_position_pct': 0.35
        }
        
        risk_limits = {
            'max_portfolio_heat': 0.05,
            'max_var': 0.04,
            'max_correlation': 0.70,
            'max_position': 0.30
        }
        
        breach_check = halt_manager.check_risk_breach(risk_metrics, risk_limits)
        
        assert breach_check['should_halt'] is True
        assert breach_check['reason'] == HaltReason.RISK_BREACH
        assert len(breach_check['breached_limits']) >= 2
        
        # Check specific breaches
        breaches = breach_check['breached_limits']
        assert 'portfolio_heat' in breaches
        assert 'correlation_exposure' in breaches
        
        # Remediation actions
        remediation = halt_manager.get_remediation_plan(breaches)
        assert 'reduce_positions' in remediation
        assert 'close_correlated' in remediation
        assert remediation['target_heat'] <= 0.05
    
    @pytest.mark.integration
    def test_gradual_halt_implementation(self, halt_manager):
        """
        Test IT.7.6: Gradual halt implementation
        Acceptance: Phased trading reduction
        """
        # Minor issue - reduce trading
        minor_issue = {
            'severity': 'warning',
            'metric': 'win_rate',
            'current_value': 0.42,  # Below 45% threshold
            'threshold': 0.45
        }
        
        minor_response = halt_manager.determine_response(minor_issue)
        
        assert minor_response['action'] == 'reduce_trading'
        assert minor_response['new_position_limit'] == 3  # From 5 to 3
        assert minor_response['risk_reduction'] == 0.25  # 25% risk reduction
        assert minor_response['allow_new_trades'] is True
        
        # Moderate issue - close only mode
        moderate_issue = {
            'severity': 'high',
            'metric': 'sharpe_ratio',
            'current_value': 0.3,
            'threshold': 0.75
        }
        
        moderate_response = halt_manager.determine_response(moderate_issue)
        
        assert moderate_response['action'] == 'close_only'
        assert moderate_response['allow_new_trades'] is False
        assert moderate_response['allow_close_trades'] is True
        
        # Severe issue - full halt
        severe_issue = {
            'severity': 'critical',
            'metric': 'system_error_rate',
            'current_value': 0.15,  # 15% error rate
            'threshold': 0.05
        }
        
        severe_response = halt_manager.determine_response(severe_issue)
        
        assert severe_response['action'] == 'full_halt'
        assert severe_response['close_all_positions'] is True
        assert severe_response['shutdown_trading'] is True
    
    @pytest.mark.integration
    def test_halt_recovery_procedures(self, halt_manager):
        """
        Test IT.7.7: Halt recovery and restart procedures
        Acceptance: Safe trading resumption
        """
        # Record halt
        halt_event = {
            'halt_id': 'HALT001',
            'reason': HaltReason.DAILY_LOSS_LIMIT,
            'timestamp': datetime.now() - timedelta(hours=2),
            'severity': 'critical'
        }
        
        halt_manager.record_halt(halt_event)
        
        # Check if can resume
        can_resume = halt_manager.check_resume_conditions(halt_event['halt_id'])
        
        # Should check multiple conditions
        assert 'time_elapsed' in can_resume
        assert 'risk_metrics_ok' in can_resume
        assert 'system_health_ok' in can_resume
        
        # Create recovery plan
        recovery_plan = halt_manager.create_recovery_plan(halt_event['halt_id'])
        
        assert recovery_plan['start_mode'] == 'gradual'
        assert recovery_plan['initial_positions'] == 1  # Start with 1 position
        assert recovery_plan['initial_risk'] == 0.01  # 1% risk initially
        assert recovery_plan['monitoring_period_hours'] == 24
        
        # Gradual increase schedule
        assert len(recovery_plan['escalation_schedule']) > 0
        first_escalation = recovery_plan['escalation_schedule'][0]
        assert first_escalation['after_hours'] == 4
        assert first_escalation['new_position_limit'] == 2
        assert first_escalation['new_risk_limit'] == 0.015
    
    @pytest.mark.integration
    def test_correlated_halt_management(self, halt_manager):
        """
        Test IT.7.8: Manage halts across correlated instruments
        Acceptance: Coordinate halts for related pairs
        """
        # Halt on EUR/USD
        eur_halt = {
            'pair': 'EUR_USD',
            'reason': HaltReason.VOLATILITY_SPIKE,
            'correlation_matrix': {
                'EUR_USD': 1.0,
                'EUR_GBP': 0.85,
                'EUR_JPY': 0.75,
                'GBP_USD': 0.70
            }
        }
        
        # Determine affected pairs
        affected = halt_manager.determine_affected_pairs(
            eur_halt,
            correlation_threshold=0.70
        )
        
        assert 'EUR_GBP' in affected
        assert 'EUR_JPY' in affected
        assert 'GBP_USD' in affected
        
        # Create coordinated response
        response = halt_manager.coordinate_halt_response(affected)
        
        assert response['EUR_GBP']['action'] == 'halt'  # High correlation
        assert response['EUR_JPY']['action'] == 'reduce'  # Moderate correlation
        assert response['GBP_USD']['action'] == 'monitor'  # Lower correlation
    
    @pytest.mark.integration
    def test_halt_notification_system(self, halt_manager):
        """
        Test IT.7.9: Halt notification and logging
        Acceptance: Comprehensive alerting and audit trail
        """
        halt_event = {
            'halt_id': 'HALT002',
            'reason': HaltReason.RISK_BREACH,
            'severity': 'critical',
            'affected_positions': 5,
            'estimated_impact': -2500,
            'timestamp': datetime.now()
        }
        
        # Generate notifications
        notifications = halt_manager.create_notifications(halt_event)
        
        assert len(notifications) > 0
        
        # Check notification priorities
        critical_notif = [n for n in notifications if n['priority'] == 'critical']
        assert len(critical_notif) > 0
        
        # Verify notification content
        first_notif = notifications[0]
        assert 'title' in first_notif
        assert 'message' in first_notif
        assert 'channels' in first_notif
        assert 'email' in first_notif['channels']
        assert 'sms' in first_notif['channels']  # Critical should use SMS
        
        # Create audit log
        audit_log = halt_manager.create_audit_log(halt_event)
        
        assert audit_log['event_type'] == 'trading_halt'
        assert audit_log['reason'] == halt_event['reason'].value
        assert 'pre_halt_state' in audit_log
        assert 'actions_taken' in audit_log
        assert 'recovery_plan' in audit_log


if __name__ == "__main__":
    pytest.main([__file__, '-v', '-m', 'integration'])