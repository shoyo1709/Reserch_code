from flask import Blueprint, render_template

# ===============================================================
# Blueprintの定義
# ===============================================================
reflection_bp = Blueprint("reflection_app", __name__, url_prefix="/reflection")


# ===============================================================
# ルーティング
# ===============================================================
@reflection_bp.route("/")
def show_template():
    return render_template("reflection/reflection.html")


# ルートを登録するために、ルートを持つサブモジュールをインポートする
from application.reflection import (  # noqa: E402,F401
    entry_get,
    entry_save,
    feedback_generate,
    question_generate,
)
