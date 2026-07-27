import os
import sys
import time
import random
import traceback

import keyboard

from selenium.webdriver.chrome.webdriver import WebDriver as ChromeWebDriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    NoSuchElementException,
    NoSuchFrameException,
    StaleElementReferenceException,
    TimeoutException,
    WebDriverException,
)


# =========================================================
# 基本設定
# =========================================================

START_COUNT = 5
LOOP_INTERVAL = 1
MIIBO_RESPONSE_WAIT = 10

driver_mi = None
driver_cc = None


# =========================================================
# パス関連
# =========================================================

def get_app_dir():
    """
    通常実行時はPythonファイルのフォルダ、
    PyInstaller実行時はEXEのフォルダを返します。
    """
    if getattr(sys, "frozen", False):
        return os.path.dirname(os.path.abspath(sys.executable))

    return os.path.dirname(os.path.abspath(__file__))


APP_DIR = get_app_dir()


def app_path(filename):
    """
    EXEまたはPythonファイルと同じフォルダ内の
    ファイルパスを返します。
    """
    return os.path.join(APP_DIR, filename)


def check_file_exists(filename):
    return os.path.isfile(app_path(filename))


def read_text_file(filename, default="", required=True):
    filepath = app_path(filename)

    if not os.path.isfile(filepath):
        if required:
            raise FileNotFoundError(
                "設定ファイルが見つかりません。\n"
                f"ファイル名: {filename}\n"
                f"検索場所: {filepath}"
            )

        return default

    with open(filepath, "r", encoding="utf-8") as file:
        return file.read().strip()


def read_bool_file(filename, default=False):
    """
    distutils.util.strtoboolを使用せずに、
    文字列をTrueまたはFalseへ変換します。
    """
    value = read_text_file(
        filename,
        default=str(default),
        required=False
    ).strip().lower()

    true_values = {
        "1",
        "true",
        "yes",
        "y",
        "on",
        "はい",
        "有効",
        "あり",
    }

    false_values = {
        "0",
        "false",
        "no",
        "n",
        "off",
        "いいえ",
        "無効",
        "なし",
    }

    if value in true_values:
        return True

    if value in false_values:
        return False

    print(
        f"警告: {filename}の値「{value}」を判定できません。"
        f"既定値の{default}を使用します。"
    )

    return default


def read_int_file(filename, default=0, minimum=None, maximum=None):
    text = read_text_file(
        filename,
        default=str(default),
        required=False
    )

    try:
        value = int(text)

    except ValueError:
        print(
            f"警告: {filename}の内容が整数ではありません。"
            f"既定値の{default}を使用します。"
        )
        value = default

    if minimum is not None:
        value = max(minimum, value)

    if maximum is not None:
        value = min(maximum, value)

    return value


# =========================================================
# Chrome起動処理
# =========================================================

def create_chrome_options():
    chrome_options = Options()

    chrome_options.add_argument("--disable-notifications")
    chrome_options.add_argument("--disable-popup-blocking")
    chrome_options.add_argument("--disable-background-networking")
    chrome_options.add_argument("--disable-features=Translate")
    chrome_options.add_argument("--no-first-run")
    chrome_options.add_argument("--no-default-browser-check")

    chrome_options.add_experimental_option(
        "excludeSwitches",
        [
            "enable-automation",
            "enable-logging",
        ]
    )

    chrome_options.add_experimental_option(
        "useAutomationExtension",
        False
    )

    return chrome_options


def create_chrome_driver(width, height, x, y):
    """
    Chrome用WebDriverを直接生成します。

    ChromeDriverのパスは指定せず、
    Selenium Managerに自動管理させます。
    """
    chrome_options = create_chrome_options()

    try:
        service = Service()

        driver = ChromeWebDriver(
            options=chrome_options,
            service=service
        )

        driver.set_window_size(width, height)
        driver.set_window_position(x, y)
        driver.set_page_load_timeout(60)

        return driver

    except WebDriverException as error:
        raise RuntimeError(
            "\nChromeの起動に失敗しました。\n\n"
            "考えられる原因:\n"
            "・Seleniumが正常にインストールされていない\n"
            "・ChromeまたはChrome for Testingがない\n"
            "・Selenium Managerの通信が遮断されている\n"
            "・セキュリティソフトに遮断されている\n"
            "・PyInstallerがSeleniumを収集できていない\n\n"
            f"詳細:\n{error}"
        ) from error


