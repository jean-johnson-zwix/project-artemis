from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any

import pandas as pd
import requests
import streamlit as st
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

from detection.corrosion import CORROSION_BASELINE

load_dotenv()

DEFAULT_API_BASE_URL = os.getenv("BACKEND_BASE_URL", "http://localhost:8000")
DEFAULT_DATABASE_URL = os.getenv("DATABASE_URL", "")
SIMULATION_SCENARIOS = {
    "Corrosion spike": "corrosion_spike",
    "Sensor anomaly": "sensor_anomaly",
    "Transmitter divergence": "transmitter_divergence",
    "Inspection overdue": "inspection_overdue",
}
STATUS_COLORS = {
    "ALERT": "#b91c1c",
    "WATCH": "#d97706",
    "NORMAL": "#15803d",
}
STATUS_SORT_ORDER = {
    "ALERT": 0,
    "WATCH": 1,
    "NORMAL": 2,
}


st.set_page_config(
    page_title="The Artemis",
    page_icon=":material/sensors:",
    layout="wide",
)


@st.cache_resource
def get_engine(database_url: str):
    if not database_url:
        return None
    return create_engine(database_url)


def api_request(method: str, base_url: str, path: str, payload: dict[str, Any] | None = None) -> tuple[bool, Any]:
    url = f"{base_url.rstrip('/')}{path}"
    try:
        response = requests.request(method, url, json=payload, timeout=30)
        response.raise_for_status()
        return True, response.json() if response.content else {}
    except requests.RequestException as exc:
        return False, getattr(exc.response, "text", str(exc))


def api_download(base_url: str, doc_id: str) -> tuple[bytes | None, str]:
    """
    Fetch a document file from GET /documents/{doc_id}/download.
    Returns (content_bytes, filename) on success, or (None, error_message) on failure.
    """
    url = f"{base_url.rstrip('/')}/documents/{doc_id}/download"
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        disposition = response.headers.get("Content-Disposition", "")
        filename = doc_id
        if 'filename="' in disposition:
            filename = disposition.split('filename="')[1].rstrip('"')
        return response.content, filename
    except requests.RequestException as exc:
        return None, str(exc)


@st.cache_data(ttl=10)
def fetch_detection_demo_data(database_url: str) -> dict[str, pd.DataFrame]:
    engine = get_engine(database_url)
    if engine is None:
        return {}

    queries = {
        "assets": """
            SELECT asset_id, tag, name, area, status, criticality
            FROM assets
            ORDER BY area NULLS LAST, tag
        """,
        "sensors": """
            SELECT sensor_id, asset_id
            FROM sensor_metadata
            ORDER BY sensor_id
        """,
        "detections": """
            SELECT
                d.detection_id,
                d.detected_at,
                d.detection_type,
                d.severity,
                d.asset_id,
                d.asset_tag,
                d.asset_name,
                d.detection_data,
                d.resolved_at,
                d.resolved_by,
                d.resolution_notes,
                i.created_at AS insight_created_at,
                i.what,
                i.why,
                i.confidence,
                i.evidence,
                i.recommended_actions,
                i.relevant_docs,
                i.remaining_life_years
            FROM detections d
            LEFT JOIN insights i ON i.detection_id = d.detection_id
            ORDER BY d.detected_at DESC
            LIMIT 12
        """,
    }

    with engine.connect() as conn:
        return {name: pd.read_sql(text(query), conn) for name, query in queries.items()}



@st.cache_data(ttl=10)
def fetch_document_demo_data(database_url: str) -> dict[str, pd.DataFrame]:
    engine = get_engine(database_url)
    if engine is None:
        return {}

    queries = {
        "documents": """
            SELECT doc_id, title, doc_type, asset_id, indexed_at, page_index_tree
            FROM documents
            ORDER BY COALESCE(indexed_at, to_timestamp(0)) DESC, doc_id DESC
            LIMIT 12
        """,
        "wiki_index": """
            SELECT doc_id, title, doc_type, one_line_summary, updated_at
            FROM wiki_index
            ORDER BY updated_at DESC
            LIMIT 12
        """,
    }

    with engine.connect() as conn:
        return {name: pd.read_sql(text(query), conn) for name, query in queries.items()}


