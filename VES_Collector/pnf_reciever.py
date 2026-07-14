import logging
from datetime import datetime, timezone

from flask import Flask, request, jsonify, render_template_string

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
LOGGER = logging.getLogger("pnf-receiver")

app = Flask(__name__)

received_events = []


@app.route("/registration", methods=["POST"])
def receive_pnf_event():
    payload = request.get_json(silent=True) or {}

    record = {
        "receivedAt": datetime.now(timezone.utc).isoformat(),
        "payload": payload,
    }
    received_events.append(record)

    LOGGER.info(
        "Received forwarded PNF: vendor=%s ip=%s (total received: %d)",
        payload.get("vendorName", "?"),
        payload.get("oamV4IpAddress", "?"),
        len(received_events),
    )

    return jsonify({"status": "received"}), 200


@app.route("/received", methods=["GET"])
def list_received():
    return jsonify({
        "count": len(received_events),
        "events": received_events,
    })


@app.route("/received/clear", methods=["POST"])
def clear_received():
    received_events.clear()
    return jsonify({"status": "cleared"})


@app.route("/healthcheck", methods=["GET"])
def healthcheck():
    return jsonify({"status": "up"})


@app.route("/")
def dashboard():
    return render_template_string("""
<!DOCTYPE html>
<html>
<head>
    <title>PNF Receiver</title>
    <meta http-equiv="refresh" content="2">
    <style>
        body{
            font-family:Arial,sans-serif;
            background:#111827;
            color:white;
            margin:30px;
        }
        h1{
            color:#60a5fa;
        }
        table{
            width:100%;
            border-collapse:collapse;
            margin-top:20px;
        }
        th,td{
            border:1px solid #374151;
            padding:10px;
            text-align:left;
            vertical-align:top;
        }
        th{
            background:#1f2937;
        }
        tr:nth-child(even){
            background:#1a2233;
        }
        pre{
            margin:0;
            white-space:pre-wrap;
            word-break:break-word;
            color:#93c5fd;
        }
        .count{
            font-size:18px;
            margin-bottom:15px;
        }
        button{
            background:#2563eb;
            color:white;
            border:none;
            padding:8px 14px;
            cursor:pointer;
            border-radius:5px;
        }
    </style>
</head>
<body>

<h1>PNF Forward Receiver</h1>

<div class="count">
    Total Received: <b>{{ events|length }}</b>
</div>

<form action="/received/clear" method="post">
    <button type="submit">Clear Events</button>
</form>

<table>
<tr>
    <th>#</th>
    <th>Received At</th>
    <th>Vendor</th>
    <th>Model</th>
    <th>Serial</th>
    <th>IP</th>
    <th>Payload</th>
</tr>

{% for event in events|reverse %}
<tr>
    <td>{{ loop.index }}</td>
    <td>{{ event.receivedAt }}</td>
    <td>{{ event.payload.vendorName }}</td>
    <td>{{ event.payload.modelNumber }}</td>
    <td>{{ event.payload.serialNumber }}</td>
    <td>{{ event.payload.oamV4IpAddress }}</td>
    <td><pre>{{ event.payload | tojson(indent=2) }}</pre></td>
</tr>
{% endfor %}

</table>

</body>
</html>
    """, events=received_events)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=9001, debug=True)