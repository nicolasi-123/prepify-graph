# -*- coding: utf-8 -*-
import networkx as nx
from typing import List, Dict, Tuple, Optional

class GraphBuilder:
    """Builds and queries the relationship graph"""
    
    def __init__(self):
        self.graph = nx.Graph()
        print(f"[GraphBuilder] New instance created - ID: {id(self)}")
        
    def add_entity(self, entity_id: str, entity_data: Dict):
        """Add entity (company or person) to graph"""
        self.graph.add_node(
            entity_id,
            name=entity_data.get('name', ''),
            type=entity_data.get('type', 'unknown'),
            city=entity_data.get('city', ''),
            country=entity_data.get('country', 'CZ'),
            insolvent=entity_data.get('insolvent', False),
            data=entity_data
        )
    
    def add_relationship(self, entity1_id: str, entity2_id: str,
                        relationship_type: str, metadata: Dict = None):
        """Add relationship between two entities"""
        if metadata is None:
            metadata = {}

        self.graph.add_edge(
            entity1_id,
            entity2_id,
            type=relationship_type,
            active=metadata.get('active', True),
            metadata=metadata
        )
    
    def find_shortest_path(self, source_id: str, target_id: str) -> Optional[List[str]]:
        """Find shortest path between two entities"""
        try:
            return nx.shortest_path(self.graph, source=source_id, target=target_id)
        except nx.NetworkXNoPath:
            print(f"No path found between {source_id} and {target_id}")
            return None
        except nx.NodeNotFound as e:
            print(f"Node not found: {e}")
            return None
    
    def find_top_k_paths(self, source_id: str, target_id: str, k: int = 3) -> List[List[str]]:
        """Find top k shortest paths between two entities"""
        try:
            paths = list(nx.shortest_simple_paths(self.graph, source=source_id, target=target_id))
            return paths[:k]
        except nx.NetworkXNoPath:
            print(f"No path found between {source_id} and {target_id}")
            return []
        except nx.NodeNotFound as e:
            print(f"Node not found: {e}")
            return []

    def find_multi_point_path(self, waypoints: List[str]) -> Optional[List[str]]:
        """Find shortest path through multiple waypoints in order"""
        if len(waypoints) < 2:
            print("Need at least 2 waypoints")
            return None

        combined_path = []

        # Find path between each consecutive pair of waypoints
        for i in range(len(waypoints) - 1):
            source = waypoints[i]
            target = waypoints[i + 1]

            try:
                segment = nx.shortest_path(self.graph, source=source, target=target)

                # Add segment to combined path, avoiding duplicates at connection points
                if i == 0:
                    combined_path.extend(segment)
                else:
                    # Skip first node of segment (it's the last node of previous segment)
                    combined_path.extend(segment[1:])

            except nx.NetworkXNoPath:
                print(f"No path found between {source} and {target}")
                return None
            except nx.NodeNotFound as e:
                print(f"Node not found: {e}")
                return None

        return combined_path
    
    def get_path_details(self, path: List[str]) -> List[Dict]:
        """Get detailed information about entities in a path"""
        details = []
        for i, node_id in enumerate(path):
            node_data = self.graph.nodes[node_id]
            detail = {
                'id': node_id,
                'name': node_data.get('name', ''),
                'type': node_data.get('type', ''),
                'position': i
            }
            
            # Add edge info if not last node
            if i < len(path) - 1:
                edge_data = self.graph.edges[node_id, path[i + 1]]
                detail['relationship_to_next'] = edge_data.get('type', '')
            
            details.append(detail)
        
        return details
    
    def get_graph_stats(self) -> Dict:
        """Get statistics about the graph"""
        return {
            'total_nodes': self.graph.number_of_nodes(),
            'total_edges': self.graph.number_of_edges(),
            'is_connected': nx.is_connected(self.graph) if len(self.graph) > 0 else False
        }
    
    def export_subgraph(self, path: List[str], depth: int = 1) -> Dict:
        """Export subgraph around a path for visualization"""
        # Get all nodes in path plus their neighbors up to depth
        nodes_to_include = set(path)
        
        for node in path:
            neighbors = nx.single_source_shortest_path_length(
                self.graph, node, cutoff=depth
            )
            nodes_to_include.update(neighbors.keys())
        
        # Create subgraph
        subgraph = self.graph.subgraph(nodes_to_include)
        
        # Convert to format suitable for Cytoscape.js
        nodes = []
        edges = []
        
        for node_id in subgraph.nodes():
            node_data = subgraph.nodes[node_id]
            nodes.append({
                'data': {
                    'id': node_id,
                    'label': node_data.get('name', node_id),
                    'type': node_data.get('type', 'unknown'),
                    'in_path': node_id in path,
                    'insolvent': node_data.get('insolvent', False),
                    'country': node_data.get('country', 'CZ'),
                    'city': node_data.get('city', '')
                }
            })
        
        for edge in subgraph.edges():
            edge_data = subgraph.edges[edge]
            edges.append({
                'data': {
                    'source': edge[0],
                    'target': edge[1],
                    'type': edge_data.get('type', 'unknown'),
                    'active': edge_data.get('active', True),
                    'in_path': edge[0] in path and edge[1] in path
                }
            })
        
        return {'nodes': nodes, 'edges': edges}

    def clear(self):
        """Clear the graph"""
        import traceback
        print(f"[GraphBuilder] GRAPH CLEARED! Stack trace:")
        traceback.print_stack()
        self.graph.clear()