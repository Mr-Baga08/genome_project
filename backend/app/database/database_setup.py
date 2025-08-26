# backend/app/database/database_setup.py

import uuid
from datetime import datetime
from typing import Dict, List, Any, Optional
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
import logging

logger = logging.getLogger(__name__)

class DatabaseManager:
    """Enhanced database manager with indexing and optimization"""
    
    def __init__(self, mongodb_url: str, database_name: str):
        self.client = motor.motor_asyncio.AsyncIOMotorClient(mongodb_url)
        self.database = self.client[database_name]
    
    async def initialize_database(self):
        """Initialize database with indexes and collections"""
        await self._create_indexes()
        await self._create_collections()
    
    async def _create_collections(self):
        """Create necessary collections"""
        collections = [
            'sequences',
            'annotations', 
            'tasks',
            'users',
            'workflows',
            'analysis_results',
            'workflow_executions'
        ]
        
        existing_collections = await self.database.list_collection_names()
        
        for collection in collections:
            if collection not in existing_collections:
                await self.database.create_collection(collection)
    
    async def _create_indexes(self):
        """Create database indexes for performance"""
        
        # Sequences collection indexes
        await self.database.sequences.create_index([("user_id", 1), ("sequence_type", 1)])
        await self.database.sequences.create_index([("organism_id", 1)])
        await self.database.sequences.create_index([("length", 1)])
        await self.database.sequences.create_index([("gc_content", 1)])
        await self.database.sequences.create_index([("checksum", 1)])
        await self.database.sequences.create_index([("created_at", -1)])
        await self.database.sequences.create_index([("is_public", 1)])
        
        # Annotations collection indexes
        await self.database.annotations.create_index([("sequence_id", 1)])
        await self.database.annotations.create_index([("feature_type", 1)])
        await self.database.annotations.create_index([("start_position", 1), ("end_position", 1)])
        await self.database.annotations.create_index([("sequence_id", 1), ("start_position", 1)])
        
        # Tasks collection indexes
        await self.database.tasks.create_index([("user_id", 1), ("status", 1)])
        await self.database.tasks.create_index([("status", 1)])
        await self.database.tasks.create_index([("priority", -1), ("created_at", 1)])
        await self.database.tasks.create_index([("created_at", -1)])
        await self.database.tasks.create_index([("task_id", 1)], unique=True)
        
        # Users collection indexes
        await self.database.users.create_index([("username", 1)], unique=True)
        await self.database.users.create_index([("email", 1)], unique=True)
        await self.database.users.create_index([("is_active", 1)])
        
        # Workflows collection indexes
        await self.database.workflows.create_index([("author", 1)])
        await self.database.workflows.create_index([("tags", 1)])
        await self.database.workflows.create_index([("is_public", 1)])
        await self.database.workflows.create_index([("created_at", -1)])
        
        # Analysis results collection indexes
        await self.database.analysis_results.create_index([("task_id", 1)])
        await self.database.analysis_results.create_index([("analysis_type", 1)])
        await self.database.analysis_results.create_index([("created_at", -1)])
    
    async def get_collection(self, collection_name: str):
        """Get database collection"""
        return self.database[collection_name]
    
    async def close_connection(self):
        """Close database connection"""
        self.client.close()

    async def store_analysis_result(self, analysis_type: str, results: Dict, metadata: Dict) -> str:
        """Store results in a dedicated collection based on analysis_type"""
        try:
            result_id = str(uuid.uuid4())
            
            # Create result document
            result_document = {
                "_id": result_id,
                "analysis_id": result_id,
                "analysis_type": analysis_type,
                "results": results,
                "metadata": metadata,
                "created_at": datetime.utcnow(),
                "status": "completed",
                "size_estimate": len(str(results)),  # Rough size estimate
                "user_id": metadata.get("user_id"),
                "workflow_id": metadata.get("workflow_id"),
                "tags": metadata.get("tags", [])
            }
            
            # Store in analysis_results collection
            collection = await self.get_collection("analysis_results")
            await collection.insert_one(result_document)
            
            logger.info(f"Analysis result stored: {analysis_type} - {result_id}")
            return result_id
            
        except Exception as e:
            logger.error(f"Error storing analysis result: {str(e)}")
            raise e

    async def get_analysis_result(self, analysis_id: str) -> Dict:
        """Retrieve a specific analysis result by its ID"""
        try:
            collection = await self.get_collection("analysis_results")
            result = await collection.find_one({"analysis_id": analysis_id})
            
            if not result:
                return {"error": f"Analysis result {analysis_id} not found"}
            
            # Convert ObjectId to string for JSON serialization
            result["_id"] = str(result["_id"])
            
            return result
            
        except Exception as e:
            logger.error(f"Error retrieving analysis result {analysis_id}: {str(e)}")
            return {"error": str(e)}

    async def list_analysis_results(
        self, 
        analysis_type: Optional[str] = None,
        user_id: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict]:
        """List analysis results with filtering"""
        try:
            collection = await self.get_collection("analysis_results")
            
            # Build filter query
            filter_query = {}
            if analysis_type:
                filter_query["analysis_type"] = analysis_type
            if user_id:
                filter_query["user_id"] = user_id
            
            # Execute query with pagination
            cursor = collection.find(filter_query).skip(offset).limit(limit).sort("created_at", -1)
            results = []
            
            async for doc in cursor:
                doc["_id"] = str(doc["_id"])
                results.append(doc)
            
            return results
            
        except Exception as e:
            logger.error(f"Error listing analysis results: {str(e)}")
            return []

    async def delete_analysis_result(self, analysis_id: str, user_id: Optional[str] = None) -> bool:
        """Delete an analysis result"""
        try:
            collection = await self.get_collection("analysis_results")
            
            # Build delete query
            delete_query = {"analysis_id": analysis_id}
            if user_id:
                delete_query["user_id"] = user_id  # Ensure user can only delete their own results
            
            result = await collection.delete_one(delete_query)
            
            if result.deleted_count > 0:
                logger.info(f"Analysis result deleted: {analysis_id}")
                return True
            else:
                logger.warning(f"Analysis result not found or access denied: {analysis_id}")
                return False
                
        except Exception as e:
            logger.error(f"Error deleting analysis result {analysis_id}: {str(e)}")
            return False

    # ============================================================================
    # CUSTOM MOTIFS MANAGEMENT
    # ============================================================================
    
    async def store_custom_motif(self, motif_data: Dict) -> str:
        """Store custom motif definition"""
        try:
            motif_id = str(uuid.uuid4())
            
            motif_document = {
                "_id": motif_id,
                "motif_id": motif_id,
                "name": motif_data.get("name"),
                "consensus_sequence": motif_data.get("consensus_sequence"),
                "pwm_matrix": motif_data.get("pwm_matrix"),
                "description": motif_data.get("description"),
                "organism": motif_data.get("organism"),
                "source": motif_data.get("source", "user_defined"),
                "created_by": motif_data.get("user_id"),
                "created_at": datetime.utcnow(),
                "is_public": motif_data.get("is_public", False),
                "usage_count": 0,
                "tags": motif_data.get("tags", []),
                "validation_status": "pending"
            }
            
            collection = await self.get_collection("custom_motifs")
            await collection.insert_one(motif_document)
            
            logger.info(f"Custom motif stored: {motif_data.get('name')} - {motif_id}")
            return motif_id
            
        except Exception as e:
            logger.error(f"Error storing custom motif: {str(e)}")
            raise e

    async def get_custom_motifs(self, user_id: str, include_public: bool = True) -> List[Dict]:
        """Get custom motifs for a user"""
        try:
            collection = await self.get_collection("custom_motifs")
            
            # Build query for user's motifs and optionally public ones
            if include_public:
                query = {
                    "$or": [
                        {"created_by": user_id},
                        {"is_public": True}
                    ]
                }
            else:
                query = {"created_by": user_id}
            
            cursor = collection.find(query).sort("created_at", -1)
            motifs = []
            
            async for doc in cursor:
                doc["_id"] = str(doc["_id"])
                motifs.append(doc)
            
            return motifs
            
        except Exception as e:
            logger.error(f"Error retrieving custom motifs for user {user_id}: {str(e)}")
            return []

    async def update_motif_usage(self, motif_id: str) -> bool:
        """Increment usage count for a motif"""
        try:
            collection = await self.get_collection("custom_motifs")
            result = await collection.update_one(
                {"motif_id": motif_id},
                {"$inc": {"usage_count": 1}, "$set": {"last_used": datetime.utcnow()}}
            )
            
            return result.modified_count > 0
            
        except Exception as e:
            logger.error(f"Error updating motif usage {motif_id}: {str(e)}")
            return False

    async def delete_custom_motif(self, motif_id: str, user_id: str) -> bool:
        """Delete a custom motif"""
        try:
            collection = await self.get_collection("custom_motifs")
            
            # Only allow deletion of user's own motifs
            result = await collection.delete_one({
                "motif_id": motif_id,
                "created_by": user_id
            })
            
            if result.deleted_count > 0:
                logger.info(f"Custom motif deleted: {motif_id}")
                return True
            else:
                logger.warning(f"Custom motif not found or access denied: {motif_id}")
                return False
                
        except Exception as e:
            logger.error(f"Error deleting custom motif {motif_id}: {str(e)}")
            return False

    # ============================================================================
    # CUSTOM ELEMENTS MANAGEMENT
    # ============================================================================
    
    async def store_custom_element(self, element_id: str, element_data: Dict) -> bool:
        """Store custom workflow element definition"""
        try:
            element_document = {
                "_id": element_id,
                "element_id": element_id,
                "name": element_data.get("name"),
                "display_name": element_data.get("display_name"),
                "description": element_data.get("description"),
                "element_type": element_data.get("type"),
                "category": element_data.get("category"),
                "input_ports": element_data.get("input_ports", []),
                "output_ports": element_data.get("output_ports", []),
                "parameters": element_data.get("parameters", {}),
                "script_content": element_data.get("script_content"),
                "script_type": element_data.get("script_type", "python"),
                "created_by": element_data.get("user_id"),
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
                "is_active": True,
                "is_public": element_data.get("is_public", False),
                "usage_count": 0,
                "validation_status": "pending",
                "tags": element_data.get("tags", [])
            }
            
            collection = await self.get_collection("custom_elements")
            await collection.insert_one(element_document)
            
            logger.info(f"Custom element stored: {element_data.get('name')} - {element_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error storing custom element: {str(e)}")
            return False

    async def get_custom_elements(self, user_id: str, include_public: bool = True) -> List[Dict]:
        """Get custom elements for a user"""
        try:
            collection = await self.get_collection("custom_elements")
            
            if include_public:
                query = {
                    "$or": [
                        {"created_by": user_id},
                        {"is_public": True}
                    ],
                    "is_active": True
                }
            else:
                query = {"created_by": user_id, "is_active": True}
            
            cursor = collection.find(query).sort("created_at", -1)
            elements = []
            
            async for doc in cursor:
                doc["_id"] = str(doc["_id"])
                elements.append(doc)
            
            return elements
            
        except Exception as e:
            logger.error(f"Error retrieving custom elements for user {user_id}: {str(e)}")
            return []

    async def update_custom_element(self, element_id: str, element_data: Dict, user_id: str) -> bool:
        """Update a custom element"""
        try:
            collection = await self.get_collection("custom_elements")
            
            update_data = {
                **element_data,
                "updated_at": datetime.utcnow(),
                "validation_status": "pending"  # Reset validation status
            }
            
            result = await collection.update_one(
                {"element_id": element_id, "created_by": user_id},
                {"$set": update_data}
            )
            
            if result.modified_count > 0:
                logger.info(f"Custom element updated: {element_id}")
                return True
            else:
                logger.warning(f"Custom element not found or access denied: {element_id}")
                return False
                
        except Exception as e:
            logger.error(f"Error updating custom element {element_id}: {str(e)}")
            return False

    async def delete_custom_element(self, element_id: str, user_id: str = None) -> bool:
        """Delete a custom element (soft delete)"""
        try:
            collection = await self.get_collection("custom_elements")
            
            # Build delete query
            query = {"element_id": element_id}
            if user_id:
                query["created_by"] = user_id  # Only allow deletion of user's own elements
            
            # Soft delete by setting is_active to False
            result = await collection.update_one(
                query,
                {"$set": {"is_active": False, "deleted_at": datetime.utcnow()}}
            )
            
            if result.modified_count > 0:
                logger.info(f"Custom element deleted: {element_id}")
                return True
            else:
                logger.warning(f"Custom element not found or access denied: {element_id}")
                return False
                
        except Exception as e:
            logger.error(f"Error deleting custom element {element_id}: {str(e)}")
            return False

    # ============================================================================
    # BATCH OPERATIONS
    # ============================================================================
    
    async def store_batch_analysis_result(self, batch_id: str, results: List[Dict]) -> bool:
        """Store batch analysis results"""
        try:
            batch_document = {
                "_id": batch_id,
                "batch_id": batch_id,
                "total_analyses": len(results),
                "successful_analyses": len([r for r in results if r.get("status") == "success"]),
                "failed_analyses": len([r for r in results if r.get("status") != "success"]),
                "results": results,
                "created_at": datetime.utcnow(),
                "batch_type": "analysis_batch",
                "processing_time_seconds": sum(r.get("processing_time", 0) for r in results),
                "metadata": {
                    "total_size_bytes": sum(r.get("size_bytes", 0) for r in results),
                    "analysis_types": list(set(r.get("analysis_type") for r in results if r.get("analysis_type")))
                }
            }
            
            collection = await self.get_collection("batch_results")
            await collection.insert_one(batch_document)
            
            logger.info(f"Batch analysis result stored: {batch_id} with {len(results)} analyses")
            return True
            
        except Exception as e:
            logger.error(f"Error storing batch analysis result: {str(e)}")
            return False

    async def get_batch_analysis_result(self, batch_id: str) -> Dict:
        """Get batch analysis results"""
        try:
            collection = await self.get_collection("batch_results")
            result = await collection.find_one({"batch_id": batch_id})
            
            if result:
                result["_id"] = str(result["_id"])
                return result
            else:
                return {"error": f"Batch result {batch_id} not found"}
                
        except Exception as e:
            logger.error(f"Error retrieving batch result {batch_id}: {str(e)}")
            return {"error": str(e)}

    # ============================================================================
    # WORKFLOW MANAGEMENT
    # ============================================================================
    
    async def store_workflow_template(self, template_data: Dict) -> str:
        """Store a reusable workflow template"""
        try:
            template_id = str(uuid.uuid4())
            
            template_document = {
                "_id": template_id,
                "template_id": template_id,
                "name": template_data.get("name"),
                "description": template_data.get("description"),
                "category": template_data.get("category"),
                "workflow_definition": template_data.get("workflow_definition"),
                "created_by": template_data.get("user_id"),
                "created_at": datetime.utcnow(),
                "is_public": template_data.get("is_public", False),
                "usage_count": 0,
                "tags": template_data.get("tags", []),
                "parameters_schema": template_data.get("parameters_schema", {}),
                "estimated_runtime": template_data.get("estimated_runtime"),
                "required_resources": template_data.get("required_resources", {})
            }
            
            collection = await self.get_collection("workflow_templates")
            await collection.insert_one(template_document)
            
            logger.info(f"Workflow template stored: {template_data.get('name')} - {template_id}")
            return template_id
            
        except Exception as e:
            logger.error(f"Error storing workflow template: {str(e)}")
            raise e

    async def get_workflow_templates(self, user_id: str, category: Optional[str] = None) -> List[Dict]:
        """Get workflow templates"""
        try:
            collection = await self.get_collection("workflow_templates")
            
            # Build query
            query = {
                "$or": [
                    {"created_by": user_id},
                    {"is_public": True}
                ]
            }
            
            if category:
                query["category"] = category
            
            cursor = collection.find(query).sort("usage_count", -1)
            templates = []
            
            async for doc in cursor:
                doc["_id"] = str(doc["_id"])
                templates.append(doc)
            
            return templates
            
        except Exception as e:
            logger.error(f"Error retrieving workflow templates: {str(e)}")
            return []

    # ============================================================================
    # USER DATA MANAGEMENT
    # ============================================================================
    
    async def store_user_preferences(self, user_id: str, preferences: Dict) -> bool:
        """Store user preferences"""
        try:
            collection = await self.get_collection("user_preferences")
            
            preference_document = {
                "user_id": user_id,
                "preferences": preferences,
                "updated_at": datetime.utcnow()
            }
            
            # Upsert operation
            await collection.update_one(
                {"user_id": user_id},
                {"$set": preference_document},
                upsert=True
            )
            
            logger.info(f"User preferences updated: {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error storing user preferences: {str(e)}")
            return False

    async def get_user_preferences(self, user_id: str) -> Dict:
        """Get user preferences"""
        try:
            collection = await self.get_collection("user_preferences")
            result = await collection.find_one({"user_id": user_id})
            
            if result:
                return result.get("preferences", {})
            else:
                # Return default preferences
                return self._get_default_preferences()
                
        except Exception as e:
            logger.error(f"Error retrieving user preferences: {str(e)}")
            return self._get_default_preferences()

    # ============================================================================
    # AUDIT LOGGING
    # ============================================================================
    
    async def log_audit_event(self, event_data: Dict) -> bool:
        """Log audit event"""
        try:
            audit_document = {
                "_id": str(uuid.uuid4()),
                "timestamp": datetime.utcnow(),
                "event_type": event_data.get("event_type"),
                "user_id": event_data.get("user_id"),
                "action": event_data.get("action"),
                "resource_type": event_data.get("resource_type"),
                "resource_id": event_data.get("resource_id"),
                "details": event_data.get("details", {}),
                "ip_address": event_data.get("ip_address"),
                "user_agent": event_data.get("user_agent"),
                "session_id": event_data.get("session_id"),
                "status": event_data.get("status", "success")
            }
            
            collection = await self.get_collection("audit_logs")
            await collection.insert_one(audit_document)
            
            return True
            
        except Exception as e:
            logger.error(f"Error logging audit event: {str(e)}")
            return False

    async def get_audit_logs(
        self,
        user_id: Optional[str] = None,
        event_type: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100
    ) -> List[Dict]:
        """Get audit logs with filtering"""
        try:
            collection = await self.get_collection("audit_logs")
            
            # Build filter query
            query = {}
            if user_id:
                query["user_id"] = user_id
            if event_type:
                query["event_type"] = event_type
            if start_date or end_date:
                date_filter = {}
                if start_date:
                    date_filter["$gte"] = start_date
                if end_date:
                    date_filter["$lte"] = end_date
                query["timestamp"] = date_filter
            
            cursor = collection.find(query).sort("timestamp", -1).limit(limit)
            logs = []
            
            async for doc in cursor:
                doc["_id"] = str(doc["_id"])
                logs.append(doc)
            
            return logs
            
        except Exception as e:
            logger.error(f"Error retrieving audit logs: {str(e)}")
            return []

    # ============================================================================
    # SYSTEM DATA MANAGEMENT
    # ============================================================================
    
    async def store_system_metric(self, metric_data: Dict) -> bool:
        """Store system performance metrics"""
        try:
            metric_document = {
                "_id": str(uuid.uuid4()),
                "timestamp": datetime.utcnow(),
                "metric_type": metric_data.get("metric_type"),
                "values": metric_data.get("values"),
                "host": metric_data.get("host", "localhost"),
                "service": metric_data.get("service"),
                "tags": metric_data.get("tags", [])
            }
            
            collection = await self.get_collection("system_metrics")
            await collection.insert_one(metric_document)
            
            # Clean up old metrics (keep only last 30 days)
            cutoff_date = datetime.utcnow() - timedelta(days=30)
            await collection.delete_many({"timestamp": {"$lt": cutoff_date}})
            
            return True
            
        except Exception as e:
            logger.error(f"Error storing system metric: {str(e)}")
            return False

    async def get_system_metrics(
        self,
        metric_type: Optional[str] = None,
        hours: int = 24
    ) -> List[Dict]:
        """Get system metrics for specified time range"""
        try:
            collection = await self.get_collection("system_metrics")
            
            # Build query
            start_time = datetime.utcnow() - timedelta(hours=hours)
            query = {"timestamp": {"$gte": start_time}}
            
            if metric_type:
                query["metric_type"] = metric_type
            
            cursor = collection.find(query).sort("timestamp", -1)
            metrics = []
            
            async for doc in cursor:
                doc["_id"] = str(doc["_id"])
                metrics.append(doc)
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error retrieving system metrics: {str(e)}")
            return []

    # ============================================================================
    # FILE METADATA MANAGEMENT
    # ============================================================================
    
    async def store_file_metadata(self, file_data: Dict) -> str:
        """Store metadata for uploaded files"""
        try:
            file_id = str(uuid.uuid4())
            
            file_document = {
                "_id": file_id,
                "file_id": file_id,
                "original_filename": file_data.get("filename"),
                "stored_path": file_data.get("stored_path"),
                "file_size": file_data.get("size"),
                "file_type": file_data.get("file_type"),
                "format": file_data.get("format"),
                "uploaded_by": file_data.get("user_id"),
                "uploaded_at": datetime.utcnow(),
                "checksum": file_data.get("checksum"),
                "metadata": file_data.get("metadata", {}),
                "access_count": 0,
                "last_accessed": None,
                "tags": file_data.get("tags", []),
                "is_temporary": file_data.get("is_temporary", False),
                "expires_at": file_data.get("expires_at")
            }
            
            collection = await self.get_collection("file_metadata")
            await collection.insert_one(file_document)
            
            logger.info(f"File metadata stored: {file_data.get('filename')} - {file_id}")
            return file_id
            
        except Exception as e:
            logger.error(f"Error storing file metadata: {str(e)}")
            raise e

    async def get_user_files(self, user_id: str, file_type: Optional[str] = None) -> List[Dict]:
        """Get files uploaded by a user"""
        try:
            collection = await self.get_collection("file_metadata")
            
            query = {"uploaded_by": user_id}
            if file_type:
                query["file_type"] = file_type
            
            cursor = collection.find(query).sort("uploaded_at", -1)
            files = []
            
            async for doc in cursor:
                doc["_id"] = str(doc["_id"])
                files.append(doc)
            
            return files
            
        except Exception as e:
            logger.error(f"Error retrieving user files: {str(e)}")
            return []

    # ============================================================================
    # COLLECTION INITIALIZATION AND INDEXES
    # ============================================================================
    
    async def create_indexes(self) -> bool:
        """Create indexes for all collections"""
        try:
            # Analysis results indexes
            analysis_collection = await self.get_collection("analysis_results")
            await analysis_collection.create_index([
                ("analysis_type", 1),
                ("created_at", -1)
            ])
            await analysis_collection.create_index([("user_id", 1), ("created_at", -1)])
            await analysis_collection.create_index([("workflow_id", 1)])
            
            # Custom motifs indexes
            motifs_collection = await self.get_collection("custom_motifs")
            await motifs_collection.create_index([("created_by", 1)])
            await motifs_collection.create_index([("is_public", 1), ("usage_count", -1)])
            await motifs_collection.create_index([("tags", 1)])
            
            # Custom elements indexes
            elements_collection = await self.get_collection("custom_elements")
            await elements_collection.create_index([("created_by", 1), ("is_active", 1)])
            await elements_collection.create_index([("is_public", 1), ("category", 1)])
            await elements_collection.create_index([("element_type", 1)])
            
            # Batch results indexes
            batch_collection = await self.get_collection("batch_results")
            await batch_collection.create_index([("created_at", -1)])
            await batch_collection.create_index([("batch_type", 1)])
            
            # Audit logs indexes
            audit_collection = await self.get_collection("audit_logs")
            await audit_collection.create_index([("user_id", 1), ("timestamp", -1)])
            await audit_collection.create_index([("event_type", 1), ("timestamp", -1)])
            await audit_collection.create_index([("timestamp", -1)])
            
            # System metrics indexes
            metrics_collection = await self.get_collection("system_metrics")
            await metrics_collection.create_index([("metric_type", 1), ("timestamp", -1)])
            await metrics_collection.create_index([("timestamp", -1)])
            
            # File metadata indexes
            files_collection = await self.get_collection("file_metadata")
            await files_collection.create_index([("uploaded_by", 1), ("uploaded_at", -1)])
            await files_collection.create_index([("file_type", 1)])
            await files_collection.create_index([("is_temporary", 1), ("expires_at", 1)])
            
            # Workflow templates indexes
            templates_collection = await self.get_collection("workflow_templates")
            await templates_collection.create_index([("created_by", 1)])
            await templates_collection.create_index([("is_public", 1), ("usage_count", -1)])
            await templates_collection.create_index([("category", 1)])
            
            # User preferences indexes
            prefs_collection = await self.get_collection("user_preferences")
            await prefs_collection.create_index([("user_id", 1)], unique=True)
            
            logger.info("✅ All database indexes created successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error creating indexes: {str(e)}")
            return False

    async def initialize_collections(self) -> bool:
        """Initialize all required collections with validation"""
        try:
            required_collections = [
                "sequences", "annotations", "analysis_tasks", "analysis_results",
                "pipelines", "pipeline_executions", "users", "organisms",
                "custom_motifs", "custom_elements", "batch_results", 
                "audit_logs", "system_metrics", "file_metadata",
                "workflow_templates", "user_preferences"
            ]
            
            for collection_name in required_collections:
                # Create collection if it doesn't exist
                await self.get_collection(collection_name)
                logger.info(f"✅ Collection '{collection_name}' ready")
            
            # Create indexes
            await self.create_indexes()
            
            # Insert default data if collections are empty
            await self._insert_default_data()
            
            logger.info("✅ All collections initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error initializing collections: {str(e)}")
            return False

    # ============================================================================
    # DATA CLEANUP AND MAINTENANCE
    # ============================================================================
    
    async def cleanup_expired_data(self) -> Dict[str, int]:
        """Clean up expired temporary data"""
        try:
            cleanup_stats = {
                "expired_files": 0,
                "old_metrics": 0,
                "completed_tasks": 0
            }
            
            current_time = datetime.utcnow()
            
            # Clean up expired temporary files
            files_collection = await self.get_collection("file_metadata")
            expired_files = await files_collection.delete_many({
                "is_temporary": True,
                "expires_at": {"$lt": current_time}
            })
            cleanup_stats["expired_files"] = expired_files.deleted_count
            
            # Clean up old system metrics (older than 30 days)
            metrics_collection = await self.get_collection("system_metrics")
            old_date = current_time - timedelta(days=30)
            old_metrics = await metrics_collection.delete_many({
                "timestamp": {"$lt": old_date}
            })
            cleanup_stats["old_metrics"] = old_metrics.deleted_count
            
            # Clean up old completed tasks (older than 7 days)
            tasks_collection = await self.get_collection("analysis_tasks")
            old_tasks = await tasks_collection.delete_many({
                "status": "completed",
                "completed_at": {"$lt": current_time - timedelta(days=7)}
            })
            cleanup_stats["completed_tasks"] = old_tasks.deleted_count
            
            logger.info(f"Database cleanup completed: {cleanup_stats}")
            return cleanup_stats
            
        except Exception as e:
            logger.error(f"Error during database cleanup: {str(e)}")
            return {"error": str(e)}

    async def vacuum_collections(self, collections: Optional[List[str]] = None) -> bool:
        """Optimize database collections (MongoDB equivalent of vacuum)"""
        try:
            target_collections = collections or [
                "sequences", "analysis_results", "audit_logs", "system_metrics"
            ]
            
            for collection_name in target_collections:
                collection = await self.get_collection(collection_name)
                
                # Reindex collection
                await collection.reindex()
                
                # Compact collection (if supported by MongoDB deployment)
                try:
                    await self.database.command("compact", collection_name)
                except Exception:
                    logger.warning(f"Compact not supported for collection: {collection_name}")
            
            logger.info(f"Collections optimized: {target_collections}")
            return True
            
        except Exception as e:
            logger.error(f"Error optimizing collections: {str(e)}")
            return False

    # ============================================================================
    # HELPER METHODS
    # ============================================================================
    
    def _get_default_preferences(self) -> Dict:
        """Get default user preferences"""
        return {
            "theme": "light",
            "notifications": {
                "email": True,
                "browser": True,
                "workflow_completion": True,
                "error_alerts": True
            },
            "analysis": {
                "default_quality_threshold": 20,
                "auto_save_results": True,
                "preferred_formats": ["fasta", "fastq"],
                "max_file_size_mb": 100
            },
            "workflow": {
                "auto_layout": True,
                "show_progress": True,
                "parallel_execution": False
            }
        }

    async def _insert_default_data(self) -> bool:
        """Insert default reference data if collections are empty"""
        try:
            # Check if organisms collection is empty and populate with defaults
            organisms_collection = await self.get_collection("organisms")
            count = await organisms_collection.count_documents({})
            
            if count == 0:
                default_organisms = [
                    {
                        "_id": 1,
                        "name": "Homo sapiens",
                        "common_name": "Human",
                        "taxonomy_id": 9606,
                        "genome_size": 3200000000,
                        "created_at": datetime.utcnow()
                    },
                    {
                        "_id": 2,
                        "name": "Escherichia coli",
                        "common_name": "E. coli",
                        "taxonomy_id": 511145,
                        "genome_size": 4600000,
                        "created_at": datetime.utcnow()
                    },
                    {
                        "_id": 3,
                        "name": "Saccharomyces cerevisiae",
                        "common_name": "Baker's yeast",
                        "taxonomy_id": 559292,
                        "genome_size": 12000000,
                        "created_at": datetime.utcnow()
                    }
                ]
                
                await organisms_collection.insert_many(default_organisms)
                logger.info("✅ Default organisms data inserted")
            
            # Add other default data as needed...
            
            return True
            
        except Exception as e:
            logger.error(f"Error inserting default data: {str(e)}")
            return False

