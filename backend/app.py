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
    print("Loading data into graph...")
    
    # Try to load real data from OR first
    try:
        from or_parser import or_parser
        print("Attempting to fetch real data from OR justice.cz...")
        real_data = or_parser.fetch_sample_data(max_companies=100)
        
        if real_data['companies']:
            print(f"Loaded {len(real_data['companies'])} real companies from OR")
            
            # Add companies to graph
            for company in real_data['companies']:
                graph_builder.add_entity(company['id'], company)
            
            # Add relationships if any
            for rel in real_data.get('relationships', []):
                graph_builder.add_relationship(
                    rel['source'],
                    rel['target'],
                    rel['type']
                )
            
            print("Real data loaded successfully!")
            return
    except Exception as e:
        print(f"Could not load real data: {e}")
        print("Falling back to sample data...")
    
    # Fallback: Sample entities
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
    
    print("Sample data loaded")

# Load sample data on startup
load_sample_data()

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
    
    for node_id in graph_builder.graph.nodes():
        node_data = graph_builder.graph.nodes[node_id]
        name = node_data.get('name', '').lower()
        city = node_data.get('city', '').lower()
        
        # Search by name, ID, or city
        if query in name or query in node_id.lower() or query in city:
            if node_id not in seen_ids:
                results.append({
                    'id': node_id,
                    'name': node_data.get('name', ''),
                    'type': node_data.get('type', ''),
                    'city': node_data.get('city', '')
                })
                seen_ids.add(node_id)
    
    # Sort results: exact matches first, then by name
    results.sort(key=lambda x: (
        not x['name'].lower().startswith(query),  # Exact matches first
        x['name'].lower()
    ))
    
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
    k = data.get('k', 3)  # Default to top 3 paths
    
    if not source_id or not target_id:
        return jsonify({"error": "Both 'source' and 'target' are required"}), 400
    
    # Find top K paths
    paths = graph_builder.find_top_k_paths(source_id, target_id, k)
    
    if not paths:
        return jsonify({
            "found": False,
            "message": f"No paths found between {source_id} and {target_id}"
        })
    
    # Get details for each path
    paths_with_details = []
    for path in paths:
        paths_with_details.append({
            "path": path,
            "length": len(path) - 1,
            "details": graph_builder.get_path_details(path)
        })
    
    # Export subgraph with all paths
    all_nodes = set()
    for path in paths:
        all_nodes.update(path)
    
    subgraph = graph_builder.export_subgraph(list(all_nodes), depth=0)
    
    return jsonify({
        "found": True,
        "count": len(paths),
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

@app.route('/api/reload-data', methods=['POST'])
def reload_data():
    """Reload data from OR justice.cz"""
    try:
        data = request.json or {}
        max_companies = data.get('max_companies', 500)
        
        # Clear existing graph
        graph_builder.graph.clear()
        
        # Fetch new data
        real_data = or_parser.fetch_sample_data(max_companies=max_companies)
        
        # Add to graph
        for company in real_data['companies']:
            graph_builder.add_entity(company['id'], company)
        
        for rel in real_data.get('relationships', []):
            graph_builder.add_relationship(
                rel['source'],
                rel['target'],
                rel['type']
            )
        
        stats = graph_builder.get_graph_stats()
        
        return jsonify({
            "success": True,
            "message": f"Loaded {len(real_data['companies'])} companies",
            "stats": stats
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

if __name__ == '__main__':
    import os
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=False, host='0.0.0.0', port=port)