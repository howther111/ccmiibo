import random
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
# from selenium.webdriver.chrome.service import Service ←削除
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
import keyboard
import time
import os
from distutils.util import strtobool
import sys

def resource_path(relative_path):
    if getattr(sys, 'frozen', False):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.dirname(__file__)
    return os.path.join(base_path, relative_path)

def check_file_exists(filepath):
    return os.path.exists(filepath)

ccforia_url = ""
kakko_flg = False
miibo_url = ""

with open('ccforia_url.txt', 'r', encoding='utf-8') as file:
    ccforia_url = str(file.read())

print(ccforia_url)

with open('kakko_flg.txt', 'r', encoding='utf-8') as file:
    kakko_flg = strtobool(file.read())

print(kakko_flg)

with open('miibo_url.txt', 'r', encoding='utf-8') as file:
    miibo_url = str(file.read())

print(miibo_url)

comment_rate = 0

# Chromeオプションを設定
chrome_options = Options()
chrome_options.add_argument('--start-maximized')

# ChromeDriverはSelenium Managerが自動取得
driver_mi = webdriver.Chrome(options=chrome_options)

# ウィンドウサイズを指定
driver_mi.set_window_size(600, 800)

# ウィンドウ位置を指定
driver_mi.set_window_position(0, 0)

# 指定したURLを開く
driver_mi.get(miibo_url)

# 2つ目のブラウザも同様
driver_cc = webdriver.Chrome(options=chrome_options)

driver_cc.set_window_size(1000, 800)
driver_cc.set_window_position(600, 0)

driver_cc.get(ccforia_url)

print("Escキーを長押しすると終了します。")

# 以下は元のコードのまま
timecount = 0
before_text = ""
startcount = 5
start_flg = True
ai_comment_flg = False
loop_fig = True

while loop_fig:
    if keyboard.is_pressed('esc'):
        print("Escキーが押されました。終了します。")
        driver_mi.quit()
        driver_cc.quit()
        loop_fig = False
        os.system("taskkill /f /im ccmiibo3.exe")
        break

    time.sleep(1)

    if timecount < startcount:
        timecount += 1
        print(timecount)

    charaouto = ""

    if timecount == startcount:
        try:
            driver_mi.switch_to.frame(driver_mi.find_element(By.TAG_NAME, "iframe"))

            card_body = driver_mi.find_element(By.CLASS_NAME, 'card-body')
            h5_element = card_body.find_element(By.TAG_NAME, 'h5')

            character_name = h5_element.text
            charaouto = character_name + "応答"

            driver_mi.switch_to.default_content()

            close_button = driver_cc.find_element(By.XPATH, '//button[text()="閉じる"]')
            close_button.click()

            print("ボタンをクリックしました。")
            time.sleep(1)

            print("ココフォリアウィンドウでキャラクターを設定してください。")

            timecount += 1

        except:
            print("「閉じる」ボタンが見つかりませんでした。")
            timecount += 1

    if timecount > startcount:

        elements = driver_cc.find_elements(By.CLASS_NAME, 'MuiListItemText-secondary')

        if elements:
            last_element = elements[-1]
            text = last_element.text

            if text != before_text:
                print("最後の<p>タグ内のテキスト:", text)

            if text == before_text:
                ai_comment_flg = False

            driver_mi.switch_to.frame(driver_mi.find_element(By.TAG_NAME, "iframe"))

            card_body = driver_mi.find_element(By.CLASS_NAME, 'card-body')
            h5_element = card_body.find_element(By.TAG_NAME, 'h5')

            character_name = h5_element.text
            charaouto = character_name + "応答"

            driver_mi.switch_to.default_content()

            if text != before_text and start_flg == False and ai_comment_flg == False:

                newtext = text.replace("強制応答", "")
                newtext = newtext.replace("応答なし", "")
                newtext = newtext.replace("mustreply", "")
                newtext = newtext.replace("noreply", "")
                newtext = newtext.replace(charaouto, "")
                newtext = newtext.replace("カッコなし", "")
                newtext = newtext.replace("カッコ無し", "")

                kakkoflg = True

                driver_mi.switch_to.frame(driver_mi.find_element(By.TAG_NAME, "iframe"))

                textarea = driver_mi.find_element(By.ID, 'chat-id-2-input')

                textarea.send_keys(newtext)
                textarea.send_keys(Keys.ENTER)

                with open('comment_rate.txt', 'r', encoding='utf-8') as file:
                    comment_rate = int(file.read())

                print(comment_rate)

                randomNum = random.randint(1, 100)

                if "強制応答" in text:
                    randomNum = 0
                elif "応答なし" in text:
                    randomNum = 101
                elif "mustreply" in text:
                    randomNum = 0
                elif "noreply" in text:
                    randomNum = 101
                elif charaouto in text:
                    randomNum = 0

                print("randomNum = " + str(randomNum))

                if "カッコなし" in text or "カッコ無し" in text or kakko_flg == False:
                    kakkoflg = False

                if randomNum <= comment_rate:

                    time.sleep(10)

                    div_elements = driver_mi.find_elements(By.CLASS_NAME, 'message-content')

                    if div_elements:

                        last_div = div_elements[-1]
                        p_elements = last_div.find_elements(By.TAG_NAME, 'p')

                        if p_elements:

                            last_p_text = ""
                            blankFlg = False

                            add_text = ""

                            if check_file_exists('addtext.txt'):
                                with open('addtext.txt', 'r', encoding='UTF-8') as f:
                                    add_text = f.read()

                            if kakkoflg:
                                last_p_text = "「" + p_elements[-1].text + "」" + add_text
                            else:
                                last_p_text = p_elements[-1].text + add_text

                            if p_elements[-1].text in ["回答なし", "回答無し", "…"]:
                                blankFlg = True

                            print("最後の<p>タグ内のテキスト:", last_p_text)

                            if not blankFlg:

                                textarea_cc = driver_cc.find_element(
                                    By.XPATH,
                                    '//textarea[@placeholder="メッセージを入力"]'
                                )

                                textarea_cc.send_keys(last_p_text)

                                submit_button = driver_cc.find_element(
                                    By.XPATH,
                                    '//button[text()="送信"]'
                                )

                                submit_button.click()

                                ai_comment_flg = True
                                before_text = last_p_text

                        else:
                            print("最後の<div>内に<p>タグが見つかりませんでした。")

                    else:
                        print("message-content が見つかりませんでした。")

            driver_mi.switch_to.default_content()

            before_text = text
            start_flg = False

        else:
            print("該当するタグが見つかりませんでした。")

sys.exit()