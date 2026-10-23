# ==============================================================================
# フィードバックを生成するためのプロンプト(暫定文面)
# システムプロンプトの設計時に、この関数の中身を差し替える
# ==============================================================================
def build_feedback_prompt(keep_content, problem_content, try_content, qa_pairs):
    prompt = (
        "あなたは、ユーザの1日の振り返りに対して、フィードバックを与えるコーチです。\n"
        "以下のKPT(Keep・Problem・Try)による振り返りを踏まえて、"
        "良かった点の認識、課題への助言、次の一歩の提案を、日本語で簡潔にフィードバックしてください。\n"
        "フィードバック以外は出力しないでください。\n\n"
        f"###Keep(続けたいこと・良かったこと)\n{keep_content}\n\n"
        f"###Problem(課題・うまくいかなかったこと)\n{problem_content}\n\n"
        f"###Try(次に試すこと)\n{try_content}\n"
    )
    if qa_pairs:
        prompt += """\n以下に深掘り質問への回答記載します。\n 
                KPTの内容だけじゃなく、深掘り質問の内容も踏まえてフィードバックを出力してください。\n"""
        prompt += "\n###深掘り質問と回答\n"
        for question, answer in qa_pairs:
            prompt += f"質問:{question}\n回答:{answer or '(未回答)'}\n"
    return prompt
