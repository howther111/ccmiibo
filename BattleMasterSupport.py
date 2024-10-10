import random

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
import keyboard
import time
import re
import pandas as pd
import os

def check_file_exists(filepath):
    return os.path.exists(filepath)

def handle_initiative(input_text):
    match = re.search(r'最高行動値キャラクターは(.+?)です', input_text)
    if match:
        character_name = match.group(1).strip()
        return f"{character_name}のメインプロセスを開始します。ムーブアクション、マイナーアクション、メジャーアクションを宣言してください。終了したら、『メインプロセス終了』と発言してください"
    return "…"
def metaga_gm_response(input_text=""):
    global round_count  # グローバル変数を使用
    print(round_count)

    # CSVファイルの読み込み
    scenario_flg = False
    if check_file_exists('scenario.csv'):
        df = pd.read_csv('scenario.csv')
        scenario_flg = True

    # データフレームの表示
    #print(df)

    # Respond to the first statement
    if "アクティブ状態" in input_text:
        return "こんにちは、メタガGMさんです。メタリックガーディアンRPGの戦闘マスタリングを開始します。『勝利条件：〇〇』という形で勝利条件を提示してください"

    if "戦闘マスタリング開始" in input_text:
        return "こんにちは、メタガGMさんです。メタリックガーディアンRPGの戦闘マスタリングを開始します。『勝利条件：〇〇』という形で勝利条件を提示してください"

    if "戦闘マスタリング再開" in input_text:
        return "こんにちは、メタガGMさんです。メタリックガーディアンRPGの戦闘マスタリングを再開します"

    # When "勝利条件：" appears
    if "勝利条件：" in input_text:
        return "初期配置をお願いします。終了したら『初期配置完了』と宣言してください"

    # When "初期配置完了" appears
    if "初期配置完了" in input_text:
        return "セットアッププロセスを開始します。『セットアッププロセス終了』という発言があればプロセスを終了します"

    # When "セットアッププロセス終了" appears
    if "セットアッププロセス終了" in input_text:
        return "イニシアチブプロセスを開始します。タイミング：イニシアチブプロセスの特技を使用したい場合は使用してください。終了後、最も行動値の高い未行動のキャラクターを確認し、『最高行動値キャラクターは〇〇です』と答えてください"

    # When "最高行動値キャラクターは〇〇です" appears
    if "最高行動値キャラクターは" in input_text:
        return handle_initiative(input_text)

    # When "メインプロセス終了" appears
    if "メインプロセス終了" in input_text:
        return "イニシアチブプロセスを開始します。タイミング：イニシアチブプロセスの特技を使用したい場合は使用してください。終了後、最も行動値の高い未行動のキャラクターを確認し、『最高行動値キャラクターは〇〇です』と答えてください。全員が行動を終了している場合、『未行動なしです』と答えてください"

    # When "未行動なしです" appears
    if "未行動なしです" in input_text:
        return "クリンナッププロセスを開始します。タイミング：クリンナッププロセスの特技を使用したい場合は使用してください。終了後、『クリンナッププロセス終了』と答えてください"

    # When "クリンナッププロセス終了" appears
    if "クリンナッププロセス終了" in input_text:
        return "セットアッププロセスを開始します。『セットアッププロセス終了』という発言があればプロセスを終了します"

    # When "勝利条件を達成しました" appears
    if "勝利条件を達成しました" in input_text:
        return "戦闘終了です。お疲れ様でした"

    if "攻撃します" in input_text:
        return "攻撃代償の消費後、命中判定を行ってください"

    if "特技を使用します" in input_text:
        return "代償を消費してください"

    if "回避します" in input_text:
        return "回避判定を行ってください。タイミング：リアクションの特技があれば使用することができます"

    if "命中しました" in input_text:
        return "攻撃側はダメージロールを行ってください。タイミング：ダメージロール直前の特技があれば使用することができます"

    if scenario_flg:
        start_match = df[df['start_word'].apply(lambda x: x in input_text)]
        if not start_match.empty:
            return start_match['text'].values[0]

        match_index = df[df['end_word'].apply(lambda x: x in input_text)].index
        if not match_index.empty:
            next_index = match_index[0] + 1
            if next_index < len(df):
                return df.loc[next_index, 'text']

    # For any input that doesn't match the conditions
    return "…"

