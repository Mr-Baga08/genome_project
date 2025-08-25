# backend/app/models/complete_models.py
from pydantic import BaseModel, Field, validator
from typing import Dict, List, Any, Optional, Union
from datetime import datetime
from enum import Enum
import uuid
import re

# Enhanced Enums
class SequenceType(str, Enum):
    DNA = "DNA"
    RNA = "RNA"
    PROTEIN = "PROTEIN"
    UNKNOWN = "UNKNOWN"

class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class TaskPriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"

class AnalysisType(str, Enum):
    BLAST_SEARCH = "blast_search"
    MULTIPLE_ALIGNMENT = "multiple_alignment"
    PHYLOGENETIC_TREE = "phylogenetic_tree"
    GENE_EXPRESSION = "gene_expression"
    VARIANT_CALLING = "variant_calling"
    ANNOTATION = "annotation"
    STATISTICS = "statistics"
    CUSTOM_SCRIPT = "custom_script"

class UserRole(str, Enum):
    USER = "user"
    RESEARCHER = "researcher"
    ADMIN = "admin"
    SUPER_ADMIN = "super_admin"

class WorkflowStatus(str, Enum):
    DRAFT = "draft"
    VALIDATED = "validated"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"

# Enhanced Sequence Models
class SequenceBuilder(BaseModel):
    """Enhanced sequence builder with validation and metadata"""
    
    name: str = Field(..., min_length=1, max_length=200)
    sequence: str = Field(..., min_length=1)
    sequence_type: SequenceType = SequenceType.UNKNOWN
    description: Optional[str] = Field(None, max_length=1000)
    organism: Optional[str] = Field(None, max_length=100)
    source_database: Optional[str] = None
    accession_number: Optional[str] = None
    version: Optional[str] = None
    quality_scores: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    tags: List[str] = Field(default_factory=list)
    is_public: bool = False
    created_by: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    @validator('sequence')
    def validate_sequence(cls, v):
        """Validate sequence characters"""
        if not v:
            raise ValueError("Sequence cannot be empty")
        
        # Remove whitespace and convert to uppercase
        v = re.sub(r'\s+', '', v.upper())
        
        # Check for valid characters based on detected type
        valid_chars = set('ATCGRYKMSWBDHVNUIEFPQXZJ*-.')
        invalid_chars = set(v) - valid_chars
        
        if invalid_chars:
            raise ValueError(f"Invalid characters in sequence: {invalid_chars}")
        
        return v
    
    @validator('sequence_type', always=True)
    def detect_sequence_type(cls, v, values):
        """Auto-detect sequence type if not specified"""
        if v == SequenceType.UNKNOWN and 'sequence' in values:
            sequence = values['sequence']
            v = cls._detect_sequence_type(sequence)
        return v
    
    @staticmethod
    def _detect_sequence_type(sequence: str) -> SequenceType:
        """Detect sequence type from content"""
        sequence = sequence.upper()
        
        dna_chars = set('ATCGRYKMSWBDHVN')
        rna_chars = set('AUCGRYKMSWBDHVN')
        protein_chars = set('ACDEFGHIKLMNPQRSTVWYXZJ*')
        
        seq_chars = set(sequence.replace('-', '').replace('.', ''))
        
        if seq_chars.issubset(dna_chars):
            return SequenceType.DNA
        elif seq_chars.issubset(rna_chars) and 'U' in seq_chars:
            return SequenceType.RNA
        elif seq_chars.issubset(protein_chars):
            return SequenceType.PROTEIN
        else:
            return SequenceType.UNKNOWN
    
    def calculate_properties(self) -> Dict[str, Any]:
        """Calculate sequence properties"""
        seq = self.sequence.replace('-', '').replace('.', '')
        
        properties = {
            "length": len(seq),
            "molecular_weight": self._calculate_molecular_weight(seq),
            "composition": self._calculate_composition(seq)
        }
        
        if self.sequence_type == SequenceType.DNA:
            properties.update(self._calculate_dna_properties(seq))
        elif self.sequence_type == SequenceType.PROTEIN:
            properties.update(self._calculate_protein_properties(seq))
        
        return properties
    
    def _calculate_molecular_weight(self, sequence: str) -> float:
        """Calculate approximate molecular weight"""
        if self.sequence_type == SequenceType.DNA:
            # Average molecular weight per nucleotide
            return len(sequence) * 330.0
        elif self.sequence_type == SequenceType.RNA:
            return len(sequence) * 340.0
        elif self.sequence_type == SequenceType.PROTEIN:
            # Average molecular weight per amino acid
            return len(sequence) * 110.0
        else:
            return 0.0
    
    def _calculate_composition(self, sequence: str) -> Dict[str, float]:
        """Calculate sequence composition"""
        if not sequence:
            return {}
        
        composition = {}
        total_chars = len(sequence)
        
        for char in set(sequence):
            count = sequence.count(char)
            composition[char] = (count / total_chars) * 100
        
        return composition
    
    def _calculate_dna_properties(self, sequence: str) -> Dict[str, Any]:
        """Calculate DNA-specific properties"""
        g_count = sequence.count('G')
        c_count = sequence.count('C')
        a_count = sequence.count('A')
        t_count = sequence.count('T')
        
        total_bases = g_count + c_count + a_count + t_count
        
        if total_bases == 0:
            return {}
        
        gc_content = ((g_count + c_count) / total_bases) * 100
        
        return {
            "gc_content": gc_content,
            "at_content": 100 - gc_content,
            "purine_content": ((a_count + g_count) / total_bases) * 100,
            "pyrimidine_content": ((c_count + t_count) / total_bases) * 100
        }
    
    def _calculate_protein_properties(self, sequence: str) -> Dict[str, Any]:
        """Calculate protein-specific properties"""
        hydrophobic = set('AILMFWYV')
        hydrophilic = set('RNDEQHKST')
        charged = set('RNDEHK')
        
        hydrophobic_count = sum(1 for aa in sequence if aa in hydrophobic)
        hydrophilic_count = sum(1 for aa in sequence if aa in hydrophilic)
        charged_count = sum(1 for aa in sequence if aa in charged)
        
        total_aa = len(sequence)
        
        if total_aa == 0:
            return {}
        
        return {
            "hydrophobic_ratio": (hydrophobic_count / total_aa) * 100,
            "hydrophilic_ratio": (hydrophilic_count / total_aa) * 100,
            "charged_ratio": (charged_count / total_aa) * 100,
            "isoelectric_point": self._estimate_isoelectric_point(sequence)
        }
    
    def _estimate_isoelectric_point(self, sequence: str) -> float:
        """Estimate isoelectric point (simplified calculation)"""
        # Simplified pI calculation
        basic_aa = sequence.count('R') + sequence.count('K') + sequence.count('H')
        acidic_aa = sequence.count('D') + sequence.count('E')
        
        if len(sequence) == 0:
            return 7.0
        
        net_charge = (basic_aa - acidic_aa) / len(sequence)
        
        # Very simplified pI estimation
        return 7.0 + (net_charge * 3.0)

