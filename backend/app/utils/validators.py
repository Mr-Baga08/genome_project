# backend/app/utils/validators.py
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, ValidationError

class WorkflowValidator:
    """Validate workflow definitions"""
    
    def __init__(self):
        self.supported_node_types = {
            'reader', 'writer', 'aligner', 'tree', 'blast', 'filter', 
            'converter', 'assembler', 'analyzer', 'visualizer'
        }
    
    def validate_workflow(self, workflow_definition: Dict[str, Any]) -> Dict[str, Any]:
        """Validate workflow definition and return validation result"""
        errors = []
        warnings = []
        
        # Check required fields
        if 'nodes' not in workflow_definition:
            errors.append("Workflow must contain 'nodes' field")
        
        if 'connections' not in workflow_definition:
            errors.append("Workflow must contain 'connections' field")
        
        if errors:
            return {'valid': False, 'errors': errors, 'warnings': warnings}
        
        nodes = workflow_definition['nodes']
        connections = workflow_definition['connections']
        
        # Validate nodes
        node_errors, node_warnings = self._validate_nodes(nodes)
        errors.extend(node_errors)
        warnings.extend(node_warnings)
        
        # Validate connections
        conn_errors, conn_warnings = self._validate_connections(connections, nodes)
        errors.extend(conn_errors)
        warnings.extend(conn_warnings)
        
        # Check for cycles
        if self._has_cycles(nodes, connections):
            errors.append("Workflow contains circular dependencies")
        
        # Check for disconnected components
        disconnected = self._find_disconnected_components(nodes, connections)
        if disconnected:
            warnings.append(f"Found {len(disconnected)} disconnected components")
        
        return {
            'valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings
        }
    
    def _validate_nodes(self, nodes: List[Dict[str, Any]]) -> tuple:
        """Validate individual nodes"""
        errors = []
        warnings = []
        node_ids = set()
        
        for i, node in enumerate(nodes):
            # Check required fields
            if 'id' not in node:
                errors.append(f"Node {i}: Missing 'id' field")
                continue
            
            node_id = node['id']
            if node_id in node_ids:
                errors.append(f"Node {i}: Duplicate ID '{node_id}'")
            node_ids.add(node_id)
            
            if 'name' not in node:
                warnings.append(f"Node {node_id}: Missing 'name' field")
            
            if 'type' not in node:
                warnings.append(f"Node {node_id}: Missing 'type' field")
            elif node['type'] not in self.supported_node_types:
                warnings.append(f"Node {node_id}: Unknown type '{node['type']}'")
        
        return errors, warnings
    
    def _validate_connections(self, connections: List[Dict[str, Any]], nodes: List[Dict[str, Any]]) -> tuple:
        """Validate connections between nodes"""
        errors = []
        warnings = []
        node_ids = {node['id'] for node in nodes}
        
        for i, conn in enumerate(connections):
            if 'from' not in conn or 'to' not in conn:
                errors.append(f"Connection {i}: Missing 'from' or 'to' field")
                continue
            
            from_id = conn['from']
            to_id = conn['to']
            
            if from_id not in node_ids:
                errors.append(f"Connection {i}: Source node '{from_id}' does not exist")
            
            if to_id not in node_ids:
                errors.append(f"Connection {i}: Target node '{to_id}' does not exist")
            
            if from_id == to_id:
                errors.append(f"Connection {i}: Self-loop detected on node '{from_id}'")
        
        return errors, warnings
    
    def _has_cycles(self, nodes: List[Dict[str, Any]], connections: List[Dict[str, Any]]) -> bool:
        """Check for cycles in the workflow graph"""
        # Build adjacency list
        graph = {node['id']: [] for node in nodes}
        for conn in connections:
            if conn['from'] in graph and conn['to'] in graph:
                graph[conn['from']].append(conn['to'])
        
        # DFS to detect cycles
        visited = set()
        rec_stack = set()
        
        def has_cycle_util(node):
            visited.add(node)
            rec_stack.add(node)
            
            for neighbor in graph.get(node, []):
                if neighbor not in visited:
                    if has_cycle_util(neighbor):
                        return True
                elif neighbor in rec_stack:
                    return True
            
            rec_stack.remove(node)
            return False
        
        for node_id in graph:
            if node_id not in visited:
                if has_cycle_util(node_id):
                    return True
        
        return False
    
    def _find_disconnected_components(self, nodes: List[Dict[str, Any]], connections: List[Dict[str, Any]]) -> List[List[str]]:
        """Find disconnected components in the workflow"""
        # Build undirected graph
        graph = {node['id']: set() for node in nodes}
        for conn in connections:
            if conn['from'] in graph and conn['to'] in graph:
                graph[conn['from']].add(conn['to'])
                graph[conn['to']].add(conn['from'])
        
        visited = set()
        components = []
        
        def dfs(node, component):
            visited.add(node)
            component.append(node)
            for neighbor in graph[node]:
                if neighbor not in visited:
                    dfs(neighbor, component)
        
        for node_id in graph:
            if node_id not in visited:
                component = []
                dfs(node_id, component)
                if len(component) > 1:  # Only count components with multiple nodes
                    components.append(component)
        
        return components
