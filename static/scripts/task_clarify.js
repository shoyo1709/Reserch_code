// task_clarify.html と連携するJavascriptファイル
// 1つの目標を、SLMとの会話で深掘りし、タスク情報を登録する

const CHAT_LABEL = "タスク生成" // このページのチャットラベル
const KICKOFF_MESSAGE = "この目標で、タスクを作ってください。" // フェーズ2の開始時に自動送信する

let roomContent = []   // 目標(ルーム)の配列
let currentRoomId = null
let state = { phase: 1, goal_summary: {}, task_draft: [] }

const goalSelect = document.getElementById('goalSelect')
const messagesContainer = document.getElementById('messagesContainer')
const emptyState = document.getElementById('emptyState')
const defaultMessage = document.getElementById('defaultMessage')
const chatHeader = document.getElementById('chatHeader')
const readyBanner = document.getElementById('readyBanner')
const confirmGoalBtn = document.getElementById('confirmGoalBtn')
const registerBtn = document.getElementById('registerBtn')
const taskBody = document.getElementById('taskBody')
const messageInput = document.getElementById('messageInput')

// タスク一覧表の列(Taskの列に対応)
const TASK_COLUMNS = [
    { key: 'title', type: 'text' },
    { key: 'description', type: 'text' },
    { key: 'deadline', type: 'number' },
    { key: 'priority', type: 'number' },
    { key: 'required_time', type: 'number' },
    { key: 'max_time', type: 'number' },
    { key: 'min_time', type: 'number' },
    { key: 'interval_minutes', type: 'number' },
]

// ===== API呼び出し(値はJSONのbodyで渡す) =====
// 指定したURL・メソッドにJSONを送り、返ってきたJSONを返す
async function postJson(url, method, body) {
    const res = await fetch(url, {
        method: method,
        headers: { 'Content-type': 'application/json' },
        body: JSON.stringify(body)
    })
    return await res.json()
}

// ===== ページロード時 =====
// 埋め込まれた目標の一覧を読み込み、前回開いていた目標(なければ先頭)を開く
document.addEventListener('DOMContentLoaded', function () {
    const roomElement = document.getElementById('roomContent')
    if (!roomElement) {
        throw new Error('目標データが見つかりません')
    }
    roomContent = JSON.parse(roomElement.textContent)
    if (!Array.isArray(roomContent)) {
        throw new Error('目標データが配列ではありません')
    }

    renderGoalOptions()

    // 前回開いていた目標があれば、続きから再開する
    const lastId = Number(sessionStorage.getItem('activeRoomId'))
    const target = roomContent.find(r => r.id === lastId) || roomContent[0]
    if (target) {
        selectRoom(target.id)
    } else {
        showNoRoom()
    }
})

// ===== 目標の切替 =====
// 上部のドロップダウンに、目標の一覧を表示する
function renderGoalOptions() {
    goalSelect.innerHTML = ''
    roomContent.forEach(room => {
        const option = document.createElement('option')
        option.value = room.id
        option.textContent = room.title
        goalSelect.appendChild(option)
    })
    if (currentRoomId !== null) {
        goalSelect.value = currentRoomId
    }
}

goalSelect.addEventListener('change', () => selectRoom(Number(goalSelect.value)))

// 目標が1件も無いときの表示にする
function showNoRoom() {
    currentRoomId = null
    messagesContainer.textContent = ''
    emptyState.style.display = 'flex'
    defaultMessage.textContent = '上の「新しい目標」から、深掘りしたい目標を作成してください'
    chatHeader.textContent = '目標を選択してください'
    state = { phase: 1, goal_summary: {}, task_draft: [] }
    renderPhase()
}

// 目標を選んだときに、対話履歴と、保存済みのフェーズ・目標カード・タスク案を読み込んで表示する
async function selectRoom(id) {
    currentRoomId = id
    goalSelect.value = id
    sessionStorage.setItem('activeRoomId', id)
    const room = roomContent.find(r => r.id === id)
    chatHeader.textContent = room.title
    messagesContainer.textContent = ''

    try {
        // 対話履歴
        const his = await postJson(`/chat/room_select/${id}`, 'PUT', {})
        if (Array.isArray(his)) {
            emptyState.style.display = 'none'
            his.forEach(h => appendMessage(h.role === 'user' ? 'user' : 'ai', h.message))
        } else {
            emptyState.style.display = 'flex'
            defaultMessage.textContent = 'まず、達成したい目標を書いてみましょう'
        }

        // フェーズ・目標の要約・タスク案
        const data = await postJson('/task-clarify/api/state', 'POST', { room_id: id })
        if (data.status === 'error') {
            alert(data.message)
            return
        }
        state = data
        renderPhase()
    } catch (error) {
        console.error('エラー:', error)
        alert('エラーが発生しました。')
    }
}

