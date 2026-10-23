from flask import jsonify, request

from models import Reflection, ReflectionQuestion, ReflectionFeedback

from application.reflection.views import reflection_bp
from application.reflection.date_check import is_valid_date_format


# ==============================================================================
# 振り返りの取得(指定した日付の入力内容と深掘り質問)
# ==============================================================================
@reflection_bp.route("/api/entry", methods=["POST"])
def entry_get():
    data = request.get_json()
    date = data.get("date")
    if not is_valid_date_format(date):
        return jsonify({"status": "error", "message": "日付の形式が正しくありません。"})

    reflection = Reflection.query.filter_by(date=date).first()

    # その日の振り返りがまだなければ、空のデータを返す
    if reflection is None:
        return jsonify(
            {
                "date": date,
                "keep_content": "",
                "problem_content": "",
                "try_content": "",
                "questions": [],
                "feedback": "",
            }
        )

    questions = (
        ReflectionQuestion.query.filter_by(reflection_id=reflection.id)
        .order_by(ReflectionQuestion.id)
        .all()
    )
    feedback = ReflectionFeedback.query.filter_by(reflection_id=reflection.id).first()
    return jsonify(
        {
            "date": date,
            "keep_content": reflection.keep_content or "",
            "problem_content": reflection.problem_content or "",
            "try_content": reflection.try_content or "",
            "questions": [
                {"id": q.id, "question": q.question, "answer": q.answer or ""}
                for q in questions
            ],
            "feedback": feedback.feedback if feedback else "",
        }
    )