# Enhanced Analysis Result Models
class AnalysisResult(BaseModel):
    """Enhanced analysis result with comprehensive metadata"""
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    analysis_type: AnalysisType
    input_data: Dict[str, Any] = Field(default_factory=dict)
    output_data: Dict[str, Any] = Field(default_factory=dict)
    parameters: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    # Execution details
    started_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    execution_time: Optional[float] = None
    status: TaskStatus = TaskStatus.PENDING
    
    # Quality and validation
    validation_results: Dict[str, Any] = Field(default_factory=dict)
    quality_metrics: Dict[str, Any] = Field(default_factory=dict)
    error_messages: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    
    # File management
    input_files: List[str] = Field(default_factory=list)
    output_files: List[str] = Field(default_factory=list)
    temp_files: List[str] = Field(default_factory=list)
    
    # User and organization
    created_by: str
    organization: Optional[str] = None
    is_public: bool = False
    shared_with: List[str] = Field(default_factory=list)
    
    # Version control
    version: int = 1
    parent_analysis_id: Optional[str] = None
    child_analyses: List[str] = Field(default_factory=list)

# Enhanced Workflow Models
class WorkflowNode(BaseModel):
    """Enhanced workflow node with validation"""
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str = Field(..., min_length=1, max_length=200)
    node_type: str = Field(..., min_length=1)
    description: Optional[str] = Field(None, max_length=1000)
    
    # Position and layout
    position: Dict[str, float] = Field(default_factory=dict)
    size: Dict[str, float] = Field(default_factory=lambda: {"width": 200, "height": 100})
    
    # Connectivity
    input_ports: List[Dict[str, Any]] = Field(default_factory=list)
    output_ports: List[Dict[str, Any]] = Field(default_factory=list)
    
    # Configuration
    parameters: Dict[str, Any] = Field(default_factory=dict)
    required_parameters: List[str] = Field(default_factory=list)
    optional_parameters: List[str] = Field(default_factory=list)
    
    # Execution
    script_content: Optional[str] = None
    script_type: Optional[str] = None
    container_image: Optional[str] = None
    
    # Status and results
    status: TaskStatus = TaskStatus.PENDING
    execution_order: Optional[int] = None
    depends_on: List[str] = Field(default_factory=list)
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    @validator('node_type')
    def validate_node_type(cls, v):
        """Validate node type"""
        valid_types = [
            'data_reader', 'data_writer', 'alignment', 'blast_search',
            'annotation', 'statistics', 'filter', 'custom_script',
            'quality_control', 'preprocessing', 'visualization'
        ]
        
        if v not in valid_types:
            raise ValueError(f"Invalid node type. Must be one of: {valid_types}")
        
        return v

