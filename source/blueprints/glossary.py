from flask import Blueprint, render_template

bp = Blueprint("glossary", __name__, url_prefix="/glossary")


@bp.route("/")
def glossary():
    """
    Renders and returns the about page template.

    **Endpoint**: ``/glossary``
    """
    return render_template("glossary.html")
