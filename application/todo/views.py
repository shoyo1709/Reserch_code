from flask import Blueprint, render_template

# ===============================================================
# Blueprintの定義
# ===============================================================
todo_bp = Blueprint("todo_app", __name__, url_prefix="/todo")


# ===============================================================
# ルーティング
# ===============================================================
@todo_bp.route("/")
def show_template():
    return render_template("todo/todo.html")


# ルートを登録するために、ルートを持つサブモジュールをインポートする
from application.todo import tasks  # noqa: E402,F401
