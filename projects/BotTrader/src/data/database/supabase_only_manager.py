"""
Supabase-Only Database Manager
All data operations through Supabase PostgreSQL
"""
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from supabase import create_client, Client
import os
import json

logger = logging.getLogger(__name__)


class SupabaseOnlyManager:
    """
    Manages all database operations through Supabase
    Handles both time-series forex data and application data
    """
    
    def __init__(self):
        """Initialize Supabase connection"""
        self.supabase_url = os.getenv('SUPABASE_URL')
        self.supabase_key = os.getenv('SUPABASE_ANON_KEY')
        self.supabase_service_key = os.getenv('SUPABASE_SERVICE_KEY')
        
        self.supabase: Optional[Client] = None
        self.supabase_admin: Optional[Client] = None
        
    async def initialize(self):
        """Initialize Supabase connections"""
        try:
            await self._init_supabase()
            await self.create_tables()
            logger.info("Supabase database manager initialized")
        except Exception as e:
            logger.error(f"Failed to initialize database manager: {e}")
            raise
    
    async def _init_supabase(self):
        """Initialize Supabase connections"""
        if not self.supabase_url or not self.supabase_key:
            raise ValueError("Missing Supabase credentials")
            
        try:
            # Create client connection
            self.supabase = create_client(
                supabase_url=self.supabase_url, 
                supabase_key=self.supabase_key
            )
            
            # Create admin client if service key available
            if self.supabase_service_key:
                self.supabase_admin = create_client(
                    supabase_url=self.supabase_url, 
                    supabase_key=self.supabase_service_key
                )
            
            logger.info("Supabase connection established")
        except Exception as e:
            logger.error(f"Failed to connect to Supabase: {e}")
            raise
    
    async def create_tables(self):
        """Create all required tables in Supabase"""
        try:
            # Use RPC to create tables with proper structure
            # These would be created via Supabase dashboard or migrations
            logger.info("Tables should be created via Supabase dashboard or migrations")
        except Exception as e:
            logger.error(f"Failed to create tables: {e}")
            raise
    
    # ==================== FOREX DATA METHODS ====================
    
    async def insert_forex_prices(self, prices_data: List[Dict]) -> int:
        """Insert forex prices into Supabase"""
        if not self.supabase or not prices_data:
            return 0
            
        try:
            # Prepare data for insertion
            records = []
            for price in prices_data:
                record = {
                    'timestamp': price['timestamp'].isoformat() if isinstance(price['timestamp'], datetime) else price['timestamp'],
                    'symbol': price['symbol'],
                    'bid': float(price['bid']),
                    'ask': float(price['ask']),
                    'spread': float(price.get('spread', 0)),
                    'volume': int(price.get('volume', 0)),
                    'timeframe': price.get('timeframe', '1min'),
                    'source': price.get('source', 'oanda')
                }
                records.append(record)
            
            # Insert using Supabase client
            response = self.supabase.table('forex_prices').upsert(records).execute()
            
            return len(response.data) if response.data else 0
        except Exception as e:
            logger.error(f"Failed to insert forex prices: {e}")
            return 0
    
    async def get_latest_price(self, symbol: str) -> Optional[Dict]:
        """Get latest price for a symbol"""
        if not self.supabase:
            return None
            
        try:
            response = self.supabase.table('forex_prices')\
                .select('*')\
                .eq('symbol', symbol)\
                .order('timestamp', desc=True)\
                .limit(1)\
                .execute()
            
            return response.data[0] if response.data else None
        except Exception as e:
            logger.error(f"Error fetching latest price: {e}")
            return None
    
    async def get_ohlc_data(
        self, 
        symbol: str, 
        timeframe: str, 
        start_time: datetime, 
        end_time: datetime
    ) -> List[Dict]:
        """Get OHLC data from Supabase"""
        if not self.supabase:
            return []
            
        try:
            # Fetch raw price data
            response = self.supabase.table('forex_prices')\
                .select('*')\
                .eq('symbol', symbol)\
                .gte('timestamp', start_time.isoformat())\
                .lte('timestamp', end_time.isoformat())\
                .order('timestamp', desc=True)\
                .execute()
            
            # Process into OHLC format if needed
            # This could be done via a Supabase function for better performance
            return response.data if response.data else []
        except Exception as e:
            logger.error(f"Error fetching OHLC data: {e}")
            return []
    
    # ==================== TRADING SIGNALS METHODS ====================
    
    async def insert_trading_signal(self, signal_data: Dict) -> bool:
        """Insert trading signal into Supabase"""
        if not self.supabase:
            return False
            
        try:
            record = {
                'timestamp': signal_data['timestamp'].isoformat() if isinstance(signal_data['timestamp'], datetime) else signal_data['timestamp'],
                'symbol': signal_data['symbol'],
                'signal_type': signal_data['signal_type'],
                'strength': float(signal_data['strength']),
                'price': float(signal_data['price']),
                'indicators_used': json.dumps(signal_data.get('indicators_used', {})),
                'ml_confidence': float(signal_data.get('ml_confidence', 0)),
                'expected_pips': int(signal_data.get('expected_pips', 0))
            }
            
            response = self.supabase.table('trading_signals').insert(record).execute()
            return len(response.data) > 0
        except Exception as e:
            logger.error(f"Error inserting trading signal: {e}")
            return False
    
    async def get_recent_signals(self, symbol: str, hours: int = 24) -> List[Dict]:
        """Get recent trading signals"""
        if not self.supabase:
            return []
            
        try:
            cutoff_time = datetime.utcnow() - timedelta(hours=hours)
            
            response = self.supabase.table('trading_signals')\
                .select('*')\
                .eq('symbol', symbol)\
                .gte('timestamp', cutoff_time.isoformat())\
                .order('timestamp', desc=True)\
                .execute()
            
            return response.data if response.data else []
        except Exception as e:
            logger.error(f"Error fetching recent signals: {e}")
            return []
    
    # ==================== ML MODEL METHODS ====================
    
    async def save_ml_prediction(self, prediction_data: Dict) -> bool:
        """Save ML model prediction"""
        if not self.supabase:
            return False
            
        try:
            response = self.supabase.table('ml_predictions')\
                .insert(prediction_data)\
                .execute()
            return len(response.data) > 0
        except Exception as e:
            logger.error(f"Error saving ML prediction: {e}")
            return False
    
    async def get_model_performance(self, model_name: str, days: int = 30) -> Dict:
        """Get model performance metrics"""
        if not self.supabase:
            return {}
            
        try:
            cutoff_time = datetime.utcnow() - timedelta(days=days)
            
            response = self.supabase.table('ml_predictions')\
                .select('*')\
                .eq('model_name', model_name)\
                .gte('timestamp', cutoff_time.isoformat())\
                .execute()
            
            predictions = response.data if response.data else []
            
            # Calculate performance metrics
            if predictions:
                correct = sum(1 for p in predictions if p.get('correct'))
                total = len(predictions)
                accuracy = correct / total if total > 0 else 0
                
                return {
                    'model_name': model_name,
                    'accuracy': accuracy,
                    'total_predictions': total,
                    'correct_predictions': correct,
                    'period_days': days
                }
            
            return {}
        except Exception as e:
            logger.error(f"Error fetching model performance: {e}")
            return {}
    
    # ==================== USER & PORTFOLIO METHODS ====================
    
    async def get_user_portfolios(self, user_id: str) -> List[Dict]:
        """Get user portfolios from Supabase"""
        if not self.supabase:
            return []
            
        try:
            response = self.supabase.table('portfolios')\
                .select('*')\
                .eq('user_id', user_id)\
                .execute()
            return response.data if response.data else []
        except Exception as e:
            logger.error(f"Error fetching portfolios: {e}")
            return []
    
    async def save_trading_strategy(self, strategy_data: Dict) -> bool:
        """Save trading strategy configuration"""
        if not self.supabase:
            return False
            
        try:
            response = self.supabase.table('trading_strategies')\
                .upsert(strategy_data)\
                .execute()
            return len(response.data) > 0
        except Exception as e:
            logger.error(f"Error saving strategy: {e}")
            return False
    
    async def record_trade(self, trade_data: Dict) -> bool:
        """Record a completed trade"""
        if not self.supabase:
            return False
            
        try:
            response = self.supabase.table('closed_trades')\
                .insert(trade_data)\
                .execute()
            return len(response.data) > 0
        except Exception as e:
            logger.error(f"Error recording trade: {e}")
            return False
    
    async def get_trading_history(self, user_id: str, days: int = 30) -> List[Dict]:
        """Get user's trading history"""
        if not self.supabase:
            return []
            
        try:
            cutoff_time = datetime.utcnow() - timedelta(days=days)
            
            response = self.supabase.table('closed_trades')\
                .select('*')\
                .eq('user_id', user_id)\
                .gte('close_time', cutoff_time.isoformat())\
                .order('close_time', desc=True)\
                .execute()
            
            return response.data if response.data else []
        except Exception as e:
            logger.error(f"Error fetching trading history: {e}")
            return []
    
    # ==================== SYSTEM CONFIGURATION ====================
    
    async def get_system_config(self, key: str) -> Optional[Any]:
        """Get system configuration value"""
        if not self.supabase:
            return None
            
        try:
            response = self.supabase.table('system_config')\
                .select('value')\
                .eq('key', key)\
                .execute()
            
            if response.data:
                return response.data[0].get('value')
            return None
        except Exception as e:
            logger.error(f"Error fetching system config: {e}")
            return None
    
    async def update_system_config(self, key: str, value: Any) -> bool:
        """Update system configuration"""
        if not self.supabase:
            return False
            
        try:
            response = self.supabase.table('system_config')\
                .upsert({'key': key, 'value': value})\
                .execute()
            return len(response.data) > 0
        except Exception as e:
            logger.error(f"Error updating system config: {e}")
            return False
    
    # ==================== ALERTS & NOTIFICATIONS ====================
    
    async def get_active_alerts(self, user_id: str) -> List[Dict]:
        """Get active alerts"""
        if not self.supabase:
            return []
            
        try:
            response = self.supabase.table('alerts')\
                .select('*')\
                .eq('user_id', user_id)\
                .eq('active', True)\
                .execute()
            return response.data if response.data else []
        except Exception as e:
            logger.error(f"Error fetching alerts: {e}")
            return []
    
    async def create_alert(self, alert_data: Dict) -> bool:
        """Create new alert"""
        if not self.supabase:
            return False
            
        try:
            response = self.supabase.table('alerts')\
                .insert(alert_data)\
                .execute()
            return len(response.data) > 0
        except Exception as e:
            logger.error(f"Error creating alert: {e}")
            return False
    
    async def close(self):
        """Close database connections (no-op for Supabase)"""
        logger.info("Supabase connections closed")


# Global instance
db_manager = SupabaseOnlyManager()