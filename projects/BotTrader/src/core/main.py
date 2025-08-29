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

from src.data.database.supabase_only_manager import db_manager
from src.data.connectors.oanda_connector import OandaV20Connector
from src.data.connectors.alphavantage_connector import AlphaVantageConnector
from src.data.redis_manager import redis_manager

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
        self.app.router.add_get('/cache/status', self.cache_status)
        self.app.router.add_get('/cache/clear', self.clear_cache)
        self.app.router.add_get('/pairs', self.forex_pairs)
        self.app.router.add_get('/latest/{symbol}', self.latest_price)
        
    async def health_check(self, request):
        """Health check endpoint"""
        try:
            # Test Supabase connection  
            supabase_ok = bool(db_manager.supabase)
            
            # Test Redis connection
            redis_status = redis_manager.get_health_status()
            redis_ok = redis_status['redis_connected']
            
            # Service is healthy if Supabase is working
            service_healthy = supabase_ok
            
            health_status = {
                'status': 'healthy' if service_healthy else 'degraded',
                'timestamp': datetime.utcnow().isoformat(),
                'services': {
                    'supabase': 'connected' if supabase_ok else 'disconnected',
                    'redis': 'connected' if redis_ok else 'fallback_memory',
                    'oanda': 'connected' if self.oanda_client else 'disconnected',
                    'alphavantage': 'connected' if self.alpha_client else 'disconnected'
                },
                'redis_info': redis_status
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
            # Try to get price from Redis cache first
            cached_price = redis_manager.get_price(symbol)
            
            if cached_price:
                logger.info(f"Price for {symbol} retrieved from cache")
                return web.json_response({
                    **cached_price,
                    'cache_hit': True
                })
            
            # If not in cache, create mock price (in production, fetch from DB/API)
            mock_price = {
                'symbol': symbol,
                'bid': 1.2345,
                'ask': 1.2347,
                'spread': 0.0002,
                'timestamp': datetime.utcnow().isoformat(),
                'source': 'mock_data',
                'cache_hit': False
            }
            
            # Cache the price for 30 seconds
            redis_manager.set_price(symbol, mock_price, ttl_seconds=30)
            
            return web.json_response(mock_price)
            
        except Exception as e:
            logger.error(f"Error getting price for {symbol}: {e}")
            return web.json_response({'error': str(e)}, status=500)
    
    async def cache_status(self, request):
        """Get Redis cache status and metrics"""
        try:
            cache_status = redis_manager.get_health_status()
            return web.json_response(cache_status)
            
        except Exception as e:
            logger.error(f"Error getting cache status: {e}")
            return web.json_response({'error': str(e)}, status=500)
    
    async def clear_cache(self, request):
        """Clear Redis cache"""
        try:
            # Get optional pattern from query parameters
            pattern = request.query.get('pattern', None)
            
            success = redis_manager.clear_cache(pattern)
            
            result = {
                'success': success,
                'pattern': pattern or 'all',
                'timestamp': datetime.utcnow().isoformat()
            }
            
            if success:
                logger.info(f"Cache cleared successfully with pattern: {pattern}")
                return web.json_response(result)
            else:
                return web.json_response(result, status=500)
            
        except Exception as e:
            logger.error(f"Error clearing cache: {e}")
            return web.json_response({'error': str(e)}, status=500)
    
    async def initialize_connections(self):
        """Initialize all external connections"""
        try:
            # Initialize database connections
            await db_manager.initialize()
            
            # Create tables (this might fail if DB structure has issues)
            try:
                await db_manager.create_forex_tables()
                logger.info("Database tables created/verified successfully")
            except Exception as table_error:
                logger.error(f"Failed to create/verify tables: {table_error}")
                # Continue without tables for now
            
            # Initialize API connections if keys are available
            oanda_key = os.getenv('OANDA_API_KEY')
            oanda_account = os.getenv('OANDA_ACCOUNT_ID')
            
            if oanda_key and oanda_account:
                try:
                    self.oanda_client = OandaV20Connector(
                        api_key=oanda_key,
                        account_id=oanda_account,
                        environment=os.getenv('OANDA_ENVIRONMENT', 'practice')
                    )
                    await self.oanda_client.initialize()
                    logger.info("OANDA client initialized")
                except Exception as oanda_error:
                    logger.error(f"Failed to initialize OANDA client: {oanda_error}")
            
            alpha_key = os.getenv('ALPHA_VANTAGE_API_KEY')
            if alpha_key:
                try:
                    self.alpha_client = AlphaVantageConnector(api_key=alpha_key)
                    await self.alpha_client.initialize()
                    logger.info("Alpha Vantage client initialized")
                except Exception as alpha_error:
                    logger.error(f"Failed to initialize Alpha Vantage client: {alpha_error}")
                
        except Exception as e:
            logger.error(f"Failed to initialize connections: {e}")
            # Don't re-raise the exception, let the app continue with partial functionality
    
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
