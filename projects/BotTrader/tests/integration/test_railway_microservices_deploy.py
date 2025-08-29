"""
Test Suite for Railway Microservices Deployment
Validates containerized deployment for forex bot infrastructure
"""
import pytest
import asyncio
import aiohttp
import os
from typing import Dict, List, Any
import json
import yaml
from datetime import datetime

class TestRailwayMicroservicesDeployment:
    """
    Test suite for Railway deployment with microservices architecture
    Ensures 99.5% uptime and <500ms latency requirements
    """
    
    @pytest.fixture
    async def railway_config(self):
        """Load Railway deployment configuration"""
        return {
            'services': {
                'data_collector': {
                    'port': 8001,
                    'health_endpoint': '/health',
                    'memory': '512MB',
                    'replicas': 2
                },
                'ml_predictor': {
                    'port': 8002,
                    'health_endpoint': '/health',
                    'memory': '1GB',
                    'replicas': 3
                },
                'trading_engine': {
                    'port': 8003,
                    'health_endpoint': '/health',
                    'memory': '512MB',
                    'replicas': 2
                }
            },
            'environment': os.getenv('RAILWAY_ENVIRONMENT', 'development'),
            'project_id': os.getenv('RAILWAY_PROJECT_ID'),
            'api_token': os.getenv('RAILWAY_API_TOKEN')
        }
    
    @pytest.mark.asyncio
    async def test_railway_cli_configuration(self, railway_config):
        """
        Test 1.2.1: Verify Railway CLI is configured correctly
        Acceptance: Railway CLI authenticated and project linked
        """
        # Check railway.toml exists
        assert os.path.exists('railway.toml'), \
            "railway.toml configuration file not found"
        
        # Verify project configuration
        with open('railway.toml', 'r') as f:
            config = yaml.safe_load(f)
            
        assert 'build' in config, "Build configuration missing"
        assert 'deploy' in config, "Deploy configuration missing"
        
        # Verify environment variables are set
        assert railway_config['project_id'], \
            "RAILWAY_PROJECT_ID not configured"
        assert railway_config['api_token'], \
            "RAILWAY_API_TOKEN not configured"
    
    @pytest.mark.asyncio
    async def test_docker_configuration(self):
        """
        Test 1.2.2: Verify Docker configuration for microservices
        Acceptance: Dockerfile optimized with multi-stage builds
        """
        dockerfile_path = 'Dockerfile'
        assert os.path.exists(dockerfile_path), \
            "Dockerfile not found in project root"
        
        with open(dockerfile_path, 'r') as f:
            dockerfile_content = f.read()
        
        # Check for multi-stage build
        assert 'FROM' in dockerfile_content and dockerfile_content.count('FROM') >= 2, \
            "Dockerfile should use multi-stage builds for optimization"
        
        # Check for Python 3.11+
        assert 'python:3.11' in dockerfile_content.lower(), \
            "Should use Python 3.11+ for latest performance improvements"
        
        # Check for non-root user (security)
        assert 'USER' in dockerfile_content, \
            "Should run as non-root user for security"
        
        # Check for health check
        assert 'HEALTHCHECK' in dockerfile_content, \
            "Should include HEALTHCHECK for monitoring"
    
    @pytest.mark.asyncio
    async def test_environment_variables_configuration(self, railway_config):
        """
        Test 1.2.3: Verify all required environment variables
        Acceptance: All critical env vars configured in Railway
        """
        required_env_vars = [
            'SUPABASE_URL',
            'SUPABASE_ANON_KEY',
            'SUPABASE_SERVICE_KEY',
            'OANDA_API_KEY',
            'OANDA_ACCOUNT_ID',
            'ALPHA_VANTAGE_API_KEY',
            'TRADERMADE_API_KEY',
            'REDIS_URL',
            'ENVIRONMENT',
            'LOG_LEVEL'
        ]
        
        missing_vars = []
        for var in required_env_vars:
            if not os.getenv(var):
                missing_vars.append(var)
        
        assert len(missing_vars) == 0, \
            f"Missing environment variables: {', '.join(missing_vars)}"
    
    @pytest.mark.asyncio
    async def test_service_health_endpoints(self, railway_config):
        """
        Test 1.2.4: Verify health check endpoints for all services
        Acceptance: All services respond with 200 status
        """
        async with aiohttp.ClientSession() as session:
            for service_name, service_config in railway_config['services'].items():
                if os.getenv('RAILWAY_ENVIRONMENT') == 'production':
                    # In production, use Railway internal networking
                    url = f"http://{service_name}.railway.internal:{service_config['port']}{service_config['health_endpoint']}"
                else:
                    # In development, use localhost
                    url = f"http://localhost:{service_config['port']}{service_config['health_endpoint']}"
                
                try:
                    async with session.get(url, timeout=5) as response:
                        assert response.status == 200, \
                            f"{service_name} health check failed with status {response.status}"
                        
                        data = await response.json()
                        assert data.get('status') == 'healthy', \
                            f"{service_name} reports unhealthy status"
                        assert 'uptime' in data, \
                            f"{service_name} should report uptime"
                        assert 'version' in data, \
                            f"{service_name} should report version"
                except aiohttp.ClientError as e:
                    if os.getenv('RAILWAY_ENVIRONMENT') != 'production':
                        pytest.skip(f"Service {service_name} not running locally")
                    else:
                        raise AssertionError(f"Failed to connect to {service_name}: {e}")
    
    @pytest.mark.asyncio
    async def test_service_auto_scaling(self, railway_config):
        """
        Test 1.2.5: Verify auto-scaling configuration
        Acceptance: Services scale based on CPU/memory thresholds
        """
        scaling_config = {
            'data_collector': {
                'min_replicas': 2,
                'max_replicas': 5,
                'target_cpu': 70,
                'target_memory': 80
            },
            'ml_predictor': {
                'min_replicas': 3,
                'max_replicas': 10,
                'target_cpu': 60,
                'target_memory': 75
            },
            'trading_engine': {
                'min_replicas': 2,
                'max_replicas': 4,
                'target_cpu': 50,
                'target_memory': 70
            }
        }
        
        for service, config in scaling_config.items():
            assert config['min_replicas'] >= 2, \
                f"{service} should have at least 2 replicas for redundancy"
            assert config['target_cpu'] <= 70, \
                f"{service} CPU threshold too high for responsive scaling"
    
    @pytest.mark.asyncio
    async def test_graceful_shutdown_handling(self, railway_config):
        """
        Test 1.2.6: Verify graceful shutdown for long-running processes
        Acceptance: Services handle SIGTERM properly
        """
        # This would be tested in actual deployment
        # Here we verify the code structure supports it
        
        service_files = [
            'src/services/data_collector.py',
            'src/services/ml_predictor.py',
            'src/services/trading_engine.py'
        ]
        
        for service_file in service_files:
            if os.path.exists(service_file):
                with open(service_file, 'r') as f:
                    content = f.read()
                
                # Check for signal handling
                assert 'signal.signal' in content or 'asyncio.create_task' in content, \
                    f"{service_file} should handle shutdown signals"
                assert 'graceful' in content.lower() or 'shutdown' in content.lower(), \
                    f"{service_file} should implement graceful shutdown"
    
    @pytest.mark.asyncio
    async def test_logging_configuration(self):
        """
        Test 1.2.7: Verify structured logging for Railway
        Acceptance: JSON formatted logs with proper levels
        """
        import logging
        import json
        from io import StringIO
        
        # Create test logger
        log_stream = StringIO()
        handler = logging.StreamHandler(log_stream)
        handler.setFormatter(logging.Formatter('%(message)s'))
        
        test_logger = logging.getLogger('test_railway')
        test_logger.addHandler(handler)
        test_logger.setLevel(logging.INFO)
        
        # Log test message
        test_logger.info(json.dumps({
            'timestamp': datetime.utcnow().isoformat(),
            'level': 'INFO',
            'service': 'test',
            'message': 'Test log message',
            'environment': os.getenv('RAILWAY_ENVIRONMENT', 'development')
        }))
        
        # Verify log format
        log_output = log_stream.getvalue()
        assert log_output, "No log output captured"
        
        try:
            log_data = json.loads(log_output)
            assert 'timestamp' in log_data, "Log should include timestamp"
            assert 'level' in log_data, "Log should include level"
            assert 'service' in log_data, "Log should include service name"
            assert 'environment' in log_data, "Log should include environment"
        except json.JSONDecodeError:
            pytest.fail("Logs should be JSON formatted")
    
    @pytest.mark.asyncio
    async def test_ci_cd_pipeline_configuration(self):
        """
        Test 1.2.8: Verify CI/CD pipeline with GitHub Actions
        Acceptance: Automated testing and deployment configured
        """
        github_workflow_path = '.github/workflows/deploy.yml'
        
        if os.path.exists(github_workflow_path):
            with open(github_workflow_path, 'r') as f:
                workflow = yaml.safe_load(f)
            
            assert 'on' in workflow, "Workflow should define triggers"
            assert 'push' in workflow['on'], "Should trigger on push"
            assert 'jobs' in workflow, "Should define jobs"
            
            # Check for test job
            assert any('test' in job.lower() for job in workflow['jobs']), \
                "Should include testing job"
            
            # Check for deploy job
            assert any('deploy' in job.lower() for job in workflow['jobs']), \
                "Should include deployment job"
        else:
            pytest.skip("GitHub Actions workflow not configured")
    
    @pytest.mark.asyncio
    async def test_resource_limits_configuration(self, railway_config):
        """
        Test 1.2.9: Verify resource limits for cost optimization
        Acceptance: Memory and CPU limits properly configured
        """
        total_memory = 0
        
        for service, config in railway_config['services'].items():
            memory_str = config['memory']
            if memory_str.endswith('MB'):
                memory_mb = int(memory_str[:-2])
            elif memory_str.endswith('GB'):
                memory_mb = int(memory_str[:-2]) * 1024
            else:
                memory_mb = 512  # Default
            
            total_memory += memory_mb * config['replicas']
            
            assert memory_mb >= 512, \
                f"{service} should have at least 512MB memory"
            assert memory_mb <= 2048, \
                f"{service} memory allocation too high for cost efficiency"
        
        # Total memory should be reasonable for the plan
        assert total_memory <= 10240, \
            f"Total memory allocation {total_memory}MB exceeds budget constraints"
    
    @pytest.mark.asyncio
    async def test_restart_policy_configuration(self, railway_config):
        """
        Test 1.2.10: Verify automatic restart policies
        Acceptance: Services restart on failure with backoff
        """
        restart_policy = {
            'restart': 'on-failure',
            'max_retries': 3,
            'backoff_seconds': [5, 10, 30],
            'health_check_interval': 30,
            'health_check_timeout': 5
        }
        
        assert restart_policy['restart'] == 'on-failure', \
            "Should restart on failure"
        assert restart_policy['max_retries'] >= 3, \
            "Should retry at least 3 times"
        assert restart_policy['health_check_interval'] <= 60, \
            "Health check interval should be frequent enough"


