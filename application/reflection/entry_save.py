from datetime import datetime

from flask import jsonify, request

from models import db, Reflection, ReflectionQuestion

from application.reflection.views import reflection_bp
from application.reflection.date_check import is_valid_past_date


# ==============================================================================
# 振り返りの保存(入力内容と、深掘り質問への回答)
# ==============================================================================
@reflection_bp.route("/api/entry", methods=["PUT"])
def entry_save():
    # JSONデータの取得
    data = request.get_json()

    # 日付データの取得
    date = data.get("date")

    # 今日以前の日付のみ保存できる
    if not is_valid_past_date(date):
        return jsonify({"status": "error", "message": "選択できない日付です。"})

    # 現在時刻のタイムスタンプ
    now = datetime.now().strftime("%Y-%m-%dT%H:%M.%f")

    # その日の振り返りがなければ新規作成、あればK・P・Tの内容を更新
    reflection = Reflection.query.filter_by(date=date).first()
    if reflection is None:
        # その日の振り返りデータベース欄を新規作成
        reflection = Reflection(date=date)
        db.session.add(reflection)

    # K・P・Tの保存
    reflection.keep_content = data.get("keep_content", "")
    reflection.problem_content = data.get("problem_content", "")
    reflection.try_content = data.get("try_content", "")
    reflection.updated_at = now
    db.session.flush()

    # 質問ごとの回答を更新(この振り返りの質問のみ対象)
    for question_id, answer in (data.get("answers") or {}).items():
        question = ReflectionQuestion.query.filter_by(
            id=int(question_id), reflection_id=reflection.id
        ).first()
        if question is not None:
            question.answer = answer

    db.session.commit()
    print("保存 =>", reflection)
    return jsonify({"status": "ok"})
