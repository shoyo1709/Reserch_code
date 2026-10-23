from flask import Blueprint, render_template, current_app

from models import Task, Event, Plan

# ===============================================================
# Blueprintの定義
# ===============================================================
calendar_bp = Blueprint("calendar_app", __name__, url_prefix="/calendar")


# ===============================================================
# ルーティング
# ===============================================================
@calendar_bp.route("/")
def show_template():
    print("カレンダー表示します。")
    # jsに送信する予定データの配列初期化
    events = []

    with current_app.app_context():
        # planテーブルにデータがあるかの確認
        # 1件でもデータがなければ、eventテーブルの情報を送信
        is_exist = Plan.query.first()
        if is_exist:
            print("planデータがあります")
            # planテーブルの情報を取得するSQL文を実行し、events配列に格納
            plan_data = Plan.query.all()

            # イベント情報の初期化(ページ読み込み時に表示されるイベント)
            for data in plan_data:
                # イベントデータの詳細を出力するときに上げるフラグ
                # 常時フラグを下げておく
                event_description_flag = False
                select_event = Event.query.filter_by(event_id=data.event_id).first()

                # print(f"event_label:{select_event}")

                # 格納するデータが「タスク」or「イベント」かの判定
                if not select_event:
                    # タスクだった時の処理
                    event_label = "タスク"
                    task_target = Task.query.filter_by(task_id=data.task_id).first()
                else:
                    # イベントがあった時の処理
                    event_label = select_event.event_label
                    event_description_flag = True

                # HTMLファイルに送信するeventsにデータを格納
                events.append(
                    {
                        "id": data.plan_id,
                        "title": data.title,
                        "start": data.start,
                        "end": data.end,
                        "event_label": event_label,
                        "description": (
                            task_target.description
                            if not event_description_flag
                            else ""
                        ),  # イベント詳細フラグが上がったら(イベントを格納するとき)、「description」には空白を格納する
                        "task_id": data.task_id,
                        "event_id": data.event_id,
                        "worked_time": data.worked_time,
                        "delete_flag": data.delete_flag,
                    }
                )

        else:
            print("planデータがありません")
            # eventテーブルの情報を取得するSQL文を実行し、events配列に格納
            events_data = Event.query.all()

            # イベント情報の初期化(ページ読み込み時に表示されるイベント)
            for data in events_data:
                # HTMLファイルに送信するeventsにデータを格納
                events.append(
                    {
                        "id": data.event_id,
                        "title": data.title,
                        "start": data.start,
                        "end": data.end,
                        "event_label": data.event_label,
                        "descrption": "",
                    }
                )
    return render_template("calendar/calendar.html", events=events)


# イベント追加画面
@calendar_bp.route("/event", methods=["GET", "POST"])
def event():
    return render_template("calendar/event_create.html")


# ルートを登録するために、ルートを持つサブモジュールをインポートする
from application.calendar import (  # noqa: E402,F401
    event_create,
    event_delete,
    event_update,
    schedule_routes,
)
