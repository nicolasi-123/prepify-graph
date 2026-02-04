# -*- coding: utf-8 -*-
import requests
import json
from typing import Dict, List, Optional

class CzechRegistryFetcher:
    """Fetches data from Czech Business Registry API"""
    
    def __init__(self):
        self.base_url = "https://dataor.justice.cz/api/3/action"
        
    def fetch_registry_data(self) -> Optional[Dict]:
        """Fetch complete registry dataset"""
        try:
            # Get package list
            response = requests.get(f"{self.base_url}/package_list")
            response.raise_for_status()
            packages = response.json()
            
            if packages.get('success'):
                # Get the latest package
                package_name = packages['result'][0] if packages['result'] else None
                if package_name:
                    return self.fetch_package_data(package_name)
            return None
        except Exception as e:
            print(f"Error fetching registry data: {e}")
            return None
    
    def fetch_package_data(self, package_name: str) -> Optional[Dict]:
        """Fetch specific package data"""
        try:
            response = requests.get(
                f"{self.base_url}/package_show",
                params={'id': package_name}
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Error fetching package {package_name}: {e}")
            return None

class ISIRFetcher:
    """Fetches data from Czech Insolvency Registry"""
    
    def __init__(self):
        self.base_url = "https://isir.justice.cz/isir/api"
        
    def search_by_ico(self, ico: str) -> Optional[Dict]:
        """Search insolvency by company ID (IČO)"""
        try:
            # ISIR API endpoint - will be implemented
            # For now, placeholder
            return {"ico": ico, "insolvencies": []}
        except Exception as e:
            print(f"Error fetching ISIR data: {e}")
            return None

class InternationalRegistryFetcher:
    """Fetches data from international registries (Cyprus, Netherlands)"""
    
    def __init__(self):
        self.opencorporates_url = "https://api.opencorporates.com/v0.4"
        
    def fetch_cyprus_data(self, company_name: str) -> Optional[Dict]:
        """Fetch Cyprus registry data via OpenCorporates"""
        try:
            response = requests.get(
                f"{self.opencorporates_url}/companies/search",
                params={
                    'q': company_name,
                    'jurisdiction_code': 'cy'
                }
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Error fetching Cyprus data: {e}")
            return None
    
    def fetch_netherlands_data(self, company_name: str) -> Optional[Dict]:
        """Fetch Netherlands registry data via OpenCorporates"""
        try:
            response = requests.get(
                f"{self.opencorporates_url}/companies/search",
                params={
                    'q': company_name,
                    'jurisdiction_code': 'nl'
                }
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Error fetching Netherlands data: {e}")
            return None