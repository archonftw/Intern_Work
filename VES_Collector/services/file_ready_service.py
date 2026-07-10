import io
import ipaddress
import logging
import mimetypes
import os
import socket
import uuid
import ftplib
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse, unquote

from jsonschema import validate

import storage.memory

from schemas.schema import FILE_READY_SCHEMA
from config import (
    MAX_FILE_STORE,
    ALLOW_REMOTE_FETCH,
    ALLOW_PRIVATE_IPS,
    MAX_FETCH_BYTES,
    FETCH_TIMEOUT_SEC,
)

try:
    import requests
    HAVE_REQUESTS = True
except ImportError:
    HAVE_REQUESTS = False

try:
    import paramiko
    HAVE_PARAMIKO = True
except ImportError:
    HAVE_PARAMIKO = False


logger = logging.getLogger("VES-COLLECTOR")


class FileFetchError(Exception):
    """Raised when a file cannot be fetched safely."""


# ------------------------------------------------------------------
# Detection / extraction / storage
# ------------------------------------------------------------------

def is_file_ready_event(event: Dict[str, Any]) -> bool:
    """
    True only for stndDefined events that actually carry a fileInfoList.
    Domain-gated first, since a fileInfoList-shaped array under some other
    domain shouldn't be treated as fileReady.
    """
    if event.get("commonEventHeader", {}).get("domain") != "stndDefined":
        return False

    stnd = event.get("stndDefinedFields")
    if not stnd:
        return False

    data = stnd.get("data", {})
    return isinstance(data.get("fileInfoList"), list)


