import json

from application.chat import task_prompts
from application.task_clarify import llm

DEFAULT_DEADLINE_DAYS = 30

TASK_FIELDS = [
    "title",
    "description",
    "deadline",
    "priority",
    "required_time",
    "max_time",
    "min_time",
    "interval_minutes",
]
INT_FIELDS = TASK_FIELDS[2:]

# task_prompts のチェーン(関数, 締切日数を渡すか)
CHAIN = [
    (task_prompts.build_question2, True),
    (task_prompts.build_question2_2, True),
    (task_prompts.build_question2_3, False),
    (task_prompts.build_question2_4, True),
    (task_prompts.build_question3, False),
    (task_prompts.build_question3_2, False),
    (task_prompts.build_question4, False),
]


def normalize_tasks(items):
    """タスク案を、Taskの列に対応する形に整える。形式が不正ならNone"""
    if not isinstance(items, list):
        return None
    tasks = []
    for item in items:
        if not isinstance(item, dict):
            continue
        title = str(item.get("title") or "").strip()
        if not title:
            continue
        task = {"title": title, "description": str(item.get("description") or "")}
        for field in INT_FIELDS:
            value = item.get(field)
            if value in (None, ""):
                task[field] = 0
                continue
            try:
                task[field] = int(float(value))
            except (TypeError, ValueError):
                return None
        tasks.append({key: task[key] for key in TASK_FIELDS})
    return tasks


def parse_task_csv(text):
    """CSV(TaskName,description,deadline,priority,required_time,maxtime,mintime,interval_minutes)をタスク案にする。
    descriptionにカンマが含まれても読めるよう、数値の6列は右から取る。"""
    tasks = []
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("TaskName"):
            continue
        parts = line.split(",")
        if len(parts) < 8:
            continue
        numbers = parts[-6:]
        item = {
            "title": parts[0],
            "description": ",".join(parts[1:-6]),
            "deadline": numbers[0],
            "priority": numbers[1],
            "required_time": numbers[2],
            "max_time": numbers[3],
            "min_time": numbers[4],
            "interval_minutes": numbers[5],
        }
        normalized = normalize_tasks([item])
        if normalized:
            tasks.extend(normalized)
    return tasks


def build_task_list_prompt(goal_summary):
    return f"""
###指示
次の目標を達成するために必要なタスクを、取り組む順に箇条書きで挙げてください。
各タスクについて、タスク名と、何をするかの詳細を書いてください。

###目標
{json.dumps(goal_summary, ensure_ascii=False)}
"""


def generate_task_draft(goal_summary):
    """目標からタスク一覧を作り、task_promptsのチェーンで属性を付けてタスク案にする。失敗時はValueError"""
    deadline = goal_summary.get("deadline_days") or DEFAULT_DEADLINE_DAYS
    text = llm.strip_think(llm.call_llm(build_task_list_prompt(goal_summary)))
    for build, uses_deadline in CHAIN:
        prompt = build(text, deadline) if uses_deadline else build(text)
        text = llm.extract_csv(llm.call_llm(prompt))
    tasks = parse_task_csv(text)
    if not tasks:
        raise ValueError("タスク案を読み取れませんでした。")
    return tasks