class WorkflowConnection(BaseModel):
    """Enhanced workflow connection with data flow validation"""
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    from_node_id: str
    to_node_id: str
    from_port: str
    to_port: str
    
    # Data flow configuration
    data_mapping: Dict[str, str] = Field(default_factory=dict)
    transform_script: Optional[str] = None
    
    # Validation
    is_valid: bool = True
    validation_errors: List[str] = Field(default_factory=list)
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)

class WorkflowExecution(BaseModel):
    """Enhanced workflow execution tracking"""
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    workflow_id: str
    workflow_definition: Dict[str, Any]
    
    # Execution details
    status: WorkflowStatus = WorkflowStatus.DRAFT
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    paused_at: Optional[datetime] = None
    
    # Progress tracking
    total_nodes: int = 0
    completed_nodes: int = 0
    failed_nodes: int = 0
    current_node: Optional[str] = None
    
    # Results and data
    input_data: Dict[str, Any] = Field(default_factory=dict)
    output_data: Dict[str, Any] = Field(default_factory=dict)
    intermediate_results: Dict[str, Any] = Field(default_factory=dict)
    
    # Node execution results
    node_results: Dict[str, Any] = Field(default_factory=dict)
    node_timings: Dict[str, float] = Field(default_factory=dict)
    node_errors: Dict[str, str] = Field(default_factory=dict)
    
    # Resource usage
    memory_usage: Dict[str, float] = Field(default_factory=dict)
    cpu_usage: Dict[str, float] = Field(default_factory=dict)
    disk_usage: Dict[str, float] = Field(default_factory=dict)
    
    # User and context
    created_by: str
    organization: Optional[str] = None
    priority: TaskPriority = TaskPriority.MEDIUM
    
    # Configuration
    max_retries: int = 3
    timeout_minutes: int = 120
    
    def calculate_progress(self) -> float:
        """Calculate execution progress percentage"""
        if self.total_nodes == 0:
            return 0.0
        return (self.completed_nodes / self.total_nodes) * 100

# Enhanced User Management Models
class UserProfile(BaseModel):
    """Enhanced user profile with biological data context"""
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    username: str = Field(..., min_length=3, max_length=50)
    email: str = Field(..., regex=r'^[^@]+@[^@]+\.[^@]+$')
    full_name: Optional[str] = Field(None, max_length=100)
    
    # Organization and role
    organization: Optional[str] = Field(None, max_length=100)
    department: Optional[str] = Field(None, max_length=100)
    role: UserRole = UserRole.USER
    permissions: List[str] = Field(default_factory=list)
    
    # Account status
    is_active: bool = True
    is_verified: bool = False
    email_verified: bool = False
    two_factor_enabled: bool = False
    
    # Preferences
    preferences: Dict[str, Any] = Field(default_factory=dict)
    notification_settings: Dict[str, bool] = Field(default_factory=lambda: {
        "email_notifications": True,
        "task_completion": True,
        "workflow_status": True,
        "security_alerts": True
    })
    
    # Usage statistics
    total_analyses: int = 0
    total_workflows: int = 0
    storage_used_mb: float = 0.0
    last_login: Optional[datetime] = None
    login_count: int = 0
    
    # Security
    password_hash: Optional[str] = None
    failed_login_attempts: int = 0
    locked_until: Optional[datetime] = None
    password_changed_at: Optional[datetime] = None
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    @validator('username')
    def validate_username(cls, v):
        """Validate username format"""
        if not re.match(r'^[a-zA-Z0-9_-]+$', v):
            raise ValueError("Username can only contain letters, numbers, underscores, and hyphens")
        return v

