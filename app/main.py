import dash

from .constants import EXTERNAL_STYLESHEETS

app = dash.Dash(
    __name__,
    title="Patient Flow & Readmission Analytics",
    external_stylesheets=EXTERNAL_STYLESHEETS,
    suppress_callback_exceptions=True,
)
server = app.server  # required for Gunicorn

from .layout import register_layout      # noqa: E402
from .callbacks import register_callbacks  # noqa: E402

register_layout(app)
register_callbacks(app)

if __name__ == "__main__":
    app.run(debug=False, host="0.0.0.0", port=8050)
