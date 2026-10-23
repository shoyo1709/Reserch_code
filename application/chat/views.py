from flask import Blueprint

# ===============================================================
# Blueprintの定義(共通API用:画面表示ルートはtask_clarify/reflectionが持つ)
# ===============================================================
chat_bp = Blueprint("chat_app", __name__, url_prefix="/chat")


# ルートを登録するために、ルートを持つサブモジュールをインポートする
from application.chat import (  # noqa: E402,F401
    room_create,
    room_delete,
    room_select,
)
