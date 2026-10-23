from datetime import datetime

from flask import jsonify, request
from langchain_ollama import OllamaLLM

from models import db, Reflection, ReflectionQuestion

from application.reflection.views import reflection_bp
from application.reflection.date_check import is_valid_past_date
from application.reflection.question_prompt import build_question_prompt
from application.chat.slm_def import clean_results2


# ==============================================================================
# 深掘り質問の生成(保存済みの振り返りを踏まえて、SLMが質問を1つ生成する)
# ==============================================================================
@reflection_bp.route("/api/questions/generate", methods=["POST"])
def question_generate():
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

    # 既存の質問・回答を、プロンプトに含める
    questions = (
        ReflectionQuestion.query.filter_by(reflection_id=reflection.id)
        .order_by(ReflectionQuestion.id)
        .all()
    )
    prompt = build_question_prompt(
        reflection.keep_content,
        reflection.problem_content,
        reflection.try_content,
        [(q.question, q.answer) for q in questions],
    )

    # ollamaのlangchainを利用した質問の生成
    try:
        print("思考開始")
        llm = OllamaLLM(model="qwen3:8b")
        question_text = clean_results2(llm.invoke(prompt))
        print(f"思考終了：{question_text}")
    except Exception as e:
        print("質問の生成に失敗:", e)
        return jsonify({"status": "error", "message": "質問の生成に失敗しました。"})

    if not question_text:
        return jsonify({"status": "error", "message": "質問の生成に失敗しました。"})

    # 生成した質問を保存
    question = ReflectionQuestion(
        reflection_id=reflection.id,
        question=question_text,
        answer="",
        created_at=datetime.now().strftime("%Y-%m-%dT%H:%M.%f"),
    )
    db.session.add(question)
    db.session.commit()
    print("登録 =>", question)

    return jsonify({"id": question.id, "question": question.question, "answer": ""})