def clear_cache_and_rerun() -> None:
    st.cache_data.clear()
    st.rerun()


def pretty_time(value: Any) -> str:
    if value is None or value == "":
        return "-"
    timestamp = pd.to_datetime(value, utc=True, errors="coerce")
    if pd.isna(timestamp):
        return str(value)
    return timestamp.strftime("%Y-%m-%d %H:%M UTC")


def derive_asset_health(asset_row: pd.Series, detections_df: pd.DataFrame) -> dict[str, Any]:
    asset_detections = detections_df.loc[detections_df["asset_id"] == asset_row["asset_id"]].copy()
    # Only unresolved detections drive fleet status
    active_detections = asset_detections.loc[asset_detections["resolved_at"].isna()] if "resolved_at" in asset_detections.columns else asset_detections
    if active_detections.empty:
        return {
            "asset_id": asset_row["asset_id"],
            "asset_tag": asset_row["tag"],
            "asset_name": asset_row["name"],
            "area": asset_row["area"],
            "criticality": asset_row["criticality"],
            "fleet_status": "NORMAL",
            "latest_detection_id": None,
            "latest_detection_type": None,
            "latest_severity": None,
            "last_seen": None,
        }

    latest = active_detections.iloc[0]
    severity = str(latest["severity"]).upper()
    fleet_status = "ALERT" if severity in {"HIGH", "CRITICAL"} else "WATCH"
    return {
        "asset_id": asset_row["asset_id"],
        "asset_tag": asset_row["tag"],
        "asset_name": asset_row["name"],
        "area": asset_row["area"],
        "criticality": asset_row["criticality"],
        "fleet_status": fleet_status,
        "latest_detection_id": latest["detection_id"],
        "latest_detection_type": latest["detection_type"],
        "latest_severity": latest["severity"],
        "last_seen": latest["detected_at"],
    }


def get_supported_assets_by_scenario(assets_df: pd.DataFrame, sensors_df: pd.DataFrame) -> dict[str, list[str]]:
    asset_ids = set(assets_df["asset_id"].tolist()) if not assets_df.empty else set()
    sensor_map = {}
    if not sensors_df.empty:
        sensor_map = dict(zip(sensors_df["sensor_id"], sensors_df["asset_id"]))

    corrosion_assets = [asset_id for asset_id in CORROSION_BASELINE.keys() if asset_id in asset_ids]
    sensor_anomaly_assets = [sensor_map["V-101-PRESS"]] if "V-101-PRESS" in sensor_map else []
    divergence_assets = [sensor_map["PT-101-PV"]] if "PT-101-PV" in sensor_map else []

    return {
        "Corrosion spike": corrosion_assets,
        "Sensor anomaly": sensor_anomaly_assets,
        "Transmitter divergence": divergence_assets,
        "Inspection overdue": corrosion_assets,
    }


def get_supported_asset_ids(assets_df: pd.DataFrame, sensors_df: pd.DataFrame) -> set[str]:
    supported = set()
    for asset_ids in get_supported_assets_by_scenario(assets_df, sensors_df).values():
        supported.update(asset_ids)
    return supported


def infer_document_relevance_reason(detection_type: str, doc: dict[str, Any]) -> str:
    doc_type = str(doc.get("doc_type", "")).upper()
    snippet = str(doc.get("snippet", "")).strip()

    if detection_type == "CORROSION_THRESHOLD":
        if "INSPECTION" in doc_type:
            return "It contains inspection findings tied to corrosion, wall thickness, or remaining life."
        return "It provides corrosion-related operating or maintenance context for the affected asset."
    if detection_type == "TRANSMITTER_DIVERGENCE":
        return "It references instrumentation or operating context relevant to the diverging transmitter readings."
    if detection_type == "SENSOR_ANOMALY":
        return "It gives operating or maintenance context that may explain the abnormal sensor behavior."
    if snippet:
        return "It includes text that the retrieval step matched against this alert."
    return "It was selected by the retrieval step as supporting context for this alert."


