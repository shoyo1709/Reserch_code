from datetime import datetime

from flask import jsonify, request
from langchain_ollama import OllamaLLM

from models import db, Reflection, ReflectionQuestion, ReflectionFeedback

from application.reflection.views import reflection_bp
from application.reflection.date_check import is_valid_past_date
from application.reflection.feedback_prompt import build_feedback_prompt
from application.chat.slm_def import clean_results2


# ==============================================================================
# フィードバックの生成(保存済みの振り返りと質問への回答を踏まえて、SLMがフィードバックを生成する)
# ==============================================================================
@reflection_bp.route("/api/feedback/generate", methods=["POST"])
def feedback_generate():
    data = request.get_json()
    date = data.get("date")

    # 今日以前の日付のみ生成できる
    if not is_valid_past_date(date):
        return jsonify({"status": "error", "message": "選択できない日付です。"})

    # 保存済みのKeep・Problem・Tryが1つでも空なら、生成しない
    reflection = Reflection.query.filter_by(date=date).first()
    contents = (
        []
        if reflection is None
        else [
            reflection.keep_content,
            reflection.problem_content,
            reflection.try_content,
        ]
    )
    if len(contents) != 3 or not all((c or "").strip() for c in contents):
        return jsonify(
            {
                "status": "error",
                "message": "Keep・Problem・Tryをすべて入力してください。",
            }
        )

    # 質問・回答を、プロンプトに含める
    questions = (
        ReflectionQuestion.query.filter_by(reflection_id=reflection.id)
        .order_by(ReflectionQuestion.id)
        .all()
    )
    prompt = build_feedback_prompt(
        reflection.keep_content,
        reflection.problem_content,
        reflection.try_content,
        [(q.question, q.answer) for q in questions],
    )

    # ollamaのlangchainを利用したフィードバックの生成
    try:
        print("思考開始")
        llm = OllamaLLM(model="qwen3:8b")
        feedback_text = clean_results2(llm.invoke(prompt))
        print(f"思考終了：{feedback_text}")
    except Exception as e:
        print("フィードバックの生成に失敗:", e)
        return jsonify(
            {"status": "error", "message": "フィードバックの生成に失敗しました。"}
        )

    if not feedback_text:
        return jsonify(
            {"status": "error", "message": "フィードバックの生成に失敗しました。"}
        )

    # 生成したフィードバックを保存(振り返り1件につき1件。再生成したときは上書きする)
    feedback = ReflectionFeedback.query.filter_by(reflection_id=reflection.id).first()
    if feedback is None:
        feedback = ReflectionFeedback(reflection_id=reflection.id)
        db.session.add(feedback)
    feedback.feedback = feedback_text
    feedback.created_at = datetime.now().strftime("%Y-%m-%dT%H:%M.%f")
    db.session.commit()
    print("登録 =>", feedback)

    return jsonify({"feedback": feedback.feedback})
