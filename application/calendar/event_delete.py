from datetime import datetime

from flask import current_app, jsonify

from models import db, Event

from application.calendar.views import calendar_bp
from application.calendar.scheduler import (
    datetime_str,
    reschedule,
    delete_event_plan,
)


# イベントの削除
@calendar_bp.route("/event/delete/<int:event_id>", methods=["PUT"])
def delete(event_id):
    print("=========削除処理===========")
    with current_app.app_context():
        print(f"id:{event_id}")
        target_event = Event.query.filter_by(event_id=event_id).first()
        print(target_event)
        target_event.delete_flag = datetime_str(datetime.today())
        db.session.add(target_event)
        print("削除 =>", target_event)

        db.session.commit()

        # 削除したイベントのplanを無効にし、再スケジューリングする
        delete_event_plan(event_id)
    reschedule()
    return jsonify({"message": "削除しました"}), 200
