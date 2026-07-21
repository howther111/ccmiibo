import os
import random
import sys
import time
from pathlib import Path

import keyboard
from google import genai
from google.genai import types
from selenium import webdriver
from selenium.common.exceptions import (
    NoSuchElementException,
    StaleElementReferenceException,
    WebDriverException,
)

from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


# =========================================================
# 基本設定
# =========================================================

DEFAULT_MODEL = "gemini-3.5-flash"

# ココフォリアの画面を確認する間隔
CHECK_INTERVAL_SECONDS = 1

# Gemini APIの再試行回数
GEMINI_RETRY_COUNT = 3

# APIエラー時の再試行間隔
GEMINI_RETRY_WAIT_SECONDS = 5

# ココフォリア送信後の待機時間
CCFOLIA_SEND_WAIT_SECONDS = 1

# ココフォリア起動後、監視を始めるまでの秒数
START_WAIT_SECONDS = 5


# =========================================================
# ファイル関連
# =========================================================

def resource_path(relative_path: str) -> str:
    """
    PyInstallerで実行ファイル化した場合と、
    Pythonスクリプトとして実行した場合の両方に対応する。
    """
    if getattr(sys, "frozen", False):
        base_path = Path(sys.executable).parent
    else:
        base_path = Path(__file__).resolve().parent

    return str(base_path / relative_path)


def check_file_exists(filepath: str) -> bool:
    return Path(resource_path(filepath)).exists()


def read_text_file(
    filename: str,
    default: str = "",
    required: bool = False
) -> str:
    """
    UTF-8のテキストファイルを読み込む。
    """
    filepath = Path(resource_path(filename))

    if not filepath.exists():
        if required:
            raise FileNotFoundError(
                f"必要な設定ファイルが見つかりません。\n"
                f"ファイル名: {filename}\n"
                f"場所: {filepath}"
            )

        return default

    return filepath.read_text(encoding="utf-8").strip()


def read_bool_file(filename: str, default: bool = False) -> bool:
    """
    true、false、1、0、yes、noなどを真偽値として読み込む。
    distutilsは廃止方向のため使用しない。
    """
    value = read_text_file(filename, str(default)).strip().lower()

    true_values = {"1", "true", "yes", "y", "on", "はい"}
    false_values = {"0", "false", "no", "n", "off", "いいえ"}

    if value in true_values:
        return True

    if value in false_values:
        return False

    print(
        f"{filename}の値「{value}」を判定できないため、"
        f"初期値の{default}を使用します。"
    )
    return default


def read_int_file(
    filename: str,
    default: int,
    minimum: int = 0,
    maximum: int = 100
) -> int:
    """
    整数設定を読み込む。
    """
    value = read_text_file(filename, str(default))

    try:
        number = int(value)
    except ValueError:
        print(
            f"{filename}の値が整数ではないため、"
            f"初期値の{default}を使用します。"
        )
        return default

    return max(minimum, min(maximum, number))


# =========================================================
# Gemini関連
# =========================================================

def get_gemini_api_key() -> str:
    """
    次の順番でGemini APIキーを取得する。

    1. 環境変数 GEMINI_API_KEY
    2. gemini_api_key.txt
    """
    api_key = os.environ.get("GEMINI_API_KEY", "").strip()

    if api_key:
        return api_key

    api_key = read_text_file("gemini_api_key.txt", "")

    if not api_key:
        raise RuntimeError(
            "Gemini APIキーが設定されていません。\n\n"
            "次のどちらかの方法で設定してください。\n"
            "・環境変数 GEMINI_API_KEY に設定する\n"
            "・gemini_api_key.txt にAPIキーだけを記入する"
        )

    return api_key


def create_gemini_chat():
    """
    Geminiクライアントと会話セッションを作成する。
    """
    api_key = get_gemini_api_key()

    model_name = read_text_file(
        "gemini_model.txt",
        DEFAULT_MODEL
    )

    system_instruction = read_text_file(
        "system_prompt.txt",
        (
            "あなたはTRPGのキャラクターとして会話します。"
            "ユーザーから送られた発言に対して、自然な日本語で返答してください。"
            "返答はココフォリアのチャット欄に投稿されるため、"
            "前置きや解説を付けず、キャラクターの発言だけを出力してください。"
            "返答は原則として短めにしてください。"
        )
    )

    client = genai.Client(api_key=api_key)

    chat = client.chats.create(
        model=model_name,
        config=types.GenerateContentConfig(
            system_instruction=system_instruction,
            temperature=1.0,
            max_output_tokens=500,
        ),
    )

    print(f"Geminiモデル: {model_name}")

    return client, chat


