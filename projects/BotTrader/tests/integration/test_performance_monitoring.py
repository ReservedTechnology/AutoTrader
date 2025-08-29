"""
Test Suite for Performance Monitoring and Alerting
Following TDD methodology for forex bot targeting 25% annual returns
Tests for real-time monitoring, metrics tracking, and alerting systems
"""
import pytest
import pytest_asyncio
import asyncio
import numpy as np
import pandas as pd
import os
import psycopg2
from supabase import create_client, Client
from datetime import datetime, timedelta
import json
from dotenv import load_dotenv

load_dotenv()


class TestPerformanceMonitoring:
    """
    Test suite for performance monitoring and metrics tracking
    Monitors P&L, Sharpe ratio, drawdown, and system health
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
    async def performance_monitor(self):
        """Initialize performance monitoring system"""
        from src.monitoring.performance_monitor import PerformanceMonitor
        
        monitor = PerformanceMonitor(
            update_interval=1,  # 1 second for testing
            alert_thresholds={
                'max_drawdown': 0.15,
                'min_sharpe': 0.75,
                'max_latency': 500
            }
        )
        await monitor.initialize()
        yield monitor
        await monitor.shutdown()
    
    @pytest.mark.asyncio
    async def test_realtime_pnl_tracking(self, performance_monitor, timescale_connection):
        """
        Test 7.1.1: Track P&L in real-time
        Acceptance: Update P&L within 1 second of trade
        """
        # Simulate trades
        trades = [
            {'symbol': 'EUR_USD', 'pnl': 150.00, 'timestamp': datetime.now()},
            {'symbol': 'GBP_JPY', 'pnl': -75.00, 'timestamp': datetime.now()},
            {'symbol': 'AUD_JPY', 'pnl': 200.00, 'timestamp': datetime.now()}
        ]
        
        initial_pnl = await performance_monitor.get_current_pnl()
        
        # Process trades
        for trade in trades:
            await performance_monitor.update_trade(trade)
        
        # Wait for update
        await asyncio.sleep(1.5)
        
        current_pnl = await performance_monitor.get_current_pnl()
        expected_pnl = initial_pnl + sum(t['pnl'] for t in trades)
        
        assert abs(current_pnl - expected_pnl) < 0.01, \
            f"P&L mismatch: {current_pnl} vs expected {expected_pnl}"
        
        # Store P&L snapshot in TimescaleDB
        cursor = timescale_connection.cursor()
        cursor.execute("""
            INSERT INTO performance_snapshots (time, data)
            VALUES (%s, %s);
        """, (
            datetime.now(),
            json.dumps({
                'metric': 'pnl',
                'value': current_pnl,
                'daily_change': current_pnl - initial_pnl,
                'trade_count': len(trades)
            })
        ))
        timescale_connection.commit()
        cursor.close()
    
    @pytest.mark.asyncio
    async def test_sharpe_ratio_calculation(self, performance_monitor):
        """
        Test 7.1.2: Calculate rolling Sharpe ratio
        Acceptance: 30-day rolling Sharpe ratio updated daily
        """
        # Generate sample returns for 30 days
        daily_returns = np.random.randn(30) * 0.01 + 0.001  # Slight positive bias
        
        for i, ret in enumerate(daily_returns):
            await performance_monitor.add_daily_return(ret)
        
        sharpe = await performance_monitor.calculate_sharpe_ratio(period_days=30)
        
        # Manual calculation for verification
        expected_sharpe = (np.mean(daily_returns) / np.std(daily_returns)) * np.sqrt(252)
        
        assert abs(sharpe - expected_sharpe) < 0.1, \
            f"Sharpe calculation error: {sharpe:.2f} vs {expected_sharpe:.2f}"
        
        # Check against thresholds
        if sharpe < 0.75:
            alerts = await performance_monitor.check_alerts()
            assert any(a['type'] == 'low_sharpe' for a in alerts), \
                "Low Sharpe ratio not triggering alert"
        
        print(f"30-day Sharpe Ratio: {sharpe:.2f}")
    
    @pytest.mark.asyncio
    async def test_drawdown_monitoring(self, performance_monitor, supabase_client):
        """
        Test 7.1.3: Monitor maximum drawdown
        Acceptance: Alert when drawdown exceeds 15%
        """
        # Simulate equity curve with drawdown
        equity_curve = [100000]  # Starting equity
        
        # Create 20% drawdown scenario
        for i in range(20):
            if i < 10:
                equity_curve.append(equity_curve[-1] * 1.01)  # Growth
            else:
                equity_curve.append(equity_curve[-1] * 0.98)  # Drawdown
        
        peak = max(equity_curve)
        current = equity_curve[-1]
        drawdown = (peak - current) / peak
        
        await performance_monitor.update_equity(current)
        current_dd = await performance_monitor.get_max_drawdown()
        
        assert abs(current_dd - drawdown) < 0.01, \
            f"Drawdown calculation error: {current_dd:.2%} vs {drawdown:.2%}"
        
        # Check for alert
        if drawdown > 0.15:
            alerts = await performance_monitor.check_alerts()
            assert any(a['type'] == 'max_drawdown_exceeded' for a in alerts), \
                "Drawdown alert not triggered"
            
            # Store alert in Supabase
            alert_data = {
                'alert_type': 'max_drawdown_exceeded',
                'severity': 'high',
                'value': drawdown,
                'threshold': 0.15,
                'timestamp': datetime.now().isoformat()
            }
            
            try:
                response = supabase_client.table('system_alerts').insert(alert_data).execute()
                assert response.data, "Failed to store alert"
            except Exception as e:
                print(f"Alert storage: {e}")
        
        print(f"Current Drawdown: {drawdown:.2%}")
    
    @pytest.mark.asyncio
    async def test_win_rate_tracking(self, performance_monitor, timescale_connection):
        """
        Test 7.1.4: Track win rate and profit factor
        Acceptance: Accurate win rate calculation
        """
        # Generate trade history
        trades = []
        for i in range(100):
            is_win = np.random.random() < 0.60  # 60% win rate target
            pnl = np.random.uniform(100, 300) if is_win else np.random.uniform(-150, -50)
            trades.append({
                'trade_id': f'trade_{i}',
                'pnl': pnl,
                'win': is_win,
                'timestamp': datetime.now() - timedelta(hours=100-i)
            })
        
        # Process trades
        for trade in trades:
            await performance_monitor.record_trade(trade)
        
        # Get metrics
        metrics = await performance_monitor.get_trading_metrics()
        
        assert 'win_rate' in metrics, "Missing win rate"
        assert 'profit_factor' in metrics, "Missing profit factor"
        assert 'avg_win' in metrics, "Missing average win"
        assert 'avg_loss' in metrics, "Missing average loss"
        
        # Verify calculations
        wins = [t for t in trades if t['win']]
        losses = [t for t in trades if not t['win']]
        
        expected_win_rate = len(wins) / len(trades)
        assert abs(metrics['win_rate'] - expected_win_rate) < 0.01, \
            "Win rate calculation error"
        
        if losses:
            total_wins = sum(t['pnl'] for t in wins)
            total_losses = abs(sum(t['pnl'] for t in losses))
            expected_pf = total_wins / total_losses if total_losses > 0 else float('inf')
            
            if expected_pf != float('inf'):
                assert abs(metrics['profit_factor'] - expected_pf) < 0.1, \
                    "Profit factor calculation error"
        
        # Store metrics in TimescaleDB
        cursor = timescale_connection.cursor()
        cursor.execute("""
            INSERT INTO trading_metrics (time, data)
            VALUES (%s, %s);
        """, (
            datetime.now(),
            json.dumps({
                'win_rate': metrics['win_rate'],
                'profit_factor': metrics['profit_factor'],
                'trade_count': len(trades),
                'period': '100_trades'
            })
        ))
        timescale_connection.commit()
        cursor.close()
        
        print(f"Win Rate: {metrics['win_rate']:.1%}")
        print(f"Profit Factor: {metrics['profit_factor']:.2f}")
    
    @pytest.mark.asyncio
    async def test_api_health_monitoring(self, performance_monitor):
        """
        Test 7.1.5: Monitor API connection health
        Acceptance: Detect API failures within 30 seconds
        """
        # Simulate API health checks
        api_status = {
            'oanda': {'status': 'healthy', 'latency': 45},
            'alpha_vantage': {'status': 'healthy', 'latency': 120},
            'tradermade': {'status': 'degraded', 'latency': 450}
        }
        
        await performance_monitor.update_api_health(api_status)
        
        # Check for degraded services
        health_alerts = await performance_monitor.check_api_health()
        
        degraded = [api for api, status in api_status.items() 
                   if status['status'] != 'healthy']
        
        assert len(health_alerts) == len(degraded), \
            "Not all degraded APIs detected"
        
        # Check latency alerts
        high_latency = [api for api, status in api_status.items() 
                       if status['latency'] > 200]
        
        latency_alerts = await performance_monitor.check_latency_alerts()
        assert len(latency_alerts) >= len(high_latency), \
            "High latency not detected"
        
        print(f"API Health Status:")
        for api, status in api_status.items():
            print(f"  {api}: {status['status']} ({status['latency']}ms)")
    
    @pytest.mark.asyncio
    async def test_model_performance_drift(self, performance_monitor, supabase_client):
        """
        Test 7.1.6: Detect ML model performance drift
        Acceptance: Alert when model accuracy drops >10%
        """
        # Simulate model predictions and outcomes
        baseline_accuracy = 0.68  # Transformer target
        
        # Generate predictions with drift
        predictions = []
        for i in range(100):
            if i < 50:
                # Good performance
                accuracy = np.random.uniform(0.65, 0.72)
            else:
                # Performance degradation
                accuracy = np.random.uniform(0.55, 0.62)
            
            predictions.append({
                'model': 'transformer',
                'accuracy': accuracy,
                'timestamp': datetime.now() - timedelta(hours=100-i)
            })
        
        # Process predictions
        for pred in predictions:
            await performance_monitor.update_model_performance(pred)
        
        # Check for drift
        drift_detected = await performance_monitor.detect_model_drift(
            baseline=baseline_accuracy,
            threshold=0.10
        )
        
        recent_accuracy = np.mean([p['accuracy'] for p in predictions[-20:]])
        expected_drift = baseline_accuracy - recent_accuracy > 0.10
        
        assert drift_detected == expected_drift, \
            f"Drift detection error: detected={drift_detected}, expected={expected_drift}"
        
        if drift_detected:
            # Store drift alert
            drift_alert = {
                'alert_type': 'model_drift',
                'model': 'transformer',
                'baseline_accuracy': baseline_accuracy,
                'current_accuracy': recent_accuracy,
                'degradation': baseline_accuracy - recent_accuracy,
                'timestamp': datetime.now().isoformat()
            }
            
            try:
                response = supabase_client.table('model_alerts').insert(drift_alert).execute()
                assert response.data, "Failed to store drift alert"
            except Exception as e:
                print(f"Drift alert storage: {e}")
        
        print(f"Model Drift: {drift_detected}")
        print(f"Recent Accuracy: {recent_accuracy:.2%}")
    
    @pytest.mark.asyncio
    async def test_resource_usage_monitoring(self, performance_monitor):
        """
        Test 7.1.7: Monitor system resource usage
        Acceptance: Track CPU, memory, and network usage
        """
        import psutil
        
        # Get current resource usage
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        
        resources = {
            'cpu_percent': cpu_percent,
            'memory_percent': memory.percent,
            'memory_used_gb': memory.used / (1024**3),
            'memory_available_gb': memory.available / (1024**3)
        }
        
        await performance_monitor.update_resource_usage(resources)
        
        # Check for resource alerts
        if cpu_percent > 80:
            alerts = await performance_monitor.check_resource_alerts()
            assert any(a['type'] == 'high_cpu' for a in alerts), \
                "High CPU usage not detected"
        
        if memory.percent > 85:
            alerts = await performance_monitor.check_resource_alerts()
            assert any(a['type'] == 'high_memory' for a in alerts), \
                "High memory usage not detected"
        
        print(f"Resource Usage:")
        print(f"  CPU: {cpu_percent:.1f}%")
        print(f"  Memory: {memory.percent:.1f}%")
    
    @pytest.mark.asyncio
    async def test_trade_frequency_monitoring(self, performance_monitor, timescale_connection):
        """
        Test 7.1.8: Monitor trade frequency and volume
        Acceptance: Detect unusual trading patterns
        """
        # Normal trading pattern (10-20 trades per hour)
        normal_hours = []
        for hour in range(24):
            trade_count = np.random.randint(10, 21)
            normal_hours.append({
                'hour': hour,
                'trade_count': trade_count,
                'volume': trade_count * np.random.uniform(10000, 50000)
            })
        
        # Add anomaly (spike in trades)
        anomaly_hour = {
            'hour': 24,
            'trade_count': 100,  # Unusual spike
            'volume': 5000000
        }
        
        # Process data
        for hour_data in normal_hours + [anomaly_hour]:
            is_anomaly = await performance_monitor.check_trade_anomaly(hour_data)
            
            if hour_data['trade_count'] > 50:
                assert is_anomaly, "Trade spike not detected"
                
                # Store anomaly
                cursor = timescale_connection.cursor()
                cursor.execute("""
                    INSERT INTO trade_anomalies (time, data)
                    VALUES (%s, %s);
                """, (
                    datetime.now(),
                    json.dumps({
                        'type': 'trade_frequency_spike',
                        'trade_count': hour_data['trade_count'],
                        'expected_range': [10, 20],
                        'severity': 'medium'
                    })
                ))
                timescale_connection.commit()
                cursor.close()
    
    @pytest.mark.asyncio
    async def test_alert_aggregation(self, performance_monitor, supabase_client):
        """
        Test 7.1.9: Aggregate and prioritize alerts
        Acceptance: Combine related alerts, prioritize by severity
        """
        # Generate multiple alerts
        alerts = [
            {'type': 'max_drawdown', 'severity': 'high', 'value': 0.18},
            {'type': 'low_sharpe', 'severity': 'medium', 'value': 0.65},
            {'type': 'api_degraded', 'severity': 'low', 'service': 'tradermade'},
            {'type': 'model_drift', 'severity': 'high', 'model': 'transformer'},
            {'type': 'high_latency', 'severity': 'medium', 'latency': 600}
        ]
        
        # Process alerts
        for alert in alerts:
            await performance_monitor.add_alert(alert)
        
        # Get aggregated alerts
        aggregated = await performance_monitor.get_aggregated_alerts()
        
        # Should be prioritized by severity
        severities = [a['severity'] for a in aggregated]
        severity_order = {'high': 3, 'medium': 2, 'low': 1}
        
        for i in range(1, len(severities)):
            assert severity_order[severities[i-1]] >= severity_order[severities[i]], \
                "Alerts not properly prioritized"
        
        # Store alert summary
        summary = {
            'timestamp': datetime.now().isoformat(),
            'total_alerts': len(alerts),
            'high_severity': sum(1 for a in alerts if a['severity'] == 'high'),
            'medium_severity': sum(1 for a in alerts if a['severity'] == 'medium'),
            'low_severity': sum(1 for a in alerts if a['severity'] == 'low'),
            'alert_details': aggregated
        }
        
        try:
            response = supabase_client.table('alert_summaries').insert(summary).execute()
            assert response.data, "Failed to store alert summary"
        except Exception as e:
            print(f"Alert summary storage: {e}")
        
        print(f"Alert Summary:")
        print(f"  High: {summary['high_severity']}")
        print(f"  Medium: {summary['medium_severity']}")
        print(f"  Low: {summary['low_severity']}")


class TestDashboardMetrics:
    """Test suite for monitoring dashboard metrics"""
    
    @pytest.mark.asyncio
    async def test_dashboard_data_generation(self):
        """
        Test 7.2.1: Generate dashboard data
        Acceptance: All required metrics available
        """
        from src.monitoring.dashboard import DashboardDataGenerator
        
        generator = DashboardDataGenerator()
        dashboard_data = await generator.generate_snapshot()
        
        required_metrics = [
            'current_pnl', 'daily_pnl', 'weekly_pnl', 'monthly_pnl',
            'win_rate', 'profit_factor', 'sharpe_ratio', 'max_drawdown',
            'open_positions', 'pending_orders', 'api_status',
            'model_performance', 'system_health'
        ]
        
        for metric in required_metrics:
            assert metric in dashboard_data, f"Missing metric: {metric}"
        
        print("Dashboard snapshot generated successfully")
    
    @pytest.mark.asyncio
    async def test_realtime_updates(self):
        """
        Test 7.2.2: Test real-time dashboard updates
        Acceptance: Updates pushed within 1 second
        """
        from src.monitoring.dashboard import RealtimeDashboard
        
        dashboard = RealtimeDashboard()
        await dashboard.start()
        
        # Subscribe to updates
        update_received = asyncio.Event()
        
        async def update_handler(data):
            update_received.set()
        
        dashboard.subscribe(update_handler)
        
        # Trigger update
        await dashboard.push_update({'test': 'data'})
        
        # Wait for update
        try:
            await asyncio.wait_for(update_received.wait(), timeout=1.0)
            assert True, "Update received within 1 second"
        except asyncio.TimeoutError:
            assert False, "Update not received within 1 second"
        
        await dashboard.stop()


if __name__ == "__main__":
    pytest.main([__file__, '-v', '--asyncio-mode=auto'])