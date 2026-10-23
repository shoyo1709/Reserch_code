// todo.htmlと連携するJavascriptファイル
// タスク情報を表示・変更する

//DOM要素の追加
const task_container = document.getElementById('task-container');
const task_add_area = document.getElementById('task-add-area');

// タスクのインスタンス
let tasks = null

//ページ読み込み時の初期化
document.addEventListener('DOMContentLoaded', async() => {
    //タスク情報の取得の関数
    //戻り値の「task_data」を取得する
    task_data = await get_task() //非同期処理の関数なので、戻り値も非同期で処理
    //タスクデータ表示の関数
    render_task(task_data)
    //「タスクを追加」ボタンの表示
    show_add_button()
});

//データベースからタスク情報を取得
//タスク情報がない場合、「タスクの情報なし」と表示する
async function get_task() {
    //Flaskにタスクデータがあるかのfetchの送信
    try{
        const res = await fetch(`/todo/get_task`)
        
        //Flaskから、タスクデータの取得
        const task_data = await res.json()
        console.log(task_data)

        //task_dataを戻り値にする
        return task_data
    }
    catch(error){
        console.log(error)
        alert('通信エラーが発生しました。')
    }

}

//タスク内容の表示
async function render_task(task_data, open_id = null) { 
    // 編集後の再表示用に、タスクデータを保持する
    tasks = task_data

    // 表示前にコンテナを空にする（重複表示を防ぐ）
    task_container.innerHTML = '';

    console.log(task_data)

    //puriority(優先順位)が高い順に表示する
    task_data.sort((a, b) => b.priority - a.priority).forEach(task => {
        // ブラウザのセッションにタスクIDを保存する
        sessionStorage.setItem(`TaskId-${task.id}`, task.id);

        //表示するタスクデータのdivクラスを設定
        const task_rend = document.createElement('details')
        task_rend.className = 'rendar-task'
        task_rend.id = 'rendar-task'

        //summary要素を作成
        const summaryEl = document.createElement('summary');

        //優先順位とタスク名
        summaryEl.innerHTML = `<strong>優先度: ${task.priority}</strong> ${task.title}`;

        //タスクの進捗度
        const progress = Math.floor((task.tasktime_now/task.required_time)*100)  // 進捗度のパーセンテージ：todo画面に表示用
        const progress_stroke = Math.floor(282.6*(1-task.tasktime_now/task.required_time))  // 進捗度の色がつかない長さの計算：プログレスバー用
        //svgタグを活用：①グレーの円、②色付きの円を重ねる方法
        //stroke-dasharray＝円周の長さ、stroke-dashoffset＝色付きの円において色がつかない分の長さ
        summaryEl.innerHTML += `<svg viewBox="0 0 100 100" width="75" height="75" fill="none" class="progress-container">
                                    <circle cx="50" cy="50" r="45" stroke="lightgray" stroke-width="10"/> 
                                    <circle cx="50" cy="50" r="45" stroke="#FB7E51" stroke-width="10" stroke-dasharray="282.6 282.6" stroke-dashoffset=${progress_stroke} class="circle-progress"/>
                                    <span class="progress-text">${progress}%</span>
                                </svg>`

        task_rend.appendChild(summaryEl)

        //タスクの詳細表と編集ボタンを表示
        render_detail(task_rend, task)

        //編集後の再表示では、編集したタスクを開いた状態にする
        task_rend.open = (task.id === open_id)

        //「task-container」にタスクデータを追加
        task_container.appendChild(task_rend)
    });

}


//タスクの詳細表(閲覧用)と編集ボタンを表示する
function render_detail(task_rend, task) {
    // すでに表示している詳細があれば取り除く
    const old_area = task_rend.querySelector('.task-detail-area')
    if (old_area) old_area.remove()

    //今日の日付の取得
    //スケジューリング開始の日付を記憶させておかないといけない
    /////未実装//////
    const today = new Date()
    today.setDate(today.getDate()+task.deadline)
    //今日の日付から何日後か計算
    //タスクの詳細と締め切り期限などをラベル付きの表で表示
    const area = document.createElement('div')
    area.className = 'task-detail-area'
    area.innerHTML = `<table class="task-detail">
                          <tr><th>タスク詳細</th><td>${task.description}</td></tr>
                          <tr><th>締め切り期限</th><td>${today.toLocaleDateString('ja-JP-u-ca-japanese')}</td></tr>
                          <tr><th>進捗時間 / 総作業時間</th><td>${task.tasktime_now}分 / ${task.required_time}分</td></tr>
                          <tr><th>最大実行時間</th><td>${task.max_time}分</td></tr>
                          <tr><th>最小実行時間</th><td>${task.min_time}分</td></tr>
                          <tr><th>休憩時間</th><td>${task.interval_minutes}分</td></tr>
                      </table>`

    //編集ボタン：押すと表が入力欄に変わる
    const edit_btn = document.createElement('button')
    edit_btn.textContent = '編集'
    edit_btn.addEventListener('click', () => render_edit(task_rend, task))
    area.appendChild(edit_btn)

    //削除ボタン：確認のうえ、タスクを削除する
    const delete_btn = document.createElement('button')
    delete_btn.textContent = '削除'
    delete_btn.addEventListener('click', async() => {
        if (!confirm('このタスクを削除しますか?')) return

        try {
            const res = await fetch(`/todo/delete_task/${task.id}`, {method: 'PUT'})
            const response = await res.json()
            if (!res.ok) {
                alert(response.message)
                return
            }
            //削除したタスクをリストから除いて再表示する
            tasks = tasks.filter(t => t.id !== task.id)
            render_task(tasks)
            alert('タスクを削除しました。\nカレンダーの予定には反映されていません。スケジューリングで組み直してください。')
        }
        catch(error) {
            console.log(error)
            alert('通信エラーが発生しました。')
        }
    })
    area.appendChild(delete_btn)

    task_rend.appendChild(area)
}