class OrganizationModel(BaseModel):
    """Organization/institution model"""
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str = Field(..., min_length=1, max_length=200)
    display_name: Optional[str] = None
    description: Optional[str] = Field(None, max_length=1000)
    
    # Contact information
    website: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[Dict[str, str]] = None
    
    # Settings
    settings: Dict[str, Any] = Field(default_factory=dict)
    storage_quota_gb: float = 100.0
    user_limit: int = 100
    
    # Members
    admin_users: List[str] = Field(default_factory=list)
    member_count: int = 0
    
    # Status
    is_active: bool = True
    subscription_tier: str = "free"
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

# Enhanced Task and Project Models
class ProjectModel(BaseModel):
    """Project model for organizing related analyses"""
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=2000)
    
    # Organization
    created_by: str
    organization: Optional[str] = None
    collaborators: List[str] = Field(default_factory=list)
    
    # Content
    sequences: List[str] = Field(default_factory=list)
    workflows: List[str] = Field(default_factory=list)
    analyses: List[str] = Field(default_factory=list)
    files: List[str] = Field(default_factory=list)
    
    # Settings
    is_public: bool = False
    tags: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    # Status
    status: str = "active"
    progress: float = 0.0
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    due_date: Optional[datetime] = None

class FileUpload(BaseModel):
    """Enhanced file upload model with security and metadata"""
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    original_filename: str
    secure_filename: str
    file_path: str
    
    # File properties
    file_size: int
    file_type: str
    mime_type: str
    checksum: str
    
    # Content analysis
    content_type: Optional[str] = None  # biological content type
    sequence_count: Optional[int] = None
    format_validation: Dict[str, Any] = Field(default_factory=dict)
    
    # Security
    virus_scan_result: Optional[str] = None
    security_flags: List[str] = Field(default_factory=list)
    upload_ip: Optional[str] = None
    
    # Access control
    uploaded_by: str
    organization: Optional[str] = None
    is_public: bool = False
    shared_with: List[str] = Field(default_factory=list)
    
    # Lifecycle
    created_at: datetime = Field(default_factory=datetime.utcnow)
    accessed_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    auto_delete: bool = False
    
    def calculate_checksum(self, file_content: bytes) -> str:
        """Calculate file checksum"""
        import hashlib
        return hashlib.sha256(file_content).hexdigest()

# Enhanced Notification Models
class NotificationModel(BaseModel):
    """Enhanced notification system"""
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    recipient_id: str
    
    # Content
    title: str = Field(..., max_length=200)
    message: str = Field(..., max_length=1000)
    notification_type: str
    priority: str = "normal"  # low, normal, high, urgent
    
    # Context
    related_entity_type: Optional[str] = None  # task, workflow, analysis, etc.
    related_entity_id: Optional[str] = None
    action_url: Optional[str] = None
    
    # Status
    is_read: bool = False
    is_dismissed: bool = False
    read_at: Optional[datetime] = None
    
    # Delivery
    delivery_methods: List[str] = Field(default_factory=lambda: ["web"])
    email_sent: bool = False
    email_sent_at: Optional[datetime] = None
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None

# Enhanced Configuration Models
class SystemConfiguration(BaseModel):
    """System-wide configuration model"""
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    
    # Application settings
    app_name: str = "UGENE Web Platform"
    app_version: str = "1.0.0"
    maintenance_mode: bool = False
    debug_mode: bool = False
    
    # Resource limits
    max_concurrent_tasks: int = 10
    max_file_upload_size_mb: int = 500
    max_workflow_nodes: int = 100
    task_timeout_minutes: int = 180
    
    # Database settings
    database_config: Dict[str, Any] = Field(default_factory=dict)
    cache_config: Dict[str, Any] = Field(default_factory=dict)
    
    # External services
    docker_enabled: bool = True
    external_databases: Dict[str, Any] = Field(default_factory=dict)
    
    # Security settings
    security_config: Dict[str, Any] = Field(default_factory=dict)
    
    # Feature flags
    feature_flags: Dict[str, bool] = Field(default_factory=lambda: {
        "custom_scripts": True,
        "external_tools": True,
        "real_time_monitoring": True,
        "batch_processing": True,
        "api_access": True
    })
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    updated_by: Optional[str] = None

