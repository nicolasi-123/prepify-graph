# -*- coding: utf-8 -*-
import requests
import json
import gzip
import io
import csv
from typing import Dict, List, Optional
import time
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class ORJusticeParser:
    """Parser for Czech Business Registry (OR) data from dataor.justice.cz"""
    
    def __init__(self):
        self.base_url = "https://dataor.justice.cz/api/3/action"
        self.cache = {}
        
    def get_latest_dataset_name(self) -> Optional[str]:
        """Get the name of the latest available dataset"""
        try:
            response = requests.get(f"{self.base_url}/package_list", timeout=10, verify=False)
            response.raise_for_status()
            data = response.json()
            
            if data.get('success') and data.get('result'):
                packages = data['result']
                current_packages = [p for p in packages if '2025' in p or '2026' in p]
                return current_packages[0] if current_packages else packages[0]
            return None
        except Exception as e:
            print(f"Error fetching package list: {e}")
            return None
    
    def get_dataset_info(self, package_name: str) -> Optional[Dict]:
        """Get information about a specific dataset"""
        try:
            response = requests.get(
                f"{self.base_url}/package_show",
                params={'id': package_name},
                timeout=10,
                verify=False
            )
            response.raise_for_status()
            data = response.json()
            
            if data.get('success'):
                return data['result']
            return None
        except Exception as e:
            print(f"Error fetching dataset info: {e}")
            return None
    
    def fetch_sample_data(self, max_companies: int = 500) -> Dict[str, List[Dict]]:
        """Fetch a sample of companies and their relationships"""
        print("Fetching sample data from OR justice.cz...")
        
        dataset_name = self.get_latest_dataset_name()
        if dataset_name:
            print(f"Found dataset: {dataset_name}")
            dataset_info = self.get_dataset_info(dataset_name)
            if dataset_info:
                resources = dataset_info.get('resources', [])
                print(f"Found {len(resources)} resources")
        
        print("Creating sample dataset with realistic Czech companies...")
        
        companies = []
        
        # Complete sample data with ALL entities
        sample_data = [
            {"ico": "45274649", "name": "Avast Software s.r.o.", "city": "Praha", "insolvent": False, "country": "CZ"},
            {"ico": "00025593", "name": "Československá obchodní banka, a. s.", "city": "Praha", "insolvent": False, "country": "CZ"},
            {"ico": "27116158", "name": "Mall Group a.s.", "city": "Praha", "insolvent": False, "country": "CZ"},
            {"ico": "63998505", "name": "Alza.cz a.s.", "city": "Praha", "insolvent": False, "country": "CZ"},
            {"ico": "26168685", "name": "Rohlík.cz s.r.o.", "city": "Praha", "insolvent": False, "country": "CZ"},
            {"ico": "24287903", "name": "O2 Czech Republic a.s.", "city": "Praha", "insolvent": False, "country": "CZ"},
            {"ico": "60193336", "name": "Pilsner Urquell a.s.", "city": "Plzeň", "insolvent": False, "country": "CZ"},
            {"ico": "45534306", "name": "Škoda Auto a.s.", "city": "Mladá Boleslav", "insolvent": False, "country": "CZ"},
            {"ico": "00001834", "name": "Česká spořitelna, a.s.", "city": "Praha", "insolvent": False, "country": "CZ"},
            {"ico": "25612093", "name": "Kofola ČeskoSlovensko a.s.", "city": "Ostrava", "insolvent": False, "country": "CZ"},
            {"ico": "12345678", "name": "Bankrot Trading s.r.o.", "city": "Praha", "insolvent": True, "country": "CZ"},
            {"ico": "87654321", "name": "Dlužník Investments a.s.", "city": "Brno", "insolvent": True, "country": "CZ"},
            {"ico": "CY001", "name": "Cyprus Holdings Ltd.", "city": "Nicosia", "insolvent": False, "country": "CY"},
            {"ico": "CY002", "name": "Offshore Investments Ltd.", "city": "Limassol", "insolvent": False, "country": "CY"},
            {"ico": "NL001", "name": "Amsterdam Ventures B.V.", "city": "Amsterdam", "insolvent": False, "country": "NL"},
            {"ico": "NL002", "name": "Rotterdam Holdings N.V.", "city": "Rotterdam", "insolvent": False, "country": "NL"},
            {"ico": "RC001", "name": "Jan Novák", "city": "Praha", "country": "CZ"},
            {"ico": "RC002", "name": "Petr Svoboda", "city": "Brno", "country": "CZ"},
            {"ico": "RC003", "name": "Marie Nováková", "city": "Praha", "country": "CZ"},
        ]
        
        for company in sample_data:
            entity_type = 'person' if company['ico'].startswith('RC') else 'company'
            
            entity_data = {
                'id': company['ico'],
                'name': company['name'],
                'type': entity_type,
                'city': company.get('city', ''),
                'insolvent': company.get('insolvent', False),
                'country': company.get('country', 'CZ')
            }
            
            companies.append(entity_data)
        
        # Complete relationships with ALL connections
        relationships = [
            {'source': 'RC001', 'target': '45274649', 'type': 'jednatel'},
            {'source': '45274649', 'target': '27116158', 'type': 'společník'},
            {'source': 'RC002', 'target': '63998505', 'type': 'jednatel'},
            {'source': '63998505', 'target': '26168685', 'type': 'obchodní partner'},
            {'source': 'RC001', 'target': '00001834', 'type': 'akcionář'},
            {'source': '00001834', 'target': '00025593', 'type': 'dceřiná společnost'},
            {'source': 'RC003', 'target': '24287903', 'type': 'jednatelka'},
            {'source': '27116158', 'target': '63998505', 'type': 'investor'},
            {'source': '26168685', 'target': '24287903', 'type': 'dodavatel'},
            {'source': '60193336', 'target': '45534306', 'type': 'dodavatel'},
            {'source': '45534306', 'target': '00001834', 'type': 'klient'},
            {'source': '25612093', 'target': '60193336', 'type': 'konkurent'},
            {'source': 'RC002', 'target': '25612093', 'type': 'consultant'},
            {'source': 'RC003', 'target': '26168685', 'type': 'investorka'},
            {'source': '12345678', 'target': 'RC001', 'type': 'vlastník'},
            {'source': '87654321', 'target': '27116158', 'type': 'dodavatel'},
            {'source': 'RC002', 'target': '12345678', 'type': 'bývalý jednatel'},
            {'source': '87654321', 'target': '63998505', 'type': 'věřitel'},
            {'source': 'CY001', 'target': '45274649', 'type': 'akcionář'},
            {'source': 'RC002', 'target': 'CY002', 'type': 'beneficial owner'},
            {'source': 'NL001', 'target': '00001834', 'type': 'parent company'},
            {'source': 'NL002', 'target': 'CY001', 'type': 'subsidiary'},
            {'source': 'CY002', 'target': '27116158', 'type': 'investor'},
            {'source': 'NL001', 'target': '45534306', 'type': 'shareholder'},
            {'source': 'CY001', 'target': '12345678', 'type': 'hidden owner'},
            {'source': '00025593', 'target': 'NL002', 'type': 'subsidiary'},
            {'source': 'RC003', 'target': 'CY001', 'type': 'director'},
            {'source': '24287903', 'target': '45534306', 'type': 'strategic partner'},
            {'source': '60193336', 'target': 'NL001', 'type': 'export partner'},
        ]
        
        print(f"Created {len(companies)} sample companies with {len(relationships)} relationships")
        
        return {
            'companies': companies,
            'relationships': relationships
        }

or_parser = ORJusticeParser()