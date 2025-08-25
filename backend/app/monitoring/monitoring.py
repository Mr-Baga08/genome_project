# backend/app/monitoring/monitoring.py
import asyncio
import json
import time
import psutil
import logging
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from collections import defaultdict, deque
from functools import wraps
import uuid
import traceback
import numpy as np

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

@dataclass
class PerformanceMetric:
    """Performance metric data structure"""
    metric_name: str
    value: float
    unit: str
    timestamp: datetime
    labels: Dict[str, str]
    threshold_warning: Optional[float] = None
    threshold_critical: Optional[float] = None

@dataclass
class SystemAlert:
    """System alert data structure"""
    alert_id: str
    severity: str  # info, warning, error, critical
    title: str
    description: str
    source: str
    timestamp: datetime
    resolved: bool = False
    resolved_at: Optional[datetime] = None
    metadata: Dict[str, Any] = None

@dataclass
class SequenceOperation:
    """Sequence operation logging structure"""
    operation_id: str
    operation_type: str
    user_id: str
    sequence_count: int
    sequence_lengths: List[int]
    parameters: Dict[str, Any]
    success: bool
    duration: float
    timestamp: datetime
    memory_usage_mb: Optional[float] = None
    error_message: Optional[str] = None

class BioinformaticsMonitoring:
    """Comprehensive monitoring system for bioinformatics platform"""
    
    def __init__(self, retention_days: int = 30):
        self.retention_days = retention_days
        
        # Performance metrics storage
        self.metrics = defaultdict(lambda: deque(maxlen=1000))
        self.alerts = deque(maxlen=1000)
        self.sequence_operations = deque(maxlen=5000)
        
        # System monitoring
        self.start_time = datetime.utcnow()
        self.system_stats = {}
        
        # Performance thresholds
        self.thresholds = {
            'cpu_usage': {'warning': 70.0, 'critical': 90.0},
            'memory_usage': {'warning': 80.0, 'critical': 95.0},
            'disk_usage': {'warning': 85.0, 'critical': 95.0},
            'response_time_ms': {'warning': 5000.0, 'critical': 15000.0},
            'error_rate': {'warning': 5.0, 'critical': 15.0}
        }
        
        # Monitoring intervals
        self.monitoring_tasks = []
        self.monitoring_active = False
        
        # Custom metrics
        self.custom_counters = defaultdict(int)
        self.custom_gauges = defaultdict(float)
        self.custom_histograms = defaultdict(list)
    
    async def start_monitoring(self):
        """Start background monitoring tasks"""
        
        if self.monitoring_active:
            return
        
        self.monitoring_active = True
        
        # Start monitoring tasks
        self.monitoring_tasks = [
            asyncio.create_task(self._monitor_system_resources()),
            asyncio.create_task(self._monitor_application_metrics()),
            asyncio.create_task(self._cleanup_old_data()),
            asyncio.create_task(self._check_system_health())
        ]
        
        logger.info("Monitoring system started")
    
    async def stop_monitoring(self):
        """Stop monitoring tasks"""
        
        self.monitoring_active = False
        
        for task in self.monitoring_tasks:
            task.cancel()
        
        # Wait for tasks to complete
        await asyncio.gather(*self.monitoring_tasks, return_exceptions=True)
        
        logger.info("Monitoring system stopped")
    
    async def _monitor_system_resources(self):
        """Monitor system resource usage"""
        
        while self.monitoring_active:
            try:
                current_time = datetime.utcnow()
                
                # CPU usage
                cpu_percent = psutil.cpu_percent(interval=1)
                self.record_metric(
                    "system_cpu_usage_percent",
                    cpu_percent,
                    "percent",
                    {"component": "system"},
                    self.thresholds['cpu_usage']['warning'],
                    self.thresholds['cpu_usage']['critical']
                )
                
                # Memory usage
                memory = psutil.virtual_memory()
                memory_percent = memory.percent
                self.record_metric(
                    "system_memory_usage_percent",
                    memory_percent,
                    "percent",
                    {"component": "system"},
                    self.thresholds['memory_usage']['warning'],
                    self.thresholds['memory_usage']['critical']
                )
                
                # Disk usage
                disk = psutil.disk_usage('/')
                disk_percent = (disk.used / disk.total) * 100
                self.record_metric(
                    "system_disk_usage_percent",
                    disk_percent,
                    "percent",
                    {"component": "system"},
                    self.thresholds['disk_usage']['warning'],
                    self.thresholds['disk_usage']['critical']
                )
                
                # Network I/O
                network = psutil.net_io_counters()
                self.record_metric("network_bytes_sent", network.bytes_sent, "bytes", {"direction": "out"})
                self.record_metric("network_bytes_recv", network.bytes_recv, "bytes", {"direction": "in"})
                
                # Process count
                process_count = len(psutil.pids())
                self.record_metric("system_process_count", process_count, "count", {"component": "system"})
                
                await asyncio.sleep(60)  # Monitor every minute
                
            except Exception as e:
                logger.error(f"Error monitoring system resources: {str(e)}")
                await asyncio.sleep(60)
    
    async def _monitor_application_metrics(self):
        """Monitor application-specific metrics"""
        
        while self.monitoring_active:
            try:
                current_time = datetime.utcnow()
                
                # Application uptime
                uptime_seconds = (current_time - self.start_time).total_seconds()
                self.record_metric("app_uptime_seconds", uptime_seconds, "seconds", {"component": "app"})
                
                # Custom counters and gauges
                for counter_name, value in self.custom_counters.items():
                    self.record_metric(f"custom_counter_{counter_name}", value, "count", {"type": "counter"})
                
                for gauge_name, value in self.custom_gauges.items():
                    self.record_metric(f"custom_gauge_{gauge_name}", value, "value", {"type": "gauge"})
                
                # Histogram metrics (calculate percentiles)
                for hist_name, values in self.custom_histograms.items():
                    if values:
                        self.record_metric(f"histogram_{hist_name}_p50", np.percentile(values, 50), "value", {"percentile": "50"})
                        self.record_metric(f"histogram_{hist_name}_p95", np.percentile(values, 95), "value", {"percentile": "95"})
                        self.record_metric(f"histogram_{hist_name}_p99", np.percentile(values, 99), "value", {"percentile": "99"})
                
                await asyncio.sleep(300)  # Monitor every 5 minutes
                
            except Exception as e:
                logger.error(f"Error monitoring application metrics: {str(e)}")
                await asyncio.sleep(300)
    
    async def _cleanup_old_data(self):
        """Clean up old monitoring data"""
        
        while self.monitoring_active:
            try:
                cutoff_time = datetime.utcnow() - timedelta(days=self.retention_days)
                
                # Clean metrics
                for metric_name, metric_deque in self.metrics.items():
                    # Remove old entries
                    while metric_deque and metric_deque[0].timestamp < cutoff_time:
                        metric_deque.popleft()
                
                # Clean alerts
                while self.alerts and self.alerts[0].timestamp < cutoff_time:
                    self.alerts.popleft()
                
                # Clean sequence operations
                while self.sequence_operations and self.sequence_operations[0].timestamp < cutoff_time:
                    self.sequence_operations.popleft()
                
                # Clean custom histograms (keep only recent data)
                max_histogram_size = 1000
                for hist_name, values in self.custom_histograms.items():
                    if len(values) > max_histogram_size:
                        # Keep only the most recent values
                        self.custom_histograms[hist_name] = values[-max_histogram_size:]
                
                logger.info("Completed monitoring data cleanup")
                
                await asyncio.sleep(3600)  # Clean every hour
                
            except Exception as e:
                logger.error(f"Error cleaning up monitoring data: {str(e)}")
                await asyncio.sleep(3600)
    
    async def _check_system_health(self):
        """Perform periodic system health checks"""
        
        while self.monitoring_active:
            try:
                health_status = await self.get_system_health()
                
                # Generate alerts based on health status
                if health_status['status'] == 'critical':
                    await self._create_alert(
                        "critical",
                        "System Health Critical",
                        f"System health is critical: {health_status.get('issues', [])}",
                        "health_monitor"
                    )
                elif health_status['status'] == 'warning':
                    await self._create_alert(
                        "warning",
                        "System Health Warning",
                        f"System health degraded: {health_status.get('issues', [])}",
                        "health_monitor"
                    )
                
                await asyncio.sleep(300)  # Check every 5 minutes
                
            except Exception as e:
                logger.error(f"Error in health check: {str(e)}")
                await asyncio.sleep(300)
    
    def record_metric(
        self, 
        metric_name: str, 
        value: float, 
        unit: str, 
        labels: Dict[str, str] = None,
        warning_threshold: float = None,
        critical_threshold: float = None
    ):
        """Record a performance metric"""
        
        if labels is None:
            labels = {}
        
        metric = PerformanceMetric(
            metric_name=metric_name,
            value=value,
            unit=unit,
            timestamp=datetime.utcnow(),
            labels=labels,
            threshold_warning=warning_threshold,
            threshold_critical=critical_threshold
        )
        
        self.metrics[metric_name].append(metric)
        
        # Check thresholds and create alerts
        if critical_threshold and value >= critical_threshold:
            asyncio.create_task(self._create_alert(
                "critical",
                f"Critical Threshold Exceeded: {metric_name}",
                f"Metric {metric_name} value {value} exceeds critical threshold {critical_threshold}",
                "threshold_monitor"
            ))
        elif warning_threshold and value >= warning_threshold:
            asyncio.create_task(self._create_alert(
                "warning",
                f"Warning Threshold Exceeded: {metric_name}",
                f"Metric {metric_name} value {value} exceeds warning threshold {warning_threshold}",
                "threshold_monitor"
            ))
    
    def log_sequence_operation(
        self, 
        operation: str, 
        user_id: str, 
        sequence_data: Dict, 
        success: bool, 
        duration: float,
        parameters: Dict = None,
        error_message: str = None
    ):
        """Log sequence operations with structured data"""
        
        if parameters is None:
            parameters = {}
        
        # Extract sequence information
        if isinstance(sequence_data, list):
            sequences = sequence_data
        elif isinstance(sequence_data, dict) and 'sequences' in sequence_data:
            sequences = sequence_data['sequences']
        else:
            sequences = [sequence_data] if sequence_data else []
        
        # Calculate sequence metrics
        sequence_count = len(sequences)
        sequence_lengths = []
        
        for seq in sequences:
            if isinstance(seq, dict):
                seq_str = seq.get('sequence', '')
            else:
                seq_str = str(seq)
            sequence_lengths.append(len(seq_str))
        
        # Get memory usage
        memory_usage = None
        try:
            process = psutil.Process()
            memory_usage = process.memory_info().rss / (1024 * 1024)  # MB
        except:
            pass
        
        # Create operation log
        operation_log = SequenceOperation(
            operation_id=str(uuid.uuid4()),
            operation_type=operation,
            user_id=user_id,
            sequence_count=sequence_count,
            sequence_lengths=sequence_lengths,
            parameters=parameters,
            success=success,
            duration=duration,
            timestamp=datetime.utcnow(),
            memory_usage_mb=memory_usage,
            error_message=error_message
        )
        
        self.sequence_operations.append(operation_log)
        
        # Update custom metrics
        self.custom_counters[f"operation_{operation}"] += 1
        self.custom_histograms[f"duration_{operation}"].append(duration)
        
        if not success:
            self.custom_counters[f"error_{operation}"] += 1
        
        # Log structured data
        log_data = {
            "event_type": "sequence_operation",
            "operation": operation,
            "user_id": user_id,
            "sequence_count": sequence_count,
            "success": success,
            "duration": duration,
            "timestamp": operation_log.timestamp.isoformat()
        }
        
        if error_message:
            log_data["error"] = error_message
        
        logger.info(f"Sequence operation logged: {json.dumps(log_data)}")
    
    async def _create_alert(self, severity: str, title: str, description: str, source: str, metadata: Dict = None):
        """Create system alert"""
        
        alert = SystemAlert(
            alert_id=str(uuid.uuid4()),
            severity=severity,
            title=title,
            description=description,
            source=source,
            timestamp=datetime.utcnow(),
            metadata=metadata or {}
        )
        
        self.alerts.append(alert)
        
        # Log alert
        logger.log(
            logging.CRITICAL if severity == "critical" else 
            logging.ERROR if severity == "error" else 
            logging.WARNING if severity == "warning" else logging.INFO,
            f"ALERT [{severity.upper()}] {title}: {description}"
        )
    
    def monitor_operation(self, operation_name: str, user_id: str = "system"):
        """Decorator to monitor operation performance"""
        
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            async def wrapper(*args, **kwargs):
                start_time = time.time()
                operation_id = str(uuid.uuid4())
                
                # Extract sequence data from arguments for logging
                sequence_data = None
                if args:
                    for arg in args:
                        if isinstance(arg, (list, dict)) and self._contains_sequence_data(arg):
                            sequence_data = arg
                            break
                
                if not sequence_data:
                    for kwarg_value in kwargs.values():
                        if isinstance(kwarg_value, (list, dict)) and self._contains_sequence_data(kwarg_value):
                            sequence_data = kwarg_value
                            break
                
                try:
                    # Execute function
                    result = await func(*args, **kwargs)
                    
                    # Calculate duration
                    duration = time.time() - start_time
                    
                    # Log successful operation
                    self.log_sequence_operation(
                        operation=operation_name,
                        user_id=user_id,
                        sequence_data=sequence_data or {},
                        success=True,
                        duration=duration,
                        parameters=kwargs
                    )
                    
                    # Record performance metric
                    self.record_metric(
                        f"operation_duration_{operation_name}",
                        duration * 1000,  # Convert to milliseconds
                        "ms",
                        {"operation": operation_name, "status": "success"}
                    )
                    
                    return result
                    
                except Exception as e:
                    # Calculate duration
                    duration = time.time() - start_time
                    
                    # Log failed operation
                    self.log_sequence_operation(
                        operation=operation_name,
                        user_id=user_id,
                        sequence_data=sequence_data or {},
                        success=False,
                        duration=duration,
                        parameters=kwargs,
                        error_message=str(e)
                    )
                    
                    # Record error metric
                    self.record_metric(
                        f"operation_errors_{operation_name}",
                        1,
                        "count",
                        {"operation": operation_name, "error_type": type(e).__name__}
                    )
                    
                    # Create alert for critical errors
                    if isinstance(e, (MemoryError, OSError)):
                        await self._create_alert(
                            "critical",
                            f"Critical Error in {operation_name}",
                            f"Operation failed with critical error: {str(e)}",
                            "operation_monitor",
                            {"operation": operation_name, "user_id": user_id}
                        )
                    
                    raise
            
            return wrapper
        return decorator
    
    def _contains_sequence_data(self, data: Any) -> bool:
        """Check if data contains sequence information"""
        
        if isinstance(data, dict):
            return any(key in data for key in ['sequence', 'sequences', 'sequence_data'])
        elif isinstance(data, list):
            return any(self._contains_sequence_data(item) for item in data[:5])  # Check first 5 items
        
        return False
    
    async def get_system_health(self) -> Dict[str, Any]:
        """Get comprehensive system health status"""
        
        health_status = {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "components": {},
            "issues": [],
            "recommendations": []
        }
        
        try:
            # Check system resources
            cpu_usage = psutil.cpu_percent()
            memory_usage = psutil.virtual_memory().percent
            disk_usage = psutil.disk_usage('/').percent if hasattr(psutil.disk_usage('/'), 'percent') else 0
            
            # System component health
            health_status["components"]["system"] = {
                "status": "healthy",
                "cpu_usage": cpu_usage,
                "memory_usage": memory_usage,
                "disk_usage": disk_usage
            }
            
            # Check thresholds
            if cpu_usage > self.thresholds['cpu_usage']['critical']:
                health_status["status"] = "critical"
                health_status["issues"].append(f"Critical CPU usage: {cpu_usage:.1f}%")
                health_status["components"]["system"]["status"] = "critical"
            elif cpu_usage > self.thresholds['cpu_usage']['warning']:
                if health_status["status"] == "healthy":
                    health_status["status"] = "warning"
                health_status["issues"].append(f"High CPU usage: {cpu_usage:.1f}%")
                health_status["components"]["system"]["status"] = "warning"
            
            if memory_usage > self.thresholds['memory_usage']['critical']:
                health_status["status"] = "critical"
                health_status["issues"].append(f"Critical memory usage: {memory_usage:.1f}%")
                health_status["components"]["system"]["status"] = "critical"
            elif memory_usage > self.thresholds['memory_usage']['warning']:
                if health_status["status"] in ["healthy", "warning"]:
                    health_status["status"] = "warning"
                health_status["issues"].append(f"High memory usage: {memory_usage:.1f}%")
                
                if health_status["components"]["system"]["status"] == "healthy":
                    health_status["components"]["system"]["status"] = "warning"
            
            # Check application metrics
            recent_errors = await self._get_recent_error_rate()
            if recent_errors > self.thresholds['error_rate']['critical']:
                health_status["status"] = "critical"
                health_status["issues"].append(f"High error rate: {recent_errors:.1f}%")
            elif recent_errors > self.thresholds['error_rate']['warning']:
                if health_status["status"] == "healthy":
                    health_status["status"] = "warning"
                health_status["issues"].append(f"Elevated error rate: {recent_errors:.1f}%")
            
            # Application component health
            health_status["components"]["application"] = {
                "status": "healthy" if recent_errors < self.thresholds['error_rate']['warning'] else "warning",
                "error_rate": recent_errors,
                "active_operations": len([op for op in self.sequence_operations if (datetime.utcnow() - op.timestamp).total_seconds() < 300])
            }
            
            # Check external dependencies (mock)
            health_status["components"]["database"] = {"status": "healthy", "connection": True}
            health_status["components"]["cache"] = {"status": "healthy", "connection": True}
            health_status["components"]["docker"] = {"status": "healthy", "available": True}
            
            # Generate recommendations
            if cpu_usage > 80:
                health_status["recommendations"].append("Consider scaling compute resources")
            if memory_usage > 85:
                health_status["recommendations"].append("Optimize memory usage or increase available memory")
            if recent_errors > 5:
                health_status["recommendations"].append("Investigate recent error patterns")
            
        except Exception as e:
            logger.error(f"Error checking system health: {str(e)}")
            health_status["status"] = "critical"
            health_status["issues"].append(f"Health check failed: {str(e)}")
        
        return health_status
    
    async def _get_recent_error_rate(self) -> float:
        """Calculate recent error rate from operations"""
        
        cutoff_time = datetime.utcnow() - timedelta(hours=1)
        recent_operations = [
            op for op in self.sequence_operations 
            if op.timestamp > cutoff_time
        ]
        
        if not recent_operations:
            return 0.0
        
        error_count = sum(1 for op in recent_operations if not op.success)
        return (error_count / len(recent_operations)) * 100
    
    async def get_performance_dashboard(self) -> Dict[str, Any]:
        """Get data for performance dashboard"""
        
        dashboard = {
            "timestamp": datetime.utcnow().isoformat(),
            "overview": {},
            "metrics": {},
            "recent_operations": [],
            "alerts": [],
            "trends": {}
        }
        
        try:
            # Overview statistics
            recent_cutoff = datetime.utcnow() - timedelta(hours=24)
            recent_operations = [op for op in self.sequence_operations if op.timestamp > recent_cutoff]
            
            dashboard["overview"] = {
                "total_operations_24h": len(recent_operations),
                "successful_operations_24h": sum(1 for op in recent_operations if op.success),
                "error_rate_24h": self._get_error_rate_for_operations(recent_operations),
                "average_duration_24h": np.mean([op.duration for op in recent_operations]) if recent_operations else 0,
                "active_alerts": len([alert for alert in self.alerts if not alert.resolved]),
                "system_uptime_hours": (datetime.utcnow() - self.start_time).total_seconds() / 3600
            }
            
            # Current metrics
            dashboard["metrics"] = {
                "cpu_usage": self._get_latest_metric_value("system_cpu_usage_percent"),
                "memory_usage": self._get_latest_metric_value("system_memory_usage_percent"),
                "disk_usage": self._get_latest_metric_value("system_disk_usage_percent"),
                "network_io": {
                    "bytes_sent": self._get_latest_metric_value("network_bytes_sent"),
                    "bytes_received": self._get_latest_metric_value("network_bytes_recv")
                }
            }
            
            # Recent operations summary
            dashboard["recent_operations"] = [
                {
                    "operation_type": op.operation_type,
                    "user_id": op.user_id,
                    "sequence_count": op.sequence_count,
                    "duration": op.duration,
                    "success": op.success,
                    "timestamp": op.timestamp.isoformat()
                }
                for op in list(self.sequence_operations)[-20:]  # Last 20 operations
            ]
            
            # Recent alerts
            dashboard["alerts"] = [
                {
                    "severity": alert.severity,
                    "title": alert.title,
                    "description": alert.description,
                    "timestamp": alert.timestamp.isoformat(),
                    "resolved": alert.resolved
                }
                for alert in list(self.alerts)[-10:]  # Last 10 alerts
            ]
            
            # Performance trends
            dashboard["trends"] = await self._calculate_performance_trends()
            
        except Exception as e:
            logger.error(f"Error generating performance dashboard: {str(e)}")
            dashboard["error"] = str(e)
        
        return dashboard
    
    def _get_latest_metric_value(self, metric_name: str) -> Optional[float]:
        """Get the latest value for a metric"""
        
        if metric_name in self.metrics and self.metrics[metric_name]:
            return self.metrics[metric_name][-1].value
        return None
    
    def _get_error_rate_for_operations(self, operations: List[SequenceOperation]) -> float:
        """Calculate error rate for operations"""
        
        if not operations:
            return 0.0
        
        error_count = sum(1 for op in operations if not op.success)
        return (error_count / len(operations)) * 100
    
    async def _calculate_performance_trends(self) -> Dict[str, Any]:
        """Calculate performance trends over time"""
        
        trends = {}
        
        try:
            # Calculate trends for key metrics
            key_metrics = [
                "system_cpu_usage_percent",
                "system_memory_usage_percent", 
                "system_disk_usage_percent"
            ]
            
            for metric_name in key_metrics:
                if metric_name in self.metrics:
                    metric_values = [m.value for m in self.metrics[metric_name]]
                    timestamps = [m.timestamp for m in self.metrics[metric_name]]
                    
                    if len(metric_values) >= 2:
                        # Calculate trend (simple linear regression slope)
                        x = np.arange(len(metric_values))
                        slope, _ = np.polyfit(x, metric_values, 1)
                        
                        trends[metric_name] = {
                            "current_value": metric_values[-1] if metric_values else 0,
                            "trend_slope": float(slope),
                            "trend_direction": "increasing" if slope > 0.1 else "decreasing" if slope < -0.1 else "stable",
                            "data_points": len(metric_values),
                            "time_range_hours": (timestamps[-1] - timestamps[0]).total_seconds() / 3600 if len(timestamps) >= 2 else 0
                        }
            
            # Operation trends
            if self.sequence_operations:
                recent_ops = list(self.sequence_operations)[-100:]  # Last 100 operations
                
                operation_types = defaultdict(list)
                for op in recent_ops:
                    operation_types[op.operation_type].append(op)
                
                trends["operations"] = {}
                for op_type, ops in operation_types.items():
                    durations = [op.duration for op in ops]
                    success_rate = (sum(1 for op in ops if op.success) / len(ops)) * 100
                    
                    trends["operations"][op_type] = {
                        "count": len(ops),
                        "success_rate": success_rate,
                        "avg_duration": np.mean(durations),
                        "duration_trend": "stable"  # Simplified
                    }
        
        except Exception as e:
            logger.error(f"Error calculating performance trends: {str(e)}")
            trends["error"] = str(e)
        
        return trends
    
    async def export_monitoring_data(self, format_type: str = "json", time_range_hours: int = 24) -> str:
        """Export monitoring data for analysis"""
        
        try:
            cutoff_time = datetime.utcnow() - timedelta(hours=time_range_hours)
            
            # Filter data by time range
            filtered_metrics = {}
            for metric_name, metric_deque in self.metrics.items():
                filtered_metrics[metric_name] = [
                    asdict(metric) for metric in metric_deque 
                    if metric.timestamp > cutoff_time
                ]
            
            filtered_operations = [
                asdict(op) for op in self.sequence_operations 
                if op.timestamp > cutoff_time
            ]
            
            filtered_alerts = [
                asdict(alert) for alert in self.alerts 
                if alert.timestamp > cutoff_time
            ]
            
            export_data = {
                "export_timestamp": datetime.utcnow().isoformat(),
                "time_range_hours": time_range_hours,
                "metrics": filtered_metrics,
                "operations": filtered_operations,
                "alerts": filtered_alerts,
                "summary": {
                    "total_metrics": len(filtered_metrics),
                    "total_operations": len(filtered_operations),
                    "total_alerts": len(filtered_alerts)
                }
            }
            
            if format_type == "json":
                return json.dumps(export_data, indent=2, default=str)
            elif format_type == "csv":
                # Convert to CSV format (simplified)
                csv_lines = ["timestamp,metric_name,value,unit,labels"]
                for metric_name, metrics in filtered_metrics.items():
                    for metric in metrics:
                        labels_str = json.dumps(metric.get('labels', {}))
                        csv_lines.append(f"{metric['timestamp']},{metric_name},{metric['value']},{metric['unit']},\"{labels_str}\"")
                return '\n'.join(csv_lines)
            else:
                raise ValueError(f"Unsupported export format: {format_type}")
                
        except Exception as e:
            logger.error(f"Error exporting monitoring data: {str(e)}")
            return f"Export failed: {str(e)}"
    
    async def set_custom_threshold(self, metric_name: str, warning: float = None, critical: float = None):
        """Set custom thresholds for metrics"""
        
        if metric_name not in self.thresholds:
            self.thresholds[metric_name] = {}
        
        if warning is not None:
            self.thresholds[metric_name]['warning'] = warning
        
        if critical is not None:
            self.thresholds[metric_name]['critical'] = critical
        
        logger.info(f"Updated thresholds for {metric_name}: warning={warning}, critical={critical}")
    
    def increment_counter(self, counter_name: str, value: int = 1, labels: Dict[str, str] = None):
        """Increment a custom counter"""
        
        if labels:
            # Include labels in counter name
            label_str = "_".join(f"{k}_{v}" for k, v in sorted(labels.items()))
            full_name = f"{counter_name}_{label_str}"
        else:
            full_name = counter_name
        
        self.custom_counters[full_name] += value
    
    def set_gauge(self, gauge_name: str, value: float, labels: Dict[str, str] = None):
        """Set a custom gauge value"""
        
        if labels:
            label_str = "_".join(f"{k}_{v}" for k, v in sorted(labels.items()))
            full_name = f"{gauge_name}_{label_str}"
        else:
            full_name = gauge_name
        
        self.custom_gauges[full_name] = value
    
    def observe_histogram(self, histogram_name: str, value: float, labels: Dict[str, str] = None):
        """Add observation to histogram"""
        
        if labels:
            label_str = "_".join(f"{k}_{v}" for k, v in sorted(labels.items()))
            full_name = f"{histogram_name}_{label_str}"
        else:
            full_name = histogram_name
        
        self.custom_histograms[full_name].append(value)
        
        # Keep histogram size manageable
        if len(self.custom_histograms[full_name]) > 1000:
            self.custom_histograms[full_name] = self.custom_histograms[full_name][-1000:]
    
    async def create_performance_report(self, time_range_hours: int = 24) -> Dict[str, Any]:
        """Create comprehensive performance report"""
        
        try:
            cutoff_time = datetime.utcnow() - timedelta(hours=time_range_hours)
            
            # Filter recent data
            recent_operations = [op for op in self.sequence_operations if op.timestamp > cutoff_time]
            recent_alerts = [alert for alert in self.alerts if alert.timestamp > cutoff_time]
            
            # Calculate statistics
            total_operations = len(recent_operations)
            successful_operations = sum(1 for op in recent_operations if op.success)
            failed_operations = total_operations - successful_operations
            
            # Operation type breakdown
            operation_breakdown = defaultdict(int)
            for op in recent_operations:
                operation_breakdown[op.operation_type] += 1
            
            # Duration statistics
            durations = [op.duration for op in recent_operations]
            duration_stats = {}
            if durations:
                duration_stats = {
                    "mean": np.mean(durations),
                    "median": np.median(durations),
                    "p95": np.percentile(durations, 95),
                    "p99": np.percentile(durations, 99),
                    "min": min(durations),
                    "max": max(durations)
                }
            
            # Alert breakdown
            alert_breakdown = defaultdict(int)
            for alert in recent_alerts:
                alert_breakdown[alert.severity] += 1
            
            report = {
                "report_period": {
                    "start_time": cutoff_time.isoformat(),
                    "end_time": datetime.utcnow().isoformat(),
                    "duration_hours": time_range_hours
                },
                "operation_summary": {
                    "total_operations": total_operations,
                    "successful_operations": successful_operations,
                    "failed_operations": failed_operations,
                    "success_rate": (successful_operations / total_operations * 100) if total_operations > 0 else 0,
                    "operation_breakdown": dict(operation_breakdown)
                },
                "performance_metrics": {
                    "duration_statistics": duration_stats,
                    "average_sequences_per_operation": np.mean([op.sequence_count for op in recent_operations]) if recent_operations else 0,
                    "total_sequences_processed": sum(op.sequence_count for op in recent_operations)
                },
                "system_health": await self.get_system_health(),
                "alerts_summary": {
                    "total_alerts": len(recent_alerts),
                    "alert_breakdown": dict(alert_breakdown),
                    "unresolved_alerts": len([alert for alert in recent_alerts if not alert.resolved])
                },
                "recommendations": await self._generate_performance_recommendations(recent_operations)
            }
            
            return report
            
        except Exception as e:
            logger.error(f"Error creating performance report: {str(e)}")
            return {"error": f"Report generation failed: {str(e)}"}
    
    async def _generate_performance_recommendations(self, operations: List[SequenceOperation]) -> List[str]:
        """Generate performance improvement recommendations"""
        
        recommendations = []
        
        try:
            if not operations:
                return ["No recent operations to analyze"]
            
            # Analyze operation patterns
            durations = [op.duration for op in operations]
            sequence_counts = [op.sequence_count for op in operations]
            
            # Check for slow operations
            if durations and np.percentile(durations, 95) > 300:  # 5 minutes
                recommendations.append("Some operations are taking very long - consider optimizing algorithms or using smaller batch sizes")
            
            # Check for large sequence processing
            if sequence_counts and max(sequence_counts) > 1000:
                recommendations.append("Large sequence batches detected - consider implementing streaming or chunked processing")
            
            # Check memory usage patterns
            memory_usages = [op.memory_usage_mb for op in operations if op.memory_usage_mb]
            if memory_usages and max(memory_usages) > 4000:  # 4GB
                recommendations.append("High memory usage detected - consider implementing memory-efficient algorithms")
            
            # Check error patterns
            failed_operations = [op for op in operations if not op.success]
            if len(failed_operations) / len(operations) > 0.1:  # >10% failure rate
                recommendations.append("High failure rate detected - review error logs and input validation")
            
            # Check for specific operation types with issues
            operation_stats = defaultdict(lambda: {"count": 0, "failures": 0, "total_duration": 0})
            
            for op in operations:
                stats = operation_stats[op.operation_type]
                stats["count"] += 1
                stats["total_duration"] += op.duration
                if not op.success:
                    stats["failures"] += 1
            
            for op_type, stats in operation_stats.items():
                failure_rate = (stats["failures"] / stats["count"]) * 100
                avg_duration = stats["total_duration"] / stats["count"]
                
                if failure_rate > 20:
                    recommendations.append(f"High failure rate for {op_type} operations ({failure_rate:.1f}%) - investigate specific issues")
                
                if avg_duration > 180:  # 3 minutes
                    recommendations.append(f"{op_type} operations are slow (avg {avg_duration:.1f}s) - consider optimization")
            
            if not recommendations:
                recommendations.append("System performance is good - no immediate optimizations needed")
            
        except Exception as e:
            logger.error(f"Error generating recommendations: {str(e)}")
            recommendations.append("Error analyzing performance data for recommendations")
        
        return recommendations

# Global monitoring instance
bioinformatics_monitoring = BioinformaticsMonitoring()