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

with open('ccforia_url.txt', 'r', encoding='utf-8') as file:
    # ファイルの内容をすべて読み込む
    ccforia_url = file.read()

# 読み込んだデータを表示
print(ccforia_url)

with open('miibo_url.txt', 'r', encoding='utf-8') as file:
    # ファイルの内容をすべて読み込む
    miibo_url = file.read()

# 読み込んだデータを表示
print(miibo_url)

with open('comment_rate.txt', 'r', encoding='utf-8') as file:
    # ファイルの内容をすべて読み込む
    comment_rate = int(file.read())

# 読み込んだデータを表示
print(comment_rate)

# ChromeDriverのパスを指定 (自身の環境に合わせてパスを変更)
chrome_driver_path = ''

# Chromeオプションを設定
chrome_options = Options()
chrome_options.add_argument('--start-maximized')  # 最大化オプション（必要な場合）

# ChromeDriverのサービスを設定
service = Service(executable_path=chrome_driver_path)

# WebDriverオブジェクトを作成
driver_mi = webdriver.Chrome(service=service, options=chrome_options)

# ウィンドウサイズを指定
driver_mi.set_window_size(800, 600)

# ウィンドウ位置を指定 (x=800, y=0)
driver_mi.set_window_position(0, 0)

# 指定したURLを開く
url = miibo_url
driver_mi.get(url)

# WebDriverオブジェクトを作成
driver_cc = webdriver.Chrome(service=service, options=chrome_options)

# ウィンドウサイズを指定
driver_cc.set_window_size(800, 600)

# ウィンドウ位置を指定 (x=800, y=0)
driver_cc.set_window_position(800, 0)

# 指定したURLを開く
url = ccforia_url
driver_cc.get(url)

print("Escキーを押すと終了します。")

# Escキーが押されるまで1秒ごとに待機するループ
timecount = 0
before_text = ""
startcount = 5
start_flg = True
ai_comment_flg = False
while True:
    if keyboard.is_pressed('esc'):  # Escキーが押されたかどうかをチェック
        print("Escキーが押されました。終了します。")
        driver_mi.quit()
        driver_cc.quit()
        break
    time.sleep(1)  # 1秒待機

    if timecount < startcount:
        timecount = timecount + 1
        print(timecount)

    if timecount == startcount:
        try:
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

        # 最後の<p>タグを取得し、テキストを抽出
        if elements:
            last_element = elements[-1]
            text = last_element.text
            if not text == before_text:
                print("最後の<p>タグ内のテキスト:", text)

            if text == before_text:
                ai_comment_flg = False

            if not text == before_text and start_flg == False and ai_comment_flg == False:
                # iframeに切り替え
                driver_mi.switch_to.frame(driver_mi.find_element(By.TAG_NAME, "iframe"))

                textarea = driver_mi.find_element(By.ID, 'chat-id-2-input')

                # 変数 text の値を textarea に入力
                textarea.send_keys(text)

                # Enterキーを押下
                textarea.send_keys(Keys.ENTER)

                # クラス名が 'btn-primary' のボタンを取得
                #button = driver_mi.find_element(By.CLASS_NAME, 'btn-primary')

                # ボタンをクリック
                #button.click()

                randomNum = random.randint(1, 100)

                if "強制応答" in text:
                    randomNum = 0
                elif "応答なし" in text:
                    randomNum = 101
                elif "mustreply" in text:
                    randomNum = 0
                elif "noreply" in text:
                    randomNum = 101

                if randomNum <= comment_rate:
                    time.sleep(10)

                    # 'message-content' クラスを持つ全ての <div> 要素を取得
                    div_elements = driver_mi.find_elements(By.CLASS_NAME, 'message-content')

                    # 最後の <div> 要素を取得
                    if div_elements:
                        last_div = div_elements[-1]

                        # 最後の <div> 内にある全ての <p> タグを取得
                        p_elements = last_div.find_elements(By.TAG_NAME, 'p')

                        # 最後の <p> タグのテキストを取得
                        if p_elements:
                            last_p_text = "「" + p_elements[-1].text + "」"
                            print("最後の <p> タグ内のテキスト:", last_p_text)

                            # 1. placeholderが「メッセージを入力」となっている<textarea>を取得
                            textarea_cc = driver_cc.find_element(By.XPATH, '//textarea[@placeholder="メッセージを入力"]')

                            # 2. last_p_textの値を<textarea>に入力
                            textarea_cc.send_keys(last_p_text)

                            # 3. テキストが「送信」となっているsubmitボタンを取得
                            submit_button = driver_cc.find_element(By.XPATH, '//button[text()="送信"]')

                            # 4. submitボタンをクリックしてメッセージを送信
                            submit_button.click()

                            ai_comment_flg = True

                            before_text = last_p_text
                        else:
                            print("最後の <div> 内に <p> タグが見つかりませんでした。")
                    else:
                        print("クラス名 'message-content' の <div> タグが見つかりませんでした。")

            # もとのコンテンツに戻る
            driver_mi.switch_to.default_content()
            before_text = text
            start_flg = False

        else:
            print("該当する<p>タグが見つかりませんでした。")

# 必要な処理を追加...

# 終了時にブラウザを閉じる
# driver.quit()