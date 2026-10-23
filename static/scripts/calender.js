//calendar.htmlと連携するJavascriptファイル
//カレンダーのイベント表示・削除・作成を行う

// カレンダーインスタンスを保持する変数
let calendarInstance = null;
// クリックされたイベントを保持する変数
let selectedEvent = null;

//DOM要素の取得
const newTitle = document.getElementById('modal-title')
const newLabel = document.getElementById('modal-label')
const newDescription = document.getElementById('modal-description')
const newStart = document.getElementById('modal-start')
const newEnd   = document.getElementById('modal-end')
const progressGroup = document.getElementById('progress-group')
const progressInput = document.getElementById('modal-progress')

/////このままだとページロード時しかカレンダーデータが反映されない
/////対策を考えないといけない
// ページ読み込み時の初期化
document.addEventListener('DOMContentLoaded', function() {
  //初回実行
  initializeCalendar();
  //初回ページロード時のカレンダー表示
  loadEventsFromTemplateData(); // render_template で送信されたデータを読み込む
});



// Fullcalendarの初期化
function initializeCalendar() {
  //初期処理
  var calendarEl = document.getElementById('calendar');
  calendarInstance = new FullCalendar.Calendar(calendarEl, {
    //ここに各種オプションを書いていくと設定が適応されていく

    // カレンダー画面の高さを画面の大きさに自動設定
    height: "auto",

    // カレンダーに表示する文字の言語選択
    locale: 'ja',

    //土日の色付け
    businessHours: true,

    //現在時刻に赤い線を引く
    nowIndicator:true,

    //editable: true, // 編集可能にする(自由に動かせる)
    selectable: true, // 日付選択可能にする(クリックが可能になる)

    // 日表示時の最大表示イベント数（最大値を超えた部分は「+more」で表示）
    dayMaxEvents: 2,

    //日付クリックすると、1日のスケジュール画面に遷移
    dateClick: function(info) {
      calendarInstance.changeView('timeGridDay',info.dateStr);
    },

    // イベントクリック
    eventClick: (info) => {
      // 選択したイベント情報の取得
      selectedEvent=info.event

      // イベントの現在値をモーダルに反映
      newTitle.value = selectedEvent.title;
      newLabel.value = selectedEvent.extendedProps.event_label;
      newDescription.value = selectedEvent.extendedProps.description;
      newStart.value = formatForInput(selectedEvent.start);
      newEnd.value   = formatForInput(selectedEvent.end);

      // 進捗時間の入力欄は、タスクの予定のときだけ表示する(保存済みの進捗時間を入力枠に反映)
      progressInput.value = selectedEvent.extendedProps.worked_time ?? 0;
      // 進捗時間の上限は、予定の開始〜終了の長さ(分)
      progressInput.max = Math.round((selectedEvent.end - selectedEvent.start) / 60000);
      progressGroup.style.display = selectedEvent.extendedProps.task_id != 0 ? 'flex' : 'none';

      // モーダルを表示
      document.getElementById('edit-modal').showModal();
    },
    
    // 「◯◯日」部分の「日」をカット
    dayCellContent: function(e) {
      e.dayNumberText = e.dayNumberText.replace('日', '');
      return e.dayNumberText
    },

    //ヘッダーのタイトルとボタン
    headerToolbar: {
      left: "prev,next today",
      center: "title",
      // right: "dayGridMonth,timeGridWeek,timeGridDay,listMonth"
      right: "dayGridMonth,timeGridWeek,listMonth"
    },
    
    //テーマシステムを「bootstrap5」に設定
    //themeSystem: 'bootstrap5',

    events: []
  });

  //キャンパスにレンダリング
  calendarInstance.render();
}

/**
 * render_template で送信されたイベントデータを読み込む処理
 * HTMLの <script id="eventsData"> から JSON データを抽出
 */
