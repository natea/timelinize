"""
Incremental Processing System for Timelinize LLM Enrichments

This module handles the continuous processing of new timeline items as they
are added to the database, ensuring efficient and timely enrichment.
"""

from dataclasses import dataclass
from typing import List, Dict, Any, Optional, Set
from datetime import datetime, timedelta
from enum import Enum
import asyncio
from collections import deque


# Processing Strategies
class ProcessingStrategy(Enum):
    IMMEDIATE = "immediate"      # Process as soon as detected
    BATCHED = "batched"         # Wait for batch size or timeout
    SCHEDULED = "scheduled"     # Process at scheduled intervals
    PRIORITY = "priority"       # Process based on priority rules


@dataclass
class ProcessingRule:
    """Rules for determining how to process items"""
    name: str
    condition: str  # SQL WHERE clause
    strategy: ProcessingStrategy
    priority: int  # 1-10, higher is more urgent
    enrichment_types: List[str]
    batch_size: Optional[int] = None
    max_wait_time: Optional[int] = None  # seconds


@dataclass
class QueuedItem:
    """Item queued for processing"""
    item_id: int
    data_source_id: int
    timestamp: datetime
    priority: int
    enrichment_types: List[str]
    retry_count: int = 0
    last_error: Optional[str] = None


# Change Detection System
class ChangeDetector:
    """Detects new or modified items requiring enrichment"""
    
    def __init__(self, db_connection, check_interval: int = 60):
        self.db = db_connection
        self.check_interval = check_interval
        self.last_check_timestamp = datetime.now()
        self.processed_items: Set[int] = set()
        self.watchers: List[DataSourceWatcher] = []
    
    async def start_monitoring(self):
        """Start continuous monitoring for changes"""
        while True:
            try:
                new_items = await self.detect_changes()
                if new_items:
                    await self.notify_watchers(new_items)
                
                await asyncio.sleep(self.check_interval)
                
            except Exception as e:
                print(f"Error in change detection: {e}")
                await asyncio.sleep(self.check_interval * 2)
    
    async def detect_changes(self) -> List[Dict[str, Any]]:
        """Detect new or modified items since last check"""
        query = """
        SELECT 
            i.id,
            i.data_source_id,
            i.timestamp,
            i.modified,
            i.data_type,
            COALESCE(es.last_enriched, 0) as last_enriched,
            COALESCE(es.enrichment_version, 0) as enrichment_version
        FROM items i
        LEFT JOIN enrichment_status es ON i.id = es.item_id
        WHERE 
            (i.stored > ? OR i.modified > ?)  -- New or modified items
            AND (
                es.last_enriched IS NULL  -- Never enriched
                OR i.modified > es.last_enriched  -- Modified after enrichment
                OR es.error_count > 0 AND es.error_count < 3  -- Retry failed items
            )
            AND i.deleted IS NULL
        ORDER BY i.timestamp DESC
        LIMIT 1000
        """
        
        cutoff_time = int(self.last_check_timestamp.timestamp())
        result = await self.db.execute(query, [cutoff_time, cutoff_time])
        
        new_items = []
        for row in result:
            if row['id'] not in self.processed_items:
                new_items.append({
                    'id': row['id'],
                    'data_source_id': row['data_source_id'],
                    'timestamp': row['timestamp'],
                    'is_modified': row['modified'] is not None,
                    'needs_retry': row['enrichment_version'] > 0
                })
                self.processed_items.add(row['id'])
        
        self.last_check_timestamp = datetime.now()
        return new_items
    
    async def notify_watchers(self, items: List[Dict[str, Any]]):
        """Notify registered watchers of new items"""
        for watcher in self.watchers:
            await watcher.handle_new_items(items)
    
    def register_watcher(self, watcher: 'DataSourceWatcher'):
        """Register a watcher for specific data sources"""
        self.watchers.append(watcher)


# Data Source Specific Watchers
class DataSourceWatcher:
    """Base class for data source specific processing logic"""
    
    def __init__(self, data_source_id: int, processing_rules: List[ProcessingRule]):
        self.data_source_id = data_source_id
        self.processing_rules = processing_rules
    
    async def handle_new_items(self, items: List[Dict[str, Any]]):
        """Handle new items from this data source"""
        relevant_items = [
            item for item in items 
            if item['data_source_id'] == self.data_source_id
        ]
        
        for item in relevant_items:
            rule = self.match_processing_rule(item)
            if rule:
                await self.queue_for_processing(item, rule)
    
    def match_processing_rule(self, item: Dict[str, Any]) -> Optional[ProcessingRule]:
        """Match item to appropriate processing rule"""
        # In production, would evaluate SQL conditions
        # For now, return first matching rule
        return self.processing_rules[0] if self.processing_rules else None
    
    async def queue_for_processing(self, item: Dict[str, Any], rule: ProcessingRule):
        """Queue item for processing based on rule"""
        # Implementation would add to appropriate queue
        pass