//編集用の表の1行(ラベルと入力欄)を作る
function edit_row(label, input) {
    const tr = document.createElement('tr')
    const th = document.createElement('th')
    th.textContent = label
    const td = document.createElement('td')
    td.appendChild(input)
    tr.append(th, td)
    return tr
}

//数値の入力欄を作る
function num_input(value, min) {
    const input = document.createElement('input')
    input.type = 'number'
    input.min = min
    input.step = 1
    input.value = value ?? ''
    return input
}


//タスク情報の入力値を検証する(問題があればメッセージを、なければnullを返す)
// schedule_deadline:スケジューリングの締切期限(文字列。未保存ならnull)
function validate_task(v, schedule_deadline) {
    // 空欄のチェック(空欄の項目があれば、その項目名を表示する。数値の空欄はNaNで渡される)
    const empties = [['タスク名', !v.title.trim()], ['優先度', Number.isNaN(v.priority)], ['タスク詳細', !v.description.trim()],
                     ['締め切り期限', Number.isNaN(v.deadline)], ['タスクの必要時間', Number.isNaN(v.required_time)],
                     ['最大実行時間', Number.isNaN(v.max_time)], ['最小実行時間', Number.isNaN(v.min_time)],
                     ['休憩時間', Number.isNaN(v.interval_minutes)]]
    for (const [name, is_empty] of empties) {
        if (is_empty) return `${name}を入力してください`
    }
    const ints = [['優先度', v.priority, 0], ['締め切り期限', v.deadline, 1], ['タスクの必要時間', v.required_time, 1],
                  ['最大実行時間', v.max_time, 1], ['最小実行時間', v.min_time, 0], ['休憩時間', v.interval_minutes, 0]]
    for (const [name, value, min] of ints) {
        if (!Number.isInteger(value) || value < min) return `${name}は${min}以上の整数で入力してください`
    }
    if (v.min_time > v.max_time) return '最小実行時間は最大実行時間以下で入力してください'
    if (v.max_time > v.required_time) return '最大実行時間はタスクの必要時間以下で入力してください'
    // 締め切り日(今日+締め切り期限の日数)が、スケジューリングの締切期限より後にならないようにする
    if (schedule_deadline) {
        const task_deadline = new Date()
        const today = new Date()

        task_deadline.setDate(task_deadline.getDate() + v.deadline)
        // 日付オブジェクトに変換して引き算（ミリ秒の差が出る）
        const diffTime = new Date(schedule_deadline) - today
        // ミリ秒を「日数」に変換する計算
        const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24))
        
        if (task_deadline > new Date(schedule_deadline)) {
            return `締め切り期限は、スケジューリングの締切期限(${schedule_deadline})以前(${diffDays}以下)になるように入力してください`
        }
    }
    return null
}


//保存済みのスケジューリングの締切期限を取得する(未保存ならnull)
async function get_schedule_deadline() {
    try {
        const res = await fetch('/todo/schedule_deadline')
        const data = await res.json()
        return data.deadline
    }
    catch(error) {
        console.log(error)
        return null
    }
}


