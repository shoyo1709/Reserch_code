from flask import current_app, jsonify, request

from models import db, Event, Plan

from application.calendar.views import calendar_bp
from application.calendar.scheduler import reschedule


# =========================================
# カレンダーのCRUD操作
# =========================================
# イベントの追加(新規作成)
@calendar_bp.route("/event/create", methods=["POST"])
def event_create():
    # イベント情報の受信(取得)
    event_data = (
        request.get_json()
    )  # calendar_create.jsから入力メッセージデータを受け取る

    # イベント登録前に、Planのイベント時間が被っているか確認する
    # もし被っていたら、jsでエラー表示を見せる
    datas = Plan.query.all()
    for data in datas:
        # 時間が被っているかの判定
        if not (data.start > event_data["end"] or data.end < event_data["start"]):
            print(f"{data.start}-{data.end}\n{event_data['start']}-{event_data['end']}")
            # event_create.jsに、イベントが被っていることを送信
            return jsonify(
                {
                    "message": "ダブルブッキング",
                    "title": data.title,
                    "start": data.start,
                    "end": data.end,
                }
            )

    # イベントが全て被っていなければ、登録処理
    # イベントの情報の登録
    with current_app.app_context():
        event_add = Event(
            title=event_data["title"],
            event_label=event_data["label"],
            start=event_data["start"],
            end=event_data["end"],
            delete_flag="0",
        )
        db.session.add(event_add)
        db.session.commit()
        print("登録 =>", event_add)

    # イベント追加後に、再スケジューリングする
    reschedule()
    return jsonify({"message": "イベント新規登録しました"}), 200
