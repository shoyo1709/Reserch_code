// reflection.htmlと連携するJavascriptファイル

const dateInput = document.getElementById('reflectionDate')
const keepInput = document.getElementById('keepContent')
const problemInput = document.getElementById('problemContent')
const tryInput = document.getElementById('tryContent')
const saveBtn = document.getElementById('saveBtn')
const generateBtn = document.getElementById('generateBtn')
const questionArea = document.getElementById('questionArea')
const feedbackBtn = document.getElementById('feedbackBtn')
const feedbackBox = document.getElementById('feedbackBox')
const feedbackText = document.getElementById('feedbackText')

let savedComplete = false // 選択中の日付で、K・P・Tの3つが保存済みか
let isGenerating = false // 質問の生成中か
let isFeedbackGenerating = false // フィードバックの生成中か

// 今日の日付(YYYY-MM-DD、ローカル時刻)
function todayString() {
    const now = new Date()
    const month = String(now.getMonth() + 1).padStart(2, '0')
    const day = String(now.getDate()).padStart(2, '0')
    return `${now.getFullYear()}-${month}-${day}`
}

// 日付の初期化(今日まで選択可能)
function initDate() {
    dateInput.max = todayString()
    dateInput.value = todayString()
}

// K・P・Tの3つがすべて入力されているか
/////　K・P・Tが3つ揃わないと、深掘り生成されないように制限するために設定
function isAllFilled(keep, problem, tryText) {
    return [keep, problem, tryText].every(text => text.trim() !== '')
}

// 生成ボタンの状態を更新する
// K・P・Tが保存済みで、かつ現在の入力も3つとも空でないときだけ押せる
function updateGenerateBtn() {
    const inputFilled = isAllFilled(keepInput.value, problemInput.value, tryInput.value)
    generateBtn.disabled = isGenerating || !(savedComplete && inputFilled)
    feedbackBtn.disabled = isFeedbackGenerating || !(savedComplete && inputFilled)
}

// フィードバックを表示する(空なら非表示にする)
function showFeedback(feedback) {
    feedbackText.textContent = feedback
    feedbackBox.hidden = !feedback
}

// 深掘り質問のボックスを追加する
function addQuestionBox(q) {
    const box = document.createElement('div')
    box.className = 'question-box'
    box.dataset.id = q.id

    const question = document.createElement('p')
    question.className = 'question-text'
    question.textContent = q.question

    const answer = document.createElement('textarea')
    answer.className = 'answer-input'
    answer.placeholder = '回答を入力...'
    answer.value = q.answer

    box.appendChild(question)
    box.appendChild(answer)
    questionArea.appendChild(box)
}

// 選択中の日付の振り返りを取得して表示する
async function loadEntry() {
    // 日付が未選択(入力欄をクリアされた場合)は今日に戻す
    if (!dateInput.value) {
        dateInput.value = todayString()
    }

    try {
        const res = await fetch('/reflection/api/entry', {
            method: 'POST',
            headers: { 'Content-type': 'application/json' },
            body: JSON.stringify({ date: dateInput.value })
        })
        const data = await res.json()

        if (data.status === 'error') {
            alert(data.message)
            return
        }

        keepInput.value = data.keep_content
        problemInput.value = data.problem_content
        tryInput.value = data.try_content
        questionArea.innerHTML = ''
        data.questions.forEach(addQuestionBox)
        showFeedback(data.feedback)

        // 取得したデータ(=保存済みの内容)で、生成ボタンの状態を決める
        savedComplete = isAllFilled(data.keep_content, data.problem_content, data.try_content)
    } catch (error) {
        console.error('エラー:', error)
        alert('エラーが発生しました。')
    }
    updateGenerateBtn()
}

// K・P・Tと、全質問への回答を保存する(成功したらtrueを返す)
async function saveEntry() {
    // 質問IDごとの回答を集める
    const answers = {}
    questionArea.querySelectorAll('.question-box').forEach(box => {
        answers[box.dataset.id] = box.querySelector('.answer-input').value
    })

    const keep = keepInput.value
    const problem = problemInput.value
    const tryText = tryInput.value

    try {
        const res = await fetch('/reflection/api/entry', {
            method: 'PUT',
            headers: { 'Content-type': 'application/json' },
            body: JSON.stringify({
                date: dateInput.value,
                keep_content: keep,
                problem_content: problem,
                try_content: tryText,
                answers: answers
            })
        })
        const data = await res.json()

        if (data.status === 'error') {
            alert(data.message)
            return false
        }

        // 保存した内容で、生成ボタンの状態を更新する
        savedComplete = isAllFilled(keep, problem, tryText)
        updateGenerateBtn()
        return true
    } catch (error) {
        console.error('エラー:', error)
        alert('エラーが発生しました。')
        return false
    }
}

// 保存ボタン
saveBtn.addEventListener('click', async () => {
    if (await saveEntry()) {
        alert('保存しました。')
    }
})

// 深掘り質問の生成ボタン:保存してから、質問を1つ生成する
generateBtn.addEventListener('click', async () => {
    isGenerating = true
    generateBtn.textContent = '生成中…'
    updateGenerateBtn()

    try {
        if (!(await saveEntry())) {
            return
        }
        
        // Flask側にK・P・Tの情報を送信
        const res = await fetch('/reflection/api/questions/generate', {
            method: 'POST',
            headers: { 'Content-type': 'application/json' },
            body: JSON.stringify({ date: dateInput.value })
        })
        const data = await res.json()

        // エラーチェック
        if (data.status === 'error') {
            alert(data.message)
            return
        }
        addQuestionBox(data)
    
    } catch (error) {
        console.error('エラー:', error)
        alert('エラーが発生しました。')
    } finally {
        isGenerating = false
        generateBtn.textContent = '深掘り質問を生成'
        updateGenerateBtn()
    }
})

// フィードバックの生成ボタン:保存してから、フィードバックを生成する
feedbackBtn.addEventListener('click', async () => {
    isFeedbackGenerating = true
    feedbackBtn.textContent = '生成中…'
    updateGenerateBtn()

    try {
        if (!(await saveEntry())) {
            return
        }

        const res = await fetch('/reflection/api/feedback/generate', {
            method: 'POST',
            headers: { 'Content-type': 'application/json' },
            body: JSON.stringify({ date: dateInput.value })
        })
        const data = await res.json()

        // エラーチェック
        if (data.status === 'error') {
            alert(data.message)
            return
        }
        showFeedback(data.feedback)

    } catch (error) {
        console.error('エラー:', error)
        alert('エラーが発生しました。')
    } finally {
        isFeedbackGenerating = false
        feedbackBtn.textContent = 'フィードバックを生成'
        updateGenerateBtn()
    }
})

// 日付を変更したら、その日の振り返りを表示する
dateInput.addEventListener('change', loadEntry)

// K・P・Tの入力が変わったら、生成ボタンの状態を更新する
;[keepInput, problemInput, tryInput].forEach(input => {
    input.addEventListener('input', updateGenerateBtn)
})

initDate()
loadEntry()