def extract_file_entries(event: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Flatten a fileReady event into one record per file, defensively."""
    header = event.get("commonEventHeader", {})
    stnd = event.get("stndDefinedFields", {})
    data = stnd.get("data", {})

    base = {
        "eventId": header.get("eventId"),
        "eventType": header.get("eventType"),
        "eventName": header.get("eventName"),
        "sourceName": header.get("sourceName"),
        "reportingEntityName": header.get("reportingEntityName"),
        "priority": header.get("priority"),
        "domain": header.get("domain"),
        "stndDefinedFieldsVersion": stnd.get("stndDefinedFieldsVersion"),
        "systemDN": data.get("systemDN"),
        "additionalText": data.get("additionalText"),
        "eventTime": data.get("eventTime"),
    }

    records = []
    file_list = data.get("fileInfoList") or []

    for file_info in file_list:
        if not isinstance(file_info, dict):
            continue

        record = dict(base)
        record.update(
            {
                "fileId": str(uuid.uuid4()),
                "receivedAt": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
                "fileSize": file_info.get("fileSize"),
                "fileLocation": file_info.get("fileLocation"),
                "fileFormat": file_info.get("fileFormat"),
                "fileDataType": file_info.get("fileDataType"),
                "fileReadyTime": file_info.get("fileReadyTime"),
                "fileExpirationTime": file_info.get("fileExpirationTime"),
                "fileCompression": file_info.get("fileCompression"),
            }
        )
        records.append(record)

    return records


def _redact_location(location: str) -> str:
    """Strip embedded credentials before logging (sftp://user:pass@host/path)."""
    try:
        parsed = urlparse(location)
        if parsed.username or parsed.password:
            host = parsed.hostname or ""
            if parsed.port:
                host += f":{parsed.port}"
            return parsed._replace(netloc=host).geturl()
    except Exception:
        pass
    return location


def store_file_entries(records: List[Dict[str, Any]]) -> None:
    if isinstance(storage.memory.FILE_STORE, list):
        storage.memory.FILE_STORE.extend(records)
        while len(storage.memory.FILE_STORE) > MAX_FILE_STORE:
            try:
                storage.memory.FILE_STORE.pop(0)
            except IndexError:
                break
    else:
        for record in records:
            storage.memory.FILE_STORE.append(record)

    for record in records:
        logger.info(
            "FILE_READY | source=%s | file=%s | size=%s",
            record.get("sourceName"),
            _redact_location(record.get("fileLocation", "")),
            record.get("fileSize"),
        )


def process_file_ready(event: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Validate, extract and store fileReady entries.

    The real event arrives wrapped (commonEventHeader + stndDefinedFields
    as siblings), but FILE_READY_SCHEMA expects a flat object. We
    reconstruct that flat shape from the header for validation purposes.

    IMPORTANT: only include a key if the header actually has it. Writing
    `key: None` for an absent-but-optional field (e.g. vesEventListenerVersion)
    makes jsonschema treat it as "present but wrong type" instead of
    "absent", which would wrongly reject valid events that simply don't
    populate every optional header field.
    """
    header = event.get("commonEventHeader", {})

    validation_payload = {
        "domain": header.get("domain"),
        "eventName": header.get("eventName"),
        "sourceName": header.get("sourceName"),
        "stndDefinedFields": event.get("stndDefinedFields"),
    }

    optional_fields = [
        "eventType", "priority", "version", "reportingEntityName",
        "sequence", "lastEpochMicrosec", "vesEventListenerVersion",
    ]
    for field in optional_fields:
        value = header.get(field)
        if value is not None:
            validation_payload[field] = value

    validate(validation_payload, FILE_READY_SCHEMA)

    records = extract_file_entries(event)
    store_file_entries(records)

    logger.info("Stored %d fileReady file(s)", len(records))
    return records


def get_file_entry(file_id: str) -> Optional[Dict[str, Any]]:
    for record in storage.memory.FILE_STORE:
        if record.get("fileId") == file_id:
            return record
    return None


def list_file_entries(
    source_name: Optional[str] = None,
    limit: int = 100,
) -> List[Dict[str, Any]]:

    results = list(storage.memory.FILE_STORE)

    if source_name:
        results = [r for r in results if r.get("sourceName") == source_name]

    try:
        limit = max(1, min(int(limit), MAX_FILE_STORE))
    except Exception:
        limit = 100

    return list(reversed(results))[:limit]


# ------------------------------------------------------------------
# Fetching - credentials come embedded in fileLocation itself, e.g.
#   sftp://username:password@ip:22/path/file.xml
# ------------------------------------------------------------------

def _host_is_private(hostname: str) -> bool:
    try:
        infos = socket.getaddrinfo(hostname, None)
    except socket.gaierror:
        return True
    for info in infos:
        ip = info[4][0]
        try:
            addr = ipaddress.ip_address(ip)
        except ValueError:
            continue
        if addr.is_private or addr.is_loopback or addr.is_link_local or addr.is_reserved:
            return True
    return False


def _guard_remote_host(hostname: str) -> None:
    if not ALLOW_REMOTE_FETCH:
        raise FileFetchError(
            "Remote fetching is disabled (ALLOW_REMOTE_FETCH=False in config). "
            "Metadata is available but content will not be fetched."
        )
    if not ALLOW_PRIVATE_IPS and _host_is_private(hostname):
        raise FileFetchError(
            f"Refusing to fetch from private/loopback host '{hostname}' "
            "(SSRF guard). Set ALLOW_PRIVATE_IPS=True in config if intentional "
            "(e.g. a local test generator)."
        )


def fetch_file_content(file_location: str):
    """
    Fetch file content for a fileLocation URL. Username/password embedded in
    the URL are extracted and used automatically for ftp/sftp.
    Returns (filename, content_bytes, content_type). Raises FileFetchError.
    """
    parsed = urlparse(file_location)
    scheme = parsed.scheme.lower()

    if scheme in ("", "file"):
        return _fetch_local(parsed, file_location)
    if scheme in ("http", "https"):
        return _fetch_http(parsed, file_location)
    if scheme == "ftp":
        return _fetch_ftp(parsed)
    if scheme == "sftp":
        return _fetch_sftp(parsed)

    raise FileFetchError(f"Unsupported or unrecognized scheme: '{scheme}'")


def _fetch_local(parsed, file_location: str):
    path = parsed.path if parsed.scheme == "file" else file_location
    if not os.path.isfile(path):
        raise FileFetchError(f"Local file not found: {path}")

    size = os.path.getsize(path)
    if size > MAX_FETCH_BYTES:
        raise FileFetchError(f"File too large to preview ({size} bytes)")

    with open(path, "rb") as f:
        content = f.read()

    filename = os.path.basename(path)
    content_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"
    return filename, content, content_type


def _fetch_http(parsed, file_location: str):
    _guard_remote_host(parsed.hostname)
    if not HAVE_REQUESTS:
        raise FileFetchError("'requests' library not installed; cannot fetch http(s) files")

    try:
        resp = requests.get(file_location, stream=True, timeout=FETCH_TIMEOUT_SEC)
        resp.raise_for_status()
    except requests.RequestException as e:
        raise FileFetchError(f"HTTP fetch failed: {e}")

    buf = io.BytesIO()
    for chunk in resp.iter_content(chunk_size=65536):
        buf.write(chunk)
        if buf.tell() > MAX_FETCH_BYTES:
            raise FileFetchError("File exceeded max fetch size during download")

    filename = os.path.basename(parsed.path) or "downloaded_file"
    content_type = resp.headers.get("Content-Type", "application/octet-stream")
    return filename, buf.getvalue(), content_type


def _fetch_ftp(parsed):
    _guard_remote_host(parsed.hostname)
    user = unquote(parsed.username) if parsed.username else "anonymous"
    passwd = unquote(parsed.password) if parsed.password else "anonymous"

    try:
        ftp = ftplib.FTP(timeout=FETCH_TIMEOUT_SEC)
        ftp.connect(parsed.hostname, parsed.port or 21)
        ftp.login(user, passwd)
        buf = io.BytesIO()
        ftp.retrbinary(f"RETR {parsed.path}", buf.write, blocksize=65536)
        ftp.quit()
    except Exception as e:
        raise FileFetchError(f"FTP fetch failed: {e}")

    if buf.tell() > MAX_FETCH_BYTES:
        raise FileFetchError("File exceeded max fetch size during download")

    filename = os.path.basename(parsed.path) or "downloaded_file"
    content_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"
    return filename, buf.getvalue(), content_type


def _fetch_sftp(parsed):
    _guard_remote_host(parsed.hostname)
    if not HAVE_PARAMIKO:
        raise FileFetchError("'paramiko' library not installed; cannot fetch sftp files")

    if not parsed.username:
        raise FileFetchError(f"No credentials embedded in fileLocation for host '{parsed.hostname}'")

    user = unquote(parsed.username)
    secret = unquote(parsed.password) if parsed.password else None

    try:
        transport = paramiko.Transport((parsed.hostname, parsed.port or 22))
        transport.connect(username=user, password=secret)
        sftp = paramiko.SFTPClient.from_transport(transport)

        stat = sftp.stat(parsed.path)
        if stat.st_size > MAX_FETCH_BYTES:
            raise FileFetchError(f"File too large to preview ({stat.st_size} bytes)")

        buf = io.BytesIO()
        sftp.getfo(parsed.path, buf)
        sftp.close()
        transport.close()
    except FileFetchError:
        raise
    except Exception as e:
        raise FileFetchError(f"SFTP fetch failed: {e}")

    filename = os.path.basename(parsed.path) or "downloaded_file"
    content_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"
    return filename, buf.getvalue(), content_type