# Processing Queue Manager
class ProcessingQueueManager:
    """Manages different processing queues based on strategy"""
    
    def __init__(self, pipeline_manager):
        self.pipeline = pipeline_manager
        self.immediate_queue: asyncio.Queue = asyncio.Queue()
        self.batch_queue: Dict[str, List[QueuedItem]] = {}
        self.priority_queue: List[QueuedItem] = []  # Heap queue
        self.scheduled_items: Dict[datetime, List[QueuedItem]] = {}
        
        self.batch_timers: Dict[str, asyncio.Task] = {}
        self.processing_tasks: List[asyncio.Task] = []
    
    async def start_processors(self):
        """Start all queue processors"""
        tasks = [
            asyncio.create_task(self.process_immediate_queue()),
            asyncio.create_task(self.process_priority_queue()),
            asyncio.create_task(self.process_scheduled_items()),
        ]
        self.processing_tasks.extend(tasks)
    
    async def add_item(self, item: QueuedItem, strategy: ProcessingStrategy, 
                      batch_key: Optional[str] = None):
        """Add item to appropriate queue"""
        if strategy == ProcessingStrategy.IMMEDIATE:
            await self.immediate_queue.put(item)
            
        elif strategy == ProcessingStrategy.BATCHED and batch_key:
            if batch_key not in self.batch_queue:
                self.batch_queue[batch_key] = []
                # Start batch timer
                self.batch_timers[batch_key] = asyncio.create_task(
                    self.batch_timeout(batch_key, 300)  # 5 minute timeout
                )
            self.batch_queue[batch_key].append(item)
            
            # Check if batch is full
            if len(self.batch_queue[batch_key]) >= 100:
                await self.process_batch(batch_key)
                
        elif strategy == ProcessingStrategy.PRIORITY:
            # Insert maintaining priority order
            self.priority_queue.append(item)
            self.priority_queue.sort(key=lambda x: (-x.priority, x.timestamp))
            
        elif strategy == ProcessingStrategy.SCHEDULED:
            # Schedule for next appropriate time
            schedule_time = self.calculate_schedule_time(item)
            if schedule_time not in self.scheduled_items:
                self.scheduled_items[schedule_time] = []
            self.scheduled_items[schedule_time].append(item)
    
    async def process_immediate_queue(self):
        """Process items requiring immediate enrichment"""
        while True:
            try:
                item = await self.immediate_queue.get()
                await self.process_single_item(item)
            except Exception as e:
                print(f"Error processing immediate item: {e}")
    
    async def process_priority_queue(self):
        """Process priority queue items"""
        while True:
            try:
                if self.priority_queue:
                    # Process highest priority item
                    item = self.priority_queue.pop(0)
                    await self.process_single_item(item)
                else:
                    await asyncio.sleep(1)
            except Exception as e:
                print(f"Error processing priority item: {e}")
    
    async def process_scheduled_items(self):
        """Process items at scheduled times"""
        while True:
            try:
                now = datetime.now()
                due_times = [t for t in self.scheduled_items.keys() if t <= now]
                
                for schedule_time in due_times:
                    items = self.scheduled_items.pop(schedule_time)
                    for item in items:
                        await self.process_single_item(item)
                
                await asyncio.sleep(60)  # Check every minute
                
            except Exception as e:
                print(f"Error processing scheduled items: {e}")
    
    async def batch_timeout(self, batch_key: str, timeout_seconds: int):
        """Process batch after timeout"""
        await asyncio.sleep(timeout_seconds)
        await self.process_batch(batch_key)
    
    async def process_batch(self, batch_key: str):
        """Process a batch of items"""
        if batch_key in self.batch_queue:
            items = self.batch_queue.pop(batch_key)
            if batch_key in self.batch_timers:
                self.batch_timers[batch_key].cancel()
                del self.batch_timers[batch_key]
            
            # Process items as batch
            item_ids = [item.item_id for item in items]
            await self.pipeline.process_items(item_ids, items[0].enrichment_types)
    
    async def process_single_item(self, item: QueuedItem):
        """Process a single queued item"""
        try:
            await self.pipeline.process_items([item.item_id], item.enrichment_types)
            await self.mark_processed(item.item_id)
        except Exception as e:
            await self.handle_processing_error(item, str(e))
    
    async def mark_processed(self, item_id: int):
        """Mark item as successfully processed"""
        # Update enrichment_status table
        pass
    
    async def handle_processing_error(self, item: QueuedItem, error: str):
        """Handle processing errors with retry logic"""
        item.retry_count += 1
        item.last_error = error
        
        if item.retry_count < 3:
            # Exponential backoff
            delay = 60 * (2 ** item.retry_count)
            retry_time = datetime.now() + timedelta(seconds=delay)
            
            if retry_time not in self.scheduled_items:
                self.scheduled_items[retry_time] = []
            self.scheduled_items[retry_time].append(item)
        else:
            # Max retries reached, mark as failed
            await self.mark_failed(item.item_id, error)
    
    async def mark_failed(self, item_id: int, error: str):
        """Mark item as failed after max retries"""
        # Update enrichment_status with error
        pass
    
    def calculate_schedule_time(self, item: QueuedItem) -> datetime:
        """Calculate when to process a scheduled item"""
        # Simple scheduling - process low priority items during off-peak hours
        now = datetime.now()
        if item.priority < 5:
            # Schedule for next 3 AM
            next_3am = now.replace(hour=3, minute=0, second=0, microsecond=0)
            if next_3am <= now:
                next_3am += timedelta(days=1)
            return next_3am
        else:
            # Process within next hour
            return now + timedelta(hours=1)


