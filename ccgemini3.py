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
from selenium.common.exceptions import (
    NoSuchElementException,
    StaleElementReferenceException,
    WebDriverException,
)
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.webdriver import WebDriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


# =========================================================
# 基本設定
# =========================================================

DEFAULT_MODEL = "gemini-3.5-flash"

# ココフォリアを確認する間隔
CHECK_INTERVAL_SECONDS = 1

# Gemini APIの再試行回数
GEMINI_RETRY_COUNT = 3

# Gemini APIエラー時の再試行間隔
GEMINI_RETRY_WAIT_SECONDS = 5

# ココフォリアへ投稿した後の待機時間
CCFOLIA_SEND_WAIT_SECONDS = 1

# Chrome起動後、監視を開始するまでの秒数
START_WAIT_SECONDS = 5


# =========================================================
# アプリケーションフォルダ
# =========================================================

def get_app_directory() -> Path:
    """
    通常のPython実行時:
        Pythonファイルが置かれているフォルダ

    PyInstaller実行時:
        CcGemini.exeが置かれているフォルダ
    """
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent

    return Path(__file__).resolve().parent


APP_DIR = get_app_directory()
LOG_FILE = APP_DIR / "CcGemini_error.log"


# =========================================================
# ログ出力
# =========================================================

def write_log(message: str) -> None:
    """
    コンソールとログファイルへ同じ内容を出力する。
    """
    print(message)

    try:
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")

        with LOG_FILE.open(
            "a",
            encoding="utf-8"
        ) as file:
            file.write(
                f"[{timestamp}] {message}\n"
            )

    except Exception:
        # ログファイルへ書き込めなくても
        # プログラム自体は継続する
        pass


def write_exception_log(
    title: str,
    error: Exception
) -> None:
    """
    例外情報とトレースバックをログへ出力する。
    """
    write_log(
        f"{title}: {error}"
    )

    write_log(
        traceback.format_exc()
    )


# =========================================================
# 設定ファイル
# =========================================================

def config_path(filename: str) -> Path:
    """
    設定ファイルの絶対パスを返す。
    """
    return APP_DIR / filename


def read_text_file(
    filename: str,
    default: str = "",
    required: bool = False
) -> str:
    """
    UTF-8またはUTF-8 BOM付きのテキストファイルを読み込む。
    """
    filepath = config_path(filename)

    if not filepath.exists():
        if required:
            raise FileNotFoundError(
                "必要な設定ファイルが見つかりません。\n"
                f"ファイル名: {filename}\n"
                f"検索場所: {filepath}"
            )

        return default

    try:
        return filepath.read_text(
            encoding="utf-8-sig"
        ).strip()

    except UnicodeDecodeError as error:
        raise RuntimeError(
            f"{filename}を読み込めませんでした。\n"
            "ファイルの文字コードをUTF-8にしてください。"
        ) from error


