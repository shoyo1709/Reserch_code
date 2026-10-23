from flask import Blueprint, render_template, current_app

from models import Room

from application.chat.config import TASK_CLARIFY_LABEL

# ===============================================================
# Blueprintの定義
# ===============================================================
task_clarify_bp = Blueprint("task_clarify_app", __name__, url_prefix="/task-clarify")


# ===============================================================
# ルーティング
# ===============================================================
@task_clarify_bp.route("/")
def show_template():
    # チャットルームの変数
    room_json = []

    # タスク明確化のチャットルームのみ取得
    with current_app.app_context():
        chat_rooms = Room.query.filter_by(chat_label=TASK_CLARIFY_LABEL).all()
        for chat_room in chat_rooms:
            room_json.append(
                {
                    "id": chat_room.id,
                    "title": chat_room.title,
                    "chat_label": chat_room.chat_label,
                    "timestamp": chat_room.time_stamp,
                }
            )
    return render_template("task_clarify/task_clarify.html", room_content=room_json)


# ルートを登録するために、ルートを持つサブモジュールをインポートする
from application.task_clarify import api  # noqa: E402,F401
