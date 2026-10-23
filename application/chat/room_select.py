from flask import current_app, jsonify

from models import History

from application.chat.views import chat_bp


# チャットコンテンツの検索・チャット画面へ送信
@chat_bp.route("/room_select/<int:room_id>", methods=["PUT"])
def room_select(room_id):
    # 対話履歴をJSON形式で送信する変数の初期化
    history = []

    # PUTで送信されたidから、対話履歴のデータベースを参照
    with current_app.app_context():
        target_his = History.query.filter_by(room_id=room_id).all()

        if target_his == []:
            return jsonify({"status": "error", "message": "対話履歴がありません。"})

        for target in target_his:
            history.append(
                {
                    "id": target.id,
                    "room_id": target.room_id,
                    "role": target.role,
                    "message": target.message,
                    "time_stamp": target.time_stamp,
                }
            )
    return jsonify(history)
