# Kongin

Kongin es un cliente Python para OAI-PMH (Open Archives Initiative Protocol for Metadata Harvesting). Proporciona acceso tipado a registros de metadatos y exportacion facil al formato REST API de DSpace.

## Caracteristicas

- **Acceso Tipado**: Accede a metadatos con `record.title`, `record.creators` en lugar de diccionarios anidados
- **Cualquier Formato XML**: Soporta oai_dc, xoai, oaire, simple_xml y cualquier otro esquema
- **Exportacion DSpace**: Convierte registros a formato JSON de DSpace REST API (versiones 7, 8, 9, 10+)
- **Paginacion Automatica**: Itera sobre todos los registros sin manejar tokens manualmente
- **Interfaz Web**: Aplicacion Streamlit para cosecha visual y subida a DSpace
- **API Simple**: Interfaz limpia y Pythonica

## Instalacion

```bash
# Libreria base
pip install kongin

# Con interfaz web
pip install kongin[web]
```

## Uso

Kongin puede usarse como libreria Python o a traves de una interfaz web.

### Opcion 1: Libreria Python (Simple)

```python
import kongin

# Cosecha en una linea
records = kongin.harvest('https://repositorio.example.org/oai')
for r in records:
    print(r.title, r.creators)

# Exportar a JSON de DSpace
kongin.export_to_dspace(records, 'output.json')
```

### Opcion 2: Libreria Python (Control Total)

```python
from kongin import OAIClient

# Conectar al repositorio
client = OAIClient('https://repositorio.example.org/oai')

# Iterar sobre registros con acceso tipado
for record in client.list_records(metadata_prefix='oai_dc'):
    print(f"Titulo: {record.title}")
    print(f"Autores: {record.creators}")
    print(f"Resumen: {record.description}")
```

### Opcion 3: Linea de Comandos

```bash
# Cosechar y guardar a JSON
kongin harvest https://repositorio.example.org/oai -o records.json

# Obtener info del repositorio
kongin identify https://repositorio.example.org/oai

# Listar sets disponibles
kongin sets https://repositorio.example.org/oai
```

### Opcion 4: Interfaz Web

```bash
streamlit run app.py
```

La interfaz web permite:
- Ingresar URL OAI-PMH y cosechar registros
- Ver resultados en una tabla con metricas
- Exportar a JSON (formato DSpace) o CSV
- Subir directamente a colecciones de DSpace

## Ejemplos de Libreria

### Cosecha Basica

```python
from kongin import OAIClient

client = OAIClient('https://repositorio.example.org/oai')

# Listar sets disponibles
sets = client.list_sets()
for s in sets:
    print(f"{s['set_spec']}: {s['set_name']}")

# Listar formatos de metadatos
formats = client.list_metadata_formats()
for f in formats:
    print(f"{f['prefix']}: {f['namespace']}")

# Obtener informacion del repositorio
info = client.identify()
print(f"Repositorio: {info['repository_name']}")
```

### Cosecha de Registros

```python
# Cosechar todos los registros de un set
for record in client.list_records(
    metadata_prefix='simple_xml',
    set_spec='articles'
):
    print(record.title)
    print(record.creators)

# Con filtro de fechas
for record in client.list_records(
    metadata_prefix='oai_dc',
    from_date='2024-01-01',
    until_date='2024-12-31'
):
    procesar(record)

# Obtener un registro especifico
record = client.get_record(
    identifier='oai:repo.example.org:12345',
    metadata_prefix='oai_dc'
)
```

### Acceso a Metadatos

```python
# Propiedades tipadas para campos comunes
print(record.title)        # Primer titulo
print(record.titles)       # Todos los titulos
print(record.creators)     # Todos los autores
print(record.description)  # Primera descripcion/resumen
print(record.date)         # Primera fecha
print(record.subjects)     # Todos los temas
print(record.identifiers)  # Todos los identificadores (DOI, URI, etc.)

# Acceder a cualquier campo directamente
volumen = record.metadata.get('oaire:citationVolume')
numero = record.metadata.get('oaire:citationIssue')
custom = record.metadata.get('custom:field')

# Obtener todos los valores de un campo
todos_derechos = record.metadata.get_all('dc:rights')

# Verificar si existe un campo
if 'dcterms:abstract' in record.metadata:
    print(record.metadata.get('dcterms:abstract'))
```

### Exportar a DSpace REST API

DSpace cambio a una REST API a partir de la version 7. Kongin soporta DSpace 7, 8, 9, 10 y versiones futuras que mantengan compatibilidad con la API.

