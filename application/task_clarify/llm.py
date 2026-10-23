import json

MODEL_NAME = "qwen3:8b"


def call_llm(prompt):
    """SLM(ollama)にプロンプトを渡し、生の応答文字列を返す"""
    from langchain_ollama import OllamaLLM

    return OllamaLLM(model=MODEL_NAME).invoke(prompt)


def strip_think(text):
    """Qwen3のthinkタグ部分を取り除く"""
    if "</think>" in text:
        text = text.split("</think>")[-1]
    return text.strip()


def extract_json(text):
    """応答から最初の{から最後の}までをJSONとして読む。失敗したらNone"""
    text = strip_think(text)
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end <= start:
        return None
    try:
        data = json.loads(text[start : end + 1])
    except json.JSONDecodeError:
        return None
    return data if isinstance(data, dict) else None


def ask_json(prompt, retries=1):
    """JSONが得られるまで、最大 retries 回やり直す。得られなければNone"""
    for _ in range(retries + 1):
        data = extract_json(call_llm(prompt))
        if data is not None:
            return data
    return None


def extract_csv(text):
    """思考タグと</finish>以降を除いた、CSV部分だけを返す"""
    text = strip_think(text)
    return text.split("</finish>")[0].strip()
