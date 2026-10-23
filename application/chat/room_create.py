from datetime import datetime

from flask import current_app, jsonify, request

from models import db, Room

from application.chat.views import chat_bp


# チャットコンテンツ新規作成・データベース保存
@chat_bp.route("/room_create", methods=["POST"])
def room_create():
    # チャットコンテンツ情報の取得
    content_data = request.get_json()

    # 比較のためのroom情報をすべて取得
    comp_datas = Room.query.all()

    # 同じタイトルのルームは作成できないように処理
    for comp_data in comp_datas:
        if content_data["title"] == comp_data.title:
            print("同じタイトルです")
            return jsonify(
                {"status": "error", "message": "エラー：タイトルが同じです。"}
            )

    # 文字列への変換 (例: 2026/05/04 15:30:00)
    str_now = datetime.now().strftime("%Y-%m-%dT%H:%M.%f")

    # Room情報の格納
    with current_app.app_context():
        room_add = Room(
            title=content_data["title"],
            chat_label=content_data["label"],
            time_stamp=str_now,
        )

    # Room情報追加のコミット
    db.session.add(room_add)
    db.session.commit()
    print("登録 =>", room_add)

    # 追加したチャットルーム検索
    add_data = Room.query.filter_by(title=room_add.title).first()
    print(add_data)

    return jsonify(
        {
            "id": add_data.id,
            "title": add_data.title,
            "chat_label": add_data.chat_label,
            "time_stamp": add_data.time_stamp,
        }
    )