function loadEventsFromTemplateData() {
  try {
      //howMessage('イベントを読み込み中...', 'info');
      
      // HTMLの script タグから JSON データを取得
      //Fullcalendarの使用上、カレンダーに表示する予定は全て「event」扱いなので、jsファイルではタスク・イベント・プラン全ての情報を「event」とする
      const eventsDataElement = document.getElementById('eventsData');
      
      if (!eventsDataElement) {
        throw new Error('イベントデータが見つかりません');
      }
      
      // JSON文字列をパース
      const eventsData = JSON.parse(eventsDataElement.textContent);
      
      if (!Array.isArray(eventsData)) {
          throw new Error('イベントデータが配列ではありません');
      }
      
      // 各イベントをFullcalendarに追加
      for(i=0;i < eventsData.length;i++){
        //「delete_flag」が「0」、つまり削除されたplan出なかったら、カレンダーに追加
        if(eventsData[i].delete_flag=="0"){
          calendarInstance.addEvent({
            id: eventsData[i].id,
            title: eventsData[i].title,
            start: eventsData[i].start,
            end: eventsData[i].end,
            // backgroundColor: event.backgroundColor,
            // borderColor: event.borderColor,
            // textColor: event.textColor,
            extendedProps: {
              event_label: eventsData[i].event_label,
              description: eventsData[i].description,
              task_id: eventsData[i].task_id,
              event_id: eventsData[i].event_id,
              worked_time: eventsData[i].worked_time,
              //     location: event.location || '',
              //     category: event.category || ''
            }
          });
        }
      }

      console.log('読み込んだイベント:', eventsData);
      
  } catch (error) {
      console.error('イベント読み込みエラー:', error);
  }
}


