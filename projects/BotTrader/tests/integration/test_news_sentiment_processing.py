"""
Integration Test for News Sentiment Processing
Following TDD methodology for forex bot targeting 25% annual returns
Tests news collection, sentiment analysis, and trading signal generation
"""
import pytest
import numpy as np
import pandas as pd
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
import asyncio
import json
import os
from typing import List, Dict, Any


class TestNewsSentimentProcessing:
    """Integration test for news sentiment analysis pipeline"""
    
    @pytest.fixture
    def sentiment_pipeline(self):
        """Initialize sentiment processing pipeline"""
        from src.sentiment.news_sentiment_pipeline import NewsSentimentPipeline
        
        pipeline = NewsSentimentPipeline(
            sources=['reuters', 'bloomberg', 'forexfactory'],
            models=['finbert', 'vader', 'custom_transformer'],
            pairs=['EUR_USD', 'GBP_USD', 'USD_JPY']
        )
        return pipeline
    
    @pytest.fixture
    def sample_news_data(self):
        """Sample news articles for testing"""
        return [
            {
                'id': 'NEWS001',
                'timestamp': datetime.now() - timedelta(minutes=5),
                'source': 'reuters',
                'headline': 'ECB Signals Potential Rate Hike Amid Inflation Concerns',
                'content': 'The European Central Bank indicated possible rate increases...',
                'currencies': ['EUR', 'USD'],
                'importance': 'high'
            },
            {
                'id': 'NEWS002',
                'timestamp': datetime.now() - timedelta(minutes=10),
                'source': 'bloomberg',
                'headline': 'Dollar Weakens as Fed Maintains Dovish Stance',
                'content': 'The US Dollar fell against major currencies following...',
                'currencies': ['USD'],
                'importance': 'medium'
            },
            {
                'id': 'NEWS003',
                'timestamp': datetime.now() - timedelta(minutes=15),
                'source': 'forexfactory',
                'headline': 'UK GDP Growth Exceeds Expectations',
                'content': 'British economic growth surprised to the upside...',
                'currencies': ['GBP'],
                'importance': 'high'
            }
        ]
    
    @pytest.mark.integration
    def test_multi_source_news_collection(self, sentiment_pipeline):
        """
        Test IT.2.1: Collect news from multiple sources
        Acceptance: Aggregate news within 2 seconds
        """
        start_time = datetime.now()
        
        with patch.object(sentiment_pipeline, 'fetch_reuters') as mock_reuters:
            with patch.object(sentiment_pipeline, 'fetch_bloomberg') as mock_bloomberg:
                with patch.object(sentiment_pipeline, 'fetch_forexfactory') as mock_forex:
                    
                    mock_reuters.return_value = [{'source': 'reuters', 'articles': 5}]
                    mock_bloomberg.return_value = [{'source': 'bloomberg', 'articles': 3}]
                    mock_forex.return_value = [{'source': 'forexfactory', 'articles': 7}]
                    
                    news = asyncio.run(sentiment_pipeline.collect_all_news())
                    
                    elapsed = (datetime.now() - start_time).total_seconds()
                    
                    assert elapsed < 2  # Fast collection
                    assert len(news) == 3  # All sources
                    
                    total_articles = sum(source[0]['articles'] for source in news)
                    assert total_articles == 15
    
    @pytest.mark.integration
    def test_sentiment_analysis_ensemble(self, sentiment_pipeline, sample_news_data):
        """
        Test IT.2.2: Ensemble sentiment analysis
        Acceptance: Combine multiple models for robust scoring
        """
        article = sample_news_data[0]  # ECB rate hike news
        
        # Mock individual model predictions
        with patch.object(sentiment_pipeline, 'analyze_finbert') as mock_finbert:
            with patch.object(sentiment_pipeline, 'analyze_vader') as mock_vader:
                with patch.object(sentiment_pipeline, 'analyze_custom') as mock_custom:
                    
                    mock_finbert.return_value = {
                        'sentiment': 'hawkish',
                        'score': 0.75,
                        'confidence': 0.85
                    }
                    
                    mock_vader.return_value = {
                        'sentiment': 'positive',
                        'score': 0.65,
                        'confidence': 0.70
                    }
                    
                    mock_custom.return_value = {
                        'sentiment': 'bullish_eur',
                        'score': 0.80,
                        'confidence': 0.90
                    }
                    
                    ensemble_result = sentiment_pipeline.analyze_ensemble(article)
                    
                    # Weighted average based on confidence
                    assert ensemble_result['final_score'] > 0.7
                    assert ensemble_result['final_sentiment'] == 'bullish_eur'
                    assert ensemble_result['confidence'] > 0.8
                    assert len(ensemble_result['model_scores']) == 3
    
    @pytest.mark.integration
    def test_currency_impact_mapping(self, sentiment_pipeline, sample_news_data):
        """
        Test IT.2.3: Map sentiment to currency pairs
        Acceptance: Accurate impact assessment per pair
        """
        sentiments = {
            'NEWS001': {'sentiment': 'bullish_eur', 'score': 0.75},  # ECB hawkish
            'NEWS002': {'sentiment': 'bearish_usd', 'score': -0.60}, # USD weak
            'NEWS003': {'sentiment': 'bullish_gbp', 'score': 0.80}   # UK growth
        }
        
        pair_impacts = sentiment_pipeline.map_currency_impacts(
            sample_news_data,
            sentiments
        )
        
        # EUR/USD should be very bullish (EUR+ and USD-)
        assert pair_impacts['EUR_USD']['sentiment_score'] > 0.6
        assert pair_impacts['EUR_USD']['direction'] == 'bullish'
        
        # GBP/USD should be bullish (GBP+ and USD-)
        assert pair_impacts['GBP_USD']['sentiment_score'] > 0.7
        assert pair_impacts['GBP_USD']['direction'] == 'bullish'
        
        # USD/JPY should be bearish (USD-)
        assert pair_impacts['USD_JPY']['sentiment_score'] < 0
        assert pair_impacts['USD_JPY']['direction'] == 'bearish'
    
    @pytest.mark.integration
    def test_real_time_sentiment_updates(self, sentiment_pipeline):
        """
        Test IT.2.4: Real-time sentiment updates
        Acceptance: Process news within 500ms of receipt
        """
        processing_times = []
        
        async def process_news_item(news):
            start = datetime.now()
            
            # Process sentiment
            sentiment = await sentiment_pipeline.process_realtime(news)
            
            processing_time = (datetime.now() - start).total_seconds() * 1000
            processing_times.append(processing_time)
            
            return sentiment
        
        # Simulate real-time news stream
        news_stream = [
            {
                'id': f'RT{i}',
                'timestamp': datetime.now(),
                'headline': f'Breaking: Market news {i}',
                'content': 'Short breaking news content...'
            }
            for i in range(10)
        ]
        
        # Process stream
        results = []
        for news in news_stream:
            result = asyncio.run(process_news_item(news))
            results.append(result)
        
        # Check processing times
        avg_time = np.mean(processing_times)
        p95_time = np.percentile(processing_times, 95)
        
        assert avg_time < 500  # Average under 500ms
        assert p95_time < 750  # 95% under 750ms
        assert len(results) == 10
    
    @pytest.mark.integration
    def test_sentiment_signal_generation(self, sentiment_pipeline):
        """
        Test IT.2.5: Generate trading signals from sentiment
        Acceptance: Clear buy/sell signals with confidence
        """
        # Strong bullish sentiment
        bullish_sentiment = {
            'EUR_USD': {
                'sentiment_score': 0.85,
                'confidence': 0.90,
                'news_volume': 15,
                'consensus': 'strong_bullish'
            }
        }
        
        signal = sentiment_pipeline.generate_trading_signal(bullish_sentiment['EUR_USD'])
        
        assert signal['action'] == 'BUY'
        assert signal['strength'] == 'strong'
        assert signal['confidence'] > 0.8
        assert 'entry_price' in signal
        assert 'stop_loss' in signal
        assert 'take_profit' in signal
        
        # Mixed sentiment (no signal)
        mixed_sentiment = {
            'GBP_USD': {
                'sentiment_score': 0.15,
                'confidence': 0.45,
                'news_volume': 3,
                'consensus': 'mixed'
            }
        }
        
        no_signal = sentiment_pipeline.generate_trading_signal(mixed_sentiment['GBP_USD'])
        
        assert no_signal['action'] == 'HOLD'
        assert no_signal['reason'] == 'insufficient_confidence'
    
    @pytest.mark.integration
    def test_sentiment_persistence(self, sentiment_pipeline):
        """
        Test IT.2.6: Store sentiment data and history
        Acceptance: Persist for backtesting and analysis
        """
        sentiments = []
        
        # Generate sentiment history
        for i in range(24):  # 24 hours of data
            sentiment = {
                'timestamp': datetime.now() - timedelta(hours=i),
                'pair': 'EUR_USD',
                'score': np.random.uniform(-1, 1),
                'confidence': np.random.uniform(0.5, 1),
                'news_count': np.random.randint(1, 10)
            }
            sentiments.append(sentiment)
        
        # Store sentiments
        stored = sentiment_pipeline.store_sentiment_history(sentiments)
        assert stored == len(sentiments)
        
        # Retrieve sentiment history
        history = sentiment_pipeline.get_sentiment_history(
            pair='EUR_USD',
            hours=24
        )
        
        assert len(history) == 24
        
        # Calculate sentiment momentum
        momentum = sentiment_pipeline.calculate_sentiment_momentum(history)
        assert 'trend' in momentum
        assert 'acceleration' in momentum
        assert momentum['trend'] in ['improving', 'deteriorating', 'stable']
    
    @pytest.mark.integration
    def test_economic_calendar_integration(self, sentiment_pipeline):
        """
        Test IT.2.7: Integrate economic calendar events
        Acceptance: Combine news with scheduled events
        """
        # Mock economic events
        events = [
            {
                'time': datetime.now() + timedelta(hours=2),
                'currency': 'USD',
                'event': 'Non-Farm Payrolls',
                'importance': 'high',
                'forecast': '200K',
                'previous': '185K'
            },
            {
                'time': datetime.now() + timedelta(hours=4),
                'currency': 'EUR',
                'event': 'ECB Rate Decision',
                'importance': 'high',
                'forecast': '4.5%',
                'previous': '4.25%'
            }
        ]
        
        # Current sentiment
        current_sentiment = {
            'EUR_USD': {'score': 0.60, 'confidence': 0.75}
        }
        
        # Adjust for upcoming events
        adjusted = sentiment_pipeline.adjust_for_events(
            current_sentiment,
            events
        )
        
        # Should reduce confidence before high-impact events
        assert adjusted['EUR_USD']['confidence'] < 0.75
        assert 'event_risk' in adjusted['EUR_USD']
        assert adjusted['EUR_USD']['event_risk'] == 'high'
        
        # Generate pre-event positioning
        positioning = sentiment_pipeline.pre_event_positioning(events[0])
        assert positioning['action'] in ['reduce_exposure', 'hedge', 'close']
    
    @pytest.mark.integration
    def test_sentiment_anomaly_detection(self, sentiment_pipeline):
        """
        Test IT.2.8: Detect sentiment anomalies
        Acceptance: Flag unusual sentiment shifts
        """
        # Normal sentiment pattern
        normal_sentiments = [
            {'timestamp': datetime.now() - timedelta(hours=i), 'score': 0.5 + np.random.normal(0, 0.1)}
            for i in range(20)
        ]
        
        # Add anomaly
        anomaly_sentiment = {
            'timestamp': datetime.now(),
            'score': -0.95  # Sudden extreme negative
        }
        normal_sentiments.append(anomaly_sentiment)
        
        # Detect anomalies
        anomalies = sentiment_pipeline.detect_anomalies(
            normal_sentiments,
            threshold=3  # 3 standard deviations
        )
        
        assert len(anomalies) == 1
        assert anomalies[0]['timestamp'] == anomaly_sentiment['timestamp']
        assert anomalies[0]['severity'] == 'high'
        
        # Generate alert for anomaly
        alert = sentiment_pipeline.create_anomaly_alert(anomalies[0])
        assert alert['level'] == 'WARNING'
        assert 'sentiment_shift' in alert['message']
    
    @pytest.mark.integration
    def test_multi_language_processing(self, sentiment_pipeline):
        """
        Test IT.2.9: Process news in multiple languages
        Acceptance: Support EN, DE, FR, JP, CN
        """
        multilingual_news = [
            {
                'language': 'en',
                'headline': 'Fed Raises Interest Rates',
                'content': 'The Federal Reserve increased rates by 25 basis points...'
            },
            {
                'language': 'de',
                'headline': 'EZB erhöht Zinssätze',
                'content': 'Die Europäische Zentralbank hat die Zinsen erhöht...'
            },
            {
                'language': 'fr',
                'headline': 'La BCE augmente les taux',
                'content': 'La Banque centrale européenne a augmenté les taux...'
            },
            {
                'language': 'jp',
                'headline': '日銀が金利を維持',
                'content': '日本銀行は金利を据え置きました...'
            }
        ]
        
        for news in multilingual_news:
            # Translate if needed
            if news['language'] != 'en':
                translated = sentiment_pipeline.translate_news(news)
                assert translated['language'] == 'en'
                assert len(translated['content']) > 0
            
            # Analyze sentiment
            sentiment = sentiment_pipeline.analyze_sentiment(news)
            assert sentiment['score'] is not None
            assert -1 <= sentiment['score'] <= 1


if __name__ == "__main__":
    pytest.main([__file__, '-v', '-m', 'integration'])