# Incremental Processing Orchestrator
class IncrementalProcessor:
    """Main orchestrator for incremental processing"""
    
    def __init__(self, db_connection, pipeline_manager):
        self.db = db_connection
        self.pipeline = pipeline_manager
        self.change_detector = ChangeDetector(db_connection)
        self.queue_manager = ProcessingQueueManager(pipeline_manager)
        self.processing_rules = []
        self.statistics = ProcessingStatistics()
    
    async def initialize(self):
        """Initialize processing rules and watchers"""
        # Load processing rules from configuration
        self.processing_rules = await self.load_processing_rules()
        
        # Set up data source watchers
        data_sources = await self.get_data_sources()
        for ds in data_sources:
            rules = [r for r in self.processing_rules if r.condition.find(f"data_source_id = {ds['id']}") >= 0]
            watcher = DataSourceWatcher(ds['id'], rules)
            self.change_detector.register_watcher(watcher)
    
    async def start(self):
        """Start incremental processing system"""
        await self.initialize()
        
        # Start all components
        tasks = [
            asyncio.create_task(self.change_detector.start_monitoring()),
            asyncio.create_task(self.queue_manager.start_processors()),
            asyncio.create_task(self.statistics.collect_metrics()),
        ]
        
        await asyncio.gather(*tasks)
    
    async def load_processing_rules(self) -> List[ProcessingRule]:
        """Load processing rules from database or config"""
        # Example rules
        return [
            ProcessingRule(
                name="immediate_messages",
                condition="data_type LIKE '%message%'",
                strategy=ProcessingStrategy.IMMEDIATE,
                priority=8,
                enrichment_types=["summary", "sentiment", "entity_extraction"]
            ),
            ProcessingRule(
                name="batch_photos",
                condition="data_type LIKE 'image/%'",
                strategy=ProcessingStrategy.BATCHED,
                priority=5,
                enrichment_types=["theme_classification"],
                batch_size=50,
                max_wait_time=600
            ),
            ProcessingRule(
                name="scheduled_location",
                condition="longitude IS NOT NULL",
                strategy=ProcessingStrategy.SCHEDULED,
                priority=3,
                enrichment_types=["context", "theme_classification"]
            ),
        ]
    
    async def get_data_sources(self) -> List[Dict[str, Any]]:
        """Get all active data sources"""
        result = await self.db.execute("SELECT id, name FROM data_sources WHERE active = 1")
        return [{"id": row[0], "name": row[1]} for row in result]


# Statistics and Monitoring
class ProcessingStatistics:
    """Tracks processing statistics and performance"""
    
    def __init__(self):
        self.stats = {
            "items_processed": 0,
            "items_queued": 0,
            "processing_time_avg": 0,
            "error_rate": 0,
            "queue_depths": {},
        }
        self.recent_errors = deque(maxlen=100)
    
    async def collect_metrics(self):
        """Continuously collect processing metrics"""
        while True:
            # Collect queue depths, processing rates, etc.
            await asyncio.sleep(60)
    
    def record_processing(self, item_id: int, duration_ms: int, success: bool):
        """Record item processing result"""
        self.stats["items_processed"] += 1
        
        # Update running average
        avg = self.stats["processing_time_avg"]
        self.stats["processing_time_avg"] = (avg * 0.95) + (duration_ms * 0.05)
        
        if not success:
            self.stats["error_rate"] = (self.stats["error_rate"] * 0.99) + 0.01
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get system health status"""
        return {
            "status": "healthy" if self.stats["error_rate"] < 0.1 else "degraded",
            "metrics": self.stats,
            "recent_errors": list(self.recent_errors)
        }