# Data Pipeline Models
class DataPipeline(BaseModel):
    """Data processing pipeline model"""
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    
    # Pipeline definition
    steps: List[Dict[str, Any]] = Field(default_factory=list)
    step_dependencies: Dict[str, List[str]] = Field(default_factory=dict)
    
    # Configuration
    input_schema: Dict[str, Any] = Field(default_factory=dict)
    output_schema: Dict[str, Any] = Field(default_factory=dict)
    default_parameters: Dict[str, Any] = Field(default_factory=dict)
    
    # Execution settings
    max_parallel_steps: int = 3
    retry_failed_steps: bool = True
    continue_on_error: bool = False
    
    # Access control
    created_by: str
    organization: Optional[str] = None
    is_template: bool = False
    is_public: bool = False
    
    # Usage statistics
    execution_count: int = 0
    success_rate: float = 0.0
    average_execution_time: float = 0.0
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

# Enhanced Validation Models
class ValidationRule(BaseModel):
    """Validation rule for biological data"""
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str = Field(..., min_length=1, max_length=100)
    description: str = Field(..., max_length=500)
    
    # Rule definition
    rule_type: str  # sequence, file, parameter, workflow
    condition: Dict[str, Any]  # JSON condition
    error_message: str
    severity: str = "error"  # error, warning, info
    
    # Applicability
    applies_to: List[str] = Field(default_factory=list)  # data types this rule applies to
    is_active: bool = True
    
    # Metadata
    created_by: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    usage_count: int = 0

class DataQualityReport(BaseModel):
    """Data quality assessment report"""
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    data_id: str
    data_type: str
    
    # Quality metrics
    overall_score: float = 0.0
    completeness_score: float = 0.0
    accuracy_score: float = 0.0
    consistency_score: float = 0.0
    
    # Detailed results
    validation_results: List[Dict[str, Any]] = Field(default_factory=list)
    quality_issues: List[Dict[str, Any]] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)
    
    # Statistics
    total_records: int = 0
    valid_records: int = 0
    invalid_records: int = 0
    warnings_count: int = 0
    errors_count: int = 0
    
    # Metadata
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    generated_by: str
    parameters_used: Dict[str, Any] = Field(default_factory=dict)

# Integration Models
class ExternalServiceIntegration(BaseModel):
    """External service integration configuration"""
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    service_name: str
    service_type: str  # database, api, tool, etc.
    
    # Connection details
    endpoint_url: Optional[str] = None
    api_key: Optional[str] = None
    connection_config: Dict[str, Any] = Field(default_factory=dict)
    
    # Status
    is_active: bool = True
    last_health_check: Optional[datetime] = None
    health_status: str = "unknown"  # healthy, degraded, down, unknown
    
    # Usage
    request_count: int = 0
    error_count: int = 0
    average_response_time: float = 0.0
    
    # Configuration
    rate_limit: Optional[int] = None
    timeout_seconds: int = 30
    retry_attempts: int = 3
    
    # Metadata
    created_by: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

# Request/Response Models with Enhanced Validation
class EnhancedTaskRequest(BaseModel):
    """Enhanced task creation request"""
    
    task_type: str
    input_data: Dict[str, Any]
    parameters: Dict[str, Any] = Field(default_factory=dict)
    
    # Execution settings
    priority: TaskPriority = TaskPriority.MEDIUM
    max_execution_time: int = 3600  # seconds
    retry_count: int = 0
    
    # Context
    project_id: Optional[str] = None
    workflow_id: Optional[str] = None
    parent_task_id: Optional[str] = None
    
    # Metadata
    tags: List[str] = Field(default_factory=list)
    description: Optional[str] = None
    
    @validator('task_type')
    def validate_task_type(cls, v):
        """Validate task type"""
        valid_types = [
            'blast_search', 'multiple_alignment', 'phylogenetic_tree',
            'gene_expression', 'variant_calling', 'annotation',
            'quality_control', 'statistics', 'custom_analysis'
        ]
        
        if v not in valid_types:
            raise ValueError(f"Invalid task type. Must be one of: {valid_types}")
        
        return v
    
    @validator('max_execution_time')
    def validate_execution_time(cls, v):
        """Validate execution time limits"""
        if v < 60:  # Minimum 1 minute
            raise ValueError("Execution time must be at least 60 seconds")
        if v > 86400:  # Maximum 24 hours
            raise ValueError("Execution time cannot exceed 24 hours")
        return v