# =========================================================
# miibo操作
# =========================================================

def switch_to_miibo_frame(driver):
    """
    miiboのiframeへ切り替えます。
    """
    try:
        driver.switch_to.default_content()

        iframe = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located(
                (By.TAG_NAME, "iframe")
            )
        )

        driver.switch_to.frame(iframe)

        return True

    except (
        TimeoutException,
        NoSuchFrameException,
        StaleElementReferenceException,
    ):
        try:
            driver.switch_to.default_content()
        except Exception:
            pass

        return False


def get_character_name(driver):
    """
    miibo画面からキャラクター名を取得します。
    """
    if not switch_to_miibo_frame(driver):
        return ""

    try:
        card_body = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located(
                (By.CLASS_NAME, "card-body")
            )
        )

        h5_element = card_body.find_element(
            By.TAG_NAME,
            "h5"
        )

        return h5_element.text.strip()

    except (
        TimeoutException,
        NoSuchElementException,
        StaleElementReferenceException,
    ):
        return ""

    finally:
        try:
            driver.switch_to.default_content()
        except Exception:
            pass


def send_to_miibo(driver, text):
    """
    miiboの入力欄へ文章を送信します。
    """
    if not switch_to_miibo_frame(driver):
        print("miiboのiframeが見つかりませんでした。")
        return False

    try:
        textarea = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable(
                (By.ID, "chat-id-2-input")
            )
        )

        textarea.click()
        textarea.send_keys(text)
        textarea.send_keys(Keys.ENTER)

        return True

    except (
        TimeoutException,
        NoSuchElementException,
        StaleElementReferenceException,
    ) as error:
        print(f"miiboへの送信に失敗しました: {error}")
        return False

    finally:
        try:
            driver.switch_to.default_content()
        except Exception:
            pass


def get_miibo_message_count(driver):
    """
    miiboの回答メッセージ数を取得します。
    """
    if not switch_to_miibo_frame(driver):
        return 0

    try:
        elements = driver.find_elements(
            By.CLASS_NAME,
            "message-content"
        )

        return len(elements)

    except Exception:
        return 0

    finally:
        try:
            driver.switch_to.default_content()
        except Exception:
            pass


def wait_for_miibo_response(driver, previous_count, timeout=30):
    """
    miiboに新しい回答が表示されるまで待ち、
    最後の回答を取得します。
    """
    end_time = time.time() + timeout

    while time.time() < end_time:
        if keyboard.is_pressed("esc"):
            return ""

        if not switch_to_miibo_frame(driver):
            time.sleep(1)
            continue

        try:
            div_elements = driver.find_elements(
                By.CLASS_NAME,
                "message-content"
            )

            if len(div_elements) > previous_count:
                last_div = div_elements[-1]

                p_elements = last_div.find_elements(
                    By.TAG_NAME,
                    "p"
                )

                if p_elements:
                    response_text = p_elements[-1].text.strip()

                    if response_text:
                        return response_text

        except (
            NoSuchElementException,
            StaleElementReferenceException,
        ):
            pass

        finally:
            try:
                driver.switch_to.default_content()
            except Exception:
                pass

        time.sleep(1)

    return ""


# =========================================================
# ココフォリア操作
# =========================================================

def get_ccforia_last_message(driver):
    """
    ココフォリアの最新メッセージを取得します。
    """
    try:
        elements = driver.find_elements(
            By.CLASS_NAME,
            "MuiListItemText-secondary"
        )

        if not elements:
            return ""

        return elements[-1].text.strip()

    except StaleElementReferenceException:
        return ""


def click_ccforia_close_button(driver):
    """
    ココフォリアの「閉じる」ボタンを押します。
    """
    try:
        close_button = WebDriverWait(driver, 5).until(
            EC.element_to_be_clickable(
                (
                    By.XPATH,
                    '//button[normalize-space(text())="閉じる"]'
                )
            )
        )

        close_button.click()

        return True

    except TimeoutException:
        return False