// ===== 表示 =====
// チャット欄にメッセージを1件追加する(文字はtextContent扱いで、HTMLとして解釈しない)
function appendMessage(role, text) {
    const div = document.createElement('div')
    div.className = role === 'user' ? 'user-message' : 'ai-message'
    const label = document.createElement('strong')
    label.textContent = role === 'user' ? 'ユーザー: ' : 'AI: '
    div.appendChild(label)
    div.appendChild(document.createTextNode(text))
    messagesContainer.appendChild(div)
    messagesContainer.scrollTop = messagesContainer.scrollHeight
    return div
}

// フェーズに応じて、ステップ表示・右ペイン(目標カード/タスク表)・ボタンの状態を切り替える
function renderPhase() {
    const phase = state.phase

    document.querySelectorAll('#stepper li').forEach(li => {
        const p = Number(li.dataset.phase)
        li.classList.toggle('active', p === phase)
        li.classList.toggle('done', p < phase)
    })

    document.getElementById('goalPane').hidden = phase !== 1
    document.getElementById('taskPane').hidden = phase === 1

    const goal = state.goal_summary || {}
    document.getElementById('goalText').textContent = goal.goal || '-'
    document.getElementById('goalDeadline').textContent = goal.deadline_days ?? '-'
    document.getElementById('goalCurrent').textContent = goal.current || '-'
    document.getElementById('goalMotivation').textContent = goal.motivation || '-'

    confirmGoalBtn.disabled = currentRoomId === null || !goal.goal
    registerBtn.hidden = phase !== 2
    registerBtn.disabled = !(state.task_draft && state.task_draft.length)
    readyBanner.hidden = true
    confirmGoalBtn.classList.remove('highlight')

    renderTaskTable()
}

// タスク案を表に表示する(フェーズ2のときだけ編集できる)
function renderTaskTable() {
    taskBody.innerHTML = ''
    const editable = state.phase === 2
    ;(state.task_draft || []).forEach(task => {
        const tr = document.createElement('tr')
        TASK_COLUMNS.forEach(col => {
            const td = document.createElement('td')
            const input = document.createElement('input')
            input.type = col.type
            input.dataset.key = col.key
            input.value = task[col.key] ?? ''
            input.disabled = !editable
            input.addEventListener('change', saveTaskDraft)
            td.appendChild(input)
            tr.appendChild(td)
        })
        taskBody.appendChild(tr)
    })
}

// 表の内容を、タスク案の配列として集める
function collectTaskDraft() {
    return Array.from(taskBody.querySelectorAll('tr')).map(tr => {
        const task = {}
        tr.querySelectorAll('input').forEach(input => {
            task[input.dataset.key] = input.value
        })
        return task
    })
}

// 表の編集内容をFlaskに保存する(成功したらtrueを返す)
async function saveTaskDraft() {
    try {
        const data = await postJson('/task-clarify/api/tasks', 'PUT', {
            room_id: currentRoomId,
            task_draft: collectTaskDraft()
        })
        if (data.status === 'error') {
            alert(data.message)
            return false
        }
        state.task_draft = data.task_draft
        return true
    } catch (error) {
        console.error('エラー:', error)
        alert('エラーが発生しました。')
        return false
    }
}