# ============================================================================
# DATABASE INITIALIZATION SCRIPT
# ============================================================================

async def initialize_database_schema():
    """Initialize complete database schema"""
    try:
        db_manager = DatabaseManager()
        await db_manager.connect()
        
        # Initialize collections and indexes
        success = await db_manager.initialize_collections()
        
        if success:
            logger.info("🎉 Database schema initialized successfully")
        else:
            logger.error("❌ Database schema initialization failed")
        
        return success
        
    except Exception as e:
        logger.error(f"Database initialization error: {str(e)}")
        return False

# MongoDB Collection Creation Commands
"""
MongoDB commands to manually create collections if needed:

use ugene_platform

db.createCollection("analysis_results")
db.createCollection("custom_motifs") 
db.createCollection("custom_elements")
db.createCollection("batch_results")
db.createCollection("audit_logs")
db.createCollection("system_metrics")
db.createCollection("file_metadata")
db.createCollection("workflow_templates")
db.createCollection("user_preferences")

# Create indexes
db.analysis_results.createIndex({ "analysis_type": 1, "created_at": -1 })
db.analysis_results.createIndex({ "user_id": 1, "created_at": -1 })
db.custom_motifs.createIndex({ "created_by": 1 })
db.custom_elements.createIndex({ "created_by": 1, "is_active": 1 })
db.audit_logs.createIndex({ "timestamp": -1 })
db.system_metrics.createIndex({ "metric_type": 1, "timestamp": -1 })
db.file_metadata.createIndex({ "uploaded_by": 1, "uploaded_at": -1 })
db.workflow_templates.createIndex({ "is_public": 1, "usage_count": -1 })
db.user_preferences.createIndex({ "user_id": 1 }, { "unique": true })
"""