def send_to_ccforia(driver, text):
    """
    ココフォリアへ文章を送信します。
    """
    try:
        textarea = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable(
                (
                    By.XPATH,
                    '//textarea[@placeholder="メッセージを入力"]'
                )
            )
        )

        textarea.click()
        textarea.send_keys(text)

        submit_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable(
                (
                    By.XPATH,
                    '//button[normalize-space(text())="送信"]'
                )
            )
        )

        submit_button.click()

        return True

    except (
        TimeoutException,
        NoSuchElementException,
        StaleElementReferenceException,
    ) as error:
        print(f"ココフォリアへの送信に失敗しました: {error}")
        return False


# =========================================================
# 文字列処理
# =========================================================

def remove_control_words(text, character_name):
    """
    発言から制御用の文字列を削除します。
    """
    control_words = [
        "強制応答",
        "応答なし",
        "mustreply",
        "noreply",
        character_name + "応答",
        "@" + character_name,
        "カッコなし",
        "カッコ無し",
    ]

    new_text = text

    for word in control_words:
        if word:
            new_text = new_text.replace(word, "")

    return new_text.strip()


def determine_random_number(original_text, character_name):
    """
    応答するかどうかを決める乱数を返します。
    """
    random_number = random.randint(1, 100)

    force_reply_words = [
        "強制応答",
        "mustreply",
        character_name + "応答",
        "@" + character_name,
    ]

    no_reply_words = [
        "応答なし",
        "noreply",
    ]

    if any(
        word and word in original_text
        for word in force_reply_words
    ):
        return 0

    if any(
        word in original_text
        for word in no_reply_words
    ):
        return 101

    # 他キャラクター宛ての@指定がある場合
    if (
        "@" in original_text
        and ("@" + character_name) not in original_text
    ):
        return 101

    return random_number


def should_use_brackets(original_text, default_kakko_flg):
    """
    回答を「」で囲むか判定します。
    """
    if not default_kakko_flg:
        return False

    if "カッコなし" in original_text:
        return False

    if "カッコ無し" in original_text:
        return False

    return True


# =========================================================
# 終了処理
# =========================================================

def close_driver(driver):
    if driver is None:
        return

    try:
        driver.quit()
    except Exception:
        pass


def save_error_log():
    error_log_path = app_path("error_log.txt")

    with open(
        error_log_path,
        "w",
        encoding="utf-8"
    ) as log_file:
        traceback.print_exc(file=log_file)

    return error_log_path


def wait_before_exit():
    try:
        input("\nEnterキーを押すと終了します。")
    except EOFError:
        pass


# =========================================================
# メイン処理
# =========================================================