def render_alert_details(selected_asset: pd.Series, detections_df: pd.DataFrame, api_base_url: str) -> None:
    st.markdown("### Alert Details")
    st.write(f"**Asset:** {selected_asset['asset_tag']} | {selected_asset['asset_name']}")

    if not selected_asset["latest_detection_id"]:
        st.info("The asset has no active detections. Select an asset with an active detection to see details and resolve the alert.")
        return

    selected = detections_df.loc[detections_df["detection_id"] == selected_asset["latest_detection_id"]].iloc[0]

    resolved_at = selected.get("resolved_at") if "resolved_at" in selected.index else None
    is_resolved = pd.notna(resolved_at) and resolved_at not in (None, "")

    severity = str(selected["severity"]).upper()
    severity_color = STATUS_COLORS["ALERT"] if severity in {"HIGH", "CRITICAL"} else STATUS_COLORS["WATCH"]

    header_left, header_right = st.columns([3, 2])
    with header_left:
        st.markdown(
            (
                "<div style='display:flex;gap:8px;align-items:center;flex-wrap:wrap;'>"
                f"<span style='background:{severity_color};color:white;padding:6px 10px;border-radius:999px;font-weight:700;font-size:0.85rem;'>{severity}</span>"
                f"<span style='background:#e5e7eb;color:#111827;padding:6px 10px;border-radius:999px;font-weight:700;font-size:0.85rem;'>{selected['detection_type']}</span>"
                f"<span style='background:#f3f4f6;color:#374151;padding:6px 10px;border-radius:999px;font-weight:700;font-size:0.85rem;'>{selected_asset['fleet_status']}</span>"
                "</div>"
            ),
            unsafe_allow_html=True,
        )
    with header_right:
        st.caption(f"Detected: {pretty_time(selected['detected_at'])}")
        if is_resolved:
            notes = selected.get("resolution_notes")
            st.success(f"Resolved by {selected.get('resolved_by', 'unknown')}")
            st.caption(pretty_time(resolved_at))
            if notes:
                st.caption(f"Notes: {notes}")

    st.markdown("#### Executive Summary")
    if pd.notna(selected.get("what")) and selected["what"]:
        st.write(f"**Summary:** {selected['what']}")
    else:
        st.caption("No summary available.")

    if pd.notna(selected.get("why")) and selected["why"]:
        st.write(f"**Likely cause:** {selected['why']}")
    else:
        st.caption("No root-cause explanation available.")

    def _parse_json_list(value: Any) -> list:
        if isinstance(value, list):
            return value
        if isinstance(value, str):
            try:
                return json.loads(value)
            except (ValueError, TypeError):
                return []
        return []

    evidence = _parse_json_list(selected["evidence"])
    actions = _parse_json_list(selected["recommended_actions"])
    docs = _parse_json_list(selected["relevant_docs"])

    supporting_col, response_col = st.columns(2, gap="large")
    with supporting_col:
        st.markdown("#### Supporting Evidence")
        if evidence:
            for item in evidence:
                st.write(f"- {item}")
        else:
            st.caption("No structured evidence available.")

        st.markdown("#### Relevant Documents")
        if docs:
            for doc in docs[:3]:
                doc_id = doc.get("doc_id", "unknown-doc")
                tree_path = doc.get("tree_path")
                reason = infer_document_relevance_reason(selected["detection_type"], doc)
                title_col, dl_col = st.columns([3, 1])
                with title_col:
                    st.write(f"**{doc.get('title', 'Document')}**")
                    st.caption(f"Document ID: {doc_id}")
                with dl_col:
                    file_bytes, filename = api_download(api_base_url, doc_id)
                    if file_bytes is not None:
                        mime = "application/pdf" if filename.endswith(".pdf") else "text/plain"
                        st.download_button(
                            label="Download",
                            data=file_bytes,
                            file_name=filename,
                            mime=mime,
                            key=f"dl-{selected['detection_id']}-{doc_id}",
                            use_container_width=True,
                        )
                with st.expander("Show relevance"):
                    st.write(f"**Why it's relevant:** {reason}")
                    if tree_path:
                        st.caption(f"Matched section: {tree_path}")
                    snippet = doc.get("snippet", "")
                    if snippet:
                        st.write(f"**Matched evidence:** {snippet}")
        else:
            st.caption("No related documents attached.")

    with response_col:
        st.markdown("#### Recommended Response")
        if actions:
            for item in actions:
                st.write(f"- {item}")
        else:
            st.caption("No recommended actions available.")

        if not is_resolved:
            st.divider()
            with st.form(f"resolve-form-{selected['detection_id']}"):
                resolved_by = st.text_input("Resolved by", value="operator")
                resolution_notes = st.text_area(
                    "How was it resolved?",
                    placeholder="e.g. Replaced corroded section, coating reapplied, sensor recalibrated…",
                    height=80,
                )
                if st.form_submit_button("Mark as resolved", use_container_width=True):
                    ok, response = api_request(
                        "POST",
                        api_base_url,
                        f"/detections/{selected['detection_id']}/resolve",
                        {
                            "resolved_by": resolved_by or "operator",
                            "resolution_notes": resolution_notes or None,
                        },
                    )
                    if ok:
                        st.success("Alert marked as resolved.")
                        st.cache_data.clear()
                        st.rerun()
                    else:
                        st.error("Failed to resolve alert.")
                        st.code(str(response))

