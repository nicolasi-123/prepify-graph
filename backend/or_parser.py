# -*- coding: utf-8 -*-
import requests
import gzip
import io
import csv
import os
import platform
from typing import Dict, List, Optional, Tuple
import time
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def parse_java_map(s):
    """Parse Java Map.toString() format into Python dicts/lists.

    Handles: {key=value;key2={nested=val}} and [{...}, {...}] arrays.
    Used for the 'udaje' field in OR justice.cz CSV exports.
    """
    pos = [0]
    length = len(s)

    def skip_ws():
        while pos[0] < length and s[pos[0]] in ' \t\n\r':
            pos[0] += 1

    def parse_value():
        skip_ws()
        if pos[0] >= length:
            return ''
        c = s[pos[0]]
        if c == '{':
            return parse_map()
        elif c == '[':
            return parse_list()
        else:
            return parse_string()

    def parse_map():
        pos[0] += 1  # skip '{'
        result = {}
        skip_ws()
        if pos[0] < length and s[pos[0]] == '}':
            pos[0] += 1
            return result
        while pos[0] < length:
            skip_ws()
            key = parse_key()
            if not key:
                break
            skip_ws()
            if pos[0] < length and s[pos[0]] == '=':
                pos[0] += 1  # skip '='
                val = parse_value()
                result[key] = val
            skip_ws()
            if pos[0] < length and s[pos[0]] == ';':
                pos[0] += 1  # skip ';'
            elif pos[0] < length and s[pos[0]] == '}':
                pos[0] += 1  # skip '}'
                break
            else:
                break
        return result

    def parse_list():
        pos[0] += 1  # skip '['
        result = []
        skip_ws()
        if pos[0] < length and s[pos[0]] == ']':
            pos[0] += 1
            return result
        while pos[0] < length:
            skip_ws()
            val = parse_value()
            result.append(val)
            skip_ws()
            if pos[0] < length and s[pos[0]] == ',':
                pos[0] += 1  # skip ','
                skip_ws()
            elif pos[0] < length and s[pos[0]] == ']':
                pos[0] += 1  # skip ']'
                break
            else:
                break
        return result

    def parse_key():
        start = pos[0]
        while pos[0] < length and s[pos[0]] not in '=;{}[]':
            pos[0] += 1
        return s[start:pos[0]].strip()

    def parse_string():
        """Parse a string value - ends at ; , } or ] at current nesting depth.

        Uses lookahead for ';' and ',' to avoid splitting text values:
        - ';' is a separator only if followed by identifier= (map entry)
        - ',' is a separator only if followed by { or [ or ] (list item boundary)
        """
        start = pos[0]
        depth = 0
        while pos[0] < length:
            c = s[pos[0]]
            if c in '{[':
                depth += 1
            elif c in '}]':
                if depth > 0:
                    depth -= 1
                else:
                    break
            elif depth == 0 and c == ',':
                # Lookahead: list separator if followed by { or [ or ]
                j = pos[0] + 1
                while j < length and s[j] in ' \t\r\n':
                    j += 1
                if j < length and s[j] in '{[]':
                    break  # List separator
                else:
                    pos[0] += 1  # Part of text value (e.g. "Výroba, obchod")
                    continue
            elif depth == 0 and c == ';':
                # Lookahead: map separator if followed by identifier=
                j = pos[0] + 1
                while j < length and s[j] in ' \t\r\n':
                    j += 1
                k = j
                while k < length and (s[k].isalnum() or s[k] == '_'):
                    k += 1
                if k > j and k < length and s[k] == '=':
                    break  # Map entry separator
                else:
                    pos[0] += 1  # Part of text value
                    continue
            pos[0] += 1
        return s[start:pos[0]].strip()

    try:
        return parse_value()
    except Exception:
        return s  # Return raw string on parse failure


