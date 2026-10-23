# データベースのモデルを定義するファイル
# Flask側のapp.pyでこのファイルをインポートする

from flask_sqlalchemy import SQLAlchemy

# Flask-SQLAlchemyの生成
db = SQLAlchemy()


# task情報
class Task(db.Model):
    # テーブル名
    __tablename__ = "task"

    # ID(PK)
    task_id = db.Column(
        db.Integer,
        primary_key=True,
        nullable=False,
    )

    # タスク名(タイトル)
    title = db.Column(db.Text)

    # タスクの詳細
    description = db.Column(db.Text)

    # タスクの締切期限
    deadline = db.Column(db.Integer)

    # タスクの優先順位
    priority = db.Column(db.Integer)

    # タスクの総必要時間(そのタスクに合計でどのくらいの作業時間があるか)
    required_time = db.Column(db.Integer)

    # タスクの現時点の作業経過時間
    tasktime_now = db.Column(db.Integer)

    # タスクの最大実行時間
    max_time = db.Column(db.Integer)

    # タスクの最小実行時間
    min_time = db.Column(db.Integer)

    # タスクのインターバル時間(タスク毎にとるべき休憩時間)
    interval_minutes = db.Column(db.Integer)

    # 削除したタイムスタンプ（delete_flag的な役割)
    # 有効なタスクは「0」、削除したタスクは削除日時を記録する(タスク情報は残す)
    delete_flag = db.Column(db.Text, default="0", server_default="0")

    # 表示用
    def __str__(self):
        return f"""ID:{self.task_id} title:{self.title} description:{self.description}\n
        deadline:{self.deadline} priority:{self.priority} required_time:{self.required_time} tasktime_now:{self.tasktime_now}\n
        max_time:{self.max_time} min_time:{self.min_time} interval_time:{self.interval_minutes}"""


# event情報
class Event(db.Model):
    # テーブル名
    __tablename__ = "event"

    # ID(PK)
    event_id = db.Column(db.Integer, primary_key=True, nullable=False)

    # イベント名
    title = db.Column(db.Text)

    # 開始日時・時間
    start = db.Column(db.Text)

    # 終了日時・時間
    end = db.Column(db.Text)

    # イベントの現時点での進捗時間
    event_label = db.Column(db.Text)

    # 削除したタイムスタンプ（delete_flag的な役割)
    # 削除した日付を残することで、いつ変更したかを記録する
    delete_flag = db.Column(db.Text)

    # 表示用
    def __str__(self):
        return f"ID:{self.event_id} title:{self.title} start:{self.start} end:{self.end} event_label:{self.event_label} delete_flag:{self.delete_flag}"


# plan情報
class Plan(db.Model):
    # テーブル名
    __tablename__ = "plan"

    # プランID(PK)
    plan_id = db.Column(db.Integer, primary_key=True, nullable=False)

    # プラン名(タイトル)
    title = db.Column(db.Text)

    # 開始日時
    start = db.Column(db.Text)

    # 終了日時
    end = db.Column(db.Text)

    # タスクID
    task_id = db.Column(db.Integer)

    # イベントID
    event_id = db.Column(db.Integer)

    # 作業時間
    worked_time = db.Column(db.Integer)

    # 削除したタイムスタンプ（delete_flag的な役割)
    # 削除した日付を残することで、いつ変更したかを記録する
    delete_flag = db.Column(db.Text)

    # 表示用
    def __str__(self):
        return f"ID:{self.plan_id} title:{self.title} start:{self.start} end:{self.end} task_id:{self.task_id} event_id:{self.event_id} worked_time:{self.worked_time} delete_flag:{self.delete_flag}"


# スケジューリングの設定(ユーザが最後に指定した締切期限を1件だけ保存する)
class ScheduleSetting(db.Model):
    # テーブル名
    __tablename__ = "schedule_setting"

    # ID(PK)(常に1件のみ)
    id = db.Column(db.Integer, primary_key=True, nullable=False)

    # 目標の締切期限(例:2026-10-20T18:00)
    deadline = db.Column(db.Text)


