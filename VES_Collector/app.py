from flask import Flask

from routes.ingestion import ingestion_bp
from routes.devices import devices_bp
from routes.stats import stats_bp
from routes.dashboard import dashboard_bp
from routes.filereferences import filereferences_bp
from routes.pnf import pnf_bp
from services.file_ready_service import is_file_ready_event, process_file_ready
from routes.cm import cm_bp
from routes.config import config_bp
from services.netconf_service import netconf_service

app = Flask(
    __name__,
    template_folder="templates",
    static_folder="static"
)



app.register_blueprint(ingestion_bp)
app.register_blueprint(devices_bp)
app.register_blueprint(stats_bp)
app.register_blueprint(dashboard_bp)
app.register_blueprint(filereferences_bp)
app.register_blueprint(pnf_bp)
app.register_blueprint(cm_bp)
app.register_blueprint(config_bp)


def auto_connect_netopeer():
    """Auto-establishes NETCONF SSH connection to Netopeer2 on boot."""
    try:
        res = netconf_service.connect(
            device_id="pnf002",
            host="127.0.0.1",
            port=830,
            username="archon",
            key_filename="/home/archon/.ssh/id_ed25519"
        )
        print(f"[NETCONF BOOT] Netopeer2 auto-connected: {res}")
    except Exception as exc:
        print(f"[NETCONF BOOT WARNING] Auto-connect to Netopeer2 failed: {exc}")

with app.app_context():
    auto_connect_netopeer()

if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=8080,
        debug=False
    )