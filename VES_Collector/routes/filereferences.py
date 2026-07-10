import io
import logging

from flask import Blueprint, request, jsonify, abort, send_file

from services.file_ready_service import (
    list_file_entries,
    get_file_entry,
    fetch_file_content,
    FileFetchError,
)

logger = logging.getLogger("VES-COLLECTOR")

# Same base path as the real VES ingestion endpoint (POST /eventListener/v7,
# owned by routes/ingestion.py). That's safe: Flask dispatches by
# (path, method), and this blueprint only ever registers GET here, so
# there's no collision with the POST handler.
#
# No ingest route in this file - fileReady events arrive through the
# existing pipeline: /eventListener/v7 (POST) -> process_single_event ->
# process_stnd -> handle_file_ready (see services/stnd_service.py).
# This blueprint is read-only, and deliberately a single URL:
#   GET /eventListener/v7                          -> list files
#   GET /eventListener/v7?file_id=X                -> one file's metadata
#   GET /eventListener/v7?file_id=X&action=preview  -> fetch + preview
#   GET /eventListener/v7?file_id=X&action=download -> fetch + download

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
        limit = request.args.get("limit", 100)
        entries = list_file_entries(source_name=source_name, limit=limit)
        return jsonify({"count": len(entries), "entries": entries})

    entry = get_file_entry(file_id)
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