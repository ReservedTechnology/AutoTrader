"""
Data Collector Microservice for BotTrader
Handles real-time forex data collection from multiple sources
"""
import asyncio
import os
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
from aiohttp import web
import json
import signal
import sys

# Configure logging
logging.basicConfig(
    level=os.getenv('LOG_LEVEL', 'INFO'),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DataCollectorService:
    """Main data collector service for forex data aggregation"""
    
    def __init__(self):
        self.app = web.Application()
        self.service_name = "data-collector"
        self.port = int(os.getenv('PORT', 8001))
        self.is_running = True
        self.start_time = datetime.utcnow()
        self.metrics = {
            'data_points_collected': 0,
            'errors': 0,
            'last_update': None,
            'active_sources': []
        }
        
        # Setup routes
        self.setup_routes()
        
        # Setup graceful shutdown
        signal.signal(signal.SIGTERM, self.handle_shutdown)
        signal.signal(signal.SIGINT, self.handle_shutdown)
    
    def setup_routes(self):
        """Configure HTTP endpoints"""
        self.app.router.add_get('/health', self.health_check)
        self.app.router.add_get('/status', self.status)
        self.app.router.add_get('/metrics', self.get_metrics)
        self.app.router.add_post('/collect', self.collect_data)
        self.app.router.add_get('/sources', self.list_sources)
    
    async def health_check(self, request):
        """Health check endpoint for container orchestration"""
        try:
            uptime = (datetime.utcnow() - self.start_time).total_seconds()
            
            # Check database connectivity (simplified for demo)
            db_status = await self.check_database()
            
            # Check data sources
            sources_status = await self.check_data_sources()
            
            health_status = {
                'status': 'healthy' if db_status and sources_status else 'degraded',
                'service': self.service_name,
                'uptime': uptime,
                'version': '1.0.0',
                'timestamp': datetime.utcnow().isoformat(),
                'checks': {
                    'database': 'connected' if db_status else 'disconnected',
                    'data_sources': 'available' if sources_status else 'unavailable'
                }
            }
            
            status_code = 200 if health_status['status'] == 'healthy' else 503
            return web.json_response(health_status, status=status_code)
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return web.json_response({
                'status': 'error',
                'error': str(e),
                'service': self.service_name
            }, status=500)
    
    async def status(self, request):
        """Detailed service status"""
        return web.json_response({
            'service': self.service_name,
            'port': self.port,
            'environment': os.getenv('ENVIRONMENT', 'development'),
            'is_running': self.is_running,
            'start_time': self.start_time.isoformat(),
            'data_points_collected': self.metrics['data_points_collected'],
            'active_sources': self.metrics['active_sources'],
            'supported_pairs': [
                'EUR_USD', 'GBP_JPY', 'AUD_JPY',
                'USD_TRY', 'NZD_JPY', 'USD_ZAR'
            ]
        })
    
    async def get_metrics(self, request):
        """Return service metrics"""
        return web.json_response(self.metrics)
    
    async def collect_data(self, request):
        """Endpoint to trigger data collection"""
        try:
            data = await request.json()
            symbol = data.get('symbol', 'EUR_USD')
            source = data.get('source', 'oanda')
            
            # Simulate data collection
            collected_data = {
                'symbol': symbol,
                'source': source,
                'timestamp': datetime.utcnow().isoformat(),
                'bid': 1.0950,
                'ask': 1.0952,
                'volume': 10000
            }
            
            # Update metrics
            self.metrics['data_points_collected'] += 1
            self.metrics['last_update'] = datetime.utcnow().isoformat()
            
            logger.info(f"Collected data for {symbol} from {source}")
            
            return web.json_response({
                'status': 'success',
                'data': collected_data
            })
            
        except Exception as e:
            logger.error(f"Data collection failed: {e}")
            self.metrics['errors'] += 1
            return web.json_response({
                'status': 'error',
                'error': str(e)
            }, status=500)
    
    async def list_sources(self, request):
        """List available data sources"""
        sources = [
            {
                'name': 'oanda',
                'type': 'primary',
                'status': 'active',
                'rate_limit': '120 req/s',
                'pairs_supported': 'all'
            },
            {
                'name': 'alphavantage',
                'type': 'historical',
                'status': 'active',
                'rate_limit': '5 req/min',
                'pairs_supported': 'major'
            },
            {
                'name': 'tradermade',
                'type': 'realtime',
                'status': 'active',
                'rate_limit': '1000 req/day',
                'pairs_supported': 'all'
            }
        ]
        
        self.metrics['active_sources'] = [s['name'] for s in sources if s['status'] == 'active']
        
        return web.json_response({'sources': sources})
    
    async def check_database(self) -> bool:
        """Check database connectivity"""
        # Simplified check - in production would actually test connection
        database_url = os.getenv('DATABASE_URL')
        return bool(database_url)
    
    async def check_data_sources(self) -> bool:
        """Check if data sources are available"""
        # Simplified check - in production would test each API
        return bool(os.getenv('OANDA_API_KEY'))
    
    def handle_shutdown(self, signum, frame):
        """Handle graceful shutdown"""
        logger.info(f"Received signal {signum}, shutting down gracefully...")
        self.is_running = False
        sys.exit(0)
    
    async def start_background_collection(self):
        """Start background data collection tasks"""
        while self.is_running:
            try:
                # Simulate periodic data collection
                logger.debug("Background collection cycle...")
                await asyncio.sleep(60)  # Collect every minute
            except Exception as e:
                logger.error(f"Background collection error: {e}")
                await asyncio.sleep(5)
    
    async def run(self):
        """Run the service"""
        logger.info(f"Starting {self.service_name} on port {self.port}")
        
        # Start background tasks
        asyncio.create_task(self.start_background_collection())
        
        # Run web server
        runner = web.AppRunner(self.app)
        await runner.setup()
        site = web.TCPSite(runner, '0.0.0.0', self.port)
        await site.start()
        
        logger.info(f"📊 Data Collector Service running on port {self.port}")
        
        # Keep running
        while self.is_running:
            await asyncio.sleep(1)


async def main():
    """Main entry point"""
    service = DataCollectorService()
    await service.run()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Service stopped by user")
    except Exception as e:
        logger.error(f"Service failed: {e}")
        sys.exit(1)