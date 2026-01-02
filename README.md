# Kongin

[![PyPI version](https://img.shields.io/pypi/v/kongin.svg)](https://pypi.org/project/kongin/)
[![Python versions](https://img.shields.io/pypi/pyversions/kongin.svg)](https://pypi.org/project/kongin/)
[![License](https://img.shields.io/pypi/l/kongin.svg)](https://github.com/h4roldov/kongin/blob/main/LICENSE)

[Leer en Español](README_ES.md)

Kongin is a Python client for OAI-PMH (Open Archives Initiative Protocol for Metadata Harvesting). It provides typed access to metadata records and easy export to DSpace REST API format.

## Features

- **Typed Access**: Access metadata with `record.title`, `record.creators` instead of nested dicts
- **Any XML Format**: Handles oai_dc, xoai, oaire, simple_xml, and any other schema
- **DSpace Export**: Convert records to DSpace REST API JSON format (versions 7, 8, 9, 10+)
- **Automatic Pagination**: Iterate over all records without manual token handling
- **Web Interface**: Streamlit app for visual harvesting and DSpace upload
- **Simple API**: Clean, Pythonic interface

## Installation

```bash
# Core library
pip install kongin

# With web interface
pip install kongin[web]
```

## Usage

Kongin can be used as a Python library or through a web interface.

### Option 1: Python Library (Simple)

```python
import kongin

# One-liner harvest
records = kongin.harvest('https://repositorio.example.org/oai')
for r in records:
    print(r.title, r.creators)

# Export to DSpace JSON
kongin.export_to_dspace(records, 'output.json')
```

### Option 2: Python Library (Full Control)

```python
from kongin import OAIClient

# Connect to repository
client = OAIClient('https://repositorio.example.org/oai')

# Iterate over records with typed access
for record in client.list_records(metadata_prefix='oai_dc'):
    print(f"Title: {record.title}")
    print(f"Authors: {record.creators}")
    print(f"Abstract: {record.description}")
```

### Option 3: Command Line

```bash
# Harvest and save to JSON
kongin harvest https://repositorio.example.org/oai -o records.json

# Get repository info
kongin identify https://repositorio.example.org/oai

# List available sets
kongin sets https://repositorio.example.org/oai
```

### Option 4: Web Interface

```bash
streamlit run app.py
```

The web interface allows you to:
- Enter OAI-PMH URL and harvest records
- View results in a table with metrics
- Export to JSON (DSpace format) or CSV
- Upload directly to DSpace collections

## Library Examples

### Basic Harvesting

```python
from kongin import OAIClient

client = OAIClient('https://repositorio.example.org/oai')

# List available sets
sets = client.list_sets()
for s in sets:
    print(f"{s['set_spec']}: {s['set_name']}")

# List metadata formats
formats = client.list_metadata_formats()
for f in formats:
    print(f"{f['prefix']}: {f['namespace']}")

# Get repository info
info = client.identify()
print(f"Repository: {info['repository_name']}")
```

### Harvesting Records

```python
# Harvest all records from a set
for record in client.list_records(
    metadata_prefix='simple_xml',
    set_spec='articles'
):
    print(record.title)
    print(record.creators)

# With date filtering
for record in client.list_records(
    metadata_prefix='oai_dc',
    from_date='2024-01-01',
    until_date='2024-12-31'
):
    process(record)

# Get a single record
record = client.get_record(
    identifier='oai:repo.example.org:12345',
    metadata_prefix='oai_dc'
)
```

### Accessing Metadata

```python
# Typed properties for common fields
print(record.title)        # First title
print(record.titles)       # All titles
print(record.creators)     # All authors
print(record.description)  # First description/abstract
print(record.date)         # First date
print(record.subjects)     # All subjects
print(record.identifiers)  # All identifiers (DOI, URI, etc.)

# Access any field directly
volume = record.metadata.get('oaire:citationVolume')
issue = record.metadata.get('oaire:citationIssue')
custom = record.metadata.get('custom:field')

# Get all values for a field
all_rights = record.metadata.get_all('dc:rights')

# Check if field exists
if 'dcterms:abstract' in record.metadata:
    print(record.metadata.get('dcterms:abstract'))
```

### Export to DSpace REST API

DSpace changed to a REST API starting from version 7. Kongin supports DSpace 7, 8, 9, 10 and future versions that maintain API compatibility.

```python
from kongin import OAIClient, DSpaceExporter

client = OAIClient('https://repositorio.example.org/oai')

# Export single record
record = client.get_record('oai:repo:123', 'oai_dc')
dspace_item = record.to_dspace()
# Result is JSON compatible with POST /api/core/items

# Export multiple records
records = list(client.list_records(set_spec='theses'))
exporter = DSpaceExporter()
items = exporter.export_records(records)

# Save to JSON file
exporter.save_json(records, 'dspace_import.json')

# Custom field mapping
custom_mapping = {
    'local:category': 'local.category',
    'oaire:citationVolume': 'local.citation.volume',
}
exporter = DSpaceExporter(custom_mapping)
items = exporter.export_records(records)
```

### Upload to DSpace

```python
from kongin import OAIClient, DSpaceClient

# Harvest records
oai = OAIClient('https://source-repo.org/oai')
records = list(oai.list_records(metadata_prefix='oai_dc', set_spec='articles'))

# Upload to DSpace
dspace = DSpaceClient(
    base_url='https://dspace.example.org',
    email='admin@example.org',
    password='password'
)

# List collections
collections = dspace.list_collections()
for c in collections:
    print(f"{c['name']} ({c['uuid']})")

# Upload to a collection
collection_id = collections[0]['uuid']
for record in records:
    dspace.create_item(record, collection_id)
```

### Manual Pagination

```python
# Get first page
page = client.list_records_page(metadata_prefix='oai_dc')
print(f"Total records: {page.complete_list_size}")

for record in page:
    process(record)

# Get next pages
while page.has_more:
    page = client.resume(page.resumption_token)
    for record in page:
        process(record)
```

## Configuration

```python
client = OAIClient(
    url='https://repositorio.example.org/oai',
    timeout=30,           # Request timeout in seconds
    max_retries=3,        # Retry failed requests
    http_method='GET',    # or 'POST'
    requests_args={       # Passed to requests library
        'verify': False,  # Disable SSL verification
        'headers': {'User-Agent': 'MyHarvester/1.0'}
    }
)
```

## API Reference

### OAIClient

- `identify()` - Get repository information
- `list_sets()` - List available sets
- `list_metadata_formats()` - List supported formats
- `get_record(identifier, metadata_prefix)` - Get single record
- `list_records(...)` - Iterate all records (auto-pagination)
- `list_records_page(...)` - Get single page (manual pagination)
- `list_identifiers(...)` - Iterate record headers only
- `harvest(**params)` - Raw OAI-PMH request

### Record

- `.identifier` - OAI identifier
- `.datestamp` - Last modified date
- `.set_specs` - Sets this record belongs to
- `.deleted` - True if record was deleted
- `.metadata` - Metadata container
- `.title`, `.creators`, `.description`, etc. - Typed properties
- `.to_dict()` - Export as dictionary
- `.to_dspace()` - Export for DSpace REST API

### Metadata

- `.get(key)` - Get first value
- `.get_all(key)` - Get all values as list
- `.to_dict()` - Export as dictionary

### DSpaceExporter

- `.export_record(record)` - Convert single record
- `.export_records(records)` - Convert multiple records
- `.to_json(records)` - Export as JSON string
- `.save_json(records, filepath)` - Save to file

### DSpaceClient

- `.list_collections()` - Get available collections
- `.list_communities()` - Get available communities
- `.create_item(record, collection_id)` - Create item in collection
- `.upload_records(records, collection_id)` - Upload multiple records

## DSpace Compatibility

This library is compatible with DSpace REST API versions:

| DSpace Version | API | Status |
|----------------|-----|--------|
| DSpace 7.x | REST API v7 | Supported |
| DSpace 8.x | REST API v7 | Supported |
| DSpace 9.x | REST API v7 | Supported |
| DSpace 10.x | REST API v7 | Supported |

Note: DSpace versions prior to 7 used a different API (XMLUI/JSPUI) and are not supported.

## License

MIT License - see [LICENSE](LICENSE) file.

## Author

[Haroldo Vivallo](mailto:h.vivallo@gmail.com)

## Acknowledgments

This project was developed with assistance from Claude (Anthropic). The code was reviewed, tested, and validated by the author. Kongin builds upon an earlier prototype to create a more robust and feature-complete OAI-PMH client.
