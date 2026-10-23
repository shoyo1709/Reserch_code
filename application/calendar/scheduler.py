from datetime import datetime, timedelta
from datetime import time as dtime

from flask import current_app
from sqlalchemy import desc, asc

from models import db, Task, Event, Plan, ScheduleSetting

# =========================================
# スケジューリングの定数
# =========================================
DATE_FORMAT = "%Y-%m-%d"  # テキストデータを日付データにするためのフォーマット定義
TIME_FORMAT = "%H:%M:%S"  # テキストデータを時間データにするためのフォーマット定義

# タスクを配置する時間帯(この範囲外の時間にはタスクを置かず、翌日の開始時刻に進める)
DAY_START = dtime(10, 0, 0)
DAY_END = dtime(18, 0, 0)

# イベント終了後に、空き時間を増やすための調整幅
EVENT_GAP = timedelta(minutes=10)

# 分割しきれなかったときに、上限を緩めていく範囲
# all_divを開始値から最大値まで増やし、それでも足りなければall_divを戻してeach_divを1増やす
ALL_DIV_START = 2
ALL_DIV_MAX = 5
EACH_DIV_START = 1
EACH_DIV_MAX = 5

# 優先度の最大値に足す値
# 足すことで「引かれる数」と「引く数」が同じになって0になることを回避し、締切時間が早い方がより優先されるようにする
PRIORITY_OFFSET = 5

# 1回の走査で分割の対象にするタスクの数(優先度が高い上位3つまで)
TASK_SCAN_LIMIT = 3


# =========================================
# 日付・時間の変換
# =========================================
# 日付と時間を含んだstr型の文字列を、datetime型に変換する関数
def str_datetime(data):
    data_replace = data.replace("T", " ")
    # timeの箇所において、「%S」がなくても「00:00:00」になるため、一旦「%S」なしでかく
    return datetime.strptime(data_replace, "%Y-%m-%d %H:%M")


# detetime型の日付と時間の情報を、str型の文字列に変換する関数
def datetime_str(data):
    return data.strftime("%Y-%m-%dT%H:%M")


# str型の日付と時間を組み合わせて、datetime型に変換する関数
# timelineの時間だけ変更したい時に使用
def date_time(date, time):
    return datetime.combine(
        datetime.strptime(date, DATE_FORMAT),
        datetime.strptime(time, TIME_FORMAT).time(),
    )


