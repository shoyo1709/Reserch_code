from datetime import datetime, timedelta

from flask import jsonify, request

from models import db, Task, ScheduleSetting

from application.calendar.scheduler import str_datetime, datetime_str
from application.todo.views import todo_bp


# =========================================
# ToDoリスト関連
# =========================================
# タスクデータの取得
@todo_bp.route("/get_task", methods=["GET"])
def get_task():
    print("タスクを取得します")
    tasks = []
    # with app.app_context():
    # データベースから全てのタスクデータの取得(削除日が記入されたタスクは除く)
    task_data = Task.query.filter(Task.delete_flag == "0").all()

    for task in task_data:
        tasks.append(
            {
                "id": task.task_id,
                "title": task.title,
                "description": task.description,
                "deadline": task.deadline,
                "priority": task.priority,
                "required_time": task.required_time,
                "tasktime_now": task.tasktime_now,
                "max_time": task.max_time,
                "min_time": task.min_time,
                "interval_minutes": task.interval_minutes,
            }
        )

    return jsonify(tasks)


# スケジューリングの締切期限(schedule_setting)の取得
# 未保存の場合は、deadlineをNoneで返す
@todo_bp.route("/schedule_deadline", methods=["GET"])
def get_schedule_deadline():
    setting = ScheduleSetting.query.first()
    return jsonify({"deadline": setting.deadline if setting else None})


# タスク情報の入力値の検証(追加・変更で共通)
# 問題があればエラーメッセージを、なければNoneを返す
def validate_task(data):
    # 空欄のチェック(項目のキー, 項目名)
    fields = [
        ("title", "タスク名"),
        ("priority", "優先度"),
        ("description", "タスク詳細"),
        ("deadline", "締め切り期限"),
        ("required_time", "タスクの必要時間"),
        ("max_time", "最大実行時間"),
        ("min_time", "最小実行時間"),
        ("interval_minutes", "休憩時間"),
    ]
    for key, name in fields:
        value = data.get(key)
        if value is None or (isinstance(value, str) and not value.strip()):
            return f"{name}を入力してください"

    # 数値項目の検証(項目名, 値, 下限)
    int_items = [
        ("優先度", data["priority"], 0),
        ("締め切り期限", data["deadline"], 1),
        ("タスクの必要時間", data["required_time"], 1),
        ("最大実行時間", data["max_time"], 1),
        ("最小実行時間", data["min_time"], 0),
        ("休憩時間", data["interval_minutes"], 0),
    ]
    for name, value, minimum in int_items:
        if not isinstance(value, int) or isinstance(value, bool) or value < minimum:
            return f"{name}は{minimum}以上の整数で入力してください"
    if data["min_time"] > data["max_time"]:
        return "最小実行時間は最大実行時間以下で入力してください"
    if data["max_time"] > data["required_time"]:
        return "最大実行時間はタスクの必要時間以下で入力してください"

    # 締め切り日(今日+締め切り期限の日数)が、スケジューリングの締切期限より後にならないようにする
    setting = ScheduleSetting.query.first()
    if setting and datetime.now() + timedelta(days=data["deadline"]) > str_datetime(
        setting.deadline
    ):
        return f"締め切り期限は、スケジューリングの締切期限({setting.deadline})以前になるように入力してください"
    return None


# タスク情報をJSに返す形(辞書)にする
def task_to_dict(task):
    return {
        "id": task.task_id,
        "title": task.title,
        "description": task.description,
        "priority": task.priority,
        "deadline": task.deadline,
        "required_time": task.required_time,
        "tasktime_now": task.tasktime_now,
        "max_time": task.max_time,
        "min_time": task.min_time,
        "interval_minutes": task.interval_minutes,
    }


# タスクの新規追加(進捗時間は0で登録する・再スケジューリングは行わない)
@todo_bp.route("/add_task", methods=["POST"])
def add_task():
    data = request.get_json()  # todo.jsから追加するタスク情報を取得

    message = validate_task(data)
    if message:
        return jsonify({"message": message}), 400

    new_task = Task(
        title=data["title"].strip(),
        description=data["description"].strip(),
        deadline=data["deadline"],
        priority=data["priority"],
        required_time=data["required_time"],
        tasktime_now=0,
        max_time=data["max_time"],
        min_time=data["min_time"],
        interval_minutes=data["interval_minutes"],
    )
    db.session.add(new_task)
    db.session.commit()
    print("タスク追加 =>", new_task)

    return jsonify({"message": "追加しました", "task": task_to_dict(new_task)})


# タスク情報の変更(進捗時間は変更しない・再スケジューリングは行わない)
@todo_bp.route("/update_task/<int:task_id>", methods=["PUT"])
def update_task(task_id):
    data = request.get_json()  # todo.jsから変更後のタスク情報を取得

    target = Task.query.filter_by(task_id=task_id, delete_flag="0").first()
    if not target:
        return jsonify({"message": "タスクが見つかりません"}), 404

    message = validate_task(data)
    if message:
        return jsonify({"message": message}), 400

    target.title = data["title"].strip()
    target.description = data["description"].strip()
    target.priority = data["priority"]
    target.deadline = data["deadline"]
    target.required_time = data["required_time"]
    target.max_time = data["max_time"]
    target.min_time = data["min_time"]
    target.interval_minutes = data["interval_minutes"]
    # 進捗時間が新しい必要時間を超える場合は、必要時間に収める
    target.tasktime_now = min(target.tasktime_now, target.required_time)
    db.session.commit()
    print("タスク更新 =>", target)

    return jsonify({"message": "更新しました", "task": task_to_dict(target)})


# タスクの削除(delete_flagに削除日時を記入し、タスク情報は残す)
@todo_bp.route("/delete_task/<int:task_id>", methods=["PUT"])
def delete_task(task_id):
    target = Task.query.filter_by(task_id=task_id, delete_flag="0").first()
    if not target:
        return jsonify({"message": "タスクが見つかりません"}), 404

    target.delete_flag = datetime_str(datetime.now())
    db.session.commit()
    print("タスク削除 =>", target)

    return jsonify({"message": "削除しました"})