def send_to_gemini(chat, message: str) -> str:
    """
    Geminiへ発言を送信し、返答テキストを取得する。
    """
    for attempt in range(1, GEMINI_RETRY_COUNT + 1):
        try:
            print("Geminiへ送信:", message)

            response = chat.send_message(message)

            if not response:
                raise RuntimeError("Geminiから応答オブジェクトが返りませんでした。")

            answer = response.text

            if not answer:
                raise RuntimeError("Geminiの返答が空でした。")

            answer = answer.strip()

            print("Geminiの返答:", answer)

            return answer

        except Exception as error:
            print(
                f"Gemini APIエラー "
                f"({attempt}/{GEMINI_RETRY_COUNT}): {error}"
            )

            if attempt < GEMINI_RETRY_COUNT:
                time.sleep(GEMINI_RETRY_WAIT_SECONDS)

    return ""


# =========================================================
# ココフォリア関連
# =========================================================

def create_ccfolia_driver(ccfolia_url: str):
    """
    ココフォリア用Chromeを起動する。
    """
    chrome_options = Options()
    chrome_options.add_argument("--start-maximized")

    # 通知を抑止
    chrome_options.add_argument("--disable-notifications")

    driver = webdriver.Chrome(options=chrome_options)

    driver.set_window_size(1200, 850)
    driver.set_window_position(0, 0)

    driver.get(ccfolia_url)

    return driver


def close_initial_dialog(driver) -> None:
    """
    ココフォリア起動時に「閉じる」ボタンがあれば押す。
    """
    try:
        close_button = WebDriverWait(driver, 5).until(
            EC.element_to_be_clickable(
                (By.XPATH, '//button[normalize-space()="閉じる"]')
            )
        )

        close_button.click()
        print("「閉じる」ボタンをクリックしました。")

    except Exception:
        print(
            "「閉じる」ボタンは見つかりませんでした。"
            "そのまま処理を続けます。"
        )


def get_latest_ccfolia_message(driver) -> str:
    """
    ココフォリアの最新メッセージを取得する。
    """
    elements = driver.find_elements(
        By.CLASS_NAME,
        "MuiListItemText-secondary"
    )

    if not elements:
        return ""

    latest_element = elements[-1]

    return latest_element.text.strip()


