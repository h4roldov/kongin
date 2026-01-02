#!/usr/bin/env python3
"""
Kongin Web Interface - OAI-PMH Harvester with DSpace Export.

Run with: streamlit run app.py
"""

import streamlit as st
import pandas as pd

from kongin import OAIClient, DSpaceExporter
from kongin.dspace_client import DSpaceClient, DSpaceAuthError, DSpaceUploadError

# Page config
st.set_page_config(
    page_title="Kongin - OAI-PMH Harvester",
    page_icon="📚",
    layout="wide"
)

# Initialize session state
if 'records' not in st.session_state:
    st.session_state.records = []
if 'harvest_error' not in st.session_state:
    st.session_state.harvest_error = None
if 'dspace_collections' not in st.session_state:
    st.session_state.dspace_collections = []


def harvest_records(url: str, prefix: str, set_spec: str, limit: int):
    """Harvest records from OAI-PMH endpoint."""
    try:
        client = OAIClient(url)
        records = []
        for i, record in enumerate(client.list_records(
            metadata_prefix=prefix,
            set_spec=set_spec or None
        )):
            records.append(record)
            if limit > 0 and i + 1 >= limit:
                break
        st.session_state.records = records
        st.session_state.harvest_error = None
    except Exception as e:
        st.session_state.harvest_error = str(e)
        st.session_state.records = []


def get_date_range(records):
    """Extract date range from records."""
    dates = [r.date for r in records if r.date]
    if not dates:
        return "N/A"
    dates_sorted = sorted(dates)
    return f"{dates_sorted[0][:4]} - {dates_sorted[-1][:4]}"


def get_unique_sets(records):
    """Count unique sets in records."""
    all_sets = set()
    for r in records:
        all_sets.update(r.set_specs)
    return len(all_sets)


# Sidebar: Configuration
with st.sidebar:
    st.header("Configuracion")

    # OAI-PMH settings
    st.subheader("OAI-PMH")
    oai_url = st.text_input(
        "URL OAI-PMH",
        placeholder="https://repositorio.example.org/oai"
    )
    prefix = st.selectbox(
        "Metadata Prefix",
        ["oai_dc", "xoai", "oaire", "simple_xml", "dim", "mets"]
    )
    set_spec = st.text_input("Set (opcional)")
    limit = st.number_input(
        "Limite de registros (0 = sin limite)",
        min_value=0,
        value=100,
        step=10
    )

    if st.button("Cosechar", type="primary", use_container_width=True):
        if oai_url:
            with st.spinner("Cosechando..."):
                harvest_records(oai_url, prefix, set_spec, limit)
        else:
            st.error("Ingresa una URL")

    st.divider()

    # DSpace settings
    st.subheader("DSpace")
    dspace_url = st.text_input(
        "URL DSpace",
        placeholder="https://demo.dspace.org"
    )
    dspace_email = st.text_input("Email")
    dspace_password = st.text_input("Password", type="password")

    if st.button("Conectar a DSpace", use_container_width=True):
        if all([dspace_url, dspace_email, dspace_password]):
            try:
                with st.spinner("Conectando..."):
                    client = DSpaceClient(
                        dspace_url,
                        dspace_email,
                        dspace_password,
                        verify_ssl=False
                    )
                    st.session_state.dspace_collections = client.list_collections()
                    st.success(f"Conectado. {len(st.session_state.dspace_collections)} colecciones.")
            except DSpaceAuthError as e:
                st.error(f"Error de autenticacion: {e}")
        else:
            st.error("Completa todos los campos")


# Main content
st.title("Kongin - OAI-PMH Harvester")

# Show harvest error if any
if st.session_state.harvest_error:
    st.error(f"Error: {st.session_state.harvest_error}")

# Show results if we have records
if st.session_state.records:
    records = st.session_state.records

    # Metrics
    st.subheader("Metricas")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total registros", len(records))
    col2.metric("Sets unicos", get_unique_sets(records))
    col3.metric("Rango fechas", get_date_range(records))
    col4.metric("Con abstract", sum(1 for r in records if r.description))

    st.divider()

    # Records table
    st.subheader("Registros")

    # Build dataframe
    df = pd.DataFrame([{
        'Titulo': r.title or '(sin titulo)',
        'Autores': ', '.join(r.creators) if r.creators else '',
        'Fecha': r.date or '',
        'Tipo': ', '.join(r.types) if r.types else '',
        'ID': r.identifier
    } for r in records])

    # Show table with selection
    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True,
        column_config={
            'Titulo': st.column_config.TextColumn(width='large'),
            'Autores': st.column_config.TextColumn(width='medium'),
            'ID': st.column_config.TextColumn(width='medium'),
        }
    )

    st.divider()

    # Export section
    st.subheader("Exportar")

    col1, col2 = st.columns(2)

    with col1:
        # JSON export
        exporter = DSpaceExporter()
        json_data = exporter.to_json(records)

        st.download_button(
            "Descargar JSON (DSpace format)",
            json_data,
            file_name="records_dspace.json",
            mime="application/json",
            use_container_width=True
        )

    with col2:
        # CSV export
        csv_data = df.to_csv(index=False)
        st.download_button(
            "Descargar CSV",
            csv_data,
            file_name="records.csv",
            mime="text/csv",
            use_container_width=True
        )

    st.divider()

    # DSpace upload section
    st.subheader("Subir a DSpace")

    if st.session_state.dspace_collections:
        collections = st.session_state.dspace_collections

        selected_collection = st.selectbox(
            "Seleccionar coleccion",
            options=range(len(collections)),
            format_func=lambda i: f"{collections[i]['name']} ({collections[i]['handle']})"
        )

        if st.button("Subir registros a DSpace", type="primary"):
            collection_id = collections[selected_collection]['uuid']

            progress = st.progress(0, text="Subiendo...")
            status = st.empty()

            try:
                client = DSpaceClient(
                    dspace_url,
                    dspace_email,
                    dspace_password,
                    verify_ssl=False
                )

                uploaded = 0
                errors = []

                for i, record in enumerate(records):
                    try:
                        client.create_item(record, collection_id)
                        uploaded += 1
                    except DSpaceUploadError as e:
                        errors.append(str(e))

                    progress.progress(
                        (i + 1) / len(records),
                        text=f"Subiendo {i + 1} de {len(records)}..."
                    )

                progress.empty()

                if errors:
                    status.warning(
                        f"Subidos: {uploaded}/{len(records)}. "
                        f"Errores: {len(errors)}"
                    )
                    with st.expander("Ver errores"):
                        for err in errors:
                            st.text(err)
                else:
                    status.success(f"Subidos {uploaded} registros correctamente.")

            except DSpaceAuthError as e:
                progress.empty()
                status.error(f"Error de autenticacion: {e}")

    else:
        st.info("Conecta a DSpace primero (panel izquierdo)")

else:
    # No records yet
    st.info("Ingresa una URL OAI-PMH y presiona 'Cosechar' para comenzar.")

    # Example URLs
    with st.expander("URLs de ejemplo"):
        st.code("""
# Repositorios de prueba:
https://repositorio.ufro.cl/oai
https://repositorio.uchile.cl/oai/request
https://repositorio.unal.edu.co/oai/request
        """)
