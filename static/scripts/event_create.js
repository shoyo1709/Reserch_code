// event_create.htmlと連携するJavascriptファイル
// イベント作成のみ対応する

//DOM要素の取得
const titleInput  = document.getElementById('titleInput');
const eventLabel = document.getElementById('event-label');
const eventStart  = document.getElementById('event-start');
const eventEnd      = document.getElementById('event-end');
const eventButton    = document.getElementById('eventButton');

//入力フォームの開始日時のinputに値が指定された時の処理
//開始日時に連動して、終了日時が指定されるようにする
eventStart.addEventListener('input', function() {
    //分数の箇所があらかじめ"00"になるように設定する　　　　//この箇所は時間があれば記述する
    console.log(eventStart.value)

    eventStart.value = formatForInput(eventStart.value)

    //イベント開始時間の1時間後に、終了時間を設定
    eventEnd.value = formatForInput_plus(eventStart.value)

    console.log(eventEnd.value)
})

//入力フォームの終了日時のinputに値が指定された時の処理
//終了日時が開始日時よりも、開始日時と同じになるように設定する。
eventEnd.addEventListener('input', function() {
    //イベントの開始時間一時間後に、終了時間を設定
    if(formatForInput(eventStart.value) > formatForInput(eventEnd.value) & eventStart.value!=""){
        eventEnd.value = formatForInput(eventStart.value)
    }
})

//入力フォームに情報を入力し、追加するボタンを押した時の処理
eventButton.addEventListener('click', async (e) => {
    //ページリロードをキャンセルする処理
    e.preventDefault();

    //2.value で値を取得 (例: "2026-04-25T15:30")
    const titleValue = titleInput.value;
    const labelValue = eventLabel.value;
    const startValue = eventStart.value;
    const endValue = eventEnd.value;

    if(!titleValue || !labelValue || !startValue || !endValue){
        alert('タイトル、ラベル、開始日時、終了日時は必須です');
        return
    }

    // //開始時間と終了時間の比較エラーチェック
    // if(timeError(startValue,endValue)){
    //     //イベントリスト欄に表示するのを防ぐ
    //     return
    // }

    try {
        //app.pyファイルの(/event/create)に向けてJSONデータを送信
        const res = await fetch('/calendar/event/create', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({"title":titleValue,"label":labelValue,"start":startValue,"end":endValue})
        });
        
        //app.pyのjsonifiyデータのレスポンスを受け取る
        // ダブルブッキングの場合の処理
        const response = await res.json();
        if(response.message=="ダブルブッキング"){
            alert(`その時間帯には、すでに他の予定があります。\nタイトル:${response.title}\n開始日時:${response.start}\n終了日時:${response.end}`)
            return
        }

        //イベントは追加されたが、分割しきれずにスケジューリングできなかった場合は、メッセージを表示する
        if(!res.ok){
            alert(response.message)
        }
        
    } catch (error) {
        //エラー処理
        console.error('エラー:', error);
        alert('通信エラーが発生しました');
    }

    // イベントリストのID取得
    const eventContainer = document.getElementById('event-list')

    // 追加されたイベントを表示
    const additionalEvent = document.createElement('li');
    additionalEvent.className='add-event'
    additionalEvent.innerHTML=`<strong>タイトル</strong>： ${titleValue}<br><strong>イベントラベル</strong>： ${labelValue}<br><strong>開始時間</strong>： ${startValue}<br><strong>終了時間</strong>： ${endValue}`
    eventContainer.appendChild(additionalEvent);

    // スクロールを下に
    eventContainer.scrollTop = eventContainer.scrollHeight;

    // スクロールを下に
    eventContainer.scrollTop = eventContainer.scrollHeight;
    
    // 入力フィールドをクリア
    document.getElementById('eventForm').reset();

})

// //開始時間と終了時間のエラーチェック：関数定義
// function timeError(start_text,end_text){
//     //文字列をデータ型に変更
//     const start_time=new Date(start_text);
//     const end_time=new Date(end_text)

//     //データ型を比較できるようにgetTime()を使用
//     if(start_time.getTime() > end_time.getTime()){
//         alert("不適切な日付入力です。")
//         //画面表示を防ぐために、ifに「true」を返す
//         return true;
//     }
// }

// datetime-local の input に渡すフォーマットに変換
//例: "2026-04-26T10:00:00" → "2026-04-26T11:00"
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