# chat_room情報
class Room(db.Model):
    # テーブル名
    __tablename__ = "room"

    # ID
    id = db.Column(db.Integer, primary_key=True, nullable=False)

    # チャットルームのタイトル
    title = db.Column(db.Text)

    # チャットラベル（タスク生成か内省か）
    chat_label = db.Column(db.Text)

    # タイムスタンプ（追加時刻を記録）
    time_stamp = db.Column(db.Text)

    # 目標の要約(JSON文字列。例: {"goal":"","deadline_days":30,"current":"","motivation":""})
    goal_summary = db.Column(db.Text)

    # フェーズ(1:目標の深掘り / 2:タスク情報の深掘り / 3:登録済み)
    phase = db.Column(db.Integer, default=1)

    # タスク案(JSON文字列。Taskの列に対応するオブジェクトの配列)
    task_draft = db.Column(db.Text)

    # 表示用
    def __str__(self):
        return f"ID:{self.id} title:{self.title} chat_label:{self.chat_label} time_stamp:{self.time_stamp}"


# 対話履歴(history)情報
class History(db.Model):
    # テーブル名
    __tablename__ = "history"

    # ID(対話履歴用)
    id = db.Column(db.Integer, primary_key=True, nullable=False)

    # RoomID
    room_id = db.Column(db.Integer)

    # role(ユーザー or AI)
    role = db.Column(db.Text)

    # message(対話テキスト)
    message = db.Column(db.Text)

    # タイムスタンプ（入力時刻を記録）
    time_stamp = db.Column(db.Text)

    # 表示用
    def __str__(self):
        return f"ID:{self.id} room_id:{self.room_id} role:{self.role} message:{self.message} time_stamp:{self.time_stamp}"


# 振り返り(reflection)情報:日付ごとに1件
class Reflection(db.Model):
    # テーブル名
    __tablename__ = "reflection"

    # ID(PK)
    id = db.Column(db.Integer, primary_key=True, nullable=False)

    # 振り返りの日付(YYYY-MM-DD、1日1件)
    date = db.Column(db.Text, unique=True, nullable=False)

    # KPT:Keep(続けたいこと・良かったこと)
    keep_content = db.Column(db.Text)

    # KPT:Problem(課題・うまくいかなかったこと)
    problem_content = db.Column(db.Text)

    # KPT:Try(次に試すこと)
    try_content = db.Column(db.Text)

    # 更新日時
    updated_at = db.Column(db.Text)

    # 表示用
    def __str__(self):
        return f"ID:{self.id} date:{self.date} keep:{self.keep_content} problem:{self.problem_content} try:{self.try_content} updated_at:{self.updated_at}"


# 振り返りの深掘り質問(reflection_question)情報
class ReflectionQuestion(db.Model):
    # テーブル名
    __tablename__ = "reflection_question"

    # ID(PK)
    id = db.Column(db.Integer, primary_key=True, nullable=False)

    # 振り返りID(reflectionテーブルのid)
    reflection_id = db.Column(db.Integer)

    # SLMが生成した深掘り質問
    question = db.Column(db.Text)

    # 質問に対するユーザーの回答
    answer = db.Column(db.Text)

    # 質問の生成日時
    created_at = db.Column(db.Text)

    # 表示用
    def __str__(self):
        return f"ID:{self.id} reflection_id:{self.reflection_id} question:{self.question} answer:{self.answer} created_at:{self.created_at}"


# 振り返りに対する、生成AIのフィードバック(振り返り1件につき1件)
class ReflectionFeedback(db.Model):
    # テーブル名
    __tablename__ = "reflection_feedback"

    # ID(PK)
    id = db.Column(db.Integer, primary_key=True, nullable=False)

    # 振り返りID(reflectionテーブルのid)
    reflection_id = db.Column(db.Integer)

    # 生成AIが生成したフィードバック
    feedback = db.Column(db.Text)

    # フィードバックの生成日時
    created_at = db.Column(db.Text)

    # 表示用
    def __str__(self):
        return f"ID:{self.id} reflection_id:{self.reflection_id} feedback:{self.feedback} created_at:{self.created_at}"
