import json
from datetime import datetime

from flask import jsonify, request

from models import db, Room, History, Task

from application.task_clarify import goal_prompts, llm, task_draft
from application.task_clarify.views import task_clarify_bp


# ==============================================================================
# 共通の補助関数
# ==============================================================================
# エラー用のJSON応答を作る(画面側は status == "error" を見てアラートを出す)
def _error(message):
    return jsonify({"status": "error", "message": message})


# DBにJSON文字列で保存している値を、辞書・配列に戻す(空や壊れた値はdefaultを返す)
def _load_json(text, default):
    if not text:
        return default
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return default


# リクエストのroom_idから、目標(Room)を1件取得する(無効なIDや存在しないIDはNone)
def _get_room(data):
    try:
        return db.session.get(Room, int(data.get("room_id")))
    except (TypeError, ValueError):
        return None


# そのルームの対話履歴を、古い順に[{"role","message"}]の形で取得する(SLMに渡す会話文脈になる)
def _history(room_id):
    rows = History.query.filter_by(room_id=room_id).order_by(History.id).all()
    return [{"role": r.role, "message": r.message} for r in rows]


# 履歴・更新時刻に使う現在時刻の文字列を返す
def _now():
    return datetime.now().strftime("%Y-%m-%dT%H:%M.%f")


# ルームに保存された目標メモを辞書で返す(未保存ならgoal・deadline_days等が空の状態)
def _goal_of(room):
    goal = goal_prompts.empty_goal()
    goal.update(_load_json(room.goal_summary, {}))
    return goal


# ルームに保存されたタスク案を配列で返す(未保存なら空配列)
def _draft_of(room):
    return _load_json(room.task_draft, [])


# 画面が状態を復元するための、フェーズ・目標メモ・タスク案をまとめた応答を作る
def _state_payload(room):
    return {
        "status": "ok",
        "phase": room.phase or 1,
        "goal_summary": _goal_of(room),
        "task_draft": _draft_of(room),
    }


# ==============================================================================
# ページ再開用:フェーズ・目標の要約・タスク案の取得
# ==============================================================================
# 目標を選んだ(ページを開き直した)ときに、保存済みのフェーズ・目標カード・タスク案を返す。
# DBは変更しない。
@task_clarify_bp.route("/api/state", methods=["POST"])
def state():
    room = _get_room(request.get_json())
    if room is None:
        return _error("目標が見つかりません。")
    return jsonify(_state_payload(room))


# ==============================================================================
# メッセージ送信(フェーズに応じて返答を作る)
# ==============================================================================
# ユーザのメッセージを受け取り、現在のフェーズに応じたAIの返答を返す。
#  フェーズ1: 会話履歴を踏まえて目標を深掘りする質問を返し、目標メモ(goal_summary)を更新する。
#             目標が明確になったと判断したら ready=True を返す。
#  フェーズ2: タスク案が空なら task_prompts のチェーンで最初のタスク案を作り、
#             以降はユーザとの会話に合わせてタスク案を更新する。
# 対話履歴(History)・目標メモ・タスク案は、SLMの処理がすべて成功した後でのみ保存する。
# 失敗した場合はエラーを返し、DBは変更しない。登録済み(フェーズ3)の目標は受け付けない。
@task_clarify_bp.route("/api/message", methods=["POST"])
def message():
    data = request.get_json()
    room = _get_room(data)
    if room is None:
        return _error("目標が見つかりません。")
    text = (data.get("message") or "").strip()
    if not text:
        return _error("メッセージが空です。")

    phase = room.phase or 1
    if phase == 3:
        return _error("登録済みの目標です。")

    history = _history(room.id) + [{"role": "user", "message": text}]
    goal = _goal_of(room)
    draft = _draft_of(room)
    ready = False

    # SLMの処理が全部成功してから、DBを更新する
    if phase == 1:
        result = llm.ask_json(goal_prompts.build_goal_prompt(history, goal))
        if result is None or not isinstance(result.get("reply"), str):
            return _error("AIの返答を読み取れませんでした。もう一度送信してください。")
        reply = result["reply"]
        goal = goal_prompts.merge_goal(goal, result.get("goal_summary"))
        ready = bool(result.get("ready"))
    else:
        if not draft:
            try:
                draft = task_draft.generate_task_draft(goal)
            except ValueError as e:
                return _error(str(e))
        result = llm.ask_json(goal_prompts.build_task_chat_prompt(goal, history, draft))
        if result is None or not isinstance(result.get("reply"), str):
            return _error("AIの返答を読み取れませんでした。もう一度送信してください。")
        reply = result["reply"]
        updated = task_draft.normalize_tasks(result.get("task_draft"))
        if updated:
            draft = updated

    db.session.add(History(room_id=room.id, role="user", message=text, time_stamp=_now()))
    db.session.add(History(room_id=room.id, role="ai", message=reply, time_stamp=_now()))
    room.goal_summary = json.dumps(goal, ensure_ascii=False)
    room.task_draft = json.dumps(draft, ensure_ascii=False)
    db.session.commit()

    return jsonify(
        {
            "status": "ok",
            "response": reply,
            "phase": phase,
            "goal_summary": goal,
            "ready": ready,
            "task_draft": draft,
        }
    )