//タスク情報の入力表を作る(編集・新規追加で共通。taskに初期値を渡す。進捗時間は入力させない)
// 戻り値:table=入力表、collect=入力値をまとめて取得する関数
function build_task_form(task) {
    const title = document.createElement('input')
    title.type = 'text'
    title.value = task.title ?? ''
    const description = document.createElement('textarea')
    description.rows = 3
    description.value = task.description ?? ''
    const priority = num_input(task.priority, 0)
    const deadline = num_input(task.deadline, 1)
    const required_time = num_input(task.required_time, 1)
    const max_time = num_input(task.max_time, 1)
    const min_time = num_input(task.min_time, 0)
    const interval_minutes = num_input(task.interval_minutes, 0)

    const table = document.createElement('table')
    table.className = 'task-detail'
    table.append(
        edit_row('タスク名', title),
        edit_row('優先度', priority),
        edit_row('タスク詳細', description),
        edit_row('締め切り期限(日後)', deadline),
        edit_row('タスクの必要時間(分)', required_time),
        edit_row('最大実行時間(分)', max_time),
        edit_row('最小実行時間(分)', min_time),
        edit_row('休憩時間(分)', interval_minutes)
    )

    const collect = () => ({
        title: title.value,
        description: description.value,
        priority: input_number(priority),
        deadline: input_number(deadline),
        required_time: input_number(required_time),
        max_time: input_number(max_time),
        min_time: input_number(min_time),
        interval_minutes: input_number(interval_minutes),
    })
    return {table, collect}
}


//保存・キャンセルボタンを作る
function build_form_buttons() {
    const save_btn = document.createElement('button')
    save_btn.textContent = '保存'
    const cancel_btn = document.createElement('button')
    cancel_btn.textContent = 'キャンセル'
    const buttons = document.createElement('div')
    buttons.className = 'task-edit-buttons'
    buttons.append(save_btn, cancel_btn)
    return {buttons, save_btn, cancel_btn}
}


//入力値を検証してFlaskに送信する(成功したらレスポンス、失敗したらnullを返す)
async function send_task(url, method, values) {
    const message = validate_task(values, await get_schedule_deadline())
    if (message) {
        alert(message)
        return null
    }

    try {
        const res = await fetch(url, {
            method: method,
            headers: {'Content-type':'application/json'},
            body: JSON.stringify(values)
        })
        const response = await res.json()
        if (!res.ok) {
            alert(response.message)
            return null
        }
        return response
    }
    catch(error) {
        console.log(error)
        alert('通信エラーが発生しました。')
        return null
    }
}


//タスク情報を編集する表を表示する(進捗時間は編集できない)
function render_edit(task_rend, task) {
    const old_area = task_rend.querySelector('.task-detail-area')
    if (old_area) old_area.remove()

    const {table, collect} = build_task_form(task)
    const {buttons, save_btn, cancel_btn} = build_form_buttons()

    const area = document.createElement('div')
    area.className = 'task-detail-area'
    area.append(table, buttons)
    task_rend.appendChild(area)

    //キャンセル：編集前の表示に戻す
    cancel_btn.addEventListener('click', () => render_detail(task_rend, task))

    //保存：入力値を検証し、Flaskに送信する
    save_btn.addEventListener('click', async() => {
        const response = await send_task(`/todo/update_task/${task.id}`, 'PUT', collect())
        if (!response) return

        //保存した内容を反映して、編集したタスクを開いた状態で再表示する
        Object.assign(task, response.task)
        render_task(tasks, task.id)
        alert('タスクを保存しました。\nカレンダーの予定には反映されていません。スケジューリングで組み直してください。')
    })
}


//新規タスクの追加フォームを表示する(「タスクを追加」ボタンを押したとき)
function render_add() {
    const {table, collect} = build_task_form({})
    const {buttons, save_btn, cancel_btn} = build_form_buttons()

    const form = document.createElement('div')
    form.className = 'task-add-form'
    form.innerHTML = '<h3>タスクを追加</h3>'
    form.append(table, buttons)

    task_add_area.innerHTML = ''
    task_add_area.appendChild(form)

    //キャンセル：フォームを閉じて、ボタンの表示に戻す
    cancel_btn.addEventListener('click', show_add_button)

    //保存：入力値を検証し、Flaskに送信する(進捗時間は0で登録される)
    save_btn.addEventListener('click', async() => {
        const response = await send_task('/todo/add_task', 'POST', collect())
        if (!response) return

        //追加したタスクをリストに加えて、開いた状態で再表示する
        tasks.push(response.task)
        show_add_button()
        render_task(tasks, response.task.id)
        alert('タスクを追加しました。\nカレンダーの予定には反映されていません。スケジューリングで組み直してください。')
    })
}


//「タスクを追加」ボタンを表示する
function show_add_button() {
    const add_btn = document.createElement('button')
    add_btn.textContent = 'タスクを追加'
    add_btn.addEventListener('click', render_add)
    task_add_area.innerHTML = ''
    task_add_area.appendChild(add_btn)
}


//数値の入力欄の値を数値に変換する(空欄は数値にならないようNaNにする)
function input_number(input) {
    return input.value === '' ? NaN : Number(input.value)
}