def count_tree_nodes(node: dict[str, Any] | None) -> int:
    if not isinstance(node, dict):
        return 0
    children = node.get("nodes") or []
    return 1 + sum(count_tree_nodes(child) for child in children if isinstance(child, dict))


def flatten_tree(node: dict[str, Any] | None, parent_path: str = "") -> list[dict[str, Any]]:
    if not isinstance(node, dict):
        return []
    title = str(node.get("title", "Untitled"))
    path = f"{parent_path} -> {title}" if parent_path else title
    rows = [{
        "Path": path,
        "Node ID": node.get("node_id", ""),
        "Start": node.get("start_index", ""),
        "End": node.get("end_index", ""),
        "Summary": node.get("summary", ""),
    }]
    for child in node.get("nodes") or []:
        if isinstance(child, dict):
            rows.extend(flatten_tree(child, path))
    return rows


def format_tree_rows(tree: dict[str, Any] | None) -> pd.DataFrame:
    rows = flatten_tree(tree)
    formatted_rows: list[dict[str, Any]] = []
    for row in rows:
        path = str(row["Path"])
        depth = path.count(" -> ")
        section_title = path.split(" -> ")[-1]
        formatted_rows.append(
            {
                "Section": f"{'    ' * depth}{section_title}",
                "Span": f"{row['Start']} - {row['End']}",
                "Summary": row["Summary"],
            }
        )
    return pd.DataFrame(formatted_rows)


def build_tree_graph(node: dict[str, Any] | None) -> str:
    if not isinstance(node, dict):
        return "digraph G {}"

    lines = [
        "digraph DocumentTree {",
        'rankdir="TB";',
        'graph [bgcolor="transparent", pad="0.2", nodesep="0.35", ranksep="0.45"];',
        'node [shape="box", style="rounded,filled", fillcolor="#F8FAFC", color="#0F766E", fontname="Helvetica", fontsize="11", margin="0.18,0.12"];',
        'edge [color="#94A3B8", penwidth="1.2"];',
    ]

    def _walk(current: dict[str, Any]) -> None:
        current_id = str(current.get("node_id", "unknown"))
        title = str(current.get("title", "Untitled")).replace('"', '\\"')
        node_label = f"Root\\n{title}" if current_id == "root" else title
        lines.append(f'"{current_id}" [label="{node_label}"];')
        for child in current.get("nodes") or []:
            if isinstance(child, dict):
                child_id = str(child.get("node_id", "unknown"))
                lines.append(f'"{current_id}" -> "{child_id}";')
                _walk(child)

    _walk(node)
    lines.append("}")
    return "\n".join(lines)


