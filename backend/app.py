# -*- coding: utf-8 -*-
from flask import Flask, request, jsonify
from flask_cors import CORS
from graph_builder import GraphBuilder
from data_fetcher import CzechRegistryFetcher, ISIRFetcher, InternationalRegistryFetcher
from or_parser import or_parser
import json

app = Flask(__name__)
CORS(app)  # Enable CORS for frontend

# Initialize components
graph_builder = GraphBuilder()
cz_fetcher = CzechRegistryFetcher()
isir_fetcher = ISIRFetcher()
intl_fetcher = InternationalRegistryFetcher()

# Sample data for testing (will be replaced with real data)
def load_sample_data():
    """Load sample Czech business registry data"""
    print("=" * 50)
    print("Loading data into graph...")
    print("=" * 50)
    
    # Try to load real data from OR first
    try:
        import or_parser as parser_module
        print("✓ OR parser module imported successfully")
        
        print("Attempting to fetch real data from OR justice.cz...")
        real_data = parser_module.or_parser.fetch_sample_data(max_companies=100)
        
        print(f"Fetched {len(real_data.get('companies', []))} companies")
        print(f"Fetched {len(real_data.get('relationships', []))} relationships")
        
        if real_data['companies']:
            print(f"Loading {len(real_data['companies'])} companies into graph...")
            
            # Add companies to graph
            for i, company in enumerate(real_data['companies']):
                graph_builder.add_entity(company['id'], company)
                if i < 5:  # Print first 5
                    print(f"  Added: {company['name']} ({company['id']})")
            
            # Add relationships if any
            print(f"Loading {len(real_data.get('relationships', []))} relationships...")
            for i, rel in enumerate(real_data.get('relationships', [])):
                graph_builder.add_relationship(
                    rel['source'],
                    rel['target'],
                    rel['type']
                )
                if i < 5:  # Print first 5
                    print(f"  Added: {rel['source']} --[{rel['type']}]--> {rel['target']}")
            
            stats = graph_builder.get_graph_stats()
            print("=" * 50)
            print(f"✓ Real data loaded successfully!")
            print(f"  Total nodes: {stats['total_nodes']}")
            print(f"  Total edges: {stats['total_edges']}")
            print("=" * 50)
            return
            
    except ImportError as e:
        print(f"✗ Import error: {e}")
        print("  or_parser module not found - using fallback data")
    except Exception as e:
        print(f"✗ Could not load real data: {e}")
        print(f"  Error type: {type(e).__name__}")
        import traceback
        traceback.print_exc()
        print("  Falling back to sample data...")
    
    # Fallback: Sample entities
    print("Loading fallback sample data...")
    entities = [
        {"id": "00012345", "name": "ABC s.r.o.", "type": "company"},
        {"id": "00067891", "name": "XYZ a.s.", "type": "company"},
        {"id": "RC123456", "name": "Jan Novák", "type": "person"},
        {"id": "RC789012", "name": "Petr Svoboda", "type": "person"},
        {"id": "00054321", "name": "DEF s.r.o.", "type": "company"},
    ]
    
    for entity in entities:
        graph_builder.add_entity(entity["id"], entity)
    
    relationships = [
        ("RC123456", "00012345", "jednatel"),
        ("00012345", "00067891", "společník"),
        ("RC789012", "00067891", "jednatel"),
        ("RC123456", "00054321", "společník"),
        ("00054321", "RC789012", "vlastník"),
    ]
    
    for source, target, rel_type in relationships:
        graph_builder.add_relationship(source, target, rel_type)
    
    print("Sample data loaded (fallback)")



@app.route('/')
def home():
    """API home endpoint"""
    return jsonify({
        "name": "Prepify Graph API",
        "version": "1.0.0",
        "endpoints": {
            "/api/search": "Search for entities",
            "/api/shortest-path": "Find shortest path between two entities",
            "/api/top-paths": "Find top K shortest paths",
            "/api/graph-stats": "Get graph statistics"
        }
    })

@app.route('/api/search', methods=['GET'])
def search_entities():
    """Search for entities by name, ID, or city"""
    query = request.args.get('q', '').lower()
    
    if not query:
        return jsonify({"error": "Query parameter 'q' is required"}), 400
    
    results = []
    seen_ids = set()
    
    print(f"Searching for: {query}")
    print(f"Total nodes in graph: {graph_builder.graph.number_of_nodes()}")
    
    for node_id in graph_builder.graph.nodes():
        node_data = graph_builder.graph.nodes[node_id]
        name = str(node_data.get('name', '')).lower()
        city = str(node_data.get('city', '')).lower()
        node_id_lower = str(node_id).lower()
        
        # Search by name, ID, or city
        if query in name or query in node_id_lower or query in city:
            if node_id not in seen_ids:
                entity_type = node_data.get('type', 'unknown')
                
                result = {
                    'id': node_id,
                    'name': node_data.get('name', 'Unknown'),
                    'type': entity_type,
                    'city': node_data.get('city', ''),
                    'insolvent': node_data.get('insolvent', False),
                    'country': node_data.get('country', 'CZ')
                }
                results.append(result)
                seen_ids.add(node_id)
                print(f"Found match: {result['name']} ({node_id})")
    
    # Sort results: exact matches first, then by name
    results.sort(key=lambda x: (
        not x['name'].lower().startswith(query),  # Exact matches first
        x['name'].lower()
    ))
    
    print(f"Returning {len(results)} results")
    return jsonify({"results": results[:20]})  # Limit to 20 results