class BulkOperationRequest(BaseModel):
    """Request for bulk operations on biological data"""
    
    operation_type: str
    target_ids: List[str] = Field(..., min_items=1, max_items=1000)
    parameters: Dict[str, Any] = Field(default_factory=dict)
    
    # Execution settings
    batch_size: int = Field(default=10, ge=1, le=100)
    parallel_execution: bool = True
    fail_fast: bool = False
    
    # Context
    project_id: Optional[str] = None
    description: Optional[str] = None
    
    @validator('operation_type')
    def validate_operation_type(cls, v):
        """Validate bulk operation type"""
        valid_operations = [
            'sequence_analysis', 'format_conversion', 'quality_control',
            'annotation', 'export', 'delete', 'update_metadata'
        ]
        
        if v not in valid_operations:
            raise ValueError(f"Invalid operation type. Must be one of: {valid_operations}")
        
        return v

# API Response Models
class PaginatedResponse(BaseModel):
    """Generic paginated response model"""
    
    items: List[Any]
    total_count: int
    page: int = Field(ge=1)
    page_size: int = Field(ge=1, le=1000)
    total_pages: int
    has_next: bool
    has_previous: bool
    
    def calculate_pagination_info(self):
        """Calculate pagination information"""
        self.total_pages = max(1, (self.total_count + self.page_size - 1) // self.page_size)
        self.has_next = self.page < self.total_pages
        self.has_previous = self.page > 1

class HealthCheckResponse(BaseModel):
    """System health check response"""
    
    status: str  # healthy, degraded, down
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    services: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    system_info: Dict[str, Any] = Field(default_factory=dict)
    performance_metrics: Dict[str, float] = Field(default_factory=dict)
    
    # Resource usage
    memory_usage_mb: Optional[float] = None
    cpu_usage_percent: Optional[float] = None
    disk_usage_percent: Optional[float] = None
    
    # Application metrics
    active_users: int = 0
    running_tasks: int = 0
    queued_tasks: int = 0
    total_sequences: int = 0
    
    def determine_overall_status(self):
        """Determine overall system status"""
        service_statuses = [service.get('status', 'unknown') for service in self.services.values()]
        
        if all(status == 'healthy' for status in service_statuses):
            self.status = 'healthy'
        elif any(status == 'down' for status in service_statuses):
            self.status = 'down'
        else:
            self.status = 'degraded'

# Custom Validation Functions
def validate_sequence_format(sequence: str, expected_type: SequenceType) -> Dict[str, Any]:
    """Validate sequence format against expected type"""
    
    validation = {
        "valid": True,
        "detected_type": SequenceType.UNKNOWN,
        "confidence": 0.0,
        "issues": []
    }
    
    if not sequence:
        validation["valid"] = False
        validation["issues"].append("Empty sequence")
        return validation
    
    # Detect actual type
    sequence_clean = sequence.upper().replace('-', '').replace('.', '')
    
    dna_chars = set('ATCGRYKMSWBDHVN')
    rna_chars = set('AUCGRYKMSWBDHVN') 
    protein_chars = set('ACDEFGHIKLMNPQRSTVWYXZJ*')
    
    seq_chars = set(sequence_clean)
    
    # Calculate confidence scores
    dna_confidence = len(seq_chars & dna_chars) / len(seq_chars) if seq_chars else 0
    rna_confidence = len(seq_chars & rna_chars) / len(seq_chars) if seq_chars else 0
    protein_confidence = len(seq_chars & protein_chars) / len(seq_chars) if seq_chars else 0
    
    # Determine detected type
    max_confidence = max(dna_confidence, rna_confidence, protein_confidence)
    
    if max_confidence >= 0.9:
        if dna_confidence == max_confidence:
            validation["detected_type"] = SequenceType.DNA
        elif rna_confidence == max_confidence and 'U' in seq_chars:
            validation["detected_type"] = SequenceType.RNA
        elif protein_confidence == max_confidence:
            validation["detected_type"] = SequenceType.PROTEIN
    
    validation["confidence"] = max_confidence
    
    # Check against expected type
    if expected_type != SequenceType.UNKNOWN and validation["detected_type"] != expected_type:
        validation["issues"].append(f"Expected {expected_type}, detected {validation['detected_type']}")
        if max_confidence < 0.7:
            validation["valid"] = False
    
    return validation

# Exception Models
class ValidationError(Exception):
    """Custom validation error"""
    
    def __init__(self, message: str, field: str = None, value: Any = None):
        self.message = message
        self.field = field
        self.value = value
        super().__init__(message)

class SecurityException(Exception):
    """Security-related exception"""
    
    def __init__(self, message: str, security_code: str = None):
        self.message = message
        self.security_code = security_code
        super().__init__(message)