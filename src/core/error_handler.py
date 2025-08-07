#!/usr/bin/env python3
"""
Enhanced Error Handler
Comprehensive error handling with circuit breaker pattern and advanced recovery
"""

import asyncio
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Callable
from loguru import logger
from enum import Enum
import traceback


class ErrorSeverity(Enum):
    """Error severity levels"""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class CircuitBreakerState(Enum):
    """Circuit breaker states"""
    CLOSED = "CLOSED"  # Normal operation
    OPEN = "OPEN"      # Circuit is open, requests are blocked
    HALF_OPEN = "HALF_OPEN"  # Testing if service is recovered


class ErrorHandler:
    """Enhanced error handling system with circuit breaker pattern"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        
        # Error tracking
        self.error_history = []
        self.error_counts = {}
        self.last_error_time = {}
        
        # Dynamic circuit breaker configuration
        self.circuit_breakers = {}
        self.circuit_breaker_config = {}  # Will be initialized in initialize()
        
        # Dynamic error severity thresholds
        self.severity_thresholds = {}  # Will be initialized in initialize()
        
        # Dynamic alert configuration
        self.alert_enabled = config.get('alerts', {}).get('enabled', True)
        self.alert_cooldown = 300  # Will be initialized in initialize()
        self.last_alert_time = {}
        
        logger.info("🛡️ Enhanced Error Handler initialized")
    
    async def initialize(self):
        """Initialize dynamic parameters"""
        try:
            # Initialize dynamic configuration
            self.circuit_breaker_config = await self._get_dynamic_circuit_breaker_config(self.config)
            self.severity_thresholds = await self._get_dynamic_severity_thresholds(self.config)
            self.alert_cooldown = await self._get_dynamic_alert_cooldown(self.config)
            
            logger.info("✅ Error Handler dynamic parameters initialized")
            
        except Exception as e:
            logger.error(f"❌ Error Handler initialization error: {e}")
            raise
    
    async def handle_error(self, error: Exception, context: str, severity: ErrorSeverity = ErrorSeverity.MEDIUM,
                          component: str = "unknown", retry_count: int = 0) -> Dict[str, Any]:
        """Handle error with comprehensive logging and recovery"""
        try:
            error_info = {
                'timestamp': datetime.now(),
                'error_type': type(error).__name__,
                'error_message': str(error),
                'context': context,
                'component': component,
                'severity': severity.value,
                'retry_count': retry_count,
                'traceback': traceback.format_exc()
            }
            
            # Log error
            self._log_error(error_info)
            
            # Track error
            self._track_error(error_info)
            
            # Check circuit breaker
            circuit_state = self._check_circuit_breaker(component)
            
            # Determine recovery action
            recovery_action = await self._determine_recovery_action(error_info, circuit_state)
            
            # Send alert if needed
            if self.alert_enabled:
                await self._send_alert(error_info, recovery_action)
            
            return {
                'handled': True,
                'circuit_state': circuit_state.value,
                'recovery_action': recovery_action,
                'should_retry': recovery_action.get('should_retry', False),
                'retry_delay': recovery_action.get('retry_delay', 0),
                'error_info': error_info
            }
            
        except Exception as e:
            logger.error(f"❌ Error handler failed: {e}")
            return {
                'handled': False,
                'circuit_state': CircuitBreakerState.OPEN.value,
                'recovery_action': {'action': 'stop', 'should_retry': False},
                'error_info': {'error': str(e)}
            }
    
    def _log_error(self, error_info: Dict[str, Any]):
        """Log error with appropriate level"""
        severity = error_info['severity']
        context = error_info['context']
        component = error_info['component']
        error_msg = error_info['error_message']
        
        log_message = f"❌ [{severity}] {component}: {context} - {error_msg}"
        
        if severity == ErrorSeverity.CRITICAL.value:
            logger.critical(log_message)
        elif severity == ErrorSeverity.HIGH.value:
            logger.error(log_message)
        elif severity == ErrorSeverity.MEDIUM.value:
            logger.warning(log_message)
        else:
            logger.debug(log_message)
    
    def _track_error(self, error_info: Dict[str, Any]):
        """Track error for analysis and circuit breaker"""
        component = error_info['component']
        severity = error_info['severity']
        
        # Add to history
        self.error_history.append(error_info)
        
        # Keep only last 1000 errors
        if len(self.error_history) > 1000:
            self.error_history = self.error_history[-1000:]
        
        # Update error counts
        if component not in self.error_counts:
            self.error_counts[component] = {}
        
        if severity not in self.error_counts[component]:
            self.error_counts[component][severity] = 0
        
        self.error_counts[component][severity] += 1
        self.last_error_time[component] = datetime.now()
        
        # Update circuit breaker
        self._update_circuit_breaker(component, error_info)
    
    def _update_circuit_breaker(self, component: str, error_info: Dict[str, Any]):
        """Update circuit breaker state for component"""
        if component not in self.circuit_breakers:
            self.circuit_breakers[component] = {
                'state': CircuitBreakerState.CLOSED,
                'failure_count': 0,
                'success_count': 0,
                'last_failure_time': None,
                'last_success_time': None
            }
        
        cb = self.circuit_breakers[component]
        
        if error_info['severity'] in [ErrorSeverity.HIGH.value, ErrorSeverity.CRITICAL.value]:
            cb['failure_count'] += 1
            cb['last_failure_time'] = datetime.now()
            
            # Check if circuit should open
            if (cb['failure_count'] >= self.circuit_breaker_config['failure_threshold'] and 
                cb['state'] == CircuitBreakerState.CLOSED):
                cb['state'] = CircuitBreakerState.OPEN
                logger.warning(f"🔴 Circuit breaker OPEN for {component}")
        
        # Reset success count on failure
        cb['success_count'] = 0
    
    def _check_circuit_breaker(self, component: str) -> CircuitBreakerState:
        """Check circuit breaker state for component"""
        if component not in self.circuit_breakers:
            return CircuitBreakerState.CLOSED
        
        cb = self.circuit_breakers[component]
        
        if cb['state'] == CircuitBreakerState.OPEN:
            # Check if recovery timeout has passed
            if (cb['last_failure_time'] and 
                (datetime.now() - cb['last_failure_time']).seconds >= self.circuit_breaker_config['recovery_timeout']):
                cb['state'] = CircuitBreakerState.HALF_OPEN
                logger.info(f"🟡 Circuit breaker HALF-OPEN for {component}")
        
        return cb['state']
    
    async def _determine_recovery_action(self, error_info: Dict[str, Any], 
                                       circuit_state: CircuitBreakerState) -> Dict[str, Any]:
        """Determine appropriate recovery action based on error and circuit state"""
        severity = error_info['severity']
        component = error_info['component']
        retry_count = error_info['retry_count']
        
        # Circuit breaker is open - don't retry
        if circuit_state == CircuitBreakerState.OPEN:
            return {
                'action': 'circuit_open',
                'should_retry': False,
                'retry_delay': 0,
                'reason': 'Circuit breaker is open'
            }
        
        # Critical errors - stop immediately
        if severity == ErrorSeverity.CRITICAL.value:
            return {
                'action': 'stop',
                'should_retry': False,
                'retry_delay': 0,
                'reason': 'Critical error - stopping operation'
            }
        
        # High severity errors - limited retries
        if severity == ErrorSeverity.HIGH.value:
            if retry_count < 2:
                return {
                    'action': 'retry',
                    'should_retry': True,
                    'retry_delay': 30,  # 30 seconds
                    'reason': f'High severity error - retry {retry_count + 1}/2'
                }
            else:
                return {
                    'action': 'stop',
                    'should_retry': False,
                    'retry_delay': 0,
                    'reason': 'Max retries reached for high severity error'
                }
        
        # Medium severity errors - more retries with exponential backoff
        if severity == ErrorSeverity.MEDIUM.value:
            if retry_count < 3:
                retry_delay = 5 * (2 ** retry_count)  # 5s, 10s, 20s
                return {
                    'action': 'retry',
                    'should_retry': True,
                    'retry_delay': retry_delay,
                    'reason': f'Medium severity error - retry {retry_count + 1}/3'
                }
            else:
                return {
                    'action': 'stop',
                    'should_retry': False,
                    'retry_delay': 0,
                    'reason': 'Max retries reached for medium severity error'
                }
        
        # Low severity errors - continue with warning
        return {
            'action': 'continue',
            'should_retry': False,
            'retry_delay': 0,
            'reason': 'Low severity error - continuing operation'
        }
    
    async def _send_alert(self, error_info: Dict[str, Any], recovery_action: Dict[str, Any]):
        """Send alert for significant errors"""
        try:
            component = error_info['component']
            severity = error_info['severity']
            
            # Check if we should send alert
            if severity in [ErrorSeverity.HIGH.value, ErrorSeverity.CRITICAL.value]:
                # Check cooldown
                if (component in self.last_alert_time and 
                    (datetime.now() - self.last_alert_time[component]).seconds < self.alert_cooldown):
                    return
                
                # Send alert (implement based on notification system)
                alert_message = f"🚨 {severity} ERROR in {component}\n"
                alert_message += f"Context: {error_info['context']}\n"
                alert_message += f"Error: {error_info['error_message']}\n"
                alert_message += f"Recovery: {recovery_action['reason']}"
                
                logger.warning(f"📢 ALERT: {alert_message}")
                
                # Update last alert time
                self.last_alert_time[component] = datetime.now()
                
        except Exception as e:
            logger.error(f"❌ Alert sending failed: {e}")
    
    async def execute_with_retry(self, func: Callable, *args, max_retries: int = 3,
                               context: str = "unknown", component: str = "unknown",
                               **kwargs) -> Any:
        """Execute function with automatic retry and error handling"""
        retry_count = 0
        
        while retry_count <= max_retries:
            try:
                # Check circuit breaker
                circuit_state = self._check_circuit_breaker(component)
                if circuit_state == CircuitBreakerState.OPEN:
                    raise Exception(f"Circuit breaker is OPEN for {component}")
                
                # Execute function
                if asyncio.iscoroutinefunction(func):
                    result = await func(*args, **kwargs)
                else:
                    result = func(*args, **kwargs)
                
                # Success - update circuit breaker
                self._record_success(component)
                return result
                
            except Exception as e:
                # Handle error
                error_result = await self.handle_error(
                    error=e,
                    context=context,
                    severity=self._determine_severity(e),
                    component=component,
                    retry_count=retry_count
                )
                
                if not error_result['recovery_action']['should_retry']:
                    raise e
                
                retry_count += 1
                retry_delay = error_result['recovery_action']['retry_delay']
                
                logger.info(f"🔄 Retrying {component} in {retry_delay}s (attempt {retry_count}/{max_retries})")
                await asyncio.sleep(retry_delay)
        
        # Max retries reached
        raise Exception(f"Max retries ({max_retries}) exceeded for {component}")
    
    def _determine_severity(self, error: Exception) -> ErrorSeverity:
        """Determine error severity based on error type and message"""
        error_type = type(error).__name__
        error_message = str(error).lower()
        
        # Critical errors
        if any(keyword in error_message for keyword in ['authentication', 'unauthorized', 'forbidden']):
            return ErrorSeverity.CRITICAL
        
        # High severity errors
        if any(keyword in error_message for keyword in ['connection', 'timeout', 'network', 'database']):
            return ErrorSeverity.HIGH
        
        # Medium severity errors
        if any(keyword in error_message for keyword in ['rate limit', 'quota', 'validation']):
            return ErrorSeverity.MEDIUM
        
        # Default to medium
        return ErrorSeverity.MEDIUM
    
    def _record_success(self, component: str):
        """Record successful operation for circuit breaker"""
        if component not in self.circuit_breakers:
            return
        
        cb = self.circuit_breakers[component]
        cb['success_count'] += 1
        cb['last_success_time'] = datetime.now()
        
        # Reset failure count on success
        if cb['success_count'] >= self.circuit_breaker_config['success_threshold']:
            cb['failure_count'] = 0
            if cb['state'] == CircuitBreakerState.HALF_OPEN:
                cb['state'] = CircuitBreakerState.CLOSED
                logger.info(f"🟢 Circuit breaker CLOSED for {component}")
    
    def get_error_statistics(self) -> Dict[str, Any]:
        """Get error statistics"""
        try:
            # Calculate error rates
            total_errors = len(self.error_history)
            error_rate_by_component = {}
            
            for component, counts in self.error_counts.items():
                total_component_errors = sum(counts.values())
                error_rate_by_component[component] = {
                    'total_errors': total_component_errors,
                    'by_severity': counts,
                    'last_error': self.last_error_time.get(component)
                }
            
            # Circuit breaker status
            circuit_breaker_status = {}
            for component, cb in self.circuit_breakers.items():
                circuit_breaker_status[component] = {
                    'state': cb['state'].value,
                    'failure_count': cb['failure_count'],
                    'success_count': cb['success_count'],
                    'last_failure': cb['last_failure_time'],
                    'last_success': cb['last_success_time']
                }
            
            return {
                'total_errors': total_errors,
                'error_rate_by_component': error_rate_by_component,
                'circuit_breaker_status': circuit_breaker_status,
                'recent_errors': self.error_history[-10:] if self.error_history else []
            }
            
        except Exception as e:
            logger.error(f"❌ Error statistics calculation failed: {e}")
            return {'error': str(e)}
    
    def reset_circuit_breaker(self, component: str):
        """Manually reset circuit breaker for component"""
        if component in self.circuit_breakers:
            cb = self.circuit_breakers[component]
            cb['state'] = CircuitBreakerState.CLOSED
            cb['failure_count'] = 0
            cb['success_count'] = 0
            logger.info(f"🔄 Circuit breaker manually reset for {component}")
    
    async def _get_dynamic_circuit_breaker_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Get dynamic circuit breaker configuration based on error patterns"""
        try:
            base_config = {
                'failure_threshold': config.get('circuit_breaker', {}).get('failure_threshold', 5),
                'recovery_timeout': config.get('circuit_breaker', {}).get('recovery_timeout', 60),
                'success_threshold': config.get('circuit_breaker', {}).get('success_threshold', 2)
            }
            
            # Adjust based on recent error patterns
            recent_errors = len([e for e in self.error_history 
                               if (datetime.now() - e['timestamp']).total_seconds() < 3600])  # Last hour
            
            if recent_errors > 20:
                # High error frequency - more conservative settings
                base_config['failure_threshold'] = max(3, base_config['failure_threshold'] - 2)
                base_config['recovery_timeout'] = min(120, base_config['recovery_timeout'] * 2)
                base_config['success_threshold'] = max(1, base_config['success_threshold'] - 1)
            elif recent_errors < 5:
                # Low error frequency - more aggressive settings
                base_config['failure_threshold'] = min(10, base_config['failure_threshold'] + 2)
                base_config['recovery_timeout'] = max(30, base_config['recovery_timeout'] // 2)
                base_config['success_threshold'] = min(5, base_config['success_threshold'] + 1)
            
            logger.info(f"📊 Dynamic circuit breaker config - failure_threshold: {base_config['failure_threshold']}, "
                       f"recovery_timeout: {base_config['recovery_timeout']}, success_threshold: {base_config['success_threshold']}")
            
            return base_config
            
        except Exception as e:
            logger.warning(f"⚠️ Could not calculate dynamic circuit breaker config: {e}")
            return {
                'failure_threshold': config.get('circuit_breaker', {}).get('failure_threshold', 5),
                'recovery_timeout': config.get('circuit_breaker', {}).get('recovery_timeout', 60),
                'success_threshold': config.get('circuit_breaker', {}).get('success_threshold', 2)
            }
    
    async def _get_dynamic_severity_thresholds(self, config: Dict[str, Any]) -> Dict[str, int]:
        """Get dynamic severity thresholds based on error patterns"""
        try:
            base_thresholds = {
                'low': config.get('error_thresholds', {}).get('low', 10),
                'medium': config.get('error_thresholds', {}).get('medium', 5),
                'high': config.get('error_thresholds', {}).get('high', 3),
                'critical': config.get('error_thresholds', {}).get('critical', 1)
            }
            
            # Adjust based on recent error severity distribution
            recent_errors = [e for e in self.error_history 
                           if (datetime.now() - e['timestamp']).total_seconds() < 3600]  # Last hour
            
            if recent_errors:
                critical_count = len([e for e in recent_errors if e['severity'] == 'CRITICAL'])
                high_count = len([e for e in recent_errors if e['severity'] == 'HIGH'])
                
                if critical_count > 2 or high_count > 5:
                    # High severity errors - lower thresholds
                    base_thresholds['critical'] = max(1, base_thresholds['critical'])
                    base_thresholds['high'] = max(2, base_thresholds['high'] - 1)
                    base_thresholds['medium'] = max(3, base_thresholds['medium'] - 2)
                elif critical_count == 0 and high_count == 0:
                    # Low severity errors - higher thresholds
                    base_thresholds['critical'] = min(3, base_thresholds['critical'] + 1)
                    base_thresholds['high'] = min(5, base_thresholds['high'] + 1)
                    base_thresholds['medium'] = min(8, base_thresholds['medium'] + 2)
            
            logger.info(f"📊 Dynamic severity thresholds - {base_thresholds}")
            return base_thresholds
            
        except Exception as e:
            logger.warning(f"⚠️ Could not calculate dynamic severity thresholds: {e}")
            return {
                'low': config.get('error_thresholds', {}).get('low', 10),
                'medium': config.get('error_thresholds', {}).get('medium', 5),
                'high': config.get('error_thresholds', {}).get('high', 3),
                'critical': config.get('error_thresholds', {}).get('critical', 1)
            }
    
    async def _get_dynamic_alert_cooldown(self, config: Dict[str, Any]) -> int:
        """Get dynamic alert cooldown based on error frequency"""
        try:
            base_cooldown = config.get('alerts', {}).get('cooldown_seconds', 300)
            
            # Check recent error frequency
            recent_errors = len([e for e in self.error_history 
                               if (datetime.now() - e['timestamp']).total_seconds() < 1800])  # Last 30 minutes
            
            if recent_errors > 15:
                # High error frequency - increase cooldown
                return min(600, base_cooldown * 2)
            elif recent_errors < 3:
                # Low error frequency - decrease cooldown
                return max(60, base_cooldown // 2)
            else:
                return base_cooldown
                
        except Exception as e:
            logger.warning(f"⚠️ Could not calculate dynamic alert cooldown: {e}")
            return config.get('alerts', {}).get('cooldown_seconds', 300)
    
    def clear_error_history(self):
        """Clear error history"""
        self.error_history.clear()
        self.error_counts.clear()
        self.last_error_time.clear()
        logger.info("🧹 Error history cleared")