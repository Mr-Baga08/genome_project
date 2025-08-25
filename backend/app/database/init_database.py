# backend/app/database/init_database.py
import asyncio
import logging
from typing import Dict, List
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import IndexModel, ASCENDING, DESCENDING, TEXT
from .database_setup import DatabaseManager
from ..models.enhanced_models import *

logger = logging.getLogger(__name__)

class DatabaseInitializer:
    """Initialize database with collections, indexes, and seed data"""
    
    def __init__(self, database_manager: DatabaseManager):
        self.db_manager = database_manager
        self.database = database_manager.database
    
    async def initialize_database(self, reset: bool = False):
        """Initialize complete database setup"""
        try:
            logger.info("Starting database initialization...")
            
            if reset:
                await self._drop_all_collections()
            
            await self._create_collections()
            await self._create_indexes()
            await self._insert_seed_data()
            await self._create_views()
            
            logger.info("Database initialization completed successfully")
            
        except Exception as e:
            logger.error(f"Database initialization failed: {str(e)}")
            raise
    
    async def _drop_all_collections(self):
        """Drop all existing collections (use with caution)"""
        logger.warning("Dropping all collections...")
        
        collection_names = await self.database.list_collection_names()
        for name in collection_names:
            await self.database.drop_collection(name)
            logger.info(f"Dropped collection: {name}")
    
    async def _create_collections(self):
        """Create all required collections"""
        collections_config = {
            'sequences': {
                'validator': {
                    '$jsonSchema': {
                        'bsonType': 'object',
                        'required': ['name', 'sequence', 'sequence_type'],
                        'properties': {
                            'name': {'bsonType': 'string'},
                            'sequence': {'bsonType': 'string'},
                            'sequence_type': {'bsonType': 'string', 'enum': ['DNA', 'RNA', 'PROTEIN']},
                            'length': {'bsonType': 'int', 'minimum': 1},
                            'gc_content': {'bsonType': 'double', 'minimum': 0, 'maximum': 100},
                            'created_at': {'bsonType': 'date'},
                            'is_public': {'bsonType': 'bool'}
                        }
                    }
                }
            },
            'annotations': {
                'validator': {
                    '$jsonSchema': {
                        'bsonType': 'object',
                        'required': ['sequence_id', 'feature_type', 'start_position', 'end_position'],
                        'properties': {
                            'sequence_id': {'bsonType': 'string'},
                            'feature_type': {'bsonType': 'string'},
                            'start_position': {'bsonType': 'int', 'minimum': 1},
                            'end_position': {'bsonType': 'int', 'minimum': 1},
                            'strand': {'bsonType': 'string', 'enum': ['+', '-', '.']},
                            'attributes': {'bsonType': 'object'}
                        }
                    }
                }
            },
            'analysis_tasks': {
                'validator': {
                    '$jsonSchema': {
                        'bsonType': 'object',
                        'required': ['task_id', 'analysis_type', 'status'],
                        'properties': {
                            'task_id': {'bsonType': 'string'},
                            'analysis_type': {'bsonType': 'string'},
                            'status': {'bsonType': 'string', 'enum': ['pending', 'running', 'completed', 'failed', 'cancelled']},
                            'priority': {'bsonType': 'string', 'enum': ['low', 'medium', 'high']},
                            'progress': {'bsonType': 'int', 'minimum': 0, 'maximum': 100},
                            'created_at': {'bsonType': 'date'},
                            'started_at': {'bsonType': 'date'},
                            'completed_at': {'bsonType': 'date'}
                        }
                    }
                }
            },
            'analysis_results': {},
            'pipelines': {},
            'pipeline_executions': {},
            'users': {
                'validator': {
                    '$jsonSchema': {
                        'bsonType': 'object',
                        'required': ['username', 'email'],
                        'properties': {
                            'username': {'bsonType': 'string', 'minLength': 3},
                            'email': {'bsonType': 'string', 'pattern': '^[^@]+@[^@]+\.[^@]+$'},
                            'is_active': {'bsonType': 'bool'},
                            'created_at': {'bsonType': 'date'}
                        }
                    }
                }
            },
            'organisms': {},
            'cache_entries': {},
            'system_logs': {}
        }
        
        existing_collections = await self.database.list_collection_names()
        
        for collection_name, config in collections_config.items():
            if collection_name not in existing_collections:
                if config.get('validator'):
                    await self.database.create_collection(
                        collection_name,
                        validator=config['validator']
                    )
                else:
                    await self.database.create_collection(collection_name)
                logger.info(f"Created collection: {collection_name}")
            else:
                logger.info(f"Collection already exists: {collection_name}")
    
    async def _create_indexes(self):
        """Create all database indexes for performance"""
        indexes_config = {
            'sequences': [
                IndexModel([('name', TEXT)], name='text_search'),
                IndexModel([('sequence_type', ASCENDING)], name='sequence_type_idx'),
                IndexModel([('organism_id', ASCENDING)], name='organism_idx'),
                IndexModel([('length', ASCENDING)], name='length_idx'),
                IndexModel([('gc_content', ASCENDING)], name='gc_content_idx'),
                IndexModel([('checksum', ASCENDING)], name='checksum_idx', unique=True),
                IndexModel([('created_at', DESCENDING)], name='created_date_idx'),
                IndexModel([('is_public', ASCENDING)], name='public_idx'),
                IndexModel([('user_id', ASCENDING), ('created_at', DESCENDING)], name='user_sequences_idx'),
                IndexModel([('sequence_type', ASCENDING), ('length', ASCENDING)], name='type_length_idx'),
            ],
            'annotations': [
                IndexModel([('sequence_id', ASCENDING)], name='sequence_annotations_idx'),
                IndexModel([('feature_type', ASCENDING)], name='feature_type_idx'),
                IndexModel([('start_position', ASCENDING), ('end_position', ASCENDING)], name='position_range_idx'),
                IndexModel([('sequence_id', ASCENDING), ('feature_type', ASCENDING)], name='seq_feature_idx'),
                IndexModel([('strand', ASCENDING)], name='strand_idx'),
                IndexModel([('attributes', TEXT)], name='attributes_text_idx'),
            ],
            'analysis_tasks': [
                IndexModel([('task_id', ASCENDING)], name='task_id_idx', unique=True),
                IndexModel([('status', ASCENDING)], name='status_idx'),
                IndexModel([('analysis_type', ASCENDING)], name='analysis_type_idx'),
                IndexModel([('user_id', ASCENDING), ('created_at', DESCENDING)], name='user_tasks_idx'),
                IndexModel([('priority', DESCENDING), ('created_at', ASCENDING)], name='priority_queue_idx'),
                IndexModel([('status', ASCENDING), ('created_at', ASCENDING)], name='status_queue_idx'),
                IndexModel([('created_at', DESCENDING)], name='recent_tasks_idx'),
                IndexModel([('analysis_type', ASCENDING), ('status', ASCENDING)], name='type_status_idx'),
            ],
            'analysis_results': [
                IndexModel([('task_id', ASCENDING)], name='task_results_idx', unique=True),
                IndexModel([('analysis_type', ASCENDING)], name='results_type_idx'),
                IndexModel([('created_at', DESCENDING)], name='results_date_idx'),
                IndexModel([('results.database', ASCENDING)], name='blast_db_idx', sparse=True),
                IndexModel([('results.method', ASCENDING)], name='method_idx', sparse=True),
            ],
            'pipelines': [
                IndexModel([('name', TEXT)], name='pipeline_name_search'),
                IndexModel([('author', ASCENDING)], name='pipeline_author_idx'),
                IndexModel([('tags', ASCENDING)], name='pipeline_tags_idx'),
                IndexModel([('is_public', ASCENDING)], name='pipeline_public_idx'),
                IndexModel([('created_at', DESCENDING)], name='pipeline_date_idx'),
                IndexModel([('category', ASCENDING)], name='pipeline_category_idx'),
            ],
            'pipeline_executions': [
                IndexModel([('execution_id', ASCENDING)], name='execution_id_idx', unique=True),
                IndexModel([('pipeline_id', ASCENDING)], name='pipeline_exec_idx'),
                IndexModel([('user_id', ASCENDING), ('started_at', DESCENDING)], name='user_executions_idx'),
                IndexModel([('status', ASCENDING)], name='execution_status_idx'),
                IndexModel([('started_at', DESCENDING)], name='execution_date_idx'),
            ],
            'users': [
                IndexModel([('username', ASCENDING)], name='username_idx', unique=True),
                IndexModel([('email', ASCENDING)], name='email_idx', unique=True),
                IndexModel([('is_active', ASCENDING)], name='active_users_idx'),
                IndexModel([('created_at', DESCENDING)], name='user_registration_idx'),
                IndexModel([('last_login', DESCENDING)], name='last_login_idx'),
            ],
            'organisms': [
                IndexModel([('scientific_name', ASCENDING)], name='scientific_name_idx', unique=True),
                IndexModel([('common_name', TEXT)], name='common_name_search'),
                IndexModel([('taxonomy_id', ASCENDING)], name='taxonomy_id_idx', unique=True),
                IndexModel([('kingdom', ASCENDING)], name='kingdom_idx'),
            ],
            'cache_entries': [
                IndexModel([('cache_key', ASCENDING)], name='cache_key_idx', unique=True),
                IndexModel([('namespace', ASCENDING)], name='cache_namespace_idx'),
                IndexModel([('expires_at', ASCENDING)], name='cache_expiry_idx'),
                IndexModel([('created_at', DESCENDING)], name='cache_date_idx'),
            ],
            'system_logs': [
                IndexModel([('level', ASCENDING)], name='log_level_idx'),
                IndexModel([('component', ASCENDING)], name='log_component_idx'),
                IndexModel([('timestamp', DESCENDING)], name='log_timestamp_idx'),
                IndexModel([('user_id', ASCENDING), ('timestamp', DESCENDING)], name='user_logs_idx'),
            ]
        }
        
        for collection_name, indexes in indexes_config.items():
            collection = self.database[collection_name]
            
            try:
                result = await collection.create_indexes(indexes)
                logger.info(f"Created {len(result)} indexes for collection: {collection_name}")
            except Exception as e:
                logger.error(f"Failed to create indexes for {collection_name}: {str(e)}")
    
    async def _insert_seed_data(self):
        """Insert initial seed data"""
        
        # Seed organisms data
        organisms_data = [
            {
                'scientific_name': 'Escherichia coli',
                'common_name': 'E. coli',
                'taxonomy_id': 562,
                'kingdom': 'Bacteria',
                'genome_size': 4641652,
                'created_at': datetime.utcnow()
            },
            {
                'scientific_name': 'Homo sapiens',
                'common_name': 'Human',
                'taxonomy_id': 9606,
                'kingdom': 'Eukaryota',
                'genome_size': 3200000000,
                'created_at': datetime.utcnow()
            },
            {
                'scientific_name': 'Saccharomyces cerevisiae',
                'common_name': 'Baker\'s yeast',
                'taxonomy_id': 4932,
                'kingdom': 'Eukaryota',
                'genome_size': 12071326,
                'created_at': datetime.utcnow()
            },
            {
                'scientific_name': 'Drosophila melanogaster',
                'common_name': 'Fruit fly',
                'taxonomy_id': 7227,
                'kingdom': 'Eukaryota',
                'genome_size': 143726002,
                'created_at': datetime.utcnow()
            }
        ]
        
        organisms_collection = self.database['organisms']
        existing_organisms = await organisms_collection.count_documents({})
        
        if existing_organisms == 0:
            await organisms_collection.insert_many(organisms_data)
            logger.info(f"Inserted {len(organisms_data)} organism records")
        else:
            logger.info(f"Organisms collection already has {existing_organisms} records")
        
        # Seed sample sequences
        sample_sequences = [
            {
                'name': 'Sample_DNA_Sequence_1',
                'description': 'Sample bacterial gene sequence',
                'sequence': 'ATGAAACGCATTAGCACCACCATTACCACCACCATCACCATTACCACAGGTAACGGTGCGGGCTGACGCGTACAGGAAACACAGAAAAAAGCCCGCACCTGACAGTGCGGGCTTTTTTTTTCGACCAAAGGTAACGAGGTAACAACCATGCGAGTGTTGAAGTTCGGCGGTACATCAGTGGCAAATGCAGAACGTTTTCTGCGTGTTGCCGATATTCTGGAAAGCAATGCCAGGCAGGGGCAGGTGGCCACCGTCCTCTCTGCCCCCGCCAAAATCACCAACCACCTGGTGGCGATGATTGAAAAAACCATTAGCGGCCAGGATGCTTTACCCAATATCAGCGATGCCGAACGTATTTTTGCCGAACTTTTGACGGGACTCGCCGCCGCCCAGCCGGGGTTCCCGCTGGCGCAATTGAAAACTTTCGTCGATCAGGAATTTGCCCAA',
                'sequence_type': 'DNA',
                'organism_id': 562,  # E. coli
                'length': 501,
                'gc_content': 52.3,
                'is_public': True,
                'created_at': datetime.utcnow(),
                'checksum': 'sample_dna_1_checksum'
            },
            {
                'name': 'Sample_Protein_Sequence_1',
                'description': 'Sample protein sequence',
                'sequence': 'MKRLATTPLTTTPSPLTTSKTNTKSAPVKKGRLQVFHHVQEQVKSVQSLQVSTNQTQVSKPRKRKNRHRKASLSTTSHSARSSTHSSVAHHVQEQVKSVQSLQVSTNQTQVSKPRKRKNRHRKASLSTTSHSARSSTHSSVAHHV',
                'sequence_type': 'PROTEIN',
                'organism_id': 9606,  # Human
                'length': 150,
                'is_public': True,
                'created_at': datetime.utcnow(),
                'checksum': 'sample_protein_1_checksum'
            }
        ]
        
        sequences_collection = self.database['sequences']
        existing_sequences = await sequences_collection.count_documents({})
        
        if existing_sequences == 0:
            await sequences_collection.insert_many(sample_sequences)
            logger.info(f"Inserted {len(sample_sequences)} sample sequences")
        else:
            logger.info(f"Sequences collection already has {existing_sequences} records")
        
        # Seed sample annotations
        sample_annotations = [
            {
                'sequence_id': 'sample_dna_1_checksum',
                'feature_type': 'gene',
                'start_position': 1,
                'end_position': 501,
                'strand': '+',
                'attributes': {
                    'gene': 'sampleGene',
                    'product': 'hypothetical protein',
                    'note': 'sample annotation'
                },
                'created_at': datetime.utcnow()
            },
            {
                'sequence_id': 'sample_dna_1_checksum',
                'feature_type': 'CDS',
                'start_position': 1,
                'end_position': 501,
                'strand': '+',
                'attributes': {
                    'gene': 'sampleGene',
                    'product': 'hypothetical protein',
                    'translation': 'MKRLATTPLTTTPSPLTTSKTNTKSAPVKKGRLQVFHHVQEQVKSVQSLQVSTNQTQVSK'
                },
                'created_at': datetime.utcnow()
            }
        ]
        
        annotations_collection = self.database['annotations']
        existing_annotations = await annotations_collection.count_documents({})
        
        if existing_annotations == 0:
            await annotations_collection.insert_many(sample_annotations)
            logger.info(f"Inserted {len(sample_annotations)} sample annotations")
        else:
            logger.info(f"Annotations collection already has {existing_annotations} records")
    
    async def _create_views(self):
        """Create database views for complex queries"""
        
        # Create view for sequence statistics
        sequence_stats_pipeline = [
            {
                '$group': {
                    '_id': '$sequence_type',
                    'count': {'$sum': 1},
                    'avg_length': {'$avg': '$length'},
                    'min_length': {'$min': '$length'},
                    'max_length': {'$max': '$length'},
                    'avg_gc_content': {'$avg': '$gc_content'}
                }
            },
            {
                '$project': {
                    'sequence_type': '$_id',
                    'count': 1,
                    'avg_length': {'$round': ['$avg_length', 2]},
                    'min_length': 1,
                    'max_length': 1,
                    'avg_gc_content': {'$round': ['$avg_gc_content', 2]},
                    '_id': 0
                }
            }
        ]
        
        try:
            await self.database.create_collection(
                'sequence_statistics_view',
                viewOn='sequences',
                pipeline=sequence_stats_pipeline
            )
            logger.info("Created sequence_statistics_view")
        except Exception as e:
            if 'already exists' not in str(e):
                logger.error(f"Failed to create sequence_statistics_view: {str(e)}")
        
        # Create view for recent analysis tasks
        recent_tasks_pipeline = [
            {
                '$match': {
                    'created_at': {
                        '$gte': {
                            '$dateSubtract': {
                                'startDate': '$$NOW',
                                'unit': 'day',
                                'amount': 30
                            }
                        }
                    }
                }
            },
            {
                '$group': {
                    '_id': {
                        'analysis_type': '$analysis_type',
                        'status': '$status'
                    },
                    'count': {'$sum': 1},
                    'avg_duration': {
                        '$avg': {
                            '$subtract': ['$completed_at', '$started_at']
                        }
                    }
                }
            },
            {
                '$project': {
                    'analysis_type': '$_id.analysis_type',
                    'status': '$_id.status',
                    'count': 1,
                    'avg_duration_ms': '$avg_duration',
                    '_id': 0
                }
            }
        ]
        
        try:
            await self.database.create_collection(
                'recent_tasks_view',
                viewOn='analysis_tasks',
                pipeline=recent_tasks_pipeline
            )
            logger.info("Created recent_tasks_view")
        except Exception as e:
            if 'already exists' not in str(e):
                logger.error(f"Failed to create recent_tasks_view: {str(e)}")
    
    async def verify_database_integrity(self):
        """Verify database setup and integrity"""
        issues = []
        
        # Check collections exist
        required_collections = [
            'sequences', 'annotations', 'analysis_tasks', 'analysis_results',
            'pipelines', 'pipeline_executions', 'users', 'organisms'
        ]
        
        existing_collections = await self.database.list_collection_names()
        missing_collections = set(required_collections) - set(existing_collections)
        
        if missing_collections:
            issues.append(f"Missing collections: {missing_collections}")
        
        # Check indexes exist
        for collection_name in required_collections:
            if collection_name in existing_collections:
                collection = self.database[collection_name]
                indexes = await collection.list_indexes().to_list(None)
                index_count = len(indexes)
                
                if index_count < 2:  # At least _id and one other index
                    issues.append(f"Collection {collection_name} has insufficient indexes: {index_count}")
        
        # Check sample data exists
        sequences_count = await self.database.sequences.count_documents({})
        if sequences_count == 0:
            issues.append("No sequences found in database")
        
        organisms_count = await self.database.organisms.count_documents({})
        if organisms_count == 0:
            issues.append("No organisms found in database")
        
        if issues:
            logger.warning(f"Database integrity issues found: {issues}")
            return False, issues
        else:
            logger.info("Database integrity verification passed")
            return True, []
    
    async def get_database_statistics(self) -> Dict:
        """Get comprehensive database statistics"""
        stats = {}
        
        collections = ['sequences', 'annotations', 'analysis_tasks', 'analysis_results', 
                      'pipelines', 'pipeline_executions', 'users', 'organisms']
        
        for collection_name in collections:
            collection = self.database[collection_name]
            count = await collection.count_documents({})
            
            # Get collection stats
            collection_stats = await self.database.command('collStats', collection_name)
            
            stats[collection_name] = {
                'count': count,
                'size_bytes': collection_stats.get('size', 0),
                'avg_obj_size': collection_stats.get('avgObjSize', 0),
                'index_count': collection_stats.get('nindexes', 0),
                'total_index_size': collection_stats.get('totalIndexSize', 0)
            }
        
        # Database-wide statistics
        db_stats = await self.database.command('dbStats')
        stats['database'] = {
            'total_size': db_stats.get('dataSize', 0),
            'storage_size': db_stats.get('storageSize', 0),
            'index_size': db_stats.get('indexSize', 0),
            'collections': db_stats.get('collections', 0),
            'objects': db_stats.get('objects', 0)
        }
        
        return stats


