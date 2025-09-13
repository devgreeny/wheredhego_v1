# starting5/readonly.py
from flask import Blueprint, redirect

# Simple blueprint for starting5 redirection
bp = Blueprint(
    "starting5",
    __name__,
)

@bp.get("/")
def index():
    # For now, redirect to the original starting5.us site 
    # You can change this to serve the actual starting5 app later
    return redirect("https://starting5.us", code=302)
