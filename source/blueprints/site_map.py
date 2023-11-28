from flask import Blueprint, render_template

bp = Blueprint("site_map", __name__, url_prefix="/site_map")


@bp.route("/")
def site_map():
    """
    Renders and returns the about page template.

    **Endpoint**: ``/site_map``
    """
    return render_template("site_map.html")