# CLI script for database initialization
async def main():
    import argparse
    import os
    
    parser = argparse.ArgumentParser(description='Initialize UGENE Web Platform database')
    parser.add_argument('--reset', action='store_true', help='Reset database (WARNING: destroys all data)')
    parser.add_argument('--verify', action='store_true', help='Verify database integrity')
    parser.add_argument('--stats', action='store_true', help='Show database statistics')
    parser.add_argument('--mongodb-url', default=os.getenv('MONGODB_URL', 'mongodb://localhost:27017'))
    parser.add_argument('--database-name', default=os.getenv('DATABASE_NAME', 'ugene_bioinformatics'))
    
    args = parser.parse_args()
    
    # Setup logging
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    try:
        # Initialize database manager
        db_manager = DatabaseManager(args.mongodb_url, args.database_name)
        await db_manager.initialize_database()
        
        initializer = DatabaseInitializer(db_manager)
        
        if args.reset:
            confirm = input("WARNING: This will delete ALL data. Type 'YES' to confirm: ")
            if confirm == 'YES':
                await initializer.initialize_database(reset=True)
            else:
                print("Reset cancelled")
                return
        elif args.verify:
            is_healthy, issues = await initializer.verify_database_integrity()
            if is_healthy:
                print("✅ Database integrity check passed")
            else:
                print("❌ Database integrity issues found:")
                for issue in issues:
                    print(f"  - {issue}")
        elif args.stats:
            stats = await initializer.get_database_statistics()
            print("📊 Database Statistics:")
            for collection, data in stats.items():
                if collection != 'database':
                    print(f"  {collection}: {data['count']} documents, {data['size_bytes']} bytes")
                else:
                    print(f"  Total: {data['objects']} objects, {data['total_size']} bytes")
        else:
            await initializer.initialize_database()
            
            # Verify setup
            is_healthy, issues = await initializer.verify_database_integrity()
            if is_healthy:
                print("✅ Database initialized successfully")
            else:
                print("⚠️  Database initialized with issues:")
                for issue in issues:
                    print(f"  - {issue}")
        
        await db_manager.close_connection()
        
    except Exception as e:
        logger.error(f"Database initialization failed: {str(e)}")
        raise

if __name__ == '__main__':
    asyncio.run(main())