def send_message_to_ccfolia(driver, message: str) -> bool:
    """
    ココフォリアへメッセージを投稿する。
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
        textarea.send_keys(message)

        try:
            submit_button = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable(
                    (
                        By.XPATH,
                        '//button[normalize-space()="送信"]'
                    )
                )
            )

            submit_button.click()

        except Exception:
            # 送信ボタンが取得できない場合はEnterで送信
            textarea.send_keys(Keys.ENTER)

        print("ココフォリアへ送信:", message)

        time.sleep(CCFOLIA_SEND_WAIT_SECONDS)

        return True

    except Exception as error:
        print("ココフォリアへの送信に失敗しました:", error)
        return False


# =========================================================
# 発言処理
# =========================================================

def remove_control_words(text: str, character_response_word: str) -> str:
    """
    ココフォリア発言から制御用文字列を除去する。
    """
    control_words = [
        "強制応答",
        "応答なし",
        "mustreply",
        "noreply",
        character_response_word,
        "カッコなし",
        "カッコ無し",
    ]

    result = text

    for word in control_words:
        if word:
            result = result.replace(word, "")

    return result.strip()


def should_reply(
    original_text: str,
    comment_rate: int,
    character_response_word: str
) -> bool:
    """
    発言へ応答するか判定する。
    """
    random_number = random.randint(1, 100)

    if "強制応答" in original_text:
        random_number = 0

    elif "mustreply" in original_text:
        random_number = 0

    elif character_response_word and character_response_word in original_text:
        random_number = 0

    elif "応答なし" in original_text:
        random_number = 101

    elif "noreply" in original_text:
        random_number = 101

    print(f"応答率: {comment_rate}%")
    print(f"乱数: {random_number}")

    return random_number <= comment_rate


def format_gemini_answer(
    answer: str,
    original_text: str,
    default_kakko_flg: bool
) -> str:
    """
    Geminiの返答をココフォリア投稿用に整形する。
    """
    use_kakko = default_kakko_flg

    if "カッコなし" in original_text:
        use_kakko = False

    if "カッコ無し" in original_text:
        use_kakko = False

    # Geminiが既にカギ括弧を付けている場合は二重にしない
    already_quoted = (
        answer.startswith("「") and answer.endswith("」")
    )

    if use_kakko and not already_quoted:
        answer = f"「{answer}」"

    add_text = read_text_file("addtext.txt", "")

    return answer + add_text


def is_blank_answer(answer: str) -> bool:
    """
    投稿しない応答を判定する。
    """
    normalized = answer.strip().strip("「」").strip()

    blank_answers = {
        "",
        "回答なし",
        "回答無し",
        "返答なし",
        "返答無し",
        "応答なし",
        "応答無し",
        "…",
        "...",
    }

    return normalized in blank_answers


# =========================================================
# メイン処理
# =========================================================

def main():
    ccfolia_url = read_text_file(
        "ccforia_url.txt",
        required=True
    )

    kakko_flg = read_bool_file(
        "kakko_flg.txt",
        default=False
    )

    # キャラクター名
    character_name = read_text_file(
        "character_name.txt",
        ""
    )

    if character_name:
        character_response_word = character_name + "応答"
    else:
        character_response_word = ""

    print("ココフォリアURL:", ccfolia_url)
    print("カッコ設定:", kakko_flg)
    print("キャラクター名:", character_name or "未設定")

    gemini_client = None
    driver_cc = None

    try:
        gemini_client, gemini_chat = create_gemini_chat()

        driver_cc = create_ccfolia_driver(ccfolia_url)

        print(
            f"{START_WAIT_SECONDS}秒後に監視を開始します。"
        )

        time.sleep(START_WAIT_SECONDS)

        close_initial_dialog(driver_cc)

        print(
            "ココフォリアで送信キャラクターを設定してください。"
        )
        print("Escキーを長押しすると終了します。")

        before_text = ""
        start_flg = True

        while True:
            if keyboard.is_pressed("esc"):
                print("Escキーが押されました。終了します。")
                break

            try:
                latest_text = get_latest_ccfolia_message(driver_cc)

                if not latest_text:
                    time.sleep(CHECK_INTERVAL_SECONDS)
                    continue

                # 起動直後に既存メッセージへ反応しないようにする
                if start_flg:
                    before_text = latest_text
                    start_flg = False

                    print(
                        "監視を開始しました。最新の既存発言は無視します。"
                    )

                    time.sleep(CHECK_INTERVAL_SECONDS)
                    continue

                # 新しい発言がない
                if latest_text == before_text:
                    time.sleep(CHECK_INTERVAL_SECONDS)
                    continue

                print("新しい発言:", latest_text)

                # 先に記録し、同じ発言への二重応答を防止
                before_text = latest_text

                comment_rate = read_int_file(
                    "comment_rate.txt",
                    default=100,
                    minimum=0,
                    maximum=100
                )

                if not should_reply(
                    latest_text,
                    comment_rate,
                    character_response_word
                ):
                    print("今回は応答しません。")
                    time.sleep(CHECK_INTERVAL_SECONDS)
                    continue

                prompt_text = remove_control_words(
                    latest_text,
                    character_response_word
                )

                if not prompt_text:
                    print(
                        "制御文字列を取り除いた結果、"
                        "送信内容が空になりました。"
                    )
                    time.sleep(CHECK_INTERVAL_SECONDS)
                    continue

                gemini_answer = send_to_gemini(
                    gemini_chat,
                    prompt_text
                )

                if is_blank_answer(gemini_answer):
                    print("Geminiが回答なしを返したため投稿しません。")
                    time.sleep(CHECK_INTERVAL_SECONDS)
                    continue

                output_text = format_gemini_answer(
                    gemini_answer,
                    latest_text,
                    kakko_flg
                )

                if send_message_to_ccfolia(
                    driver_cc,
                    output_text
                ):
                    # 自分が投稿した文を次回の監視対象から除外する
                    before_text = output_text

            except StaleElementReferenceException:
                print(
                    "ココフォリアの画面が更新されました。"
                    "次の監視で再取得します。"
                )

            except NoSuchElementException as error:
                print("ココフォリアの要素が見つかりません:", error)

            except WebDriverException as error:
                print("Chrome操作中にエラーが発生しました:", error)

            except Exception as error:
                print("処理中にエラーが発生しました:", error)

            time.sleep(CHECK_INTERVAL_SECONDS)

    except KeyboardInterrupt:
        print("キーボード操作により終了します。")

    except Exception as error:
        print("起動エラー:", error)

    finally:
        if driver_cc is not None:
            try:
                driver_cc.quit()
            except Exception:
                pass

        if gemini_client is not None:
            try:
                gemini_client.close()
            except Exception:
                pass

        print("プログラムを終了しました。")


if __name__ == "__main__":
    main()