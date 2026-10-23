import os
import re
from datetime import datetime

from application.chat.config import DEFAULT_TEMPERATURE, DEFAULT_TOP_P, DEFAULT_TOP_K, DIR_OUTPUT

# =========================================
# SLM関連の変数・関数の定義
# =========================================

# タスク生成のログファイル名
filename = os.listdir(DIR_OUTPUT)
i = 0
count = 0
filename_log = "{}_t{:.2f}_p{:.2f}_k{:03d}_{}.log".format(
    datetime.today().day, DEFAULT_TEMPERATURE, DEFAULT_TOP_P, DEFAULT_TOP_K, i
)
while True:
    for file in filename:
        if file == filename_log:
            count += 1
    if count == 0:
        break
    else:
        i += 1
        count = 0
        filename_log = "0701_t{:.2f}_p{:.2f}_k{:03d}_{}.log".format(
            DEFAULT_TEMPERATURE, DEFAULT_TOP_P, DEFAULT_TOP_K, i
        )
print(f"最終的なログ：{filename_log}")

####
#### 関数
####


## 結果を整理する
## 回答文がない回答の場合
def clean_results2(results):
    # 結果の辞書を作っておく
    dic_results = {}

    # 各生成結果をスキャン
    # for result in results:
    # sentence = result[0]  # 入力文
    response = results  # 回答文

    # gpt-oss の思考部分を取り除く
    if "assistantfinal" in response:
        response = re.split("assistantfinal", response)[1]

        # Qwen3 等の think タグの部分を取り除く
    if "</think>" in response:
        response = re.split("</think>", response)[1]

    # 回答文のリストを取得
    lines = re.split(r"[\n\r]+", response)

    # 各回答文をスキャン
    new_lines = ""
    for line in lines:
        # 最初が # 記号で始まる回答文はスキップ
        if line.startswith("#"):
            continue
        # 余計な文字を削除
        line = re.sub(r"[\s\n\r]+", "", line)
        line = re.sub(r"^\d+\.\s*", "", line)
        line = re.sub(r"\*\*(.+)\*\*", r"\1", line)
        # この時点で空文字列になっていたらスキップ
        if len(line) == 0:
            continue
        # ここで採用
        new_lines += line

    # モデルと回答の対を辞書に記録
    # if sentence not in dic_results:
    #     dic_results[sentence] = []
    # dic_results[sentence].append(new_lines)

    # 結果の辞書を返す
    # return dic_results
    return new_lines


## ディレクトリがなければ作成する
def ensure_directory(dir):
    if not os.path.exists(dir):
        os.makedirs(dir)


def save_results2(sentence, results):  # 元文を1行目に生成し、2行目からresultを書き込む
    ensure_directory(DIR_OUTPUT)
    path_log = os.path.join(DIR_OUTPUT, filename_log)
    with open(path_log, "w") as f:
        print("元文:", sentence, file=f)
        print(
            "TaskName,description,deadline,priority,required_time,maxtime,mintime,interval_minutes"
        )
        for result in results:
            print(result, file=f)
        print("</finish>")


def save_results3(
    sentence, results
):  # 元文を1行目に生成し、2行目にラベル欄を生成、3行目からresult(配列)を書き込む
    ensure_directory(DIR_OUTPUT)
    path_log = os.path.join(DIR_OUTPUT, filename_log)
    with open(path_log, "w") as f:
        print("元文:", sentence, file=f)
        print("TaskName,description,deadline,priority,required_time")
        for result in results:
            print(result, file=f)


def think(result):
    lines = result.splitlines()  # 改行文字で分割し、リストにして渡す
    new_lines = ""
    in_think = False
    for line in lines:
        # DeepSeek/Qwen3 の think タグの部分をreaultに格納する
        if "<think>" in line:
            in_think = True
            new_lines = "思考過程\n"
            continue
        if "</think>" in line:
            #     in_think = False
            new_lines += "現時点での出力\n"
            continue
        if in_think:
            # ここで採用
            new_lines += line + "\n"
        if len(line) == 0:
            continue

    new_lines += "\n"

    return new_lines
