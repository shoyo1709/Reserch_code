from flask import jsonify, request

from application.calendar.views import calendar_bp
from application.calendar.scheduler import schedule_plan, save_deadline, ScheduleError


# =========================================
# アプリのスケジューリング処理
# =========================================
@calendar_bp.route("/schedule", methods=["POST", "GET"])
def schedule():
    # jsファイルから、目標達成の締め切り日時(文字列)を受信
    schedule_data = request.get_json()
    # print(schedule_data["deadline"])

    # イベントの追加・変更・削除による自動スケジューリングのため、締切期限を保存する
    save_deadline(schedule_data["deadline"])
    schedule_plan(schedule_data["deadline"])
    return jsonify({"message": "スケジューリング完了"}), 200


# 分割しきれなかったときは、メッセージをエラーとして返す(スケジューリングする全てのルートに適用)
@calendar_bp.errorhandler(ScheduleError)
def schedule_error(error):
    return jsonify({"message": str(error)}), 400
