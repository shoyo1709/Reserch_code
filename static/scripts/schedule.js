// スケジュールボタンと連携するJavascriptファイル
// タスクをスケジューリングする

//スケジュールボタンを押した時、モーダルを表示する
document.getElementById('schedule').addEventListener('click', ()=>{
    //スケジューリングモーダルを表示
    document.getElementById('schedule-modal').showModal();
})

//目標達成の終了日程を指定し、決定ボタンを押した時、スケジューリングを開始し、表示する。
document.getElementById('modal-decide-btn').addEventListener('click', async() => {
//目標達成の締め切り日時を取得
const schedule_deadline = document.getElementById('schedule-deadline').value

if(!schedule_deadline){
    alert('締め切り時間を入力してください')
    return
}

//締め切り日時が現在より前の場合は、タスクを配置できないため警告して終了する
if(new Date(schedule_deadline) < new Date()){
    alert('締め切り時間は現在より後の日時を指定してください')
    return
}

console.log(schedule_deadline)

//Flask側に目標達成の締め切り日時を送信する
try{
    const res = await fetch(`/calendar/schedule`,{
    method: "POST",
    headers: {"Content-type":"application/json"},
    body: JSON.stringify({deadline:schedule_deadline})
    })
      
    //Flask側で失敗した(404や500など)場合は、完了を表示せずに終了する
    //分割しきれなかった場合は、Flask側から返されたメッセージを表示する
    if(!res.ok){
        const errorBody = await res.json().catch(() => ({}))
        alert(errorBody.message || 'スケジューリングに失敗しました。')
        return
    }
  
  
}catch(error){
    console.log(error)
    alert('通信エラーが発生しました。')
}
  
//スケジューリング完了を表示
alert('スケジューリングが完了しました。')

//作成されたplanをカレンダーに表示するため、ページを再読み込みする
location.reload()
  
//モーダルをとじる
document.getElementById('schedule-modal').close();
})
  
//キャンセルボタンを押した時、モーダルを閉じる
document.getElementById('schedule-cancel-btn').addEventListener('click', () => {
    document.getElementById('schedule-modal').close();
})
  