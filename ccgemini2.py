import multiprocessing
import os
import random
import sys
import time
import traceback
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

CHECK_INTERVAL_SECONDS = 1
GEMINI_RETRY_COUNT = 3
GEMINI_RETRY_WAIT_SECONDS = 5
CCFOLIA_SEND_WAIT_SECONDS = 1
START_WAIT_SECONDS = 5


# =========================================================
# 実行フォルダ
# =========================================================

def get_app_directory() -> Path:
    """
    通常実行時:
        Pythonファイルが置かれているフォルダ

    PyInstaller実行時:
        CcGemini.exeが置かれているフォルダ

    設定ファイルは、必ずこのフォルダから読み込む。
    """
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent

    return Path(__file__).resolve().parent


APP_DIR = get_app_directory()
LOG_FILE = APP_DIR / "CcGemini_error.log"


def write_log(message: str) -> None:
    """
    コンソールとログファイルの両方へ出力する。
    """
    print(message)

    try:
        with LOG_FILE.open(
            "a",
            encoding="utf-8"
        ) as file:
            timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
            file.write(f"[{timestamp}] {message}\n")

    except Exception:
        pass


def config_path(filename: str) -> Path:
    """
    設定ファイルの絶対パスを取得する。
    """
    return APP_DIR / filename


# =========================================================
# 設定ファイル関連
# =========================================================

def read_text_file(
    filename: str,
    default: str = "",
    required: bool = False
) -> str:
    filepath = config_path(filename)

    if not filepath.exists():
        if required:
            raise FileNotFoundError(
                f"必要な設定ファイルが見つかりません。\n"
                f"ファイル名: {filename}\n"
                f"検索場所: {filepath}"
            )

        return default

    try:
        return filepath.read_text(
            encoding="utf-8-sig"
        ).strip()

    except UnicodeDecodeError:
        raise RuntimeError(
            f"{filename}を読み込めませんでした。\n"
            "文字コードをUTF-8にしてください。"
        )


