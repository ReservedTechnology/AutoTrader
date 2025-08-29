"""
Main application entry point for Railway deployment
Forex Trading Bot with hybrid database architecture
"""
import asyncio
import logging
import os
from aiohttp import web, web_runner
import json
from datetime import datetime
import sys

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from src.data.database.hybrid_manager import db_manager
from src.data.connectors.oanda_connector import OandaV20Connector
from src.data.connectors.alphavantage_connector import AlphaVantageConnector

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ForexTradingBot:
    """Main Forex Trading Bot Application"""
    
    def __init__(self):
        self.app = web.Application()
        self.setup_routes()
        self.oanda_client = None
        self.alpha_client = None
        
    def setup_routes(self):
        """Setup HTTP routes for monitoring and API"""
        self.app.router.add_get('/health', self.health_check)
        self.app.router.add_get('/status', self.status_check)
        self.app.router.add_get('/metrics', self.metrics)
        self.app.router.add_get('/pairs', self.forex_pairs)
        self.app.router.add_get('/latest/{symbol}', self.latest_price)
        
    async def health_check(self, request):
        """Health check endpoint for Railway"""
        try:
            # Test TimescaleDB connection
            timescale_ok = bool(db_manager.timescale_pool)
            
            # Test Supabase connection  
            supabase_ok = bool(db_manager.supabase)
            
            health_status = {
                'status': 'healthy' if (timescale_ok and supabase_ok) else 'degraded',
                'timestamp': datetime.utcnow().isoformat(),
                'services': {
                    'timescaledb': 'connected' if timescale_ok else 'disconnected',
                    'supabase': 'connected' if supabase_ok else 'disconnected',
                    'oanda': 'connected' if self.oanda_client else 'disconnected',
                    'alphavantage': 'connected' if self.alpha_client else 'disconnected'
                }
            }
            
            status_code = 200 if health_status['status'] == 'healthy' else 503
            return web.json_response(health_status, status=status_code)
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return web.json_response({
                'status': 'error',
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat()
            }, status=500)
    
    async def status_check(self, request):
        """Detailed status for monitoring"""
        try:
            status = {
                'bot_version': '1.0.0',
                'environment': os.getenv('NODE_ENV', 'development'),
                'uptime': 'TODO: calculate uptime',
                'forex_pairs': [
                    'USD_ZAR', 'GBP_JPY', 'AUD_JPY', 
                    'USD_TRY', 'NZD_JPY', 'EUR_USD'
                ],
                'database_status': {
                    'timescaledb': {
                        'connected': bool(db_manager.timescale_pool),
                        'purpose': 'time-series forex data'
                    },
                    'supabase': {
                        'connected': bool(db_manager.supabase),
                        'purpose': 'application data & auth'
                    }
                },
                'trading_active': False,  # TODO: implement trading status
                'last_update': datetime.utcnow().isoformat()
            }
            
            return web.json_response(status)
            
        except Exception as e:
            logger.error(f"Status check failed: {e}")
            return web.json_response({'error': str(e)}, status=500)
    
    async def metrics(self, request):
        """Metrics endpoint for monitoring"""
        # TODO: Implement proper metrics collection
        metrics = {
            'trades_today': 0,
            'profit_loss': 0.0,
            'win_rate': 0.0,
            'sharpe_ratio': 0.0,
            'data_points_processed': 0,
            'api_calls_remaining': {
                'oanda': 'unlimited',
                'alphavantage': 'unknown'
            }
        }
        
        return web.json_response(metrics)
    
    async def forex_pairs(self, request):
        """List supported forex pairs"""
        pairs = {
            'priority_pairs': [
                {
                    'symbol': 'USD_ZAR',
                    'name': 'US Dollar / South African Rand',
                    'volatility': 'ultra-high',
                    'typical_spread': '15-25 pips'
                },
                {
                    'symbol': 'GBP_JPY', 
                    'name': 'British Pound / Japanese Yen',
                    'volatility': 'high',
                    'typical_spread': '0.5-2.0 pips',
                    'nickname': 'The Dragon'
                },
                {
                    'symbol': 'AUD_JPY',
                    'name': 'Australian Dollar / Japanese Yen', 
                    'volatility': 'high',
                    'typical_spread': '1.2-1.8 pips'
                },
                {
                    'symbol': 'USD_TRY',
                    'name': 'US Dollar / Turkish Lira',
                    'volatility': 'ultra-high', 
                    'typical_spread': '20-40 pips'
                },
                {
                    'symbol': 'NZD_JPY',
                    'name': 'New Zealand Dollar / Japanese Yen',
                    'volatility': 'extreme',
                    'typical_spread': 'variable'
                },
                {
                    'symbol': 'EUR_USD',
                    'name': 'Euro / US Dollar',
                    'volatility': 'medium',
                    'typical_spread': '0.8-1.11 pips',
                    'notes': 'maximum liquidity'
                }
            ]
        }
        
        return web.json_response(pairs)
    
    async def latest_price(self, request):
        """Get latest price for a forex pair"""
        symbol = request.match_info['symbol']
        
        try:
            # TODO: Get real latest price from TimescaleDB
            mock_price = {
                'symbol': symbol,
                'bid': 1.2345,
                'ask': 1.2347,
                'spread': 0.0002,
                'timestamp': datetime.utcnow().isoformat(),
                'source': 'mock_data'
            }
            
            return web.json_response(mock_price)
            
        except Exception as e:
            logger.error(f"Error getting price for {symbol}: {e}")
            return web.json_response({'error': str(e)}, status=500)
    
    async def initialize_connections(self):
        """Initialize all external connections"""
        try:
            # Initialize database connections
            await db_manager.initialize()
            await db_manager.create_forex_tables()
            
            # Initialize API connections if keys are available
            oanda_key = os.getenv('OANDA_API_KEY')
            oanda_account = os.getenv('OANDA_ACCOUNT_ID')
            
            if oanda_key and oanda_account:
                self.oanda_client = OandaV20Connector(
                    api_key=oanda_key,
                    account_id=oanda_account,
                    environment=os.getenv('OANDA_ENVIRONMENT', 'practice')
                )
                await self.oanda_client.initialize()
                logger.info("OANDA client initialized")
            
            alpha_key = os.getenv('ALPHA_VANTAGE_API_KEY')
            if alpha_key:
                self.alpha_client = AlphaVantageConnector(api_key=alpha_key)
                await self.alpha_client.initialize()
                logger.info("Alpha Vantage client initialized")
                
        except Exception as e:
            logger.error(f"Failed to initialize connections: {e}")
    
    async def start_data_collection(self):
        """Start background data collection tasks"""
        # TODO: Implement data collection loop
        logger.info("Data collection would start here")
        
    async def run(self):
        """Run the application"""
        try:
            # Initialize all connections
            await self.initialize_connections()
            
            # Start background tasks
            await self.start_data_collection()
            
            # Start web server
            port = int(os.getenv('PORT', 8000))
            runner = web_runner.AppRunner(self.app)
            await runner.setup()
            
            site = web_runner.TCPSite(runner, '0.0.0.0', port)
            await site.start()
            
            logger.info(f"🚀 Forex Trading Bot started on port {port}")
            logger.info(f"📊 Health check: http://localhost:{port}/health")
            logger.info(f"📈 Status: http://localhost:{port}/status")
            
            # Keep running
            while True:
                await asyncio.sleep(60)
                
        except Exception as e:
            logger.error(f"Application error: {e}")
            raise
        finally:
            await db_manager.close()


async def main():
    """Main entry point"""
    bot = ForexTradingBot()
    await bot.run()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Application stopped by user")
    except Exception as e:
        logger.error(f"Application failed: {e}")
        sys.exit(1)
