# backend/app/services/workflow_engine.py
import asyncio
import uuid
from datetime import datetime
from typing import Dict, List, Any, Optional
from ..services.data_readers import DataReaderService
from ..services.analysis_tools import AnalysisToolsService

class WorkflowEngine:
    """Central workflow execution engine"""
    
    def __init__(self, db, cache_manager, logger):
        self.db = db
        self.cache = cache_manager
        self.logger = logger
        self.data_reader = DataReaderService()
        self.analysis_tools = AnalysisToolsService()
        self.active_workflows = {}
        
        # Register workflow elements
        self.element_registry = {
            # Data Readers
            'read_alignment': self.data_reader.read_alignment,
            'read_annotations': self.data_reader.read_annotations,
            'read_fastq_se': self.data_reader.read_fastq_se_reads,
            'read_fastq_pe': self.data_reader.read_fastq_pe_reads,
            'read_file_urls': self.data_reader.read_file_urls,
            
            # Analysis Tools
            'blast_search': self.analysis_tools.run_blast_search,
            'multiple_alignment': self.analysis_tools.run_multiple_alignment,
            
            # Basic operations
            'filter_sequences': self._filter_sequences,
            'statistics': self._calculate_statistics,
        }
    
    async def execute_workflow(self, workflow_definition: Dict, input_data: Any = None, user_id: str = None) -> str:
        """Execute workflow asynchronously"""
        workflow_id = str(uuid.uuid4())
        
        workflow_context = {
            'id': workflow_id,
            'definition': workflow_definition,
            'user_id': user_id,
            'status': 'running',
            'current_step': 0,
            'results': [],
            'started_at': datetime.utcnow(),
            'data': input_data
        }
        
        self.active_workflows[workflow_id] = workflow_context
        
        # Start workflow execution in background
        asyncio.create_task(self._execute_workflow_steps(workflow_context))
        
        return workflow_id
    
    async def _execute_workflow_steps(self, context: Dict):
        """Execute workflow steps sequentially"""
        try:
            steps = context['definition'].get('nodes', [])
            
            for i, step in enumerate(steps):
                context['current_step'] = i + 1
                
                # Get element function
                element_type = step.get('type', '')
                if element_type not in self.element_registry:
                    raise ValueError(f"Unknown workflow element: {element_type}")
                
                element_function = self.element_registry[element_type]
                parameters = step.get('parameters', {})
                
                # Execute step
                if asyncio.iscoroutinefunction(element_function):
                    step_result = await element_function(context['data'], **parameters)
                else:
                    step_result = element_function(context['data'], **parameters)
                
                context['results'].append({
                    'step': i + 1,
                    'type': element_type,
                    'result': step_result,
                    'timestamp': datetime.utcnow().isoformat()
                })
                
                # Update data for next step
                context['data'] = step_result
            
            context['status'] = 'completed'
            context['completed_at'] = datetime.utcnow()
            
        except Exception as e:
            context['status'] = 'failed'
            context['error'] = str(e)
            context['failed_at'] = datetime.utcnow()
            self.logger.error(f"Workflow {context['id']} failed: {str(e)}")
        
        # Store final results in database
        await self._store_workflow_results(context)
    
    async def _filter_sequences(self, sequences: List[Dict], criteria: Dict = None) -> List[Dict]:
        """Filter sequences based on criteria"""
        if criteria is None:
            criteria = {}
            
        filtered = []
        for seq in sequences:
            include = True
            
            # Length filter
            if 'min_length' in criteria:
                if len(seq.get('sequence', '')) < criteria['min_length']:
                    include = False
            
            if 'max_length' in criteria:
                if len(seq.get('sequence', '')) > criteria['max_length']:
                    include = False
            
            if include:
                filtered.append(seq)
        
        return filtered
    
    async def _calculate_statistics(self, sequences: List[Dict]) -> Dict:
        """Calculate statistics for sequences"""
        if not sequences:
            return {"error": "No sequences provided"}
        
        lengths = [len(seq.get('sequence', '')) for seq in sequences]
        
        return {
            "sequence_count": len(sequences),
            "total_length": sum(lengths),
            "average_length": sum(lengths) / len(lengths),
            "min_length": min(lengths),
            "max_length": max(lengths)
        }
    
    async def _store_workflow_results(self, context: Dict):
        """Store workflow results in database"""
        try:
            await self.db.workflow_results.insert_one(context)
        except Exception as e:
            self.logger.error(f"Failed to store workflow results: {str(e)}")
    
    def get_workflow_status(self, workflow_id: str) -> Optional[Dict]:
        """Get workflow execution status"""
        return self.active_workflows.get(workflow_id)