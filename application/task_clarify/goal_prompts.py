import json

GOAL_KEYS = ["goal", "deadline_days", "current", "motivation"]


def empty_goal():
    return {"goal": "", "deadline_days": None, "current": "", "motivation": ""}


def merge_goal(current, update):
    """AIが返したgoal_summaryを、既知のキーだけ・空でない値だけ取り込む"""
    merged = dict(current)
    if not isinstance(update, dict):
        return merged
    for key in GOAL_KEYS:
        value = update.get(key)
        if value is None or value == "":
            continue
        if key == "deadline_days":
            try:
                merged[key] = int(value)
            except (TypeError, ValueError):
                pass
        else:
            merged[key] = str(value)
    return merged


def format_history(history):
    lines = []
    for h in history:
        who = "ユーザ" if h["role"] == "user" else "AI"
        lines.append(f"{who}: {h['message']}")
    return "\n".join(lines)


def build_goal_prompt(history, goal_summary):
    """フェーズ1:目標の深掘り"""
    return f"""
###指示
あなたはユーザの目標を深掘りするインストラクターです。
会話履歴と現在の目標メモを踏まえ、ユーザの目標を具体的にするために、まだ分かっていないことを質問してください。
深掘りする観点は「目標そのもの」「締切(何日後か)」「現状」「動機」です。

###制約
・質問は1返答につき1問にしてください。
・目標メモには、会話から分かったことだけを書き、推測で埋めないでください。
・目標・締切・現状が具体的に分かったら ready を true にしてください。まだ足りない場合は false にしてください。
・出力は次のJSONのみとし、他の文章は出力しないでください。

###出力形式
{{"reply": "ユーザへの返答(質問を1つ含める)", "goal_summary": {{"goal": "", "deadline_days": 30, "current": "", "motivation": ""}}, "ready": false}}
(deadline_days は今日から何日後かの整数。分からなければ null)

###現在の目標メモ
{json.dumps(goal_summary, ensure_ascii=False)}

###会話履歴
{format_history(history)}
"""


def build_task_chat_prompt(goal_summary, history, task_draft):
    """フェーズ2:タスク情報の深掘り"""
    return f"""
###指示
あなたはユーザの目標を達成するためのタスクを作るインストラクターです。
確定した目標と現在のタスク案、会話履歴を踏まえ、タスク案を更新してください。
ユーザの状況(使える時間、得意・不得意など)がまだ分からなければ、質問を1つしてください。

###制約
・質問は1返答につき1問にしてください。
・タスク案の締切(deadline)は目標の締切日数以下の整数(日数)にしてください。
・priority は1から始まる連番、時間はすべて分の整数にしてください。
・出力は次のJSONのみとし、他の文章は出力しないでください。

###出力形式
{{"reply": "ユーザへの返答", "task_draft": [{{"title": "", "description": "", "deadline": 0, "priority": 1, "required_time": 0, "max_time": 0, "min_time": 0, "interval_minutes": 0}}]}}

###確定した目標
{json.dumps(goal_summary, ensure_ascii=False)}

###現在のタスク案
{json.dumps(task_draft, ensure_ascii=False)}

###会話履歴
{format_history(history)}
"""
