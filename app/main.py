import dash

from .constants import EXTERNAL_STYLESHEETS

app = dash.Dash(
    __name__,
    title="Patient Flow & Readmission Analytics",
    external_stylesheets=EXTERNAL_STYLESHEETS,
    suppress_callback_exceptions=True,
)
server = app.server  # required for Gunicorn

# Import to register layout and callbacks with the app instance
from . import layout    # noqa: E402, F401
from . import callbacks  # noqa: E402, F401

if __name__ == "__main__":
    app.run(debug=False, host="0.0.0.0", port=8050)
