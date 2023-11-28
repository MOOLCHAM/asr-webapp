from flask import Blueprint, render_template

bp = Blueprint("replay", __name__, url_prefix="/replay")


@bp.route("/")
def replay():
    """
    Renders and returns the about page template.

    **Endpoint**: ``/replay``
    """
    return render_template("replay.html")
