from flask import current_app, jsonify, request

from models import db, Event, Plan, Task

from application.calendar.views import calendar_bp
from application.calendar.scheduler import reschedule, delete_event_plan, str_datetime


# イベントの変更
@calendar_bp.route("/event/update/<int:event_id>", methods=["PUT"])
def update(event_id):
    data = request.get_json()  # calendar.jsから変更後のイベント情報を取得

    # イベント情報の更新(event_idを参照)
    print("==========更新実行==========")
    with current_app.app_context():
        pre_target = Event.query.filter_by(event_id=event_id).first()
        print("更新前=>", pre_target)
        pre_target.title = data["title"]
        pre_target.event_label = data["event_label"]
        pre_target.start = data["start"]
        pre_target.end = data["end"]
        db.session.add(pre_target)
        db.session.commit()
        adv_target = Event.query.filter_by(event_id=event_id).first()
        print("更新後=>", adv_target)

        # 変更前のイベントのplanを無効にし、再スケジューリングで変更後のイベントを登録する
        delete_event_plan(event_id)
    reschedule()
    return jsonify({"message": "更新しました"}), 200


# タスク(plan)の進捗時間(分)の保存
# planの作業時間(worked_time)を入力値に更新し、変更前との差分だけタスクの進捗(tasktime_now)に反映する
# タスクの進捗は0〜総必要時間の範囲とし、再スケジューリングは行わない
@calendar_bp.route("/plan/progress/<int:plan_id>", methods=["PUT"])
def plan_progress(plan_id):
    data = request.get_json()  # calendar.jsから入力された進捗時間(分)を取得

    plan = Plan.query.filter_by(plan_id=plan_id).first()
    task = Task.query.filter_by(task_id=plan.task_id).first() if plan else None
    if not task:
        return jsonify({"message": "タスクが見つかりません"}), 404

    # 進捗時間は、予定の開始〜終了の長さ(分)以下のみ保存できる
    ## JS側でも上限の制限チェックを設けているが、Flask側でもチェックを設けている
    plan_minutes = int(
        (str_datetime(plan.end) - str_datetime(plan.start)).total_seconds() // 60
    )
    if data["minutes"] > plan_minutes:
        return (
            jsonify(
                {
                    "message": f"進捗時間は予定の長さ({plan_minutes}分)以下で入力してください"
                }
            ),
            400,
        )

    diff = data["minutes"] - plan.worked_time
    plan.worked_time = data["minutes"]
    task.tasktime_now = max(0, min(task.tasktime_now + diff, task.required_time))
    db.session.commit()
    print("進捗更新 =>", plan, task)
    return jsonify({"message": "更新しました"}), 200


# タスク(plan)の日時の変更
# 他のplan(イベント・タスク)の時間帯と被っている場合は、変更しない
@calendar_bp.route("/plan/update/<int:plan_id>", methods=["PUT"])
def plan_update(plan_id):
    data = request.get_json()  # calendar.jsから変更後の日時を取得

    # 有効なplanのうち、自分以外のplanと時間が被っているかの判定
    others = Plan.query.filter(Plan.delete_flag == "0", Plan.plan_id != plan_id).all()
    for other in others:
        if other.start < data["end"] and other.end > data["start"]:
            return jsonify(
                {
                    "message": "時間が重複しています",
                    "title": other.title,
                    "start": other.start,
                    "end": other.end,
                }
            )

    target = Plan.query.filter_by(plan_id=plan_id).first()
    target.start = data["start"]
    target.end = data["end"]
    db.session.commit()
    print("更新 =>", target)

    # 変更したタスク以降のplanを、再スケジューリングする
    reschedule(start_from=data["end"])
    return jsonify({"message": "更新しました"}), 200