def read_bool_file(
    filename: str,
    default: bool = False
) -> bool:
    value = read_text_file(
        filename,
        str(default)
    ).strip().lower()

    true_values = {
        "1",
        "true",
        "yes",
        "y",
        "on",
        "はい"
    }

    false_values = {
        "0",
        "false",
        "no",
        "n",
        "off",
        "いいえ"
    }

    if value in true_values:
        return True

    if value in false_values:
        return False

    write_log(
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
    value = read_text_file(
        filename,
        str(default)
    )

    try:
        number = int(value)

    except ValueError:
        write_log(
            f"{filename}の値が整数ではないため、"
            f"{default}を使用します。"
        )

        return default

    return max(
        minimum,
        min(maximum, number)
    )


# =========================================================
# Gemini API関連
# =========================================================

def get_gemini_api_key() -> str:
    """
    次の順序でAPIキーを取得する。

    1. 環境変数 GEMINI_API_KEY
    2. gemini_api_key.txt
    """
    api_key = os.environ.get(
        "GEMINI_API_KEY",
        ""
    ).strip()

    if api_key:
        return api_key

    api_key = read_text_file(
        "gemini_api_key.txt",
        ""
    )

    if not api_key:
        raise RuntimeError(
            "Gemini APIキーが設定されていません。\n\n"
            "CcGemini.exeと同じフォルダに"
            "gemini_api_key.txtを置き、"
            "APIキーを記入してください。"
        )

    return api_key


def create_gemini_chat():
    api_key = get_gemini_api_key()

    model_name = read_text_file(
        "gemini_model.txt",
        DEFAULT_MODEL
    )

    system_instruction = read_text_file(
        "system_prompt.txt",
        (
            "あなたはTRPGのキャラクターとして会話します。\n"
            "送られた発言に自然な日本語で返答してください。\n"
            "返答はココフォリアへ投稿されます。\n"
            "前置きや解説を付けず、"
            "キャラクターの発言だけを出力してください。\n"
            "返答は原則として短めにしてください。"
        )
    )

    write_log(
        f"使用するGeminiモデル: {model_name}"
    )

    client = genai.Client(
        api_key=api_key
    )

    chat = client.chats.create(
        model=model_name,
        config=types.GenerateContentConfig(
            system_instruction=system_instruction,
            temperature=1.0,
            max_output_tokens=500,
        ),
    )

    return client, chat


def send_to_gemini(
    chat,
    message: str
) -> str:
    for attempt in range(
        1,
        GEMINI_RETRY_COUNT + 1
    ):
        try:
            write_log(
                f"Geminiへ送信: {message}"
            )

            response = chat.send_message(
                message
            )

            if response is None:
                raise RuntimeError(
                    "Geminiから応答が返りませんでした。"
                )

            answer = getattr(
                response,
                "text",
                None
            )

            if not answer:
                raise RuntimeError(
                    "Geminiの返答が空でした。"
                )

            answer = answer.strip()

            write_log(
                f"Geminiの返答: {answer}"
            )

            return answer

        except Exception as error:
            write_log(
                f"Gemini APIエラー"
                f"（{attempt}/{GEMINI_RETRY_COUNT}）: "
                f"{error}"
            )

            if attempt < GEMINI_RETRY_COUNT:
                time.sleep(
                    GEMINI_RETRY_WAIT_SECONDS
                )

    return ""


# =========================================================
# ココフォリア関連
# =========================================================

def create_ccfolia_driver(
    ccfolia_url: str
):
    chrome_options = Options()

    chrome_options.add_argument(
        "--disable-notifications"
    )

    chrome_options.add_argument(
        "--disable-popup-blocking"
    )

    chrome_options.add_argument(
        "--disable-dev-shm-usage"
    )

    chrome_options.add_argument(
        "--no-first-run"
    )

    chrome_options.add_argument(
        "--no-default-browser-check"
    )

    driver = webdriver.Chrome(
        options=chrome_options
    )

    driver.set_window_size(
        1200,
        850
    )

    driver.set_window_position(
        0,
        0
    )

    driver.get(
        ccfolia_url
    )

    return driver


def close_initial_dialog(
    driver
) -> None:
    try:
        close_button = WebDriverWait(
            driver,
            5
        ).until(
            EC.element_to_be_clickable(
                (
                    By.XPATH,
                    '//button[normalize-space()="閉じる"]'
                )
            )
        )

        close_button.click()

        write_log(
            "「閉じる」ボタンをクリックしました。"
        )

    except Exception:
        write_log(
            "「閉じる」ボタンは見つかりませんでした。"
            "そのまま処理を続けます。"
        )


def get_latest_ccfolia_message(
    driver
) -> str:
    elements = driver.find_elements(
        By.CLASS_NAME,
        "MuiListItemText-secondary"
    )

    if not elements:
        return ""

    return elements[-1].text.strip()


def send_message_to_ccfolia(
    driver,
    message: str
) -> bool:
    try:
        textarea = WebDriverWait(
            driver,
            10
        ).until(
            EC.element_to_be_clickable(
                (
                    By.XPATH,
                    '//textarea[@placeholder="メッセージを入力"]'
                )
            )
        )

        textarea.click()

        # 古い入力内容が残っていた場合に消去
        textarea.send_keys(
            Keys.CONTROL,
            "a"
        )

        textarea.send_keys(
            Keys.BACKSPACE
        )

        textarea.send_keys(
            message
        )

        try:
            submit_button = WebDriverWait(
                driver,
                5
            ).until(
                EC.element_to_be_clickable(
                    (
                        By.XPATH,
                        '//button[normalize-space()="送信"]'
                    )
                )
            )

            submit_button.click()

        except Exception:
            textarea.send_keys(
                Keys.ENTER
            )

        write_log(
            f"ココフォリアへ送信: {message}"
        )

        time.sleep(
            CCFOLIA_SEND_WAIT_SECONDS
        )

        return True

    except Exception as error:
        write_log(
            f"ココフォリアへの送信に失敗しました: {error}"
        )

        return False


# =========================================================
# メッセージ処理
# =========================================================

def remove_control_words(
    text: str,
    character_response_word: str
) -> str:
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
            result = result.replace(
                word,
                ""
            )

    return result.strip()


def should_reply(
    original_text: str,
    comment_rate: int,
    character_response_word: str
) -> bool:
    random_number = random.randint(
        1,
        100
    )

    if (
        "強制応答" in original_text
        or "mustreply" in original_text
    ):
        random_number = 0

    elif (
        character_response_word
        and character_response_word in original_text
    ):
        random_number = 0

    elif (
        "応答なし" in original_text
        or "noreply" in original_text
    ):
        random_number = 101

    write_log(
        f"応答率: {comment_rate}%"
    )

    write_log(
        f"判定用乱数: {random_number}"
    )

    return random_number <= comment_rate


def format_gemini_answer(
    answer: str,
    original_text: str,
    default_kakko_flg: bool
) -> str:
    use_kakko = default_kakko_flg

    if (
        "カッコなし" in original_text
        or "カッコ無し" in original_text
    ):
        use_kakko = False

    answer = answer.strip()

    already_quoted = (
        answer.startswith("「")
        and answer.endswith("」")
    )

    if use_kakko and not already_quoted:
        answer = f"「{answer}」"

    add_text = read_text_file(
        "addtext.txt",
        ""
    )

    return answer + add_text


def is_blank_answer(
    answer: str
) -> bool:
    normalized = (
        answer
        .strip()
        .strip("「」")
        .strip()
    )

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
    write_log(
        "CcGeminiを起動します。"
    )

    write_log(
        f"実行フォルダ: {APP_DIR}"
    )

    ccfolia_url = read_text_file(
        "ccforia_url.txt",
        required=True
    )

    kakko_flg = read_bool_file(
        "kakko_flg.txt",
        default=False
    )

    character_name = read_text_file(
        "character_name.txt",
        ""
    )

    if character_name:
        character_response_word = (
            character_name + "応答"
        )
    else:
        character_response_word = ""

    gemini_client = None
    driver_cc = None

    try:
        gemini_client, gemini_chat = (
            create_gemini_chat()
        )

        driver_cc = create_ccfolia_driver(
            ccfolia_url
        )

        write_log(
            f"{START_WAIT_SECONDS}秒後に監視を開始します。"
        )

        time.sleep(
            START_WAIT_SECONDS
        )

        close_initial_dialog(
            driver_cc
        )

        write_log(
            "ココフォリアで送信キャラクターを"
            "設定してください。"
        )

        write_log(
            "Escキーを押すと終了します。"
        )

        before_text = ""
        start_flg = True

        while True:
            if keyboard.is_pressed("esc"):
                write_log(
                    "Escキーが押されました。"
                    "終了します。"
                )
                break

            try:
                latest_text = (
                    get_latest_ccfolia_message(
                        driver_cc
                    )
                )

                if not latest_text:
                    time.sleep(
                        CHECK_INTERVAL_SECONDS
                    )
                    continue

                if start_flg:
                    before_text = latest_text
                    start_flg = False

                    write_log(
                        "監視を開始しました。"
                        "既存の最新発言は無視します。"
                    )

                    time.sleep(
                        CHECK_INTERVAL_SECONDS
                    )
                    continue

                if latest_text == before_text:
                    time.sleep(
                        CHECK_INTERVAL_SECONDS
                    )
                    continue

                write_log(
                    f"新しい発言: {latest_text}"
                )

                # Gemini処理中の二重応答を防止
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
                    write_log(
                        "今回は応答しません。"
                    )

                    time.sleep(
                        CHECK_INTERVAL_SECONDS
                    )
                    continue

                prompt_text = remove_control_words(
                    latest_text,
                    character_response_word
                )

                if not prompt_text:
                    write_log(
                        "制御命令を取り除いた結果、"
                        "送信内容が空になりました。"
                    )

                    time.sleep(
                        CHECK_INTERVAL_SECONDS
                    )
                    continue

                gemini_answer = send_to_gemini(
                    gemini_chat,
                    prompt_text
                )

                if not gemini_answer:
                    write_log(
                        "Geminiから返答を取得できませんでした。"
                    )

                    time.sleep(
                        CHECK_INTERVAL_SECONDS
                    )
                    continue

                if is_blank_answer(
                    gemini_answer
                ):
                    write_log(
                        "回答なし指定のため投稿しません。"
                    )

                    time.sleep(
                        CHECK_INTERVAL_SECONDS
                    )
                    continue

                output_text = format_gemini_answer(
                    gemini_answer,
                    latest_text,
                    kakko_flg
                )

                send_message_to_ccfolia(
                    driver_cc,
                    output_text
                )

            except StaleElementReferenceException:
                write_log(
                    "画面が更新されたため、"
                    "次の監視で再取得します。"
                )

            except NoSuchElementException as error:
                write_log(
                    f"ココフォリアの要素が"
                    f"見つかりません: {error}"
                )

            except WebDriverException as error:
                write_log(
                    f"Chrome操作エラー: {error}"
                )

            except Exception as error:
                write_log(
                    f"監視処理エラー: {error}"
                )

                write_log(
                    traceback.format_exc()
                )

            time.sleep(
                CHECK_INTERVAL_SECONDS
            )

    except KeyboardInterrupt:
        write_log(
            "キーボード操作により終了します。"
        )

    except Exception as error:
        write_log(
            f"起動エラー: {error}"
        )

        write_log(
            traceback.format_exc()
        )

        # exeをダブルクリックした場合でも
        # エラーを確認できるようにする
        try:
            input(
                "\nエラーが発生しました。"
                "Enterキーを押すと終了します。"
            )
        except Exception:
            time.sleep(10)

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

        write_log(
            "CcGeminiを終了しました。"
        )


if __name__ == "__main__":
    # PyInstallerによるWindows実行ファイル化に必要
    multiprocessing.freeze_support()

    main()