// datetime-local の input に渡すフォーマットに変換
//例: "2026-04-26T10:00:00" → "2026-04-26T10:00"
//d.getMonth()+1：getMonth()は0月から数えるため、+1にしている
function formatForInput(date) {
  const d = new Date(date);
  // 数値を二桁に変更する関数（例："0"=>"00"）
  const pad = n => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${pad(d.getMonth()+1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(0)}`;
}


//開始日時の一時間後に設定する関数
//例: "2026-04-26T10:00:00" → "2026-04-26T11:00"
function formatForInput_plus(date) {
  const d = new Date(date);
  const pad = n => String(n).padStart(2, '0');
  // 24時以降になるかの判定
  if(d.getHours()+1 >= 24){
      // d.getHours()が24時以降の場合は、0時になるように変更する
      return `${d.getFullYear()}-${pad(d.getMonth()+1)}-${pad(d.getDate()+1)}T${pad(0)}:${pad(d.getMinutes())}`;
  }
  else{
      return `${d.getFullYear()}-${pad(d.getMonth()+1)}-${pad(d.getDate())}T${pad(d.getHours()+1)}:${pad(d.getMinutes())}`;
  }
}


//入力フォームの開始日時のinputに値が指定された時の処理
//開始日時に連動して、終了日時が指定されるようにする
newStart.addEventListener('input', function() {
  //分数の箇所があらかじめ"00"になるように設定する　　　　//この箇所は時間があれば記述する
  console.log(newStart.value)

  newStart.value = formatForInput(newStart.value)

  //イベント開始時間の1時間後に、終了時間を設定
  newEnd.value = formatForInput_plus(newStart.value)

  console.log(newEnd.value)
})


//入力フォームの終了日時のinputに値が指定された時の処理
//終了日時が開始日時よりも前の日程になった場合、開始日時と同じになるように設定する。
newEnd.addEventListener('input', function() {
  //イベントの開始時間一時間後に、終了時間を設定
  if(formatForInput(newStart.value) > formatForInput(newEnd.value) & newStart.value!=""){
    newEnd.value = formatForInput_plus(newStart.value)
  }
})


//　イベント情報を入力して、データベースに保存するため、Flaskに情報を送る
document.getElementById('modal-save-btn').addEventListener('click', async() => {
  // const newTitle = document.getElementById('modal-title').value.trim(); //「.trim()」は空白をなくし、バリデーションをつけるためにある。
  // const newLabel = document.getElementById('modal-label').value;
  // const newStart = document.getElementById('modal-start').value;
  // const newEnd   = document.getElementById('modal-end').value;

  
  //情報が漏れなく記載されているかのバリデーション
  if (!newTitle.value.trim() || !newStart.value || !newEnd.value) { //「.trim()」は空白をなくし、バリデーションをつけるため。
    alert('タイトルと開始日時、終了日時は必須です');
    return;
  }

  // タスクの場合は、そのplanの日時だけを変更する
  if (selectedEvent.extendedProps.task_id != 0) {
    try {
      const res = await fetch(`/calendar/plan/update/${selectedEvent.id}`,{
        method: 'PUT',
        headers: {'Content-type':'application/json'},
        body: JSON.stringify({start:newStart.value,end:newEnd.value})
      })
      const response = await res.json()

      // 日時は変更されたが、分割しきれずに再スケジューリングできなかった場合は、メッセージを表示する
      if (!res.ok) {
        alert(response.message)
        location.reload()
        return
      }

      // 他のイベント・タスクと時間が被っている場合は、エラーを表示して変更しない
      if (response.message == "時間が重複しています") {
        alert(`その時間帯には、すでに他の予定があります。\nタイトル:${response.title}\n開始日時:${response.start}\n終了日時:${response.end}`)
        return
      }
      location.reload()
    }
    catch(error){
      console.error('エラー:', error);
      alert('エラーが発生しました。')
    }
    return
  }

  try {
    const res = await fetch(`/calendar/event/update/${selectedEvent.extendedProps.event_id}`,{
      method: 'PUT',
      headers: {'Content-type':'application/json'},
      body: JSON.stringify({title:newTitle.value.trim(),event_label:newLabel.value,start:newStart.value,end:newEnd.value})
    })

    //Flaskから、返信が返ってきたら、再スケジューリングされたplanを表示するため、ページを再読み込みする
    const updateMessage = await res.json(); // Flaskから保存済みデータを受け取る
    // 変更は保存されたが、分割しきれずに再スケジューリングできなかった場合は、メッセージを表示する
    if(!res.ok){
      alert(updateMessage.message)
    }
    if(updateMessage){
      location.reload()
    }
  }
  catch(error){
    //エラー処理
    console.error('エラー:', error);
    alert('エラーが発生しました。')
  }

  //モーダルをとじる
  closeModal();
})


// 進捗を保存ボタンを押した時の処理
// 入力した進捗時間(分)をplanに保存し、変更前との差分をタスクの進捗に反映する(再スケジューリングはしない)
document.getElementById('modal-progress-btn').addEventListener('click', async() => {
  const minutes = Number(progressInput.value)
  if (progressInput.value === '' || !Number.isInteger(minutes) || minutes < 0) {
    alert('進捗時間は0以上の整数(分)で入力してください')
    return
  }
  // 予定の長さを超える進捗時間は保存できない
  if (minutes > Number(progressInput.max)) {
    alert(`進捗時間は予定の長さ(${progressInput.max}分)以下で入力してください`)
    return
  }

  try {
    const res = await fetch(`/calendar/plan/progress/${selectedEvent.id}`,{
      method: 'PUT',
      headers: {'Content-type':'application/json'},
      body: JSON.stringify({minutes:minutes})
    })
    const response = await res.json()
    if (!res.ok) {
      alert(response.message)
      return
    }
    // 次に同じ予定を開いたときも、保存した値が表示されるようにする
    selectedEvent.setExtendedProp('worked_time', minutes)
    closeModal()
  }
  catch(error){
    console.error('エラー:', error);
    alert('エラーが発生しました。')
  }
})


// モーダルを閉じる関数の定義
function closeModal() {
  selectedEvent = null;
  document.getElementById('edit-modal').close();
}


// キャンセルボタン
document.getElementById('modal-cancel-btn').addEventListener('click', closeModal);


//削除ボタン押した時の処理
document.getElementById('modal-delete-btn').addEventListener('click', async() => {
  //削除するかの最終確認を挟む
  if(confirm("この予定を削除しますか?")){
    try{
      //Flaskへデータの送信(ただし、送信するデータは「id」のみ)
      const res = await fetch(`/calendar/event/delete/${selectedEvent.extendedProps.event_id}`,{
        method: "PUT",
        headers: {"Content-type":"application/json"},
      })
      
      //////「削除メッセージの取得」は不要：理由はスケジューリング自体を変更するため
      //削除メッセージの取得
      // const deleteMessage = await res.json()
      // if(deleteMessage){
      //   //メッセージを受け取ったら、イベントを削除
      //   selectedEvent.remove()
      // }

      // 削除は保存されたが、分割しきれずに再スケジューリングできなかった場合は、メッセージを表示する
      if(!res.ok){
        const deleteMessage = await res.json()
        alert(deleteMessage.message)
      }

      //再スケジューリングされたplanを表示するため、ページを再読み込みする
      location.reload()
    }

    catch(error){
      console.log(error)
      alert('通信エラーが発生しました。')
    }
  }
})