api_base_url = DEFAULT_API_BASE_URL
database_url = DEFAULT_DATABASE_URL

detection_data = fetch_detection_demo_data(database_url) if database_url else {}
document_data = fetch_document_demo_data(database_url) if database_url else {}

title_col, refresh_col = st.columns([5, 1])
with title_col:
    st.title("Artemis Dashboard")
with refresh_col:
    st.write("")
    st.write("")
    if st.button("Refresh", use_container_width=True):
        clear_cache_and_rerun()

if not database_url:
    st.info("Set `DATABASE_URL` in the environment to show detections, insights, and document graph status from Postgres.")

detection_tab, docs_tab = st.tabs(["Monitor", "Documents Graph"])

with detection_tab:
    detections_df = detection_data.get("detections", pd.DataFrame()).copy()
    assets_df = detection_data.get("assets", pd.DataFrame()).copy()
    sensors_df = detection_data.get("sensors", pd.DataFrame()).copy()

    st.markdown(
        """
        <style>
        div[data-testid="stForm"] button[kind="secondaryFormSubmit"] {
            background: #0f766e;
            color: white;
            border: 1px solid #0f766e;
            border-radius: 999px;
            font-weight: 700;
        }
        div[data-testid="stForm"] button[kind="secondaryFormSubmit"]:hover {
            background: #115e59;
            border-color: #115e59;
            color: white;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
    with st.container(border=True):
        header_col, simulate_col = st.columns([4.2, 2.3], vertical_alignment="top")
        with header_col:
            st.subheader("Asset Monitoring Dashboard")
        with simulate_col:
            supported_assets_by_scenario = get_supported_assets_by_scenario(assets_df, sensors_df)
            with st.form("simulate-form"):
                select_col, asset_col, button_col = st.columns([2.1, 2.3, 1.2], vertical_alignment="bottom")
                with select_col:
                    scenario_label = st.selectbox(
                        "Scenario",
                        list(SIMULATION_SCENARIOS.keys()),
                        index=0,
                        label_visibility="collapsed",
                    )
                asset_options = supported_assets_by_scenario.get(scenario_label, [])
                if not asset_options:
                    asset_options = ["No supported asset"]
                with asset_col:
                    selected_asset_id = st.selectbox(
                        "Asset",
                        asset_options,
                        format_func=lambda asset_id: (
                            asset_id
                            if assets_df.empty or asset_id == "No supported asset"
                            else f"{assets_df.loc[assets_df['asset_id'] == asset_id, 'tag'].iloc[0]} | {asset_id}"
                        ),
                        label_visibility="collapsed",
                    )
                with button_col:
                    trigger = st.form_submit_button("Trigger", use_container_width=True, disabled=selected_asset_id == "No supported asset")
                if trigger and selected_asset_id != "No supported asset":
                    payload = {
                        "scenario": SIMULATION_SCENARIOS[scenario_label],
                        "asset_id": selected_asset_id,
                        "overrides": {},
                    }
                    ok, response = api_request("POST", api_base_url, "/simulate/event", payload)
                    if ok:
                        st.success("Scenario submitted")
                        st.cache_data.clear()
                        st.rerun()
                    else:
                        st.error("Scenario failed")
                        st.code(str(response))

        if not detections_df.empty:
            detections_df["detected_at"] = pd.to_datetime(detections_df["detected_at"], utc=True, errors="coerce")

        if assets_df.empty:
            st.info("Connect the database to show fleet status.")
        else:
            supported_asset_ids = get_supported_asset_ids(assets_df, sensors_df)
            assets_df = assets_df.loc[assets_df["asset_id"].isin(supported_asset_ids)].copy()

            if assets_df.empty:
                st.info("No assets in the current dataset support the simulation scenarios.")
            else:
                fleet_rows = [derive_asset_health(asset_row, detections_df) for _, asset_row in assets_df.iterrows()]
                fleet_df = pd.DataFrame(fleet_rows)
                fleet_df["status_rank"] = fleet_df["fleet_status"].map(STATUS_SORT_ORDER).fillna(99)
                fleet_df = fleet_df.sort_values(["status_rank", "asset_tag", "asset_name"]).reset_index(drop=True)
                st.session_state.setdefault("selected_asset_id", fleet_df.iloc[0]["asset_id"] if not fleet_df.empty else None)

                card_columns = st.columns(4)
                for index, asset in fleet_df.iterrows():
                    column = card_columns[index % 4]
                    status_color = STATUS_COLORS[asset["fleet_status"]]
                    is_selected = asset["asset_id"] == st.session_state.get("selected_asset_id")
                    border_color = status_color if is_selected else "#e5e7eb"
                    column.markdown(
                        (
                            f"<div style='border:2px solid {border_color};border-radius:16px;padding:16px;"
                            "margin-bottom:16px;background:#ffffff;'>"
                            f"<div style='font-size:0.85rem;color:#6b7280;margin-bottom:8px;'>{asset['area'] or 'No area'}</div>"
                            f"<div style='font-size:1.05rem;font-weight:700;margin-bottom:6px;'>{asset['asset_tag']}</div>"
                            f"<div style='font-size:0.95rem;color:#374151;margin-bottom:14px;'>{asset['asset_id']}</div>"
                            f"<div style='display:inline-block;padding:6px 10px;border-radius:999px;"
                            f"background:{status_color};color:white;font-size:0.85rem;font-weight:700;'>"
                            f"{asset['fleet_status']}</div>"
                            "</div>"
                        ),
                        unsafe_allow_html=True,
                    )
                    button_label = "Open alert" if asset["latest_detection_id"] else "Open asset"
                    if column.button(button_label, key=f"asset-{asset['asset_id']}", use_container_width=True, type="primary" if is_selected else "secondary"):
                        st.session_state["selected_asset_id"] = asset["asset_id"]
                        st.rerun()

    if "fleet_df" in locals():
        selected_asset_id = st.session_state.get("selected_asset_id")
        if selected_asset_id:
            selected_asset_rows = fleet_df.loc[fleet_df["asset_id"] == selected_asset_id]
            if not selected_asset_rows.empty:
                with st.container(border=True):
                    render_alert_details(selected_asset_rows.iloc[0], detections_df, api_base_url)

with docs_tab:
    st.subheader("Document Intelligence")
    st.caption("Ingest a document, track its indexing state, and inspect the generated document map used for retrieval.")

    docs_df = document_data.get("documents", pd.DataFrame()).copy()
    wiki_df = document_data.get("wiki_index", pd.DataFrame()).copy()
    asset_options = detection_data.get("assets", pd.DataFrame()).copy()

    ingest_col, output_col = st.columns([1, 1.35], gap="large")

    with ingest_col:
        with st.container(border=True):
            st.markdown("### Ingest Document")
            with st.form("document-ingest-form"):
                doc_id = st.text_input("Document ID", value="DOC-DEMO-001")
                doc_title = st.text_input("Title", value="V-101 Demo Inspection Report")
                selected_doc_asset = st.selectbox(
                    "Asset",
                    asset_options["asset_id"].tolist() if not asset_options.empty else ["AREA-HP-SEP:V-101"],
                    format_func=lambda asset_id: (
                        asset_id
                        if asset_options.empty
                        else f"{asset_options.loc[asset_options['asset_id'] == asset_id, 'tag'].iloc[0]} | {asset_id}"
                    ),
                )
                doc_type = st.text_input("Document type", value="INSPECTION_REPORT")
                doc_content = st.text_area(
                    "Content",
                    height=260,
                    value=(
                        "HP Separator V-101 Inspection Report\n\n"
                        "Executive Summary\n"
                        "Inspection on V-101 found wall thickness at 4.7 mm at shell grid E-3. "
                        "Design minimum is 5.0 mm. Corrosion rate is estimated at 0.38 mm/year.\n\n"
                        "Recommendations\n"
                        "Re-inspect V-101 within 6 months. Review coating condition and confirm remaining allowance."
                    ),
                )
                with st.expander("Advanced fields"):
                    doc_revision = st.text_input("Revision", value="A")
                    doc_author = st.text_input("Author", value="Demo Engineer")

                ingest_document = st.form_submit_button("Ingest document", use_container_width=True)
                if ingest_document:
                    payload = {
                        "doc_id": doc_id,
                        "asset_id": selected_doc_asset or None,
                        "doc_type": doc_type,
                        "title": doc_title,
                        "revision": doc_revision or None,
                        "author": doc_author or None,
                        "issue_date": datetime.now(timezone.utc).isoformat(),
                        "content": doc_content,
                    }
                    ok, response = api_request("POST", api_base_url, "/documents/ingest", payload)
                    if ok:
                        st.session_state["selected_document_id"] = doc_id
                        st.success("Document submitted for indexing")
                        st.cache_data.clear()
                        st.rerun()
                    else:
                        st.error("Document ingest failed")
                        st.code(str(response))

            st.caption("The document map breaks raw text into navigable sections so alerts can retrieve the most relevant evidence.")

    with output_col:
        with st.container(border=True):
            st.markdown("### Document Output")
            if docs_df.empty:
                st.info("Ingest a document to see its indexing state, AI summary, and generated document map.")
            else:
                doc_options = docs_df["doc_id"].tolist()
                default_doc_id = st.session_state.get("selected_document_id", doc_options[0])
                if default_doc_id not in doc_options:
                    default_doc_id = doc_options[0]
                selected_doc_id = st.selectbox(
                    "Selected document",
                    doc_options,
                    index=doc_options.index(default_doc_id),
                    format_func=lambda value: (
                        f"{value} | {docs_df.loc[docs_df['doc_id'] == value, 'title'].iloc[0]}"
                    ),
                )
                st.session_state["selected_document_id"] = selected_doc_id

                selected_doc = docs_df.loc[docs_df["doc_id"] == selected_doc_id].iloc[0]
                tree = selected_doc["page_index_tree"] if isinstance(selected_doc["page_index_tree"], dict) else None
                indexed = pd.notna(selected_doc["indexed_at"])
                status_text = "Graph ready" if indexed else "Indexing in progress"
                status_variant = "ready" if indexed else "indexing"

                if status_variant == "ready":
                    st.success(f"{status_text} for {selected_doc['title']}")
                else:
                    st.warning(f"{status_text} for {selected_doc['title']}")

                meta_cols = st.columns(4)
                with meta_cols[0]:
                    st.metric("Status", "Ready" if indexed else "Indexing")
                with meta_cols[1]:
                    st.metric("Document ID", selected_doc["doc_id"])
                with meta_cols[2]:
                    st.metric("Asset", selected_doc["asset_id"] or "-")
                with meta_cols[3]:
                    st.metric("Graph Nodes", count_tree_nodes(tree))

                st.caption(f"Indexed at: {pretty_time(selected_doc['indexed_at']) if indexed else '-'}")

                wiki_match = wiki_df.loc[wiki_df["doc_id"] == selected_doc_id]
                st.markdown("#### AI Summary")
                if not wiki_match.empty:
                    st.write(wiki_match.iloc[0]["one_line_summary"])
                else:
                    st.caption("AI summary will appear after indexing completes.")

                st.markdown("#### Generated Document Map")
                if tree:
                    st.markdown("**Tree Diagram**")
                    st.graphviz_chart(build_tree_graph(tree), use_container_width=True)
                    st.markdown("**Section Table**")
                    formatted_tree_df = format_tree_rows(tree)
                    st.dataframe(formatted_tree_df, use_container_width=True, hide_index=True)
                else:
                    st.info("The generated document map will appear here once indexing completes.")

                with st.expander("Technical JSON"):
                    st.code(json.dumps(selected_doc["page_index_tree"], indent=2, default=str), language="json")