# ==============================================================================
# 「この目標で確定」:フェーズ1 -> 2
# ==============================================================================
# ユーザが「この目標で確定」を押したときに、フェーズを1から2(タスク情報の深掘り)へ進める。
# 目標メモに目標(goal)がまだ無い場合や、フェーズ1以外の場合はエラーを返し、DBは変更しない。
@task_clarify_bp.route("/api/goal/confirm", methods=["POST"])
def goal_confirm():
    room = _get_room(request.get_json())
    if room is None:
        return _error("目標が見つかりません。")
    if (room.phase or 1) != 1:
        return _error("目標の深掘りは完了しています。")
    goal = _goal_of(room)
    if not goal["goal"]:
        return _error("目標がまだ決まっていません。もう少し会話してください。")
    room.phase = 2
    db.session.commit()
    return jsonify({"status": "ok", "phase": 2, "goal_summary": goal})


# ==============================================================================
# ユーザが編集したタスク案の保存
# ==============================================================================
# 画面の右ペインで編集したタスク案を、目標(Room)のtask_draftとして保存する。
# 数値の列は整数に整えて保存する。タスクの深掘り中(フェーズ2)以外や、形式が不正な場合は
# エラーを返し、DBは変更しない。Taskテーブルへの登録はここでは行わない。
@task_clarify_bp.route("/api/tasks", methods=["PUT"])
def tasks_save():
    data = request.get_json()
    room = _get_room(data)
    if room is None:
        return _error("目標が見つかりません。")
    if (room.phase or 1) != 2:
        return _error("タスク情報を編集できるのは、タスクの深掘り中のみです。")
    tasks = task_draft.normalize_tasks(data.get("task_draft"))
    if tasks is None:
        return _error("タスク情報の形式が正しくありません。")
    room.task_draft = json.dumps(tasks, ensure_ascii=False)
    db.session.commit()
    return jsonify({"status": "ok", "task_draft": tasks})


# ==============================================================================
# 「タスクを登録」:タスク案をTaskテーブルへ保存する
# ==============================================================================
# 保存済みのタスク案の各行を、Taskテーブルに1件ずつ登録し、目標のフェーズを3(登録済み)にする。
# 登録済みの目標は、以後メッセージ送信・タスク編集・再登録ができなくなる(二重登録の防止)。
# タスクの深掘り中(フェーズ2)以外や、タスク案が空の場合はエラーを返し、DBは変更しない。
@task_clarify_bp.route("/api/tasks/register", methods=["POST"])
def tasks_register():
    room = _get_room(request.get_json())
    if room is None:
        return _error("目標が見つかりません。")
    if (room.phase or 1) != 2:
        return _error("登録できるのは、タスクの深掘り中のみです。")
    tasks = _draft_of(room)
    if not tasks:
        return _error("登録するタスクがありません。")
    for t in tasks:
        db.session.add(
            Task(
                title=t["title"],
                description=t["description"],
                deadline=t["deadline"],
                priority=t["priority"],
                required_time=t["required_time"],
                tasktime_now=0,
                max_time=t["max_time"],
                min_time=t["min_time"],
                interval_minutes=t["interval_minutes"],
            )
        )
    room.phase = 3
    db.session.commit()
    return jsonify({"status": "ok", "registered": len(tasks), "phase": 3})