# =========================================
# スケジューラ
# =========================================
# task・eventの情報から、planテーブルを作成するクラス
# 「timeline」(次にタスクを置く時刻)を、イベントとイベントの間の空き時間(left_time〜right_time)の中で
# 進めながら、優先度の高いタスクから順に分割して配置する
class Scheduler:
    # スケジュールに必要な値の設定・状態の初期化(DBの読み込みは run() で行う)
    # start_from:指定すると、その日時以降のplanだけを再スケジューリングする(省略時は現在時刻から全て)
    def __init__(self, all_div, each_div, schedule_deadline, start_from=None):
        # 1日に分割できるタスクの回数の上限
        self.all_div = all_div
        # 1つのタスクを1日に分割できる回数の上限
        self.each_div = each_div

        # スケジュールする当日の日付/時間を設定する
        self.now = datetime.now().replace(microsecond=0)
        print(f"スケジュール当日:{self.now}")

        # 再スケジューリングの開始日時(指定がなければ現在時刻。現在より前には配置しない)
        self.start_from = start_from
        self.start = max(str_datetime(start_from), self.now) if start_from else self.now

        # 目標の締切期限を設定する
        self.deadline = str_datetime(schedule_deadline)
        print(f"締切期限:{self.deadline}")

    # -------------------------------------------------
    # 実行
    # -------------------------------------------------
    # スケジューリングを実行し、配置しきれなかった残り必要時間の合計(分)を返す
    # 0以下なら、全てのタスクを配置できている
    def run(self):
        self._load_data()
        self._init_state()

        while True:
            # timelineが、left_time〜right_timeの範囲内に収まっているか判定
            timeline_flag = self.left_time <= self.timeline < self.right_time

            # 範囲外、またはタスクを走査し終えたら、left_time・right_timeを次のイベントに変換する
            if not timeline_flag or not self.scanning_tasks:
                self._move_window()
                timeline_flag = False

            # timelineが、タスクを置ける時間帯か判定
            work_time_flag = self._in_working_hours()

            # タスクを置けない時間帯、または1日の分割上限なら、timelineを翌日に進める
            if not work_time_flag or not self.within_daily_limit:
                self._next_day()
                timeline_flag = False

            # 1日の分割回数の上限の判定
            self.within_daily_limit = self.splits_today < self.all_div

            # 分割対象のタスクを走査し終えたら、left・right変換して分割を続行させる
            if self.task_idx == len(self.tasks) or self.task_idx >= TASK_SCAN_LIMIT:
                self.scanning_tasks = False

            # 全てのタスクの残り必要時間が0なら、分割を終了する
            if sum(self.remaining.values()) <= 0:
                self.finished = True

            # 確認用
            print(
                f"left_time:{self.left_time}<timeline:{self.timeline}<right_time:{self.right_time}"
            )
            print(f"timeline_flag:{timeline_flag}")
            print(f"work_time_flag:{work_time_flag}")

            # 条件が全て当てはまっていれば、タスクを1回分配置する
            if (
                timeline_flag
                and work_time_flag
                and self.within_daily_limit
                and self.scanning_tasks
                and not self.finished
            ):
                print(f"remaining:{self.remaining}")
                self._place_task()

            # タスクの分割が全て終わったら、残りのイベントをplanに反映して終了する
            if self.finished:
                self._insert_remaining_events()
                break

        # 全てのタスクを配置できたときだけ、planをDBに反映する(配置できなければDBは変更しない)
        if sum(self.remaining.values()) <= 0:
            self._commit_plans()

        return sum(self.remaining.values())

    # -------------------------------------------------
    # 準備
    # -------------------------------------------------
    # task・event・planの情報をDBから読み込み、スケジュールの準備をする
    #  ・taskの残り必要時間(総必要時間 - 作業済みの時間)と、各タスクの分割回数を用意する
    #  ・有効なeventを開始時間順に取得し、締切期限より後のイベントは除く
    #  ・再スケジューリングで残すplanの時間を、残り必要時間から差し引く(planの変更は、配置できたときに行う)
    #  ・新しいplanの番号は、最後のplan_idの次の数値から始める(plan_idは増え続ける。planが無ければ1から)
    def _load_data(self):
        # テーブルtaskの情報を取得(優先度が高い順に取り出す)
        # 削除日が記入されたタスクは、分割するタスクに含めない
        self.tasks = (
            Task.query.filter(Task.delete_flag == "0")
            .order_by(desc(Task.priority))
            .all()
        )

        # 「総必要時間」-「実際に作業した時間」を残り時間とする(これによりリスケジューリングも対応できる)
        self.remaining = {
            t.task_id: t.required_time - t.tasktime_now for t in self.tasks
        }
        # 1日あたりの、各タスクの分割回数
        self.split_count = {t.task_id: 0 for t in self.tasks}

        # イベント開始時間順に、有効なeventの情報を取得
        events = Event.query.filter_by(delete_flag="0").order_by(asc(Event.start)).all()

        # 再スケジューリングで残すplan(start_fromより前のplan)のうち、これから行う予定のタスクの時間は、
        # 残り必要時間から差し引く(二重に配置しないため)
        if self.start_from:
            for kept in Plan.query.filter(
                Plan.delete_flag == "0",
                Plan.task_id != 0,
                Plan.start < self.start_from,
            ).all():
                if str_datetime(kept.start) >= self.now:
                    minutes = (
                        str_datetime(kept.end) - str_datetime(kept.start)
                    ).total_seconds() // 60
                    self.remaining[kept.task_id] -= int(minutes)

        # 目標の締切期限より遅いイベントは除く
        # (タスクの配置には使わず、最後にplanへ登録だけする)
        self.events = [e for e in events if str_datetime(e.start) <= self.deadline]
        self.late_events = [e for e in events if str_datetime(e.start) > self.deadline]

        # plan_idは増え続けるため、最後の数値の次の数値から始まる
        last_plan = Plan.query.order_by(desc(Plan.plan_id)).first()
        self.plan_id = last_plan.plan_id + 1 if last_plan else 1

        # 登録予定のplan(配置できたときに、DBへ書き込む)
        self.new_plans = []

    # スケジュール開始時の、timeline・left_time・right_time・各フラグを初期化する
    #  ・スケジュール当日より前に終わっているイベントは読み飛ばす
    #  ・イベントが1件も無ければ、締切期限までを空き時間にする
    def _init_state(self):
        # 参照中のイベント番号
        self.event_idx = 0
        # 参照中のタスク番号(常に0から数え直す)
        self.task_idx = 0
        # その日に分割した回数
        self.splits_today = 0

        # タスクを走査中か:Falseならleft・right変換
        self.scanning_tasks = True
        # 1日の分割上限内か:Falseなら日付変更
        self.within_daily_limit = True
        # 各タスクの分割上限内か:Falseなら午前・午後(時間帯)変更
        self.within_task_limit = True
        # timelineの日付変更を許可するか:Falseなら日付変更を回避
        self.date_change_flag = True
        # イベントが最後まで行ったか:Trueなら分割を終了する
        self.last_event_flag = False
        # 分割を終了するか
        self.finished = False

        # planを確定するための基準時間を指定(最初は現在時刻を格納)
        self.timeline = self.start
        # 作業の開始時刻より早かった場合は、開始時刻にそろえる
        if self.timeline.time() <= DAY_START:
            self.timeline = datetime.combine(self.start.date(), DAY_START)

        # 時間配分をするための、左の時間・右の時間の初期化
        self.left_time = self.start

        # スケジュール当日より前に終わっているイベントは、timelineを動かさずにそのままplanに保存し、読み飛ばす
        # (イベントの日時へtimelineが巻き戻らないようにするため)
        while self.event_idx < len(self.events) and self.start > str_datetime(
            self.events[self.event_idx].end
        ):
            self._insert_event_plan(self.events[self.event_idx])
            self.event_idx += 1

        if self.event_idx >= len(self.events):
            # 残りのイベントが1件も無いなら、締切期限までを空き時間とし、イベントは最後まで来ている扱いにする
            self.last_event_flag = True
            self.right_time = self.deadline
        else:
            # 次のイベントの開始までが空き時間
            self.right_time = str_datetime(self.events[self.event_idx].start)

        # task配列計算(最初)
        self._sort_tasks()

    # -------------------------------------------------
    # タスクの並び替え
    # -------------------------------------------------
    # 優先度と締切時間を考慮して計算し、最小値の順にtask配列を並び替える
    # 評価値 = (優先度の最大値 - 優先度) / 優先度の最大値 * (締切までの残り分数 - 残り必要時間)
    def _sort_tasks(self):
        if not self.tasks:
            return

        priority_max = max(t.priority for t in self.tasks) + PRIORITY_OFFSET

        scored = []
        for t in self.tasks:
            slack_minutes = (
                self.now + timedelta(days=t.deadline) - self.timeline
            ).total_seconds() // 60
            score = ((priority_max - t.priority) / priority_max) * (
                slack_minutes - self.remaining[t.task_id]
            )
            scored.append((score, t.task_id))

        scored.sort()  # 昇順に並び替える(最小順に並びかえ)
        by_id = {t.task_id: t for t in self.tasks}
        self.tasks = [by_id[task_id] for _, task_id in scored]

    # -------------------------------------------------
    # left_time・right_time・timelineの移動
    # -------------------------------------------------
    # timelineが範囲外になったときに、left_time・right_timeを次のイベントに変換する
    #  ・イベントが最後まで来ていたら、分割を終了する
    #  ・timelineがleft_timeより早い場合は、timelineをleft_timeに合わせるだけで、変換はしない
    #  ・それ以外は、次のイベントへ進み、タスクの走査を最初からやり直す
    # 変換後にtimelineが範囲外なら、timelineの日付は変更しないようにする
    def _move_window(self):
        if self.last_event_flag:
            self.finished = True
            return

        if self.timeline < self.left_time:
            # 例)日付変更直後は、timeline=10:00・left_time=10:30のような場合がある
            self.timeline = self.left_time
        else:
            self._next_event_window()
            self.event_idx += 1  # left・right変換後、次のイベントカウントを進める
            self.task_idx = 0
            self.scanning_tasks = True

        # 変換後すぐに判定し、left・rightの日付が変更されているか確認
        # ここに引っかかると日付変更できていないため、timelineは維持される
        if not (self.left_time <= self.timeline < self.right_time):
            self.date_change_flag = False

    # 参照中のイベントをplanに反映し、left_time・right_timeを次のイベントの前後に変換する
    #  ・最後のイベントなら、right_timeを締切期限にして、イベントが最後まで来たことを記録する
    #  ・timelineが締切期限を過ぎていて、left_timeも締切期限より後なら、1つ前のイベントの後を左端にする
    #  ・timelineが締切期限を過ぎていて、left_timeはまだ前なら、分割を終了する
    #  ・それ以外は通常どおり、このイベントの後〜次のイベントの開始までを空き時間にする
    def _next_event_window(self):
        event = self.events[self.event_idx]
        is_last = self.event_idx == len(self.events) - 1

        if is_last:
            print("イベントが最後まで来ました")
            self.last_event_flag = True
            self._insert_event_plan(event)
            self._set_window(str_datetime(event.end) + EVENT_GAP, self.deadline)

        elif self.deadline < self.timeline:
            self._insert_event_plan(event)
            if self.deadline < self.left_time:
                previous = self.events[self.event_idx - 1]
                self._set_window(str_datetime(previous.end) + EVENT_GAP, self.deadline)
            else:
                self.finished = True

        else:
            self._insert_event_plan(event)
            next_event = self.events[self.event_idx + 1]
            self._set_window(
                str_datetime(event.end) + EVENT_GAP, str_datetime(next_event.start)
            )

    # left_time・right_timeを設定する
    # timelineの日付変更が許可されているときは、timelineをleft_timeまで進める
    # (timelineは前に進めるだけで、過去のイベントの日時などに巻き戻さない)
    def _set_window(self, left_time, right_time):
        self.left_time = left_time
        self.right_time = right_time
        if self.date_change_flag and self.timeline < left_time:
            self.timeline = left_time

    # timelineが、タスクを置ける時間帯(DAY_START〜DAY_END)に収まっているかを返す
    #  ・時間帯外ならFalse
    #  ・時間帯内でも、日付がleft_time〜right_timeに合っていない場合は、日付変更ができていないときだけTrue
    #  ・各タスクの分割上限に来ていたらFalse(時間帯を変更する)
    def _in_working_hours(self):
        if not (DAY_START <= self.timeline.time() < DAY_END):
            return False
        if not (self.left_time <= self.timeline < self.right_time):
            # 例)1月1日12:00<12月31日14:00<1月1日16:00 のように、時間は合っていても日付が合わない場合
            return not self.date_change_flag
        return self.within_task_limit

    # timelineを翌日の開始時刻に進め、1日ごとの回数をリセットする
    # 進めた後にtimelineが範囲外なら、date_change_flagを立てる
    def _next_day(self):
        self.timeline = datetime.combine(
            self.timeline.date() + timedelta(days=1), DAY_START
        )
        self.within_daily_limit = True
        self.within_task_limit = True

        if not (self.left_time <= self.timeline < self.right_time):
            print("date_change_flagが立ちました")
            self.date_change_flag = True
        else:
            self.date_change_flag = False

        self._reset_day_counters()

    # 日付が変わるため、各タスクの分割回数・1日の分割回数・タスクの走査位置を初期化する
    def _reset_day_counters(self):
        for task_id in self.split_count:
            self.split_count[task_id] = 0
        self.splits_today = 0
        self.task_idx = 0

    # -------------------------------------------------
    # タスクの配置
    # -------------------------------------------------
    # 参照中のタスクを、空き時間(timeline〜right_time)に置けるか判定して分割する
    #  ・最大実行時間とインターバルを置ける:通常の分割(最大実行時間まで)
    #  ・最小実行時間とインターバルなら置ける:空き時間ぎりぎりまで分割
    #  ・置けない:次のタスクに移る(最後のタスクなら、left・right変換のために走査を終える)
    def _place_task(self):
        task = self.tasks[self.task_idx]
        max_span = timedelta(minutes=task.max_time + task.interval_minutes)
        min_span = timedelta(minutes=task.min_time + task.interval_minutes)

        if self.timeline + max_span <= self.right_time:
            self._split_or_skip(task, task.max_time)

        elif self.timeline + min_span <= self.right_time < self.timeline + max_span:
            # 空き時間(分数)からインターバルを引いた時間
            free_minutes = (
                int((self.right_time - self.timeline).total_seconds() // 60)
                - task.interval_minutes
            )
            self._split_or_skip(task, free_minutes)

        else:
            if self.task_idx < len(self.tasks) - 1:
                self.task_idx += 1
            else:
                self.scanning_tasks = False
                self.task_idx = 0

    # このタスクの1日の分割回数に余裕があれば分割し、上限なら次のタスクへ移る
    #  ・次のタスクが無い(最後のタスク)なら、日付が変わるものとして各回数をリセットし、時間帯を変更する
    # else_chunk:「残り時間も空き時間も十分」なときに割り当てる分数
    def _split_or_skip(self, task, else_chunk):
        if self.split_count[task.task_id] < self.each_div:
            self._split_task(task, else_chunk)
        elif len(self.tasks) <= 1 or self.task_idx == len(self.tasks) - 1:
            self._reset_day_counters()
            self.within_task_limit = False
        else:
            self.task_idx += 1

    # タスクを1回分だけ分割して、planに登録する
    #  ・分割後の残り時間が最小実行時間以上、最大実行時間未満なら、最小実行時間だけ残るように割り当てる
    #  ・分割後の残り時間が最小実行時間より少ないなら、残り時間を全て割り当てる
    #  ・それ以外は else_chunk(最大実行時間、または空き時間)を割り当てる
    # 残り時間が0になったタスクは配列から除き、残りのタスクを並び替え直す
    def _split_task(self, task, else_chunk):
        task_id = task.task_id
        remaining = self.remaining[task_id]
        start = self.timeline

        temp = remaining - task.min_time  # 判定用の時間範囲変数
        if task.min_time <= temp < task.max_time:
            chunk = temp
        elif temp < task.min_time:
            chunk = remaining
        else:
            chunk = else_chunk

        end = start + timedelta(minutes=chunk)
        self.remaining[task_id] = remaining - chunk
        self.timeline = end + timedelta(minutes=task.interval_minutes)
        self.split_count[task_id] += 1  # 各タスクの回数カウント
        self.splits_today += 1  # 分割回数のカウント

        self._insert_task_plan(task.title, start, end, task_id)

        # 残り時間が0なら、taskの中身を消す(優先度再計算のために消す必要がある)
        if self.remaining[task_id] == 0:
            self.tasks.pop(self.task_idx)
            self.task_idx = 0

        # taskの配列を再計算
        self._sort_tasks()

    # -------------------------------------------------
    # planテーブルへの登録
    # -------------------------------------------------
    # eventの情報を、planテーブルに登録する
    # 再スケジューリングで残すplan(start_fromより前の有効なplan)があるeventは、登録しない
    def _insert_event_plan(self, event):
        if (
            self.start_from
            and Plan.query.filter(
                Plan.event_id == event.event_id,
                Plan.delete_flag == "0",
                Plan.start < self.start_from,
            ).first()
        ):
            return
        self._save_plan(
            Plan(
                plan_id=self.plan_id,
                title=event.title,
                start=event.start,
                end=event.end,
                task_id=0,
                event_id=event.event_id,
                worked_time=0,
                delete_flag="0",
            )
        )

    # 分割したタスクの情報を、planテーブルに登録する
    def _insert_task_plan(self, title, start, end, task_id):
        self._save_plan(
            Plan(
                plan_id=self.plan_id,
                title=title,
                start=datetime_str(start),
                end=datetime_str(end),
                task_id=task_id,
                event_id=0,
                worked_time=0,
                delete_flag="0",
            )
        )

    # planを登録予定として溜め、次のplan_idに進める(DBへの書き込みは_commit_plansで行う)
    def _save_plan(self, plan):
        self.new_plans.append(plan)
        self.plan_id += 1
        print("登録 =>", plan)

    # 古いplanに「スケジューリングする日付」を記入し、溜めておいた新しいplanをDBに書き込む
    #  ・start_fromの指定があれば、その日時以降のplanだけに記入し、それより前のplanは残す
    def _commit_plans(self):
        targets = Plan.query.filter_by(delete_flag="0")
        if self.start_from:
            targets = targets.filter(Plan.start >= self.start_from)
        for target in targets.all():
            target.delete_flag = datetime_str(self.now)
        db.session.add_all(self.new_plans)
        db.session.commit()

    # まだplanに反映していないイベントと、締切期限より後のイベントを、全てplanテーブルに登録する
    def _insert_remaining_events(self):
        for event in self.events[self.event_idx :] + self.late_events:
            self._insert_event_plan(event)


# =========================================
# スケジューリング関連
# =========================================
# 分割しきれなかったときのエラー(remaining:配置しきれなかった残り必要時間の合計(分))
class ScheduleError(Exception):
    def __init__(self, remaining):
        self.remaining = remaining
        super().__init__(f"残り時間{remaining}分が分割しきれません。")


# スケジュール関数の定義
# schedule_deadline:目標の締切期限(文字列)
# start_from:指定すると、その日時以降のplanだけを再スケジューリングする
# 分割しきれなければ、all_divを増やして繰り返す(ALL_DIV_MAXまで)。
# それでも足りなければall_divを戻してeach_divを増やし、EACH_DIV_MAXまで繰り返す
# 全て試しても分割しきれなければ、DBを変更せずに、ScheduleErrorを発生させる
def schedule_plan(schedule_deadline, start_from=None):
    # SQLAlchemy操作をするためのスコープの定義
    with current_app.app_context():
        remaining = 0
        for each_div in range(EACH_DIV_START, EACH_DIV_MAX + 1):
            for all_div in range(ALL_DIV_START, ALL_DIV_MAX + 1):
                remaining = Scheduler(
                    all_div, each_div, schedule_deadline, start_from
                ).run()
                if remaining <= 0:
                    return
        raise ScheduleError(remaining)


# 目標の締切期限を保存する(常に1件だけ上書きする)
def save_deadline(schedule_deadline):
    setting = ScheduleSetting.query.first()
    if setting:
        setting.deadline = schedule_deadline
    else:
        db.session.add(ScheduleSetting(deadline=schedule_deadline))
    db.session.commit()


# イベントの追加・変更・削除のあとに、保存済みの締切期限で再スケジューリングする
# 締切期限が未保存、または現在より前のときは、何もしない
# (現在より前だと、タスクを配置できずにplanだけ削除日が記入されるため)
# start_from:指定すると、その日時以降のplanだけを再スケジューリングする
def reschedule(start_from=None):
    setting = ScheduleSetting.query.first()
    if not setting or str_datetime(setting.deadline) < datetime.now():
        return
    schedule_plan(setting.deadline, start_from)


# 指定したイベントの有効なplanに、削除日を記入する(変更・削除されたイベントのplanを無効にする)
def delete_event_plan(event_id):
    for target in Plan.query.filter_by(event_id=event_id, delete_flag="0").all():
        target.delete_flag = datetime_str(datetime.now())
    db.session.commit()