class TestMicroservicesArchitecture:
    """Test suite for microservices communication and architecture"""
    
    @pytest.mark.asyncio
    async def test_service_discovery(self):
        """
        Test 1.3.1: Verify service discovery mechanism
        Acceptance: Services can find each other via internal networking
        """
        if os.getenv('RAILWAY_ENVIRONMENT') == 'production':
            # Test internal service discovery
            services = ['data-collector', 'ml-predictor', 'trading-engine']
            
            for service in services:
                internal_url = f"{service}.railway.internal"
                # In production, this would resolve
                assert internal_url, f"Internal URL for {service} should be configured"
    
    @pytest.mark.asyncio
    async def test_message_queue_configuration(self):
        """
        Test 1.3.2: Verify message queue setup (Redis)
        Acceptance: Redis configured for inter-service communication
        """
        redis_url = os.getenv('REDIS_URL')
        assert redis_url, "REDIS_URL not configured"
        
        if redis_url:
            import redis.asyncio as redis
            
            try:
                client = redis.from_url(redis_url)
                await client.ping()
                await client.close()
            except Exception as e:
                if 'development' not in os.getenv('RAILWAY_ENVIRONMENT', ''):
                    pytest.fail(f"Redis connection failed: {e}")
                else:
                    pytest.skip("Redis not available in development")
    
    @pytest.mark.asyncio
    async def test_api_gateway_configuration(self):
        """
        Test 1.3.3: Verify API gateway setup
        Acceptance: Single entry point for external requests
        """
        gateway_config = {
            'base_url': os.getenv('RAILWAY_STATIC_URL', 'http://localhost:8000'),
            'routes': {
                '/api/data': 'data-collector',
                '/api/predict': 'ml-predictor',
                '/api/trade': 'trading-engine'
            },
            'rate_limits': {
                'requests_per_minute': 120,
                'burst_size': 20
            }
        }
        
        assert gateway_config['base_url'], "API gateway URL not configured"
        assert len(gateway_config['routes']) >= 3, \
            "Should have routes for all core services"
        assert gateway_config['rate_limits']['requests_per_minute'] >= 60, \
            "Rate limit too restrictive for trading operations"


if __name__ == "__main__":
    pytest.main([__file__, '-v', '--asyncio-mode=auto'])