# Example usage:
# response = metaga_gm_response("勝利条件：敵を倒す")
# print(response)

with open('ccforia_url.txt', 'r', encoding='utf-8') as file:
    # ファイルの内容をすべて読み込む
    ccforia_url = file.read()

# 読み込んだデータを表示
print(ccforia_url)

# ChromeDriverのパスを指定 (自身の環境に合わせてパスを変更)
chrome_driver_path = ''

# Chromeオプションを設定
chrome_options = Options()
chrome_options.add_argument('--start-maximized')  # 最大化オプション（必要な場合）

# ChromeDriverのサービスを設定
service = Service(executable_path=chrome_driver_path)

# WebDriverオブジェクトを作成
driver_cc = webdriver.Chrome(service=service, options=chrome_options)

# ウィンドウサイズを指定
driver_cc.set_window_size(1200, 800)

# ウィンドウ位置を指定 (x=800, y=0)
driver_cc.set_window_position(0, 0)

# 指定したURLを開く
url = ccforia_url
driver_cc.get(url)

print("Escキーを押すと終了します。")

# Escキーが押されるまで1秒ごとに待機するループ
timecount = 0
before_text = ""
startcount = 5
ai_comment_flg = False
kakko_flg = False
global round_count  # グローバル変数を使用
round_count = 0
while True:
    if keyboard.is_pressed('esc'):  # Escキーが押されたかどうかをチェック
        print("Escキーが押されました。終了します。")
        driver_cc.quit()
        break
    time.sleep(1)  # 1秒待機

    if timecount < startcount:
        timecount = timecount + 1
        print(timecount)

    charaouto = ""

    if timecount == startcount:
        try:

            # h5タグのテキストを抽出します
            character_name = "バトルマスターサポート"
            charaouto = character_name + "応答"

            close_button = driver_cc.find_element(By.XPATH, '//button[text()="閉じる"]')
            close_button.click()
            print("ボタンをクリックしました。")
            time.sleep(1)
            print("ココフォリアウィンドウでキャラクターを設定してください。")
            timecount = timecount + 1
        except:
            print("「閉じる」ボタンが見つかりませんでした。")
            timecount = timecount + 1

    if timecount > startcount:
        # classが'MultiTypography-root'の<p>タグを全て取得
        elements = driver_cc.find_elements(By.CLASS_NAME, 'MuiListItemText-secondary')

        time.sleep(1)

        # 最後の<p>タグを取得し、テキストを抽出
        if elements:
            last_element = elements[-1]
            text = last_element.text
            response = ""
            response_flg = False
            if not text == before_text:
                print("最後の<p>タグ内のテキスト:", text)
                if kakko_flg:
                    response = "「" + metaga_gm_response(text) + "」"
                else:
                    response = metaga_gm_response(text)
                print(response)

            if (not response == "…") and (not response == "「…」"):
                response_flg = True

            if text == before_text:
                ai_comment_flg = False

            if (not text == before_text) and response_flg == True and ai_comment_flg ==False:
                print("send process")
                # 1. placeholderが「メッセージを入力」となっている<textarea>を取得
                textarea_cc = driver_cc.find_element(By.XPATH,
                                                     '//textarea[@placeholder="メッセージを入力"]')

                # 2. last_p_textの値を<textarea>に入力
                textarea_cc.send_keys(response)

                # 3. テキストが「送信」となっているsubmitボタンを取得
                submit_button = driver_cc.find_element(By.XPATH, '//button[text()="送信"]')

                # 4. submitボタンをクリックしてメッセージを送信
                submit_button.click()

                ai_comment_flg = True
            # もとのコンテンツに戻る
            before_text = text

        else:
            print("該当する<p>タグが見つかりませんでした。")

# 必要な処理を追加...

# 終了時にブラウザを閉じる
# driver.quit()