def main():
    global driver_mi
    global driver_cc

    print("=" * 60)
    print("CcMiiboを起動します。")
    print(f"実行フォルダ: {APP_DIR}")
    print("=" * 60)

    # 設定ファイル読み込み
    ccforia_url = read_text_file(
        "ccforia_url.txt"
    )

    miibo_url = read_text_file(
        "miibo_url.txt"
    )

    kakko_flg = read_bool_file(
        "kakko_flg.txt",
        default=False
    )

    if not ccforia_url.startswith(
        ("http://", "https://")
    ):
        raise ValueError(
            "ccforia_url.txtに正しいURLを入力してください。"
        )

    if not miibo_url.startswith(
        ("http://", "https://")
    ):
        raise ValueError(
            "miibo_url.txtに正しいURLを入力してください。"
        )

    print(f"ココフォリアURL: {ccforia_url}")
    print(f"miibo URL: {miibo_url}")
    print(f"カッコ設定: {kakko_flg}")

    # miiboブラウザ起動
    print("\nmiibo用ブラウザを起動しています。")

    driver_mi = create_chrome_driver(
        width=600,
        height=800,
        x=0,
        y=0
    )

    driver_mi.get(miibo_url)

    # ココフォリアブラウザ起動
    print("ココフォリア用ブラウザを起動しています。")

    driver_cc = create_chrome_driver(
        width=1000,
        height=800,
        x=600,
        y=0
    )

    driver_cc.get(ccforia_url)

    print("\nEscキーを長押しすると終了します。")

    time_count = 0
    before_text = ""
    start_flg = True
    ai_comment_flg = False

    while True:
        if keyboard.is_pressed("esc"):
            print("\nEscキーが押されました。終了します。")
            break

        time.sleep(LOOP_INTERVAL)

        if time_count < START_COUNT:
            time_count += 1
            print(time_count)

        if time_count == START_COUNT:
            character_name = get_character_name(
                driver_mi
            )

            if character_name:
                print(
                    f"キャラクター名: {character_name}"
                )
            else:
                print(
                    "miiboからキャラクター名を"
                    "取得できませんでした。"
                )

            if click_ccforia_close_button(driver_cc):
                print(
                    "ココフォリアの「閉じる」ボタンを"
                    "クリックしました。"
                )
            else:
                print(
                    "ココフォリアの「閉じる」ボタンは"
                    "見つかりませんでした。"
                )

            print(
                "ココフォリアウィンドウで"
                "キャラクターを設定してください。"
            )

            time_count += 1
            continue

        if time_count <= START_COUNT:
            continue

        text = get_ccforia_last_message(
            driver_cc
        )

        if not text:
            print(
                "ココフォリアの発言が"
                "見つかりませんでした。"
            )
            continue

        if text != before_text:
            print(
                f"\nココフォリア最新発言: {text}"
            )

        else:
            ai_comment_flg = False

        character_name = get_character_name(
            driver_mi
        )

        if not character_name:
            print(
                "miiboのキャラクター名を"
                "取得できませんでした。"
            )

            before_text = text
            start_flg = False
            continue

        is_new_message = text != before_text

        if (
            is_new_message
            and not start_flg
            and not ai_comment_flg
        ):
            new_text = remove_control_words(
                text,
                character_name
            )

            if not new_text:
                print(
                    "制御用文字列を削除すると空になるため、"
                    "miiboへ送信しません。"
                )

                before_text = text
                continue

            use_brackets = should_use_brackets(
                text,
                kakko_flg
            )

            # miibo送信前のメッセージ数を記録
            previous_message_count = (
                get_miibo_message_count(driver_mi)
            )

            print(
                f"miiboへ送信: {new_text}"
            )

            if not send_to_miibo(
                driver_mi,
                new_text
            ):
                before_text = text
                continue

            comment_rate = read_int_file(
                "comment_rate.txt",
                default=0,
                minimum=0,
                maximum=100
            )

            print(
                f"現在の応答率: {comment_rate}%"
            )

            random_number = determine_random_number(
                text,
                character_name
            )

            print(
                f"randomNum = {random_number}"
            )

            if random_number <= comment_rate:
                print(
                    "miiboの回答を待っています。"
                )

                # 固定10秒待機
                time.sleep(MIIBO_RESPONSE_WAIT)

                # さらに新規回答が出るまで最大30秒確認
                response_text = wait_for_miibo_response(
                    driver_mi,
                    previous_message_count,
                    timeout=30
                )

                if not response_text:
                    print(
                        "miiboの回答を"
                        "取得できませんでした。"
                    )

                elif response_text in {
                    "回答なし",
                    "回答無し",
                    "…",
                }:
                    print(
                        "回答なし指定のため、"
                        "ココフォリアへ送信しません。"
                    )

                else:
                    add_text = read_text_file(
                        "addtext.txt",
                        default="",
                        required=False
                    )

                    if use_brackets:
                        output_text = (
                            "「"
                            + response_text
                            + "」"
                            + add_text
                        )

                    else:
                        output_text = (
                            response_text
                            + add_text
                        )

                    print(
                        f"ココフォリアへ送信: {output_text}"
                    )

                    if send_to_ccforia(
                        driver_cc,
                        output_text
                    ):
                        ai_comment_flg = True

            else:
                print(
                    "応答率の判定により、"
                    "今回は回答しません。"
                )

        before_text = text
        start_flg = False


# =========================================================
# 実行
# =========================================================

if __name__ == "__main__":
    try:
        main()

    except KeyboardInterrupt:
        print("\n手動で終了されました。")

    except Exception as error:
        print("\n予期しないエラーが発生しました。")
        print("=" * 60)
        print(str(error))
        print("=" * 60)

        traceback.print_exc()

        try:
            error_log_path = save_error_log()

            print(
                "\nエラーログを保存しました。"
            )
            print(error_log_path)

        except Exception as log_error:
            print(
                "エラーログの保存にも失敗しました。"
            )
            print(log_error)

        wait_before_exit()

    finally:
        close_driver(driver_mi)
        close_driver(driver_cc)

    sys.exit(0)