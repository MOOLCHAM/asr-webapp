from flask import Blueprint, render_template

bp = Blueprint("contact", __name__, url_prefix="/contact")


@bp.route("/")
def contact():
    """
    Renders and returns the contact page template.

    **Endpoint**: ``/contact``
    """
    return render_template("contact.html")
