from flask import current_app, jsonify

from models import db, Room, History

from application.chat.views import chat_bp


# チャットルームの削除
@chat_bp.route("/room_delete/<int:room_id>", methods=["PUT"])
def room_delete(room_id):
    print(f"room_id:{room_id}")

    with current_app.app_context():
        # ルームIDの参照して、チャットルームをデータベースから削除
        room_target = Room.query.filter_by(id=room_id).first()
        db.session.delete(room_target)
        db.session.commit()
        print("削除 =>", room_target)

        # ルームIDの参照して、対話履歴をデータベースから削除
        his_targets = History.query.filter_by(room_id=room_id).all()
        for his_target in his_targets:
            db.session.delete(his_target)
            db.session.commit()
            print("削除 =>", his_target)
    return jsonify({"message": "チャットルーム・履歴を削除しました"})
