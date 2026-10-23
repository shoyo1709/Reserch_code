import os

# Transformer関連のインポート
os.environ["HF_HUB_OFFLINE"] = (
    "1"  # オフライン環境にあるときに有効にする、特にQwen3を使用するときに表示する
)

# 変数の定義
IS_CHAT = True
USE_SYSTEM_PROMPT = True
DEFAULT_MODEL_ID = "Qwen/Qwen3-14B"
# DEFAULT_MODEL_ID = "openai/gpt-oss-20b"
DEFAULT_THINK = 1
DEFAULT_MAX_TOKENS = 16384
DEFAULT_TEMPERATURE = 0.5
DEFAULT_TOP_P = 0.8
DEFAULT_TOP_K = 20
DIR_OUTPUT = "results/"
NUM_SENTENCES = 0  # 0 なら全ての文
VERBOSE = True  # False だと出力を画面表示しない

# チャットページごとのルームラベル(Room.chat_label の値)
TASK_CLARIFY_LABEL = "タスク生成"

## システムのプロンプト
DEFAULT_SYSTEM_PROMPT = """
    ###背景情報
    あなたはユーザの目標を細分化し、達成するためのタスクとその詳細情報を作成するインストラクターです。
    相手に寄り添いながら、適切な返答・質問をしてください
    """


# 目標の締切期限
# 対話的になった場合はこれは削除する（今は安直な入出力のため残している）
deadline = 30
