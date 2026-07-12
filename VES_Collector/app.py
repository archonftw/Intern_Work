from flask import Flask

from routes.ingestion import ingestion_bp
from routes.devices import devices_bp
from routes.stats import stats_bp
from routes.dashboard import dashboard_bp
from routes.filereferences import filereferences_bp
from routes.pnf import pnf_bp
from services.file_ready_service import is_file_ready_event, process_file_ready

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


if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=8080,
        debug=False
    )