def read_bool_file(
    filename: str,
    default: bool = False
) -> bool:
    """
    テキストファイルの内容を真偽値として読み込む。
    """
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
        "はい",
    }

    false_values = {
        "0",
        "false",
        "no",
        "n",
        "off",
        "いいえ",
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
    """
    テキストファイルの内容を整数として読み込む。
    """
    value = read_text_file(
        filename,
        str(default)
    )

    try:
        number = int(value)

    except ValueError:
        write_log(
            f"{filename}の値「{value}」が整数ではないため、"
            f"{default}を使用します。"
        )

        return default

    return max(
        minimum,
        min(maximum, number)
    )


# =========================================================
# Gemini API
# =========================================================

def get_gemini_api_key() -> str:
    """
    次の優先順位でGemini APIキーを取得する。

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
    """
    Geminiクライアントとチャットセッションを作成する。
    """
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
    """
    Geminiへメッセージを送り、返答を取得する。
    """
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
                "Gemini APIエラー"
                f"（{attempt}/{GEMINI_RETRY_COUNT}）: "
                f"{error}"
            )

            if attempt < GEMINI_RETRY_COUNT:
                time.sleep(
                    GEMINI_RETRY_WAIT_SECONDS
                )

    return ""


# =========================================================
# Chrome・ココフォリア
# =========================================================

def create_chrome_options() -> Options:
    """
    Chrome起動用のオプションを作成する。
    """
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

    chrome_options.add_argument(
        "--start-maximized"
    )

    return chrome_options


def create_ccfolia_driver(
    ccfolia_url: str
) -> WebDriver:
    """
    Chrome用ServiceとWebDriverを直接作成する。

    Service()へ実行ファイルの場所を指定しない場合、
    Selenium Managerによって適切なChromeDriverが
    自動的に用意される。
    """
    chrome_options = create_chrome_options()

    # ChromeDriverの起動・停止を管理するService
    chrome_service = Service()

    # webdriver.Chrome()を使用せず、
    # Chrome用WebDriverを直接作成する
    driver = WebDriver(
        service=chrome_service,
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
    driver: WebDriver
) -> None:
    """
    ココフォリア起動時に「閉じる」ボタンがあれば押す。
    """
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
    driver: WebDriver
) -> str:
    """
    ココフォリアに表示されている
    最新のメッセージを取得する。
    """
    elements = driver.find_elements(
        By.CLASS_NAME,
        "MuiListItemText-secondary"
    )

    if not elements:
        return ""

    latest_element = elements[-1]

    return latest_element.text.strip()


def get_message_textarea(
    driver: WebDriver
):
    """
    ココフォリアのメッセージ入力欄を取得する。
    """
    return WebDriverWait(
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


def clear_textarea(
    textarea
) -> None:
    """
    入力欄に文字が残っている場合に消去する。
    """
    textarea.click()

    textarea.send_keys(
        Keys.CONTROL,
        "a"
    )

    textarea.send_keys(
        Keys.BACKSPACE
    )


def send_message_to_ccfolia(
    driver: WebDriver,
    message: str
) -> bool:
    """
    ココフォリアへメッセージを投稿する。
    """
    try:
        textarea = get_message_textarea(
            driver
        )

        clear_textarea(
            textarea
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
            # 送信ボタンを取得できなかった場合は
            # Enterキーで送信する
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
        write_exception_log(
            "ココフォリアへの送信に失敗しました",
            error
        )

        return False


# =========================================================
# 発言処理
# =========================================================

def remove_control_words(
    text: str,
    character_response_word: str
) -> str:
    """
    Geminiへ送信する前に、制御命令を除去する。
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
    """
    ココフォリアの発言へ応答するか判定する。
    """
    random_number = random.randint(
        1,
        100
    )

    # 応答しない命令を最優先する
    if (
        "応答なし" in original_text
        or "noreply" in original_text
    ):
        random_number = 101

    # 強制応答命令
    elif (
        "強制応答" in original_text
        or "mustreply" in original_text
    ):
        random_number = 0

    # キャラクター名による強制応答
    elif (
        character_response_word
        and character_response_word in original_text
    ):
        random_number = 0

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
    """
    Geminiの返答をココフォリア投稿用に整形する。
    """
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
    """
    ココフォリアへ投稿しない返答か判定する。
    """
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
# 終了処理
# =========================================================

def close_driver(
    driver: WebDriver | None
) -> None:
    """
    Chromeを安全に終了する。
    """
    if driver is None:
        return

    try:
        driver.quit()

    except Exception as error:
        write_log(
            f"Chrome終了時のエラー: {error}"
        )


def close_gemini_client(
    client
) -> None:
    """
    Geminiクライアントを安全に終了する。
    """
    if client is None:
        return

    try:
        client.close()

    except Exception as error:
        write_log(
            f"Geminiクライアント終了時のエラー: {error}"
        )


# =========================================================
# メイン処理
# =========================================================

def main() -> None:
    write_log(
        "CcGeminiを起動します。"
    )

    write_log(
        f"実行フォルダ: {APP_DIR}"
    )

    gemini_client = None
    driver_cc = None

    try:
        # -------------------------------------------------
        # 設定ファイルの読み込み
        # -------------------------------------------------

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

        write_log(
            f"キャラクター名: "
            f"{character_name if character_name else '未設定'}"
        )

        write_log(
            f"カギ括弧設定: {kakko_flg}"
        )

        # -------------------------------------------------
        # Gemini APIの準備
        # -------------------------------------------------

        gemini_client, gemini_chat = (
            create_gemini_chat()
        )

        # -------------------------------------------------
        # Chromeの起動
        # -------------------------------------------------

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

        # -------------------------------------------------
        # 監視用変数
        # -------------------------------------------------

        before_text = ""
        start_flg = True

        # -------------------------------------------------
        # ココフォリアの監視
        # -------------------------------------------------

        while True:
            if keyboard.is_pressed("esc"):
                write_log(
                    "Escキーが押されました。終了します。"
                )

                break

            try:
                latest_text = (
                    get_latest_ccfolia_message(
                        driver_cc
                    )
                )

                # メッセージが見つからない
                if not latest_text:
                    time.sleep(
                        CHECK_INTERVAL_SECONDS
                    )

                    continue

                # 起動時に表示されていた最新発言には反応しない
                if start_flg:
                    before_text = latest_text
                    start_flg = False

                    write_log(
                        "監視を開始しました。"
                        "既存の最新発言には応答しません。"
                    )

                    time.sleep(
                        CHECK_INTERVAL_SECONDS
                    )

                    continue

                # 新しい発言がない
                if latest_text == before_text:
                    time.sleep(
                        CHECK_INTERVAL_SECONDS
                    )

                    continue

                write_log(
                    f"新しい発言: {latest_text}"
                )

                # Geminiの処理中に同じ発言へ
                # 二重応答しないよう先に保存する
                before_text = latest_text

                # 応答率は毎回ファイルから読み直す
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

                # 制御命令を除去する
                prompt_text = remove_control_words(
                    latest_text,
                    character_response_word
                )

                if not prompt_text:
                    write_log(
                        "制御命令を取り除いた結果、"
                        "Geminiへ送信する内容が空になりました。"
                    )

                    time.sleep(
                        CHECK_INTERVAL_SECONDS
                    )

                    continue

                # Geminiへ送信する
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

                # 回答なしの場合は投稿しない
                if is_blank_answer(
                    gemini_answer
                ):
                    write_log(
                        "Geminiが回答なしを返したため、"
                        "ココフォリアへ投稿しません。"
                    )

                    time.sleep(
                        CHECK_INTERVAL_SECONDS
                    )

                    continue

                # カギ括弧や追加文章を付ける
                output_text = format_gemini_answer(
                    gemini_answer,
                    latest_text,
                    kakko_flg
                )

                # ココフォリアへ投稿する
                if send_message_to_ccfolia(
                    driver_cc,
                    output_text
                ):
                    # 自分が投稿した文章を監視対象から除外する
                    before_text = output_text

            except StaleElementReferenceException:
                write_log(
                    "ココフォリアの画面が更新されました。"
                    "次の監視で要素を再取得します。"
                )

            except NoSuchElementException as error:
                write_log(
                    "ココフォリアの要素が見つかりません: "
                    f"{error}"
                )

            except WebDriverException as error:
                write_exception_log(
                    "Chrome操作中にエラーが発生しました",
                    error
                )

            except Exception as error:
                write_exception_log(
                    "監視処理中にエラーが発生しました",
                    error
                )

            time.sleep(
                CHECK_INTERVAL_SECONDS
            )

    except KeyboardInterrupt:
        write_log(
            "キーボード操作により終了します。"
        )

    except Exception as error:
        write_exception_log(
            "CcGeminiの起動中にエラーが発生しました",
            error
        )

        # exeをダブルクリックして起動した場合でも
        # エラー内容を確認できるようにする
        try:
            input(
                "\nエラーが発生しました。"
                "\nCcGemini_error.logも確認してください。"
                "\nEnterキーを押すと終了します。"
            )

        except Exception:
            time.sleep(10)

    finally:
        close_driver(
            driver_cc
        )

        close_gemini_client(
            gemini_client
        )

        write_log(
            "CcGeminiを終了しました。"
        )


# =========================================================
# プログラム開始
# =========================================================

if __name__ == "__main__":
    # Windows環境でPyInstallerを使用する際に必要
    multiprocessing.freeze_support()

    main()