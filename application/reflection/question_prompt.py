# ==============================================================================
# 深掘り質問を生成するためのプロンプト(暫定文面)
# システムプロンプトの設計時に、この関数の中身を差し替える
# ==============================================================================
def build_question_prompt(keep_content, problem_content, try_content, qa_pairs):
    prompt = (
        "あなたは、ユーザの1日の振り返りを深掘りする聞き役です。\n"
        "以下のKPT(Keep・Problem・Try)による振り返りと、これまでの質問・回答を踏まえて、"
        "振り返りをより深めるための質問を日本語で1つだけ出力してください。\n"
        "質問文以外は出力しないでください。\n\n"
        f"###Keep(続けたいこと・良かったこと)\n{keep_content}\n\n"
        f"###Problem(課題・うまくいかなかったこと)\n{problem_content}\n\n"
        f"###Try(次に試すこと)\n{try_content}\n"
    )
    if qa_pairs:
        prompt += "\n###これまでの質問と回答\n"
        for question, answer in qa_pairs:
            prompt += f"質問:{question}\n回答:{answer or '(未回答)'}\n"
    return prompt