class ORJusticeParser:
    """Parser for Czech Business Registry (OR) data from dataor.justice.cz"""

    def __init__(self):
        self.base_url = "https://dataor.justice.cz/api/3/action"
        self.cache = {}
        self.isir_cache = {}  # Cache ISIR lookups
        self.opencorporates_cache = {}

        # CSV cache directory (external to project - data files are large)
        if platform.system() == 'Windows':
            self.cache_dir = os.path.join(os.environ.get('LOCALAPPDATA', 'C:\\prepify-data'), 'prepify', 'or-cache')
        else:
            self.cache_dir = '/var/cache/prepify/or-cache'

    def _get_cache_path(self, dataset_name: str) -> str:
        """Get cache file path for a dataset"""
        safe_name = dataset_name.replace('/', '_').replace('\\', '_')
        return os.path.join(self.cache_dir, f"{safe_name}.csv")

    def _is_cache_valid(self, cache_path: str, max_age_days: int = 7) -> bool:
        """Check if cached file exists and is recent enough"""
        if not os.path.exists(cache_path):
            return False
        age = time.time() - os.path.getmtime(cache_path)
        return age < max_age_days * 86400

    def parse_or_row(self, row: Dict) -> Tuple[Optional[Dict], List[Dict]]:
        """Parse a single OR CSV row, extracting company + relationships from udaje JSON.

        Returns:
            (company_dict, list_of_relationship_dicts)
        """
        ico = row.get('ico', '').strip()
        if not ico:
            return None, []

        company_name = row.get('nazev', row.get('obchodniJmeno', '')).strip()
        if not company_name:
            company_name = f"Společnost {ico}"

        # Parse udaje field (Java Map.toString() format, NOT JSON)
        udaje_raw = row.get('udaje', '')
        udaje = []
        if udaje_raw:
            try:
                parsed = parse_java_map(udaje_raw)
                if isinstance(parsed, list):
                    udaje = parsed
                elif isinstance(parsed, dict):
                    udaje = [parsed]
            except Exception:
                pass

        # Extract city from SIDLO entries (use latest non-deleted SIDLO)
        city = ''
        for item in udaje:
            if not isinstance(item, dict):
                continue
            typ = item.get('udajTyp', {})
            typ_kod = typ.get('kod', '') if isinstance(typ, dict) else ''
            if typ_kod == 'SIDLO' and not item.get('vymazDatum'):
                adresa = item.get('adresa', {})
                if isinstance(adresa, dict):
                    city = adresa.get('obec', '')
                break
        # Fallback: try flat CSV columns for city
        if not city:
            city = row.get('sidlo_nazevObce', row.get('mesto', '')).strip()

        company = {
            'id': ico,
            'name': company_name,
            'type': 'company',
            'city': city or 'neznámé',
            'country': 'CZ',
            'insolvent': False
        }

        relationships = []
        persons_found = {}  # {person_id: person_data}

        for item in udaje:
            if not isinstance(item, dict):
                continue
            typ = item.get('udajTyp', {})
            typ_kod = typ.get('kod', '') if isinstance(typ, dict) else ''

            # --- STATUTORY ORGAN (directors / jednatele / board members) ---
            if typ_kod == 'STATUTARNI_ORGAN':
                podudaje = item.get('podudaje', [])
                if not isinstance(podudaje, list):
                    continue
                for member in podudaje:
                    if not isinstance(member, dict):
                        continue
                    mt = member.get('udajTyp', {})
                    member_kod = mt.get('kod', '') if isinstance(mt, dict) else ''
                    if member_kod != 'STATUTARNI_ORGAN_CLEN':
                        continue

                    osoba = member.get('osoba', {})
                    if not osoba:
                        continue

                    jmeno = osoba.get('jmeno', '').strip()
                    prijmeni = osoba.get('prijmeni', '').strip()
                    narozDatum = osoba.get('narozDatum', '').strip()

                    if not prijmeni:
                        continue

                    person_id = f"RC_{prijmeni}_{jmeno}_{narozDatum}".replace(' ', '_')
                    is_active = not member.get('vymazDatum')

                    # Determine role (funkce is typically a plain string like "Jednatel")
                    funkce = member.get('funkce', '')
                    if isinstance(funkce, dict):
                        role = funkce.get('nazev', 'jednatel').lower()
                    elif isinstance(funkce, str) and funkce:
                        role = funkce.lower()
                    else:
                        role = 'jednatel'

                    persons_found[person_id] = {
                        'id': person_id,
                        'name': f"{jmeno} {prijmeni}".strip(),
                        'type': 'person',
                        'city': '',
                        'country': 'CZ',
                        'insolvent': False
                    }

                    relationships.append({
                        'source': person_id,
                        'target': ico,
                        'type': role or 'jednatel',
                        'active': is_active
                    })

            # --- SHAREHOLDERS (společníci) ---
            elif typ_kod == 'SPOLECNIK':
                spol_podudaje = item.get('podudaje', [])
                if not isinstance(spol_podudaje, list):
                    continue
                for spolecnik in spol_podudaje:
                    if not isinstance(spolecnik, dict):
                        continue
                    st = spolecnik.get('udajTyp', {})
                    spolecnik_kod = st.get('kod', '') if isinstance(st, dict) else ''
                    is_active = not spolecnik.get('vymazDatum')

                    if spolecnik_kod == 'SPOLECNIK_OSOBA':
                        # Natural person shareholder
                        osoba = spolecnik.get('osoba', {})
                        if not osoba:
                            continue

                        jmeno = osoba.get('jmeno', '').strip()
                        prijmeni = osoba.get('prijmeni', '').strip()
                        narozDatum = osoba.get('narozDatum', '').strip()

                        if not prijmeni:
                            continue

                        person_id = f"RC_{prijmeni}_{jmeno}_{narozDatum}".replace(' ', '_')

                        persons_found[person_id] = {
                            'id': person_id,
                            'name': f"{jmeno} {prijmeni}".strip(),
                            'type': 'person',
                            'city': '',
                            'country': 'CZ',
                            'insolvent': False
                        }

                        relationships.append({
                            'source': person_id,
                            'target': ico,
                            'type': 'společník',
                            'active': is_active
                        })

                    elif spolecnik_kod == 'SPOLECNIK_PRAVNICKA_OSOBA':
                        # Legal entity shareholder
                        pravnicka = spolecnik.get('pravnickaOsoba', {})
                        if not pravnicka:
                            continue

                        shareholder_ico = pravnicka.get('ico', '').strip()
                        if shareholder_ico:
                            relationships.append({
                                'source': shareholder_ico,
                                'target': ico,
                                'type': 'společník',
                                'active': is_active
                            })

        return company, relationships, persons_found

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

    def download_or_dataset(self, package_name: str) -> Optional[str]:
        """Download OR dataset CSV file"""
        print(f"Downloading dataset: {package_name}...")

        try:
            dataset_info = self.get_dataset_info(package_name)
            if not dataset_info:
                return None

            resources = dataset_info.get('resources', [])
            csv_resource = None

            # Find CSV resource (prefer CSV over XML for speed)
            for resource in resources:
                fmt = resource.get('format', '').upper()
                fmt_enum = resource.get('formatEnum', '').upper()
                if fmt in ['CSV', 'CSV.GZ'] or fmt_enum in ['CSV', 'CSV_GZ']:
                    csv_resource = resource
                    break

            if not csv_resource:
                print("No CSV resource found, looking for XML...")
                for resource in resources:
                    if resource.get('format', '').upper() == 'XML':
                        print("[WARNING] XML found but too large, using sample data")
                        return None

            url = csv_resource.get('url')
            if not url:
                print("No download URL found")
                return None

            print(f"Downloading from: {url}")
            print("[WARNING] This may take a while (file is ~50-200MB)...")

            # Download with streaming
            response = requests.get(url, stream=True, timeout=120, verify=False)
            response.raise_for_status()

            # Save to temp file
            import tempfile
            temp_file = tempfile.NamedTemporaryFile(mode='wb', delete=False, suffix='.csv')

            # Download in chunks
            total_size = int(response.headers.get('content-length', 0))
            downloaded = 0

            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    temp_file.write(chunk)
                    downloaded += len(chunk)
                    if total_size > 0:
                        progress = (downloaded / total_size) * 100
                        if progress % 10 < 1:  # Print every ~10%
                            print(f"Downloaded: {progress:.0f}%")

            temp_file.close()
            print(f"[SUCCESS] Download complete: {temp_file.name}")

            # Check if gzipped
            if url.endswith('.gz'):
                print("Decompressing gzip file...")
                import gzip
                import shutil

                temp_file_gz = temp_file.name
                temp_file_csv = temp_file.name.replace('.csv', '_extracted.csv')

                with gzip.open(temp_file_gz, 'rb') as f_in:
                    with open(temp_file_csv, 'wb') as f_out:
                        shutil.copyfileobj(f_in, f_out)

                print(f"[SUCCESS] Decompressed to: {temp_file_csv}")
                return temp_file_csv

            return temp_file.name

        except Exception as e:
            print(f"[ERROR] Error downloading dataset: {e}")
            return None

    def parse_or_csv(self, filepath: str, max_rows: int = 1000) -> Dict[str, List[Dict]]:
        """Parse OR CSV file extracting companies, persons, and relationships from udaje JSON."""
        print(f"[OR PARSER] Parsing CSV: {filepath}")
        print(f"[OR PARSER] Max rows: {max_rows}")

        companies = []
        relationships = []
        all_persons = {}  # Dedup persons across rows: {person_id: person_data}
        company_icos = set()  # Track which company IČOs we've seen

        try:
            # Try different encodings
            encodings = ['utf-8', 'windows-1250', 'iso-8859-2']
            file_handle = None

            for encoding in encodings:
                try:
                    file_handle = open(filepath, 'r', encoding=encoding)
                    first_line = file_handle.readline()
                    file_handle.seek(0)
                    print(f"[OK] Encoding: {encoding}")
                    break
                except UnicodeDecodeError:
                    if file_handle:
                        file_handle.close()
                    continue

            if not file_handle:
                print("[ERROR] Could not determine file encoding")
                return {'companies': [], 'relationships': []}

            reader = csv.DictReader(file_handle)
            columns = reader.fieldnames or []
            print(f"[OK] Columns: {columns[:8]}...")
            has_udaje = 'udaje' in columns
            if not has_udaje:
                print("[WARNING] No 'udaje' column found - relationships will be empty")

            parsed_count = 0
            skipped = 0

            for i, row in enumerate(reader):
                if parsed_count >= max_rows:
                    break

                try:
                    result = self.parse_or_row(row)
                    if result[0] is None:
                        skipped += 1
                        continue

                    company, rels, persons = result
                    ico = company['id']

                    # Skip duplicate IČOs
                    if ico in company_icos:
                        continue
                    company_icos.add(ico)

                    companies.append(company)
                    relationships.extend(rels)
                    all_persons.update(persons)
                    parsed_count += 1

                    if parsed_count % 50 == 0:
                        print(f"[PROGRESS] {parsed_count}/{max_rows} companies, "
                              f"{len(relationships)} relationships, {len(all_persons)} persons")

                except Exception as row_err:
                    skipped += 1
                    if skipped <= 3:
                        print(f"[WARNING] Row {i} parse error: {row_err}")

            file_handle.close()

            # Add deduplicated persons to the companies list (they're entities too)
            companies.extend(all_persons.values())

            print(f"[SUCCESS] Parsed {parsed_count} companies, "
                  f"{len(all_persons)} persons, {len(relationships)} relationships "
                  f"(skipped {skipped} rows)")

            return {'companies': companies, 'relationships': relationships}

        except Exception as e:
            print(f"[ERROR] CSV parse error: {e}")
            import traceback
            traceback.print_exc()
            return {'companies': [], 'relationships': []}

    def download_and_parse(self, max_companies: int = 100) -> Dict[str, List[Dict]]:
        """Download real OR data and parse it with relationship extraction.

        Uses cached CSV if available and recent (< 7 days old).
        """
        print("=" * 50)
        print(f"[REAL DATA] Downloading and parsing OR data (max {max_companies} companies)...")
        print("=" * 50)

        # Step 1: Find the latest dataset
        dataset_name = self.get_latest_dataset_name()
        if not dataset_name:
            print("[ERROR] Could not find OR dataset")
            return {'companies': [], 'relationships': []}

        print(f"[OK] Dataset: {dataset_name}")

        # Step 2: Check cache
        cache_path = self._get_cache_path(dataset_name)
        csv_path = None

        if self._is_cache_valid(cache_path):
            print(f"[CACHE] Using cached CSV: {cache_path}")
            csv_path = cache_path
        else:
            # Download fresh
            csv_path = self.download_or_dataset(dataset_name)
            if not csv_path:
                print("[ERROR] Download failed")
                return {'companies': [], 'relationships': []}

            # Copy to cache
            try:
                os.makedirs(self.cache_dir, exist_ok=True)
                import shutil
                shutil.copy2(csv_path, cache_path)
                print(f"[CACHE] Saved to cache: {cache_path}")
            except Exception as cache_err:
                print(f"[WARNING] Could not cache file: {cache_err}")

        # Step 3: Parse
        result = self.parse_or_csv(csv_path, max_rows=max_companies)

        companies = result.get('companies', [])
        relationships = result.get('relationships', [])

        if not companies:
            print("[WARNING] No companies parsed from real data")
            return {'companies': [], 'relationships': []}

        print(f"[SUCCESS] Real data: {len(companies)} entities, {len(relationships)} relationships")
        return {'companies': companies, 'relationships': relationships}

    def check_isir_insolvency(self, ico: str) -> bool:
        """Check if company is insolvent using ISIR API"""
        if ico in self.isir_cache:
            return self.isir_cache[ico]

        try:
            # ISIR API endpoint for insolvency registry
            url = "https://isir.justice.cz/isir/common/api/v1/subjects"

            params = {
                'ico': ico,
                'limit': 1
            }

            response = requests.get(url, params=params, timeout=5, verify=False)

            if response.status_code == 200:
                data = response.json()
                # If any records found, company has insolvency proceedings
                is_insolvent = len(data.get('items', [])) > 0
                self.isir_cache[ico] = is_insolvent
                return is_insolvent

            # If API fails, assume not insolvent
            self.isir_cache[ico] = False
            return False

        except Exception as e:
            print(f"Warning: ISIR check failed for {ico}: {e}")
            self.isir_cache[ico] = False
            return False

    def batch_check_isir(self, companies: List[Dict]) -> List[Dict]:
        """Batch check ISIR insolvency status for multiple companies"""
        print(f"Checking ISIR insolvency status for {len(companies)} companies...")

        for i, company in enumerate(companies):
            if i % 50 == 0:
                print(f"ISIR check progress: {i}/{len(companies)}")

            ico = company['id']
            is_insolvent = self.check_isir_insolvency(ico)
            company['insolvent'] = is_insolvent

            # Rate limiting - be nice to the API
            if i % 10 == 0:
                time.sleep(0.5)

        insolvent_count = sum(1 for c in companies if c.get('insolvent'))
        print(f"[SUCCESS] Found {insolvent_count} insolvent companies")

        return companies

    def fetch_opencorporates_entity(self, jurisdiction: str, company_number: str) -> Optional[Dict]:
        """Fetch company data from OpenCorporates API"""
        cache_key = f"{jurisdiction}:{company_number}"

        if cache_key in self.opencorporates_cache:
            return self.opencorporates_cache[cache_key]

        try:
            # OpenCorporates API endpoint
            url = f"https://api.opencorporates.com/v0.4/companies/{jurisdiction}/{company_number}"

            response = requests.get(url, timeout=10, verify=False)

            if response.status_code == 200:
                data = response.json()
                company_data = data.get('results', {}).get('company', {})

                if company_data:
                    entity = {
                        'id': f"{jurisdiction.upper()}{company_number}",
                        'name': company_data.get('name', 'Unknown'),
                        'type': 'company',
                        'city': company_data.get('registered_address', {}).get('locality', ''),
                        'country': jurisdiction.upper(),
                        'insolvent': company_data.get('current_status') in ['Dissolved', 'Inactive', 'Liquidation']
                    }

                    self.opencorporates_cache[cache_key] = entity
                    return entity

            return None

        except Exception as e:
            print(f"Warning: OpenCorporates fetch failed for {jurisdiction}:{company_number}: {e}")
            return None

    def add_foreign_entities_sample(self) -> List[Dict]:
        """Add sample foreign entities from Cyprus and Netherlands"""
        print("Adding sample foreign entities...")

        foreign_entities = []

        # Cyprus entities
        cyprus_samples = [
            ("cy", "HE123456", "Cyprus Holdings Ltd.", "Nicosia"),
            ("cy", "HE234567", "Offshore Investments Ltd.", "Limassol"),
        ]

        for jurisdiction, number, name, city in cyprus_samples:
            # Try to fetch real data, fallback to sample
            entity = self.fetch_opencorporates_entity(jurisdiction, number)
            if not entity:
                entity = {
                    'id': f"{jurisdiction.upper()}{number}",
                    'name': name,
                    'type': 'company',
                    'city': city,
                    'country': jurisdiction.upper(),
                    'insolvent': False
                }
            foreign_entities.append(entity)
            time.sleep(0.5)  # Rate limiting

        # Netherlands entities
        nl_samples = [
            ("nl", "12345678", "Amsterdam Ventures B.V.", "Amsterdam"),
            ("nl", "87654321", "Rotterdam Holdings N.V.", "Rotterdam"),
        ]

        for jurisdiction, number, name, city in nl_samples:
            entity = self.fetch_opencorporates_entity(jurisdiction, number)
            if not entity:
                entity = {
                    'id': f"{jurisdiction.upper()}{number}",
                    'name': name,
                    'type': 'company',
                    'city': city,
                    'country': jurisdiction.upper(),
                    'insolvent': False
                }
            foreign_entities.append(entity)
            time.sleep(0.5)

        print(f"[SUCCESS] Added {len(foreign_entities)} foreign entities")
        return foreign_entities
    
    def fetch_sample_data(self, max_companies: int = 100, use_real_data: bool = False) -> Dict[str, List[Dict]]:
        """Fetch companies and relationships - real OR data or synthetic fallback.

        Args:
            max_companies: Maximum number of companies to fetch
            use_real_data: If True, attempt to download and parse real OR data
        """
        if use_real_data:
            try:
                result = self.download_and_parse(max_companies=max_companies)
                if result['companies']:
                    return result
                print("[WARNING] Real data returned empty, falling back to synthetic data")
            except Exception as e:
                print(f"[ERROR] Real data failed: {e}")
                print("[WARNING] Falling back to synthetic data")

        return self._get_synthetic_data()

    def _get_synthetic_data(self) -> Dict[str, List[Dict]]:
        """Return synthetic dataset with 107 Czech business entities and 205 relationships.

        Used as fallback when real OR data is unavailable.
        Covers: 65 CZ companies, 25 persons, 17 foreign (CY/NL/SK/DE/LU/UK), 5 insolvent.
        """
        print("[SYNTHETIC] Loading synthetic dataset with 107 entities...")

        companies = []

        # 107 entities: 65 Czech companies, 25 persons, 17 foreign companies
        # Format: (ico, name, city, insolvent, country)
        sample_entities = [
                # ========== CZECH COMPANIES (65) ==========
                # --- Tech / Internet (12) ---
                ("45274649", "Avast Software s.r.o.", "Praha", False, "CZ"),
                ("27116158", "Mall Group a.s.", "Praha", False, "CZ"),
                ("63998505", "Alza.cz a.s.", "Praha", False, "CZ"),
                ("26168685", "Rohlík.cz s.r.o.", "Praha", False, "CZ"),
                ("26493241", "Seznam.cz, a.s.", "Praha", False, "CZ"),
                ("29148928", "Socialbakers a.s.", "Praha", False, "CZ"),
                ("28169522", "JetBrains s.r.o.", "Praha", False, "CZ"),
                ("24675539", "Kentico Software s.r.o.", "Brno", False, "CZ"),
                ("29307880", "Y Soft Corporation a.s.", "Brno", False, "CZ"),
                ("26441381", "GoodData s.r.o.", "Praha", False, "CZ"),
                ("05765251", "Productboard s.r.o.", "Praha", False, "CZ"),
                ("28434498", "Zásilkovna s.r.o.", "Praha", False, "CZ"),
                # --- Finance / Banking (5) ---
                ("00025593", "Československá obchodní banka, a. s.", "Praha", False, "CZ"),
                ("00001834", "Česká spořitelna, a.s.", "Praha", False, "CZ"),
                ("00023272", "Komerční banka, a.s.", "Praha", False, "CZ"),
                ("00003468", "Česká pojišťovna a.s.", "Praha", False, "CZ"),
                ("26177005", "Home Credit a.s.", "Brno", False, "CZ"),
                # --- Telecom (1) ---
                ("24287903", "O2 Czech Republic a.s.", "Praha", False, "CZ"),
                # --- Energy (6) ---
                ("60197901", "ČEZ, a.s.", "Praha", False, "CZ"),
                ("25788001", "Energo-Pro a.s.", "Praha", False, "CZ"),
                ("26840065", "EPH a.s.", "Praha", False, "CZ"),
                ("25312782", "ČEZ Distribuce, a.s.", "Děčín", False, "CZ"),
                ("26418814", "Net4Gas s.r.o.", "Praha", False, "CZ"),
                ("88990011", "Severomoravská energetika s.r.o.", "Ostrava", False, "CZ"),
                # --- Manufacturing / Heavy Industry (13) ---
                ("45534306", "Škoda Auto a.s.", "Mladá Boleslav", False, "CZ"),
                ("60193336", "Pilsner Urquell a.s.", "Plzeň", False, "CZ"),
                ("25612093", "Kofola ČeskoSlovensko a.s.", "Ostrava", False, "CZ"),
                ("60193468", "Plzeňský Prazdroj, a.s.", "Plzeň", False, "CZ"),
                ("60193531", "Budějovický Budvar, n.p.", "České Budějovice", False, "CZ"),
                ("63078333", "Moravia Steel a.s.", "Třinec", False, "CZ"),
                ("47675829", "ArcelorMittal Ostrava a.s.", "Ostrava", False, "CZ"),
                ("48173355", "Vítkovice Holding a.s.", "Ostrava", False, "CZ"),
                ("25860011", "Tatra Trucks a.s.", "Kopřivnice", False, "CZ"),
                ("47150904", "TŘINECKÉ ŽELEZÁRNY, a.s.", "Třinec", False, "CZ"),
                ("45193509", "LINET spol. s r.o.", "Slaný", False, "CZ"),
                ("25649329", "Moravská ocelárna s.r.o.", "Ostrava", False, "CZ"),
                ("44556600", "Liberecký textil a.s.", "Liberec", False, "CZ"),
                # --- Investment / Holdings (5) ---
                ("49240480", "Agrofert, a.s.", "Praha", False, "CZ"),
                ("63480174", "Penta Investments s.r.o.", "Praha", False, "CZ"),
                ("28185480", "Rockaway Capital s.r.o.", "Praha", False, "CZ"),
                ("28195078", "Avast Holding a.s.", "Praha", False, "CZ"),
                ("25302914", "CZEC Holdings s.r.o.", "Praha", False, "CZ"),
                # --- Construction / Real Estate (5) ---
                ("49241257", "Metrostav a.s.", "Praha", False, "CZ"),
                ("26267063", "CTP Invest s.r.o.", "Humpolec", False, "CZ"),
                ("55667788", "Reality Invest Praha s.r.o.", "Praha", False, "CZ"),
                ("66778899", "Reality Invest Brno s.r.o.", "Brno", False, "CZ"),
                ("60108088", "Komerční reality s.r.o.", "Praha", False, "CZ"),
                # --- Ostrava Regional (3) ---
                ("27082440", "Ostrava Property Development s.r.o.", "Ostrava", False, "CZ"),
                ("26830311", "Ostravské vodárny a kanalizace a.s.", "Ostrava", False, "CZ"),
                ("77889900", "Dopravní podnik Ostrava a.s.", "Ostrava", False, "CZ"),
                # --- Pharma / Health (2) ---
                ("26178559", "Zentiva Group a.s.", "Praha", False, "CZ"),
                ("25671651", "Novaservis a.s.", "Brno", False, "CZ"),
                # --- Media / Logistics (2) ---
                ("26505398", "Prima TV a.s.", "Praha", False, "CZ"),
                ("11223300", "Prague Logistics s.r.o.", "Praha", False, "CZ"),
                # --- Agriculture / Mining / Regional (5) ---
                ("22334400", "Moravský zemědělský fond a.s.", "Olomouc", False, "CZ"),
                ("33445500", "Jihočeské doly a.s.", "České Budějovice", False, "CZ"),
                ("99001122", "Technologický park Brno a.s.", "Brno", False, "CZ"),
                ("25352555", "OKD, a.s.", "Ostrava", False, "CZ"),
                ("66001122", "Liberecké sklárny a.s.", "Liberec", False, "CZ"),
                # --- State Enterprise (1) ---
                ("00000795", "Státní tiskárna cenin, s.p.", "Praha", False, "CZ"),
                # --- Insolvent Companies (5) ---
                ("12345678", "Bankrot Trading s.r.o.", "Praha", True, "CZ"),
                ("87654321", "Dlužník Investments a.s.", "Brno", True, "CZ"),
                ("15890520", "Firma v insolvenci s.r.o.", "Ostrava", True, "CZ"),
                ("33344455", "Zkrachovalá stavební a.s.", "Praha", True, "CZ"),
                ("44556677", "Dluh Reality s.r.o.", "Brno", True, "CZ"),

                # ========== PERSONS (25) ==========
                ("RC001", "Jan Novák", "Praha", False, "CZ"),
                ("RC002", "Petr Svoboda", "Brno", False, "CZ"),
                ("RC003", "Marie Nováková", "Praha", False, "CZ"),
                ("RC004", "Karel Dvořák", "Praha", False, "CZ"),
                ("RC005", "Tomáš Procházka", "Ostrava", False, "CZ"),
                ("RC006", "Eva Černá", "Praha", False, "CZ"),
                ("RC007", "Jiří Veselý", "Brno", False, "CZ"),
                ("RC008", "Lucie Krejčová", "Praha", False, "CZ"),
                ("RC009", "Martin Horák", "Plzeň", False, "CZ"),
                ("RC010", "Barbora Němcová", "Ostrava", False, "CZ"),
                ("RC011", "Ondřej Marek", "Praha", False, "CZ"),
                ("RC012", "Zuzana Pospíšilová", "Brno", False, "CZ"),
                ("RC013", "David Král", "Praha", False, "CZ"),
                ("RC014", "Andrea Sedláčková", "Ostrava", False, "CZ"),
                ("RC015", "Filip Holub", "Praha", False, "CZ"),
                ("RC016", "Tereza Vlčková", "Olomouc", False, "CZ"),
                ("RC017", "Radek Bartoš", "Praha", False, "CZ"),
                ("RC018", "Jana Říhová", "Liberec", False, "CZ"),
                ("RC019", "Michal Šťastný", "Praha", False, "CZ"),
                ("RC020", "Petra Urbanová", "Brno", False, "CZ"),
                ("RC021", "Lukáš Fiala", "České Budějovice", False, "CZ"),
                ("RC022", "Markéta Benešová", "Praha", False, "CZ"),
                ("RC023", "Vojtěch Kopecký", "Ostrava", False, "CZ"),
                ("RC024", "Daniela Marková", "Plzeň", False, "CZ"),
                ("RC025", "Stanislav Růžička", "Praha", False, "CZ"),

                # ========== FOREIGN COMPANIES (17) ==========
                # --- Cyprus (4) ---
                ("CY001", "Cyprus Holdings Ltd.", "Nicosia", False, "CY"),
                ("CY002", "Offshore Investments Ltd.", "Limassol", False, "CY"),
                ("CY003", "Lemesos Trading Ltd.", "Limassol", False, "CY"),
                ("CY004", "Eurogate Holdings Ltd.", "Nicosia", False, "CY"),
                # --- Netherlands (4) ---
                ("NL001", "Amsterdam Ventures B.V.", "Amsterdam", False, "NL"),
                ("NL002", "Rotterdam Holdings N.V.", "Rotterdam", False, "NL"),
                ("NL003", "Dutch Capital Management B.V.", "Amsterdam", False, "NL"),
                ("NL004", "Eindhoven Tech Invest B.V.", "Eindhoven", False, "NL"),
                # --- Slovakia (3) ---
                ("SK001", "Bratislava Holdings a.s.", "Bratislava", False, "SK"),
                ("SK002", "Košice Industrial s.r.o.", "Košice", False, "SK"),
                ("SK003", "Žilina Energo s.r.o.", "Žilina", False, "SK"),
                # --- Germany (3) ---
                ("DE001", "München Beteiligungen GmbH", "München", False, "DE"),
                ("DE002", "Berlin Automotive AG", "Berlin", False, "DE"),
                ("DE003", "Hamburg Logistik GmbH", "Hamburg", False, "DE"),
                # --- Luxembourg (2) ---
                ("LU001", "Luxembourg Finance S.A.", "Luxembourg", False, "LU"),
                ("LU002", "Grand Duchy Capital S.à r.l.", "Luxembourg", False, "LU"),
                # --- UK (1) ---
                ("UK001", "London Equity Partners LLP", "London", False, "UK"),
        ]

        for ico, name, city, insolvent, country in sample_entities:
            entity_type = 'person' if ico.startswith('RC') else 'company'
            companies.append({
                'id': ico,
                'name': name,
                'type': entity_type,
                'city': city,
                'insolvent': insolvent,
                'country': country
            })

        # ~220 relationships modeling realistic Czech corporate structures
        # Patterns: holding structures, shared directors, offshore ownership chains,
        # supply chains, financial connections, insolvency networks
        relationships = [
            # =============================================
            # TECH / INTERNET CLUSTER
            # =============================================
            # Directors & board members
            {'source': 'RC001', 'target': '45274649', 'type': 'jednatel', 'active': True},
            {'source': 'RC001', 'target': '28195078', 'type': 'člen představenstva', 'active': True},
            {'source': 'RC006', 'target': '27116158', 'type': 'jednatelka', 'active': True},
            {'source': 'RC008', 'target': '63998505', 'type': 'jednatelka', 'active': True},
            {'source': 'RC002', 'target': '63998505', 'type': 'člen dozorčí rady', 'active': True},
            {'source': 'RC011', 'target': '26168685', 'type': 'jednatel', 'active': True},
            {'source': 'RC013', 'target': '26493241', 'type': 'jednatel', 'active': True},
            {'source': 'RC015', 'target': '29148928', 'type': 'jednatel', 'active': True},
            {'source': 'RC019', 'target': '28169522', 'type': 'jednatel', 'active': True},
            {'source': 'RC007', 'target': '24675539', 'type': 'jednatel', 'active': True},
            {'source': 'RC012', 'target': '29307880', 'type': 'jednatelka', 'active': True},
            {'source': 'RC022', 'target': '26441381', 'type': 'jednatelka', 'active': True},
            {'source': 'RC025', 'target': '05765251', 'type': 'jednatel', 'active': True},
            {'source': 'RC003', 'target': '28434498', 'type': 'jednatelka', 'active': True},
            # Ownership & investment in tech
            {'source': '28195078', 'target': '45274649', 'type': 'mateřská společnost', 'active': True},
            {'source': '28185480', 'target': '27116158', 'type': 'investor', 'active': True},
            {'source': '28185480', 'target': '26168685', 'type': 'investor', 'active': True},
            {'source': '28185480', 'target': '28434498', 'type': 'investor', 'active': True},
            {'source': 'NL004', 'target': '26493241', 'type': 'akcionář', 'active': True},
            {'source': 'CY001', 'target': '45274649', 'type': 'akcionář', 'active': True},
            {'source': 'UK001', 'target': '29148928', 'type': 'investor', 'active': True},
            {'source': 'NL001', 'target': '05765251', 'type': 'investor', 'active': True},
            {'source': '45274649', 'target': '27116158', 'type': 'společník', 'active': True},
            {'source': '27116158', 'target': '63998505', 'type': 'investor', 'active': True},
            {'source': '63998505', 'target': '26168685', 'type': 'obchodní partner', 'active': True},
            {'source': '26441381', 'target': '29148928', 'type': 'strategický partner', 'active': True},
            {'source': '05765251', 'target': '26441381', 'type': 'obchodní partner', 'active': True},
            {'source': '99001122', 'target': '24675539', 'type': 'inkubátor', 'active': True},
            {'source': '99001122', 'target': '29307880', 'type': 'inkubátor', 'active': True},
            {'source': '28434498', 'target': '63998505', 'type': 'dodavatel', 'active': True},

            # =============================================
            # FINANCE / BANKING CLUSTER
            # =============================================
            # Directors & board members
            {'source': 'RC004', 'target': '00025593', 'type': 'člen představenstva', 'active': True},
            {'source': 'RC004', 'target': '00001834', 'type': 'člen dozorčí rady', 'active': True},
            {'source': 'RC011', 'target': '00023272', 'type': 'člen představenstva', 'active': True},
            {'source': 'RC006', 'target': '00003468', 'type': 'člen dozorčí rady', 'active': True},
            {'source': 'RC020', 'target': '26177005', 'type': 'jednatelka', 'active': True},
            {'source': 'RC022', 'target': '00001834', 'type': 'člen představenstva', 'active': True},
            {'source': 'RC011', 'target': '00003468', 'type': 'člen dozorčí rady', 'active': True},
            # Financial relationships
            {'source': 'NL001', 'target': '00001834', 'type': 'akcionář', 'active': True},
            {'source': '00025593', 'target': 'NL002', 'type': 'dceřiná společnost', 'active': True},
            {'source': '00001834', 'target': '00025593', 'type': 'mezibankovní partner', 'active': True},
            {'source': '00023272', 'target': '00003468', 'type': 'pojistný partner', 'active': True},
            {'source': 'LU001', 'target': '00025593', 'type': 'akcionář', 'active': True},
            {'source': 'LU001', 'target': '00023272', 'type': 'akcionář', 'active': True},
            {'source': 'LU002', 'target': 'LU001', 'type': 'mateřská společnost', 'active': True},
            {'source': '26177005', 'target': 'SK001', 'type': 'dceřiná společnost', 'active': True},
            {'source': 'RC001', 'target': '00001834', 'type': 'akcionář', 'active': True},
            # Bank-client relationships
            {'source': '00001834', 'target': '55667788', 'type': 'věřitel', 'active': True},
            {'source': '00023272', 'target': '66778899', 'type': 'věřitel', 'active': True},
            {'source': '00025593', 'target': '49241257', 'type': 'věřitel', 'active': True},
            {'source': '45534306', 'target': '00001834', 'type': 'klient', 'active': True},

            # =============================================
            # ENERGY CLUSTER
            # =============================================
            # Directors & board members
            {'source': 'RC017', 'target': '60197901', 'type': 'člen představenstva', 'active': True},
            {'source': 'RC017', 'target': '26840065', 'type': 'předseda představenstva', 'active': True},
            {'source': 'RC017', 'target': '25312782', 'type': 'člen dozorčí rady', 'active': True},
            {'source': 'RC025', 'target': '25788001', 'type': 'jednatel', 'active': True},
            {'source': 'RC013', 'target': '26418814', 'type': 'jednatel', 'active': True},
            {'source': 'RC014', 'target': '88990011', 'type': 'jednatelka', 'active': True},
            # Corporate structure
            {'source': '60197901', 'target': '25312782', 'type': 'mateřská společnost', 'active': True},
            {'source': '26840065', 'target': '25788001', 'type': 'dceřiná společnost', 'active': True},
            {'source': '26840065', 'target': '26418814', 'type': 'dceřiná společnost', 'active': True},
            {'source': '26840065', 'target': '88990011', 'type': 'dceřiná společnost', 'active': True},
            {'source': 'DE001', 'target': '26840065', 'type': 'akcionář', 'active': True},
            {'source': 'CY003', 'target': '26840065', 'type': 'akcionář', 'active': True},
            {'source': 'NL003', 'target': 'CY003', 'type': 'mateřská společnost', 'active': True},
            {'source': 'SK003', 'target': '88990011', 'type': 'dodavatel', 'active': True},
            # Energy supply to industry
            {'source': '60197901', 'target': '45534306', 'type': 'dodavatel', 'active': True},
            {'source': '60197901', 'target': '47675829', 'type': 'dodavatel', 'active': True},
            {'source': '88990011', 'target': '77889900', 'type': 'dodavatel', 'active': True},
            {'source': '88990011', 'target': '26830311', 'type': 'dodavatel', 'active': True},

            # =============================================
            # MANUFACTURING / HEAVY INDUSTRY CLUSTER
            # =============================================
            # Directors & board members
            {'source': 'RC009', 'target': '60193336', 'type': 'člen představenstva', 'active': True},
            {'source': 'RC009', 'target': '60193468', 'type': 'člen dozorčí rady', 'active': True},
            {'source': 'RC024', 'target': '60193336', 'type': 'člen dozorčí rady', 'active': True},
            {'source': 'RC005', 'target': '47675829', 'type': 'člen představenstva', 'active': True},
            {'source': 'RC005', 'target': '48173355', 'type': 'předseda představenstva', 'active': True},
            {'source': 'RC005', 'target': '63078333', 'type': 'člen dozorčí rady', 'active': True},
            {'source': 'RC023', 'target': '25649329', 'type': 'jednatel', 'active': True},
            {'source': 'RC023', 'target': '47150904', 'type': 'člen představenstva', 'active': True},
            {'source': 'RC010', 'target': '25860011', 'type': 'člen dozorčí rady', 'active': True},
            {'source': 'RC021', 'target': '60193531', 'type': 'člen představenstva', 'active': True},
            {'source': 'RC018', 'target': '44556600', 'type': 'jednatelka', 'active': True},
            {'source': 'RC024', 'target': '45193509', 'type': 'jednatelka', 'active': True},
            # Automotive supply chain
            {'source': 'DE002', 'target': '45534306', 'type': 'akcionář', 'active': True},
            {'source': '45534306', 'target': '25860011', 'type': 'odběratel', 'active': True},
            {'source': 'DE002', 'target': '25860011', 'type': 'strategický partner', 'active': True},
            {'source': '45534306', 'target': '25312782', 'type': 'odběratel', 'active': True},
            # Steel / mining supply chain
            {'source': '47675829', 'target': '63078333', 'type': 'dodavatel', 'active': True},
            {'source': '63078333', 'target': '47150904', 'type': 'dodavatel', 'active': True},
            {'source': '47150904', 'target': '25649329', 'type': 'dodavatel', 'active': True},
            {'source': '48173355', 'target': '47675829', 'type': 'strategický partner', 'active': True},
            {'source': '25352555', 'target': '47675829', 'type': 'dodavatel', 'active': True},
            {'source': '25352555', 'target': '48173355', 'type': 'dodavatel', 'active': True},
            {'source': 'SK002', 'target': '63078333', 'type': 'obchodní partner', 'active': True},
            {'source': 'SK002', 'target': '47150904', 'type': 'dodavatel', 'active': True},
            {'source': '33445500', 'target': '47675829', 'type': 'dodavatel', 'active': True},
            # Beer & beverage connections
            {'source': '60193336', 'target': '60193468', 'type': 'sesterská společnost', 'active': True},
            {'source': '25612093', 'target': '60193336', 'type': 'konkurent', 'active': True},
            {'source': '60193531', 'target': '60193336', 'type': 'konkurent', 'active': True},
            {'source': '25612093', 'target': 'SK001', 'type': 'dceřiná společnost', 'active': True},
            {'source': '60193336', 'target': '45534306', 'type': 'dodavatel', 'active': True},
            {'source': 'NL001', 'target': '45534306', 'type': 'akcionář', 'active': True},
            # Liberec manufacturing
            {'source': '44556600', 'target': '66001122', 'type': 'dodavatel', 'active': True},
            {'source': '44556600', 'target': '49241257', 'type': 'dodavatel', 'active': True},
            {'source': 'RC018', 'target': '66001122', 'type': 'jednatelka', 'active': True},

            # =============================================
            # INVESTMENT / HOLDINGS CLUSTER
            # =============================================
            # Directors & board members
            {'source': 'RC004', 'target': '49240480', 'type': 'předseda představenstva', 'active': True},
            {'source': 'RC004', 'target': '63480174', 'type': 'člen představenstva', 'active': True},
            {'source': 'RC011', 'target': '28185480', 'type': 'jednatel', 'active': True},
            {'source': 'RC015', 'target': '25302914', 'type': 'jednatel', 'active': True},
            {'source': 'RC019', 'target': '63480174', 'type': 'člen dozorčí rady', 'active': True},
            # Portfolio holdings
            {'source': '49240480', 'target': '22334400', 'type': 'dceřiná společnost', 'active': True},
            {'source': '49240480', 'target': '26178559', 'type': 'akcionář', 'active': True},
            {'source': '49240480', 'target': '26505398', 'type': 'akcionář', 'active': True},
            {'source': '49240480', 'target': '60193531', 'type': 'akcionář', 'active': True},
            {'source': '63480174', 'target': '26177005', 'type': 'investor', 'active': True},
            {'source': '63480174', 'target': '00003468', 'type': 'akcionář', 'active': True},
            {'source': '63480174', 'target': '26178559', 'type': 'investor', 'active': True},
            {'source': '25302914', 'target': '55667788', 'type': 'mateřská společnost', 'active': True},
            {'source': '25302914', 'target': '66778899', 'type': 'mateřská společnost', 'active': True},
            # Offshore investment chains
            {'source': 'CY004', 'target': '63480174', 'type': 'akcionář', 'active': True},
            {'source': 'LU002', 'target': 'CY004', 'type': 'mateřská společnost', 'active': True},
            {'source': 'UK001', 'target': 'LU002', 'type': 'investor', 'active': True},
            {'source': 'NL003', 'target': '49240480', 'type': 'akcionář', 'active': True},
            {'source': 'CY002', 'target': '28185480', 'type': 'akcionář', 'active': True},
            {'source': 'CY004', 'target': '25302914', 'type': 'investor', 'active': True},
            {'source': 'CY002', 'target': '27116158', 'type': 'investor', 'active': True},

            # =============================================
            # CONSTRUCTION / REAL ESTATE CLUSTER
            # =============================================
            # Directors & board members
            {'source': 'RC008', 'target': '49241257', 'type': 'člen představenstva', 'active': True},
            {'source': 'RC016', 'target': '26267063', 'type': 'jednatelka', 'active': True},
            {'source': 'RC015', 'target': '55667788', 'type': 'jednatel', 'active': True},
            {'source': 'RC020', 'target': '66778899', 'type': 'jednatelka', 'active': True},
            {'source': 'RC019', 'target': '60108088', 'type': 'jednatel', 'active': True},
            # Business relationships
            {'source': '49241257', 'target': '26267063', 'type': 'dodavatel', 'active': True},
            {'source': '49241257', 'target': '55667788', 'type': 'dodavatel', 'active': True},
            {'source': '26267063', 'target': '66778899', 'type': 'investor', 'active': True},
            {'source': '55667788', 'target': '60108088', 'type': 'obchodní partner', 'active': True},
            {'source': '49241257', 'target': '77889900', 'type': 'dodavatel', 'active': True},
            {'source': '26267063', 'target': '99001122', 'type': 'investor', 'active': True},
            {'source': '33344455', 'target': '49241257', 'type': 'bývalý dodavatel', 'active': False},

            # =============================================
            # OSTRAVA REGIONAL CLUSTER
            # =============================================
            # Directors & board members
            {'source': 'RC005', 'target': '27082440', 'type': 'jednatel', 'active': True},
            {'source': 'RC010', 'target': '26830311', 'type': 'člen představenstva', 'active': True},
            {'source': 'RC014', 'target': '77889900', 'type': 'člen představenstva', 'active': True},
            {'source': 'RC023', 'target': '27082440', 'type': 'člen dozorčí rady', 'active': True},
            # Regional connections
            {'source': '27082440', 'target': '26830311', 'type': 'obchodní partner', 'active': True},
            {'source': '77889900', 'target': '26830311', 'type': 'odběratel', 'active': True},
            {'source': '47675829', 'target': '77889900', 'type': 'sponzor', 'active': True},
            {'source': '48173355', 'target': '27082440', 'type': 'investor', 'active': True},
            {'source': '15890520', 'target': '27082440', 'type': 'bývalý dodavatel', 'active': False},

            # =============================================
            # TELECOM / MEDIA CLUSTER
            # =============================================
            {'source': 'RC003', 'target': '24287903', 'type': 'člen dozorčí rady', 'active': True},
            {'source': 'RC008', 'target': '26505398', 'type': 'člen představenstva', 'active': True},
            {'source': '24287903', 'target': '26505398', 'type': 'obchodní partner', 'active': True},
            {'source': '24287903', 'target': '45534306', 'type': 'strategický partner', 'active': True},
            {'source': '26168685', 'target': '24287903', 'type': 'dodavatel', 'active': True},
            {'source': '26493241', 'target': '24287903', 'type': 'reklamní partner', 'active': True},

            # =============================================
            # PHARMA / HEALTH CLUSTER
            # =============================================
            {'source': 'RC012', 'target': '26178559', 'type': 'člen dozorčí rady', 'active': True},
            {'source': 'RC016', 'target': '25671651', 'type': 'jednatelka', 'active': True},
            {'source': '26178559', 'target': '25671651', 'type': 'dodavatel', 'active': True},
            {'source': 'DE001', 'target': '26178559', 'type': 'akcionář', 'active': True},

            # =============================================
            # LOGISTICS CLUSTER
            # =============================================
            {'source': 'RC001', 'target': '11223300', 'type': 'jednatel', 'active': True},
            {'source': '11223300', 'target': '28434498', 'type': 'obchodní partner', 'active': True},
            {'source': 'DE003', 'target': '11223300', 'type': 'strategický partner', 'active': True},
            {'source': 'DE003', 'target': '28434498', 'type': 'obchodní partner', 'active': True},
            {'source': '11223300', 'target': '45534306', 'type': 'dodavatel', 'active': True},

            # =============================================
            # AGRICULTURE / MINING / REGIONAL
            # =============================================
            {'source': 'RC016', 'target': '22334400', 'type': 'člen dozorčí rady', 'active': True},
            {'source': 'RC021', 'target': '33445500', 'type': 'jednatel', 'active': True},
            {'source': '22334400', 'target': '25612093', 'type': 'dodavatel', 'active': True},
            {'source': 'RC010', 'target': '25352555', 'type': 'člen dozorčí rady', 'active': True},
            {'source': 'RC007', 'target': '99001122', 'type': 'člen představenstva', 'active': True},

            # =============================================
            # STATE ENTERPRISE
            # =============================================
            {'source': 'RC004', 'target': '00000795', 'type': 'člen dozorčí rady', 'active': True},
            {'source': '00000795', 'target': '00001834', 'type': 'klient', 'active': True},
            {'source': '00000795', 'target': '00025593', 'type': 'klient', 'active': True},

            # =============================================
            # INSOLVENT CONNECTIONS (former relationships)
            # =============================================
            # Bankrot Trading network
            {'source': '12345678', 'target': 'RC001', 'type': 'bývalý jednatel', 'active': False},
            {'source': '12345678', 'target': '87654321', 'type': 'společník', 'active': False},
            {'source': 'CY001', 'target': '12345678', 'type': 'hidden owner', 'active': False},
            {'source': '12345678', 'target': '55667788', 'type': 'bývalý dodavatel', 'active': False},
            # Dlužník Investments network
            {'source': '87654321', 'target': '27116158', 'type': 'bývalý dodavatel', 'active': False},
            {'source': '87654321', 'target': '63998505', 'type': 'věřitel', 'active': True},
            {'source': 'RC002', 'target': '12345678', 'type': 'bývalý jednatel', 'active': False},
            {'source': 'RC002', 'target': '87654321', 'type': 'likvidátor', 'active': True},
            # Firma v insolvenci network
            {'source': '15890520', 'target': '25649329', 'type': 'bývalý dodavatel', 'active': False},
            {'source': '15890520', 'target': '48173355', 'type': 'bývalý dodavatel', 'active': False},
            {'source': 'RC010', 'target': '15890520', 'type': 'bývalý jednatel', 'active': False},
            # Zkrachovalá stavební network
            {'source': '33344455', 'target': '55667788', 'type': 'bývalý subdodavatel', 'active': False},
            {'source': '33344455', 'target': '66778899', 'type': 'bývalý subdodavatel', 'active': False},
            {'source': 'RC019', 'target': '33344455', 'type': 'bývalý jednatel', 'active': False},
            # Dluh Reality network
            {'source': '44556677', 'target': '66778899', 'type': 'bývalý partner', 'active': False},
            {'source': '44556677', 'target': '87654321', 'type': 'propojená osoba', 'active': False},
            {'source': 'RC007', 'target': '44556677', 'type': 'bývalý jednatel', 'active': False},
            {'source': '44556677', 'target': '00023272', 'type': 'dlužník', 'active': True},

            # =============================================
            # CROSS-BORDER / OFFSHORE CHAINS
            # =============================================
            # NL → CY → CZ offshore chains (already partially defined above)
            {'source': 'NL002', 'target': 'CY001', 'type': 'mateřská společnost', 'active': True},
            {'source': 'RC003', 'target': 'CY001', 'type': 'director', 'active': True},
            {'source': 'RC002', 'target': 'CY002', 'type': 'beneficial owner', 'active': True},
            # DE connections
            {'source': 'DE001', 'target': '48173355', 'type': 'investor', 'active': True},
            {'source': 'DE002', 'target': 'DE001', 'type': 'sesterská společnost', 'active': True},
            {'source': 'DE001', 'target': 'DE003', 'type': 'sesterská společnost', 'active': True},
            # SK connections
            {'source': 'SK001', 'target': 'SK002', 'type': 'obchodní partner', 'active': True},
            {'source': 'SK003', 'target': 'SK001', 'type': 'obchodní partner', 'active': True},
            {'source': 'NL004', 'target': '29307880', 'type': 'investor', 'active': True},
            # Export partnerships
            {'source': '60193336', 'target': 'NL001', 'type': 'export partner', 'active': True},
            {'source': '45193509', 'target': 'DE003', 'type': 'export partner', 'active': True},

            # =============================================
            # HUB PERSONS - additional cross-sector links
            # =============================================
            # Karel Dvořák (RC004) - oligarch / super-connector
            {'source': 'RC004', 'target': '60197901', 'type': 'člen dozorčí rady', 'active': True},
            {'source': 'RC004', 'target': '45534306', 'type': 'člen dozorčí rady', 'active': True},
            # Eva Černá (RC006) - cross-sector
            {'source': 'RC006', 'target': '49241257', 'type': 'člen dozorčí rady', 'active': True},
            # Martin Horák (RC009) - Plzeň + Budvar
            {'source': 'RC009', 'target': '60193531', 'type': 'člen dozorčí rady', 'active': True},
            # Andrea Sedláčková (RC014) - Ostrava energy + beverage
            {'source': 'RC014', 'target': '25612093', 'type': 'člen dozorčí rady', 'active': True},
            # Ondřej Marek (RC011) - finance + VC
            {'source': 'RC003', 'target': '26168685', 'type': 'investorka', 'active': True},
            # Markéta Benešová (RC022) - tech + finance
            {'source': 'RC022', 'target': '28195078', 'type': 'člen dozorčí rady', 'active': True},
            # Stanislav Růžička (RC025) - energy + tech
            {'source': 'RC025', 'target': '60197901', 'type': 'prokurista', 'active': True},
            # RC002 former consultant
            {'source': 'RC002', 'target': '25612093', 'type': 'consultant', 'active': False},
        ]

        print(f"[SUCCESS] Loaded {len(companies)} companies with {len(relationships)} relationships")

        return {
            'companies': companies,
            'relationships': relationships
        }

or_parser = ORJusticeParser()