"""
Test Suite for Alert System
Following TDD methodology for forex bot targeting 25% annual returns
Tests for alerts, notifications, and monitoring
"""
import pytest
import numpy as np
import pandas as pd
from unittest.mock import Mock, patch, MagicMock, call
from datetime import datetime, timedelta
import json
import asyncio
from enum import Enum


class AlertLevel(Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"
    EMERGENCY = "EMERGENCY"


class AlertType(Enum):
    PRICE = "PRICE"
    RISK = "RISK"
    PERFORMANCE = "PERFORMANCE"
    SYSTEM = "SYSTEM"
    TRADE = "TRADE"


class TestAlertManager:
    """Test suite for alert management system"""
    
    @pytest.fixture
    def alert_manager(self):
        """Initialize alert manager"""
        from src.monitoring.alert_manager import AlertManager
        
        manager = AlertManager(
            channels=['email', 'webhook', 'log'],
            rate_limit_per_hour=100
        )
        return manager
    
    def test_alert_creation(self, alert_manager):
        """
        Test 13.1.1: Create and validate alerts
        Acceptance: Structured alert format
        """
        alert = alert_manager.create_alert(
            level=AlertLevel.WARNING,
            type=AlertType.RISK,
            title="High Portfolio Heat",
            message="Portfolio heat at 4.8%, approaching 5% limit",
            data={'heat': 0.048, 'limit': 0.05}
        )
        
        assert alert['id'] is not None
        assert alert['level'] == AlertLevel.WARNING
        assert alert['type'] == AlertType.RISK
        assert alert['timestamp'] is not None
        assert 'heat' in alert['data']
        assert alert['status'] == 'pending'
    
    def test_alert_priority_queue(self, alert_manager):
        """
        Test 13.1.2: Priority-based alert queue
        Acceptance: Process critical alerts first
        """
        # Create alerts with different priorities
        alerts = [
            alert_manager.create_alert(AlertLevel.INFO, AlertType.SYSTEM, "Info", "System update"),
            alert_manager.create_alert(AlertLevel.CRITICAL, AlertType.RISK, "Critical", "Stop loss hit"),
            alert_manager.create_alert(AlertLevel.WARNING, AlertType.PRICE, "Warning", "Price spike"),
            alert_manager.create_alert(AlertLevel.EMERGENCY, AlertType.SYSTEM, "Emergency", "System down")
        ]
        
        # Process queue
        processed_order = alert_manager.process_queue()
        
        # Should process in priority order: EMERGENCY > CRITICAL > WARNING > INFO
        assert processed_order[0]['level'] == AlertLevel.EMERGENCY
        assert processed_order[1]['level'] == AlertLevel.CRITICAL
        assert processed_order[2]['level'] == AlertLevel.WARNING
        assert processed_order[3]['level'] == AlertLevel.INFO
    
    def test_alert_rate_limiting(self, alert_manager):
        """
        Test 13.1.3: Rate limit alert sending
        Acceptance: Prevent alert flooding
        """
        # Send many alerts quickly
        sent_count = 0
        blocked_count = 0
        
        for i in range(150):
            alert = alert_manager.create_alert(
                AlertLevel.INFO,
                AlertType.PRICE,
                f"Alert {i}",
                "Test message"
            )
            
            if alert_manager.can_send_alert(alert):
                sent_count += 1
                alert_manager.record_sent(alert)
            else:
                blocked_count += 1
        
        # Should respect rate limit (100 per hour)
        assert sent_count <= 100
        assert blocked_count == 50
    
    def test_alert_deduplication(self, alert_manager):
        """
        Test 13.1.4: Deduplicate similar alerts
        Acceptance: Prevent duplicate notifications
        """
        # Create similar alerts
        alert1 = alert_manager.create_alert(
            AlertLevel.WARNING,
            AlertType.RISK,
            "High Drawdown",
            "Drawdown exceeds 10%",
            data={'drawdown': 0.11}
        )
        
        alert2 = alert_manager.create_alert(
            AlertLevel.WARNING,
            AlertType.RISK,
            "High Drawdown",
            "Drawdown exceeds 10%",
            data={'drawdown': 0.115}
        )
        
        # Check if duplicate
        is_duplicate = alert_manager.is_duplicate(
            alert2,
            time_window_seconds=300  # 5 minutes
        )
        
        assert is_duplicate is True
        
        # Different alert should not be duplicate
        alert3 = alert_manager.create_alert(
            AlertLevel.WARNING,
            AlertType.PRICE,
            "Price Alert",
            "EUR/USD breakout"
        )
        
        assert alert_manager.is_duplicate(alert3) is False
    
    def test_alert_aggregation(self, alert_manager):
        """
        Test 13.1.5: Aggregate related alerts
        Acceptance: Group similar alerts
        """
        # Create multiple related alerts
        alerts = []
        for i in range(5):
            alerts.append(alert_manager.create_alert(
                AlertLevel.WARNING,
                AlertType.TRADE,
                "Failed Order",
                f"Order {i} failed",
                data={'order_id': f'ORD{i}', 'reason': 'insufficient_margin'}
            ))
        
        # Aggregate alerts
        aggregated = alert_manager.aggregate_alerts(
            alerts,
            group_by='reason',
            time_window_seconds=60
        )
        
        assert len(aggregated) == 1  # All have same reason
        assert aggregated[0]['count'] == 5
        assert aggregated[0]['title'] == "Failed Order (5 occurrences)"
        assert 'insufficient_margin' in aggregated[0]['message']


class TestNotificationChannels:
    """Test suite for notification channels"""
    
    @pytest.fixture
    def notification_system(self):
        """Initialize notification system"""
        from src.monitoring.notification_system import NotificationSystem
        
        system = NotificationSystem()
        return system
    
    @patch('smtplib.SMTP')
    def test_email_notification(self, mock_smtp, notification_system):
        """
        Test 13.2.1: Send email notifications
        Acceptance: Deliver alerts via email
        """
        alert = {
            'level': AlertLevel.CRITICAL,
            'title': 'Critical Risk Alert',
            'message': 'Portfolio heat exceeded limit',
            'timestamp': datetime.now()
        }
        
        success = notification_system.send_email(
            alert,
            recipients=['trader@example.com'],
            smtp_config={
                'host': 'smtp.gmail.com',
                'port': 587,
                'user': 'bot@example.com',
                'password': 'secret'
            }
        )
        
        assert success is True
        mock_smtp.assert_called_once()
        
        # Verify email content
        smtp_instance = mock_smtp.return_value.__enter__.return_value
        assert smtp_instance.send_message.called
    
    @patch('requests.post')
    def test_webhook_notification(self, mock_post, notification_system):
        """
        Test 13.2.2: Send webhook notifications
        Acceptance: POST alerts to webhook URL
        """
        alert = {
            'level': AlertLevel.WARNING,
            'title': 'Price Alert',
            'message': 'EUR/USD reached target',
            'data': {'symbol': 'EUR_USD', 'price': 1.10500}
        }
        
        mock_post.return_value.status_code = 200
        
        success = notification_system.send_webhook(
            alert,
            webhook_url='https://hooks.slack.com/services/XXX',
            headers={'Content-Type': 'application/json'}
        )
        
        assert success is True
        mock_post.assert_called_once()
        
        # Verify payload
        call_args = mock_post.call_args
        payload = json.loads(call_args[1]['data'])
        assert payload['title'] == 'Price Alert'
        assert 'EUR_USD' in str(payload)
    
    @patch('telegram.Bot.send_message')
    def test_telegram_notification(self, mock_send, notification_system):
        """
        Test 13.2.3: Send Telegram notifications
        Acceptance: Deliver alerts via Telegram
        """
        alert = {
            'level': AlertLevel.INFO,
            'title': 'Trade Executed',
            'message': 'Long EUR/USD @ 1.10500'
        }
        
        mock_send.return_value = Mock(message_id=123)
        
        success = notification_system.send_telegram(
            alert,
            bot_token='123456:ABC-DEF',
            chat_id='-1001234567890'
        )
        
        assert success is True
        mock_send.assert_called_once()
    
    def test_multi_channel_broadcast(self, notification_system):
        """
        Test 13.2.4: Broadcast to multiple channels
        Acceptance: Send alert to all configured channels
        """
        alert = {
            'level': AlertLevel.CRITICAL,
            'title': 'System Critical',
            'message': 'Database connection lost'
        }
        
        with patch.object(notification_system, 'send_email') as mock_email:
            with patch.object(notification_system, 'send_webhook') as mock_webhook:
                with patch.object(notification_system, 'send_telegram') as mock_telegram:
                    mock_email.return_value = True
                    mock_webhook.return_value = True
                    mock_telegram.return_value = False  # One fails
                    
                    results = notification_system.broadcast(
                        alert,
                        channels=['email', 'webhook', 'telegram']
                    )
                    
                    assert results['email'] is True
                    assert results['webhook'] is True
                    assert results['telegram'] is False
                    assert results['success_rate'] == 2/3
    
    def test_notification_retry(self, notification_system):
        """
        Test 13.2.5: Retry failed notifications
        Acceptance: Retry with exponential backoff
        """
        alert = {
            'level': AlertLevel.WARNING,
            'title': 'Test Alert',
            'message': 'Testing retry logic'
        }
        
        with patch.object(notification_system, 'send_webhook') as mock_webhook:
            # Fail twice, then succeed
            mock_webhook.side_effect = [False, False, True]
            
            success = notification_system.send_with_retry(
                alert,
                channel='webhook',
                max_retries=3,
                backoff_seconds=1
            )
            
            assert success is True
            assert mock_webhook.call_count == 3


class TestAlertRules:
    """Test suite for alert rules and triggers"""
    
    @pytest.fixture
    def alert_rules(self):
        """Initialize alert rules engine"""
        from src.monitoring.alert_rules import AlertRulesEngine
        
        engine = AlertRulesEngine()
        return engine
    
    def test_threshold_rule(self, alert_rules):
        """
        Test 13.3.1: Threshold-based alert rules
        Acceptance: Trigger when value exceeds threshold
        """
        rule = alert_rules.create_rule(
            name='high_drawdown',
            type='threshold',
            field='drawdown',
            operator='>',
            value=0.10,
            alert_level=AlertLevel.WARNING
        )
        
        # Test triggering
        should_alert = alert_rules.evaluate_rule(
            rule,
            data={'drawdown': 0.12}
        )
        
        assert should_alert is True
        
        # Test not triggering
        should_not_alert = alert_rules.evaluate_rule(
            rule,
            data={'drawdown': 0.08}
        )
        
        assert should_not_alert is False
    
    def test_rate_of_change_rule(self, alert_rules):
        """
        Test 13.3.2: Rate of change alert rules
        Acceptance: Detect rapid changes
        """
        rule = alert_rules.create_rule(
            name='rapid_price_move',
            type='rate_of_change',
            field='price',
            threshold=0.01,  # 1% in time window
            time_window_seconds=60,
            alert_level=AlertLevel.WARNING
        )
        
        # Simulate price history
        price_history = [
            {'timestamp': datetime.now() - timedelta(seconds=90), 'price': 1.10000},
            {'timestamp': datetime.now() - timedelta(seconds=60), 'price': 1.10100},
            {'timestamp': datetime.now() - timedelta(seconds=30), 'price': 1.10300},
            {'timestamp': datetime.now(), 'price': 1.11200}  # >1% move
        ]
        
        should_alert = alert_rules.evaluate_rate_rule(rule, price_history)
        
        assert should_alert is True
    
    def test_pattern_detection_rule(self, alert_rules):
        """
        Test 13.3.3: Pattern-based alert rules
        Acceptance: Detect specific patterns
        """
        rule = alert_rules.create_rule(
            name='consecutive_losses',
            type='pattern',
            pattern='consecutive',
            field='trade_result',
            value='loss',
            count=3,
            alert_level=AlertLevel.WARNING
        )
        
        # Test with consecutive losses
        trades = [
            {'trade_result': 'win'},
            {'trade_result': 'loss'},
            {'trade_result': 'loss'},
            {'trade_result': 'loss'}
        ]
        
        should_alert = alert_rules.evaluate_pattern_rule(rule, trades)
        
        assert should_alert is True
        
        # Test without pattern
        trades_mixed = [
            {'trade_result': 'loss'},
            {'trade_result': 'win'},
            {'trade_result': 'loss'}
        ]
        
        should_not_alert = alert_rules.evaluate_pattern_rule(rule, trades_mixed)
        
        assert should_not_alert is False
    
    def test_composite_rule(self, alert_rules):
        """
        Test 13.3.4: Composite alert rules
        Acceptance: Combine multiple conditions
        """
        rule = alert_rules.create_composite_rule(
            name='high_risk_market',
            operator='AND',
            rules=[
                {
                    'type': 'threshold',
                    'field': 'volatility',
                    'operator': '>',
                    'value': 0.02
                },
                {
                    'type': 'threshold',
                    'field': 'spread',
                    'operator': '>',
                    'value': 0.0005
                }
            ],
            alert_level=AlertLevel.CRITICAL
        )
        
        # Both conditions true
        data_high_risk = {
            'volatility': 0.025,
            'spread': 0.0006
        }
        
        assert alert_rules.evaluate_composite_rule(rule, data_high_risk) is True
        
        # Only one condition true
        data_medium_risk = {
            'volatility': 0.025,
            'spread': 0.0003
        }
        
        assert alert_rules.evaluate_composite_rule(rule, data_medium_risk) is False
    
    def test_scheduled_rule(self, alert_rules):
        """
        Test 13.3.5: Scheduled alert rules
        Acceptance: Trigger at specific times
        """
        rule = alert_rules.create_rule(
            name='daily_summary',
            type='scheduled',
            schedule='0 17 * * *',  # 5 PM daily
            alert_level=AlertLevel.INFO
        )
        
        # Test at scheduled time
        current_time = datetime(2025, 1, 29, 17, 0, 0)
        should_alert = alert_rules.should_trigger_scheduled(rule, current_time)
        
        assert should_alert is True
        
        # Test at different time
        other_time = datetime(2025, 1, 29, 14, 30, 0)
        should_not_alert = alert_rules.should_trigger_scheduled(rule, other_time)
        
        assert should_not_alert is False


class TestAlertDashboard:
    """Test suite for alert dashboard and history"""
    
    @pytest.fixture
    def alert_dashboard(self):
        """Initialize alert dashboard"""
        from src.monitoring.alert_dashboard import AlertDashboard
        
        dashboard = AlertDashboard()
        return dashboard
    
    def test_alert_history_storage(self, alert_dashboard):
        """
        Test 13.4.1: Store alert history
        Acceptance: Persistent alert storage
        """
        alerts = []
        for i in range(10):
            alert = {
                'id': f'ALT{i}',
                'timestamp': datetime.now() - timedelta(hours=i),
                'level': AlertLevel.WARNING if i % 2 == 0 else AlertLevel.INFO,
                'title': f'Alert {i}',
                'status': 'sent'
            }
            alerts.append(alert)
            alert_dashboard.store_alert(alert)
        
        # Retrieve history
        history = alert_dashboard.get_history(limit=5)
        
        assert len(history) == 5
        assert history[0]['id'] == 'ALT0'  # Most recent first
    
    def test_alert_statistics(self, alert_dashboard):
        """
        Test 13.4.2: Calculate alert statistics
        Acceptance: Track alert metrics
        """
        # Add sample alerts
        for _ in range(30):
            alert_dashboard.store_alert({
                'level': np.random.choice([AlertLevel.INFO, AlertLevel.WARNING, AlertLevel.CRITICAL]),
                'type': np.random.choice([AlertType.PRICE, AlertType.RISK, AlertType.TRADE]),
                'timestamp': datetime.now() - timedelta(hours=np.random.randint(0, 24))
            })
        
        stats = alert_dashboard.get_statistics(period='24h')
        
        assert 'total_alerts' in stats
        assert 'by_level' in stats
        assert 'by_type' in stats
        assert 'alerts_per_hour' in stats
        assert stats['total_alerts'] == 30
    
    def test_alert_search(self, alert_dashboard):
        """
        Test 13.4.3: Search alert history
        Acceptance: Filter and search alerts
        """
        # Add various alerts
        alert_dashboard.store_alert({
            'id': 'ALT1',
            'level': AlertLevel.CRITICAL,
            'type': AlertType.RISK,
            'title': 'High Drawdown',
            'message': 'Drawdown exceeds 15%',
            'timestamp': datetime.now()
        })
        
        alert_dashboard.store_alert({
            'id': 'ALT2',
            'level': AlertLevel.WARNING,
            'type': AlertType.PRICE,
            'title': 'Price Spike',
            'message': 'EUR/USD spike detected',
            'timestamp': datetime.now()
        })
        
        # Search by level
        critical_alerts = alert_dashboard.search(level=AlertLevel.CRITICAL)
        assert len(critical_alerts) == 1
        assert critical_alerts[0]['id'] == 'ALT1'
        
        # Search by text
        price_alerts = alert_dashboard.search(text='EUR/USD')
        assert len(price_alerts) == 1
        assert price_alerts[0]['id'] == 'ALT2'
    
    def test_alert_acknowledgment(self, alert_dashboard):
        """
        Test 13.4.4: Track alert acknowledgment
        Acceptance: Monitor alert response
        """
        alert = {
            'id': 'ALT123',
            'level': AlertLevel.CRITICAL,
            'title': 'Critical Alert',
            'status': 'pending'
        }
        
        alert_dashboard.store_alert(alert)
        
        # Acknowledge alert
        success = alert_dashboard.acknowledge_alert(
            alert_id='ALT123',
            user='trader1',
            notes='Investigating issue'
        )
        
        assert success is True
        
        # Check acknowledgment
        updated_alert = alert_dashboard.get_alert('ALT123')
        assert updated_alert['status'] == 'acknowledged'
        assert updated_alert['acknowledged_by'] == 'trader1'
        assert updated_alert['acknowledgment_time'] is not None


if __name__ == "__main__":
    pytest.main([__file__, '-v'])