```python
from kongin import OAIClient, DSpaceExporter

client = OAIClient('https://repositorio.example.org/oai')

# Exportar un registro
record = client.get_record('oai:repo:123', 'oai_dc')
dspace_item = record.to_dspace()
# Resultado es JSON compatible con POST /api/core/items

# Exportar multiples registros
records = list(client.list_records(set_spec='theses'))
exporter = DSpaceExporter()
items = exporter.export_records(records)

# Guardar a archivo JSON
exporter.save_json(records, 'dspace_import.json')

# Mapeo de campos personalizado
mapeo_custom = {
    'local:category': 'local.category',
    'oaire:citationVolume': 'local.citation.volume',
}
exporter = DSpaceExporter(mapeo_custom)
items = exporter.export_records(records)
```

### Subir a DSpace

```python
from kongin import OAIClient, DSpaceClient

# Cosechar registros
oai = OAIClient('https://repo-origen.org/oai')
records = list(oai.list_records(metadata_prefix='oai_dc', set_spec='articles'))

# Subir a DSpace
dspace = DSpaceClient(
    base_url='https://dspace.example.org',
    email='admin@example.org',
    password='password'
)

# Listar colecciones
collections = dspace.list_collections()
for c in collections:
    print(f"{c['name']} ({c['uuid']})")

# Subir a una coleccion
collection_id = collections[0]['uuid']
for record in records:
    dspace.create_item(record, collection_id)
```

### Paginacion Manual

```python
# Obtener primera pagina
page = client.list_records_page(metadata_prefix='oai_dc')
print(f"Total registros: {page.complete_list_size}")

for record in page:
    procesar(record)

# Obtener siguientes paginas
while page.has_more:
    page = client.resume(page.resumption_token)
    for record in page:
        procesar(record)
```

## Configuracion

```python
client = OAIClient(
    url='https://repositorio.example.org/oai',
    timeout=30,           # Timeout en segundos
    max_retries=3,        # Reintentos para requests fallidos
    http_method='GET',    # o 'POST'
    requests_args={       # Pasado a la libreria requests
        'verify': False,  # Desactivar verificacion SSL
        'headers': {'User-Agent': 'MiCosechador/1.0'}
    }
)
```

## Referencia de API

### OAIClient

- `identify()` - Obtener informacion del repositorio
- `list_sets()` - Listar sets disponibles
- `list_metadata_formats()` - Listar formatos soportados
- `get_record(identifier, metadata_prefix)` - Obtener un registro
- `list_records(...)` - Iterar todos los registros (paginacion automatica)
- `list_records_page(...)` - Obtener una pagina (paginacion manual)
- `list_identifiers(...)` - Iterar solo headers de registros
- `harvest(**params)` - Request OAI-PMH crudo

### Record

- `.identifier` - Identificador OAI
- `.datestamp` - Fecha de ultima modificacion
- `.set_specs` - Sets a los que pertenece
- `.deleted` - True si el registro fue eliminado
- `.metadata` - Contenedor de metadatos
- `.title`, `.creators`, `.description`, etc. - Propiedades tipadas
- `.to_dict()` - Exportar como diccionario
- `.to_dspace()` - Exportar para DSpace REST API

### Metadata

- `.get(key)` - Obtener primer valor
- `.get_all(key)` - Obtener todos los valores como lista
- `.to_dict()` - Exportar como diccionario

### DSpaceExporter

- `.export_record(record)` - Convertir un registro
- `.export_records(records)` - Convertir multiples registros
- `.to_json(records)` - Exportar como string JSON
- `.save_json(records, filepath)` - Guardar a archivo

### DSpaceClient

- `.list_collections()` - Obtener colecciones disponibles
- `.list_communities()` - Obtener comunidades disponibles
- `.create_item(record, collection_id)` - Crear item en coleccion
- `.upload_records(records, collection_id)` - Subir multiples registros

## Compatibilidad con DSpace

Esta libreria es compatible con las versiones de DSpace REST API:

| Version DSpace | API | Estado |
|----------------|-----|--------|
| DSpace 7.x | REST API v7 | Soportado |
| DSpace 8.x | REST API v7 | Soportado |
| DSpace 9.x | REST API v7 | Soportado |
| DSpace 10.x | REST API v7 | Soportado |

Nota: Las versiones de DSpace anteriores a 7 usaban una API diferente (XMLUI/JSPUI) y no estan soportadas.

## Licencia

Licencia MIT - ver archivo [LICENSE](LICENSE).

## Autor

[Haroldo Vivallo](mailto:h.vivallo@gmail.com)

## Reconocimientos

Este proyecto fue desarrollado con asistencia de Claude (Anthropic). El codigo fue revisado, probado y validado por el autor. Kongin se construye sobre un prototipo anterior para crear un cliente OAI-PMH mas robusto y completo.