// ===== メッセージ送信 =====
// メッセージを送り、AIの返答とフェーズ・目標カード・タスク案の更新を画面に反映する。
// AIが「目標が明確になった」と判定したら、確定を呼びかけるバナーを出す。
async function sendMessage(message) {
    if (currentRoomId === null) {
        alert('先に目標を作成してください。')
        return
    }
    emptyState.style.display = 'none'
    appendMessage('user', message)
    const thinking = appendMessage('ai', '思考中...')

    try {
        const data = await postJson('/task-clarify/api/message', 'POST', {
            room_id: currentRoomId,
            message: message
        })
        if (data.status === 'error') {
            thinking.remove()
            alert(data.message)
            return
        }
        thinking.lastChild.textContent = data.response
        state.phase = data.phase
        state.goal_summary = data.goal_summary
        state.task_draft = data.task_draft
        renderPhase()

        // AIが「目標が明確になった」と判定したら、確定を呼びかける
        if (data.phase === 1 && data.ready && state.goal_summary.goal) {
            readyBanner.hidden = false
            confirmGoalBtn.classList.add('highlight')
        }
    } catch (error) {
        console.error('エラー:', error)
        thinking.lastChild.textContent = '通信エラーが発生しました'
    }
}

// 送信ボタンを押したときの処理
document.getElementById('messageButton').addEventListener('click', async (e) => {
    e.preventDefault()
    const message = messageInput.value.trim()
    if (!message) {
        return
    }
    messageInput.value = ''
    await sendMessage(message)
})

// ===== フェーズ操作 =====
// 「この目標で確定」:フェーズ2へ進め、タスク案の作成をAIに依頼する
confirmGoalBtn.addEventListener('click', async () => {
    try {
        const data = await postJson('/task-clarify/api/goal/confirm', 'POST', { room_id: currentRoomId })
        if (data.status === 'error') {
            alert(data.message)
            return
        }
        state.phase = data.phase
        state.goal_summary = data.goal_summary
        renderPhase()
        // タスク案の作成を、AIに依頼する
        await sendMessage(KICKOFF_MESSAGE)
    } catch (error) {
        console.error('エラー:', error)
        alert('エラーが発生しました。')
    }
})

// 「タスクを登録」:表の編集内容を保存してから、Taskテーブルへ登録する
registerBtn.addEventListener('click', async () => {
    // 表の編集内容を保存してから登録する
    if (!await saveTaskDraft()) {
        return
    }
    try {
        const data = await postJson('/task-clarify/api/tasks/register', 'POST', { room_id: currentRoomId })
        if (data.status === 'error') {
            alert(data.message)
            return
        }
        state.phase = data.phase
        renderPhase()
        alert(`${data.registered}件のタスクを登録しました。`)
    } catch (error) {
        console.error('エラー:', error)
        alert('エラーが発生しました。')
    }
})

// ===== 目標の追加・削除 =====
// 「新しい目標」ボタン:目標名を入力するモーダルを開く
document.getElementById('newchat-btn').addEventListener('click', () => {
    document.getElementById('edit-modal').showModal()
})

// モーダルの「保存」:目標(ルーム)を作成して、その目標を開く
document.getElementById('modal-save-btn').addEventListener('click', async () => {
    const title = document.getElementById('modal-title').value
    if (!title) {
        alert('目標の名前は必須です')
        return
    }
    try {
        const room = await postJson('/chat/room_create', 'POST', { title: title, label: CHAT_LABEL })
        if (room.status === 'error') {
            alert('エラー:既にその名前で登録されています。')
        } else {
            roomContent.push({ id: room.id, title: room.title, chat_label: room.chat_label, timestamp: room.time_stamp })
            renderGoalOptions()
            await selectRoom(room.id)
        }
    } catch (error) {
        console.error('エラー:', error)
        alert('エラーが発生しました。')
    }
    closeModal()
})

document.getElementById('modal-cancel-btn').addEventListener('click', closeModal)

// モーダルの入力を消して閉じる
function closeModal() {
    document.getElementById('chat-form').reset()
    document.getElementById('edit-modal').close()
}

// 「この目標を削除」:目標と会話履歴を削除し、残っている目標があればその先頭を開く
document.getElementById('deleteGoalBtn').addEventListener('click', async () => {
    if (currentRoomId === null || !confirm('この目標と会話履歴を削除しますか?')) {
        return
    }
    try {
        await postJson(`/chat/room_delete/${currentRoomId}`, 'PUT', {})
        roomContent = roomContent.filter(r => r.id !== currentRoomId)
        sessionStorage.removeItem('activeRoomId')
        currentRoomId = null
        renderGoalOptions()
        if (roomContent.length) {
            await selectRoom(roomContent[0].id)
        } else {
            showNoRoom()
        }
    } catch (error) {
        console.error('エラー:', error)
        alert('エラーが発生しました。')
    }
})