@app.route('/api/shortest-path', methods=['POST'])
def find_shortest_path():
    """Find shortest path between two entities"""
    data = request.json
    
    source_id = data.get('source')
    target_id = data.get('target')
    
    if not source_id or not target_id:
        return jsonify({"error": "Both 'source' and 'target' are required"}), 400
    
    # Find shortest path
    path = graph_builder.find_shortest_path(source_id, target_id)
    
    if not path:
        return jsonify({
            "found": False,
            "message": f"No path found between {source_id} and {target_id}"
        })
    
    # Get path details
    path_details = graph_builder.get_path_details(path)
    
    # Export subgraph for visualization
    subgraph = graph_builder.export_subgraph(path, depth=1)
    
    return jsonify({
        "found": True,
        "path": path,
        "path_length": len(path) - 1,  # Number of edges
        "details": path_details,
        "subgraph": subgraph
    })

@app.route('/api/top-paths', methods=['POST'])
def find_top_paths():
    """Find top K shortest paths between two entities"""
    data = request.json
    
    source_id = data.get('source')
    target_id = data.get('target')
    k = data.get('k', 3)
    exclude_insolvent = data.get('exclude_insolvent', False)
    exclude_foreign = data.get('exclude_foreign', False)
    
    if not source_id or not target_id:
        return jsonify({"error": "Both 'source' and 'target' are required"}), 400
    
    # Find top K paths
    paths = graph_builder.find_top_k_paths(source_id, target_id, k)
    
    if not paths:
        return jsonify({
            "found": False,
            "message": f"No paths found between {source_id} and {target_id}"
        })
    
    # Filter paths based on criteria
    filtered_paths = []
    for path in paths:
        path_valid = True
        
        # Check each node in path
        for node_id in path:
            node_data = graph_builder.graph.nodes[node_id]
            
            # Skip insolvent entities if filter is on
            if exclude_insolvent and node_data.get('insolvent', False):
                path_valid = False
                break
            
            # Skip foreign entities if filter is on
            if exclude_foreign and node_data.get('country', 'CZ') != 'CZ':
                path_valid = False
                break
        
        if path_valid:
            filtered_paths.append(path)
    
    if not filtered_paths:
        return jsonify({
            "found": False,
            "message": "No paths found matching your filter criteria"
        })
    
    # Get details for each path
    paths_with_details = []
    for path in filtered_paths:
        paths_with_details.append({
            "path": path,
            "length": len(path) - 1,
            "details": graph_builder.get_path_details(path)
        })
    
    # Export subgraph with all paths
    all_nodes = set()
    for path in filtered_paths:
        all_nodes.update(path)
    
    subgraph = graph_builder.export_subgraph(list(all_nodes), depth=0)
    
    # Add insolvent and country info to subgraph nodes
    for node in subgraph['nodes']:
        node_id = node['data']['id']
        node_data = graph_builder.graph.nodes[node_id]
        node['data']['insolvent'] = node_data.get('insolvent', False)
        node['data']['country'] = node_data.get('country', 'CZ')
    
    return jsonify({
        "found": True,
        "count": len(filtered_paths),
        "paths": paths_with_details,
        "subgraph": subgraph
    })

@app.route('/api/graph-stats', methods=['GET'])
def get_graph_stats():
    """Get graph statistics"""
    stats = graph_builder.get_graph_stats()
    return jsonify(stats)

@app.route('/api/entities/<entity_id>', methods=['GET'])
def get_entity_details(entity_id):
    """Get detailed information about a specific entity"""
    if entity_id not in graph_builder.graph.nodes():
        return jsonify({"error": "Entity not found"}), 404
    
    node_data = graph_builder.graph.nodes[entity_id]
    
    # Get neighbors
    neighbors = list(graph_builder.graph.neighbors(entity_id))
    neighbor_details = []
    
    for neighbor_id in neighbors:
        neighbor_data = graph_builder.graph.nodes[neighbor_id]
        edge_data = graph_builder.graph.edges[entity_id, neighbor_id]
        
        neighbor_details.append({
            'id': neighbor_id,
            'name': neighbor_data.get('name', ''),
            'type': neighbor_data.get('type', ''),
            'relationship': edge_data.get('type', '')
        })
    
    return jsonify({
        'id': entity_id,
        'name': node_data.get('name', ''),
        'type': node_data.get('type', ''),
        'neighbors': neighbor_details,
        'neighbor_count': len(neighbors)
    })

@app.route('/api/debug/reload', methods=['POST'])
def debug_reload():
    """Debug endpoint to reload data"""
    graph_builder.graph.clear()
    load_sample_data()
    stats = graph_builder.get_graph_stats()
    return jsonify({
        "reloaded": True,
        "stats": stats
    })

    # Load sample data on startup (only once)
if graph_builder.graph.number_of_nodes() == 0:
    load_sample_data()
else:
    print(f"Graph already loaded with {graph_builder.graph.number_of_nodes()} nodes")

if __name__ == '__main__':
    import os
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=False, host='0.0.0.0', port=port)
