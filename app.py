##
## 目標達成支援システム：ウェブアプリのappファイル
##

# Flask関連のインポート
from flask import Flask, render_template

# データベース関連のインポート
from models import db

# Transformer関連のインポート
import os

# =========================================
# インスタンス生成
# =========================================
# アプリ本体の作成
app = Flask(__name__)

# =========================================
# Flaskに関する設定
# =========================================
# 乱数を設定
app.config["SECRET_KEY"] = os.urandom(24)

# DBファイルの設定
base_dir = os.path.dirname(__file__)
database = "sqlite:///" + os.path.join(
    base_dir, "db/test.db"
)  # データベースの変更はこの変数で変更

app.config["SQLALCHEMY_DATABASE_URI"] = database
# 警告抑制のための推奨設定
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# エラー表示の設定
app.config["DEBUG"] = True

# dbとFlaskとの紐付け
db.init_app(app)

# 存在しないテーブルのみ作成する(既存テーブルには影響しない)
with app.app_context():
    db.create_all()

# =========================================
# Blueprintの登録
# =========================================
# カレンダー関連
from application.calendar.views import calendar_bp

app.register_blueprint(calendar_bp)

# チャット機能
from application.chat.views import chat_bp

app.register_blueprint(chat_bp)

# todo関連
from application.todo.views import todo_bp

app.register_blueprint(todo_bp)

# 目標設定関連
from application.task_clarify.views import task_clarify_bp

app.register_blueprint(task_clarify_bp)

# 内省・振り返り関連
from application.reflection.views import reflection_bp

app.register_blueprint(reflection_bp)


# =========================================
# ルーティング
# =========================================
# TOPページ
@app.route("/")
def top():
    return render_template("top.html")


# ==============================================================================
# 実行
# ==============================================================================
if __name__ == "__main__":
    app.run(debug=False, port=5001)
    # app.run(debug=False, port=5000)
