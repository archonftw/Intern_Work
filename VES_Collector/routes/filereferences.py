import io
import logging

from flask import Blueprint, request, jsonify, abort, send_file
from services.db_service import get_db_connection, release_db_connection
from psycopg2.extras import RealDictCursor
from services.file_ready_service import (
    fetch_file_content,
    FileFetchError,
)
from storage import memory as storage_memory

logger = logging.getLogger("VES-COLLECTOR")

filereferences_bp = Blueprint(
    "filereferences",
    __name__,
    url_prefix=""
)


@filereferences_bp.route("/eventListener/v7", methods=["GET"])
def file_references():
    file_id = request.args.get("file_id")

    if not file_id:
        source_name = request.args.get("sourceName")
        limit = int(request.args.get("limit", 100))
        
        # Fetch file references from PostgreSQL stored stndDefined events
        entries = _list_file_entries_from_db(source_name=source_name, limit=limit)
        return jsonify({"count": len(entries), "entries": entries})

    entry = _get_file_entry_from_db(file_id)
    if entry is None:
        abort(404, description="No such file entry found")

    action = request.args.get("action")

    if action is None:
        return jsonify(entry)

    if action == "preview":
        return _preview(file_id, entry)

    if action == "download":
        return _download(entry)

    return jsonify({"error": f"Unknown action '{action}'. Use 'preview' or 'download'."}), 400


def _list_file_entries_from_db(source_name=None, limit=100):
    """
    Extracts fileReady details from stndDefined events stored in PostgreSQL.
    """
    conn = get_db_connection()
    if not conn:
        # Fallback to in-memory FILE_STORE
        entries = []
        for finfo in storage_memory.FILE_STORE[:limit]:
            entries.append({
                "fileId": finfo.get("fileId"),
                "receivedAt": finfo.get("receivedAt"),
                "sourceName": finfo.get("sourceName"),
                "fileFormat": finfo.get("fileFormat"),
                "fileDataType": finfo.get("fileDataType"),
                "fileSize": finfo.get("fileSize"),
                "fileReadyTime": finfo.get("fileReadyTime"),
                "fileExpirationTime": finfo.get("fileExpirationTime"),
                "fileLocation": finfo.get("fileLocation")
            })
        return entries

    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            query = """
                SELECT received_at, source_name, raw_payload 
                FROM ves_events 
                WHERE domain = 'stndDefined'
            """
            params = []
            if source_name:
                query += " AND source_name = %s"
                params.append(source_name)

            query += " ORDER BY received_at DESC LIMIT %s"
            params.append(limit)

            cur.execute(query, tuple(params))
            rows = cur.fetchall()

            entries = []
            for row in rows:
                raw = row["raw_payload"]
                stnd = raw.get("stndDefinedFields", {})
                data = stnd.get("data", {})
                
                # Check for fileInfoList or fileReady attributes
                file_info_list = data.get("fileInfoList", [])
                if not file_info_list and ("fileId" in data or "fileLocation" in data):
                    file_info_list = [data]

                for finfo in file_info_list:
                    entries.append({
                        "fileId": finfo.get("fileId"),
                        "receivedAt": row["received_at"].isoformat() if row["received_at"] else None,
                        "sourceName": row["source_name"],
                        "fileFormat": finfo.get("fileFormat"),
                        "fileDataType": finfo.get("fileDataType"),
                        "fileSize": finfo.get("fileSize"),
                        "fileReadyTime": finfo.get("fileReadyTime"),
                        "fileExpirationTime": finfo.get("fileExpirationTime"),
                        "fileLocation": finfo.get("fileLocation")
                    })
            return entries
    except Exception as e:
        logger.error("Failed to list file entries from DB: %s", e)
        return []
    finally:
        release_db_connection(conn)


def _get_file_entry_from_db(file_id):
    entries = _list_file_entries_from_db(limit=500)
    for entry in entries:
        if entry.get("fileId") == file_id:
            return entry
    return None


def _preview(file_id, entry):
    try:
        filename, content, content_type = fetch_file_content(entry.get("fileLocation", ""))
    except FileFetchError as e:
        return jsonify({
            "fileId": file_id,
            "fetched": False,
            "reason": str(e),
            "metadata": entry,
        }), 200

    content_type = content_type or "application/octet-stream"
    is_textual = content_type.startswith("text/") or content_type in (
        "application/json", "application/xml"
    )

    payload = {
        "fileId": file_id,
        "filename": filename,
        "contentType": content_type,
        "sizeBytes": len(content),
        "fetched": True,
        "metadata": entry,
    }

    if is_textual:
        payload["textContent"] = content.decode("utf-8", errors="replace")
    else:
        payload["note"] = "Binary or non-text content; use action=download to retrieve raw bytes."

    return jsonify(payload)


def _download(entry):
    try:
        filename, content, content_type = fetch_file_content(entry.get("fileLocation", ""))
    except FileFetchError as e:
        return jsonify({"error": str(e)}), 502

    return send_file(
        io.BytesIO(content),
        mimetype=content_type or "application/octet-stream",
        as_attachment=True,
        download_name=filename,
    )