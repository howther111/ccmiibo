from __future__ import annotations

import io
import queue
import sys
import threading
import time
import traceback
import wave
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import requests
import sounddevice as sd
import tkinter as tk
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
from tkinter import messagebox, ttk
from tkinter.scrolledtext import ScrolledText


# ============================================================
# 基本設定
# ============================================================

VOICEVOX_URL = "http://127.0.0.1:50021"
CHECK_INTERVAL_SECONDS = 0.5
START_WAIT_SECONDS = 3.0
VOICEVOX_MAX_TEXT_LENGTH = 180

# マイク録音設定
SPEECH_THRESHOLD = 0.015
SILENCE_SECONDS = 1.2
WAITING_TIMEOUT_SECONDS = 30.0
MAX_RECORDING_SECONDS = 60.0
PRE_ROLL_SECONDS = 0.3
AUDIO_BLOCK_SECONDS = 0.05

WINDOW_TITLE = "CcVoice"
WINDOW_SIZE = "900x700"

CHARACTER_FOLDER_PREFIX = "CcGeminiVoice_"


# ============================================================
# アプリケーションフォルダ・ログ
# ============================================================

def application_directory() -> Path:
    """
    通常実行時は.pyファイルのあるフォルダ、
    PyInstaller実行時は.exeファイルのあるフォルダを返す。
    """
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent

    return Path(__file__).resolve().parent


APP_DIR = application_directory()
LOG_FILE = APP_DIR / "CcVoice_error.log"


def write_log(message: str) -> None:
    print(message)

    try:
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        with LOG_FILE.open("a", encoding="utf-8") as file:
            file.write(f"[{timestamp}] {message}\n")
    except Exception:
        pass


def write_exception_log(title: str, error: Exception) -> None:
    write_log(f"{title}: {error}")
    write_log(traceback.format_exc())


# ============================================================
# テキスト設定
# ============================================================

def read_text_file(
    path: Path,
    default: str = "",
    required: bool = False,
) -> str:
    if not path.exists():
        if required:
            raise FileNotFoundError(
                "必要な設定ファイルが見つかりません。\n\n"
                f"{path}"
            )
        return default

    try:
        return path.read_text(encoding="utf-8-sig").strip()
    except UnicodeDecodeError as error:
        raise RuntimeError(
            f"{path.name}を読み込めませんでした。\n"
            "UTF-8形式で保存してください。"
        ) from error


def read_int_file(path: Path, default: int) -> int:
    value = read_text_file(path, str(default))
    try:
        return int(value)
    except ValueError:
        write_log(
            f"{path} の値「{value}」が整数ではないため "
            f"{default} を使用します。"
        )
        return default


def read_float_file(path: Path, default: float) -> float:
    value = read_text_file(path, str(default))
    try:
        return float(value)
    except ValueError:
        write_log(
            f"{path} の値「{value}」が数値ではないため "
            f"{default} を使用します。"
        )
        return default


# ============================================================
# キャラクター設定
# ============================================================

@dataclass(frozen=True)
class CharacterVoiceConfig:
    folder: Path
    character_name: str

    speaker_id: int
    speed_scale: float
    pitch_scale: float
    intonation_scale: float
    volume_scale: float
    pre_phoneme_length: float
    post_phoneme_length: float


def load_character_voice_config(folder: Path) -> CharacterVoiceConfig:
    """
    GeminiVoice.pyと同名のVOICEVOX設定ファイルを読み込む。

    必須:
        character_name.txt

    任意:
        speaker_id.txt
        speedScale.txt
        pitchScale.txt
        intonationScale.txt
        volumeScale.txt
        prePhonemeLength.txt
        postPhonemeLength.txt
    """
    character_name = read_text_file(
        folder / "character_name.txt",
        required=True,
    )

    if not character_name:
        raise RuntimeError(
            f"{folder.name}/character_name.txt が空です。"
        )

    return CharacterVoiceConfig(
        folder=folder,
        character_name=character_name,
        speaker_id=read_int_file(folder / "speaker_id.txt", 1),
        speed_scale=read_float_file(folder / "speedScale.txt", 1.0),
        pitch_scale=read_float_file(folder / "pitchScale.txt", 0.0),
        intonation_scale=read_float_file(
            folder / "intonationScale.txt", 1.0
        ),
        volume_scale=read_float_file(folder / "volumeScale.txt", 1.0),
        pre_phoneme_length=read_float_file(
            folder / "prePhonemeLength.txt", 0.1
        ),
        post_phoneme_length=read_float_file(
            folder / "postPhonemeLength.txt", 0.1
        ),
    )


def discover_character_voices() -> tuple[
    dict[str, CharacterVoiceConfig],
    list[str],
]:
    """
    CcVoice.exeと同じフォルダにある
    CcGeminiVoice_* フォルダを自動検索する。
    """
    configs: dict[str, CharacterVoiceConfig] = {}
    warnings: list[str] = []

    for folder in sorted(APP_DIR.iterdir()):
        if not folder.is_dir():
            continue

        if not folder.name.startswith(CHARACTER_FOLDER_PREFIX):
            continue

        try:
            config = load_character_voice_config(folder)

            if config.character_name in configs:
                old_folder = configs[config.character_name].folder
                warnings.append(
                    f"キャラクター名「{config.character_name}」が重複しています。\n"
                    f"  先: {old_folder.name}\n"
                    f"  後: {folder.name}\n"
                    "後から読み込んだ設定を使用します。"
                )

            configs[config.character_name] = config

        except Exception as error:
            warnings.append(
                f"{folder.name} を読み込めませんでした: {error}"
            )

    return configs, warnings


# ============================================================
# 音声機器
# ============================================================

@dataclass(frozen=True)
class AudioDevice:
    index: int
    display_name: str


def get_audio_devices() -> tuple[list[AudioDevice], list[AudioDevice]]:
    input_devices: list[AudioDevice] = []
    output_devices: list[AudioDevice] = []

    devices = sd.query_devices()

    for index, device in enumerate(devices):
        name = str(device.get("name", f"Device {index}"))
        host_api_index = int(device.get("hostapi", 0))

        try:
            host_api_name = sd.query_hostapis(host_api_index)["name"]
        except Exception:
            host_api_name = "Unknown"

        display_name = f"[{index}] {name} / {host_api_name}"

        if int(device.get("max_input_channels", 0)) > 0:
            input_devices.append(
                AudioDevice(index=index, display_name=display_name)
            )

        if int(device.get("max_output_channels", 0)) > 0:
            output_devices.append(
                AudioDevice(index=index, display_name=display_name)
            )

    return input_devices, output_devices


def get_default_device_index(kind: str) -> int | None:
    try:
        default_devices = sd.default.device

        if isinstance(default_devices, (list, tuple)):
            index = (
                default_devices[0]
                if kind == "input"
                else default_devices[1]
            )
        else:
            index = default_devices

        index = int(index)
        if index >= 0:
            return index

    except Exception:
        pass

    return None



# ============================================================
# マイク録音
# ============================================================

def choose_recording_sample_rate(device_index: int) -> int:
    """可能なら16kHz、非対応なら機器の既定値を使用する。"""
    try:
        sd.check_input_settings(
            device=device_index,
            samplerate=16000,
            channels=1,
            dtype="float32",
        )
        return 16000
    except Exception:
        device_info = sd.query_devices(device_index, "input")
        return int(round(float(device_info["default_samplerate"])))


def convert_float_audio_to_wav(
    audio: np.ndarray,
    sample_rate: int,
) -> bytes:
    audio = np.asarray(audio, dtype=np.float32)
    audio = np.clip(audio, -1.0, 1.0)
    pcm16 = (audio * 32767.0).astype(np.int16)

    wav_buffer = io.BytesIO()
    with wave.open(wav_buffer, "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(pcm16.tobytes())

    return wav_buffer.getvalue()


def record_until_silence(
    device_index: int,
    stop_event: threading.Event,
    status_callback,
) -> bytes | None:
    """
    音声を検出してから、一定時間無音が続くまで録音する。
    """
    sample_rate = choose_recording_sample_rate(device_index)
    block_size = max(1, int(sample_rate * AUDIO_BLOCK_SECONDS))
    audio_queue: queue.Queue[np.ndarray] = queue.Queue()

    pre_roll_block_count = max(
        1,
        int(PRE_ROLL_SECONDS / AUDIO_BLOCK_SECONDS),
    )

    from collections import deque
    pre_roll: deque[np.ndarray] = deque(
        maxlen=pre_roll_block_count
    )

    def audio_callback(
        indata: np.ndarray,
        frames: int,
        callback_time: Any,
        status: sd.CallbackFlags,
    ) -> None:
        del frames, callback_time, status
        audio_queue.put(indata.copy())

    status_callback("音声を待っています……")

    speech_started = False
    recorded_blocks: list[np.ndarray] = []
    waiting_started_at = time.monotonic()
    recording_started_at: float | None = None
    last_voice_at: float | None = None

    try:
        with sd.InputStream(
            device=device_index,
            samplerate=sample_rate,
            channels=1,
            dtype="float32",
            blocksize=block_size,
            callback=audio_callback,
        ):
            while not stop_event.is_set():
                try:
                    block = audio_queue.get(timeout=0.2)
                except queue.Empty:
                    continue

                mono_block = block[:, 0]
                rms = float(
                    np.sqrt(
                        np.mean(
                            np.square(
                                mono_block.astype(np.float64)
                            )
                        )
                    )
                )
                now = time.monotonic()

                if not speech_started:
                    pre_roll.append(mono_block.copy())

                    if rms >= SPEECH_THRESHOLD:
                        speech_started = True
                        recording_started_at = now
                        last_voice_at = now
                        recorded_blocks.extend(list(pre_roll))
                        pre_roll.clear()
                        status_callback("音声を録音しています……")

                    elif (
                        now - waiting_started_at
                        >= WAITING_TIMEOUT_SECONDS
                    ):
                        status_callback(
                            "音声が検出されませんでした。"
                        )
                        return None

                else:
                    recorded_blocks.append(mono_block.copy())

                    if rms >= SPEECH_THRESHOLD:
                        last_voice_at = now

                    if (
                        last_voice_at is not None
                        and now - last_voice_at >= SILENCE_SECONDS
                    ):
                        break

                    if (
                        recording_started_at is not None
                        and now - recording_started_at
                        >= MAX_RECORDING_SECONDS
                    ):
                        break

    except sd.PortAudioError as error:
        raise RuntimeError(
            "マイクを開けませんでした。\\n"
            "別の入力機器を選択するか、Windowsの"
            "マイク使用許可を確認してください。\\n\\n"
            f"詳細: {error}"
        ) from error

    if stop_event.is_set() or not recorded_blocks:
        return None

    audio = np.concatenate(recorded_blocks)

    if audio.size == 0:
        return None

    return convert_float_audio_to_wav(
        audio=audio,
        sample_rate=sample_rate,
    )


def transcribe_with_windows_speech(
    wav_bytes: bytes,
) -> str:
    """
    マイク音声を文字列へ変換する。
    SpeechRecognition + Google Web Speech APIを利用する。
    """
    try:
        import speech_recognition as sr
    except ImportError as error:
        raise RuntimeError(
            "音声認識ライブラリがありません。\\n"
            "pip install SpeechRecognition を実行してください。"
        ) from error

    recognizer = sr.Recognizer()

    with sr.AudioFile(io.BytesIO(wav_bytes)) as source:
        audio_data = recognizer.record(source)

    try:
        return recognizer.recognize_google(
            audio_data,
            language="ja-JP",
        ).strip()

    except sr.UnknownValueError:
        return ""

    except sr.RequestError as error:
        raise RuntimeError(
            "音声認識サービスへ接続できませんでした。\\n\\n"
            f"{error}"
        ) from error


# ============================================================
# VOICEVOX
# ============================================================

def split_text_for_voicevox(
    text: str,
    max_length: int = VOICEVOX_MAX_TEXT_LENGTH,
) -> list[str]:
    text = " ".join(text.split()).strip()

    if not text:
        return []

    chunks: list[str] = []
    current = ""

    for char in text:
        current += char

        if len(current) >= max_length or char in "。！？!?":
            chunks.append(current.strip())
            current = ""

    if current.strip():
        chunks.append(current.strip())

    return [chunk for chunk in chunks if chunk]


class VoiceVoxClient:
    def __init__(self, base_url: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()

    def check_connection(self) -> None:
        try:
            response = self.session.get(
                f"{self.base_url}/version",
                timeout=5,
            )
            response.raise_for_status()

        except requests.exceptions.ConnectionError as error:
            raise RuntimeError(
                "VOICEVOX Engineに接続できません。\n\n"
                "VOICEVOXを起動してからCcVoiceを開始してください。"
            ) from error

        except requests.exceptions.RequestException as error:
            raise RuntimeError(
                "VOICEVOX Engineの確認に失敗しました。\n\n"
                f"{error}"
            ) from error

    def synthesize(
        self,
        text: str,
        config: CharacterVoiceConfig,
    ) -> bytes:
        try:
            query_response = self.session.post(
                f"{self.base_url}/audio_query",
                params={
                    "text": text,
                    "speaker": config.speaker_id,
                },
                timeout=60,
            )
            query_response.raise_for_status()

            audio_query = query_response.json()
            audio_query["speedScale"] = config.speed_scale
            audio_query["pitchScale"] = config.pitch_scale
            audio_query["intonationScale"] = config.intonation_scale
            audio_query["volumeScale"] = config.volume_scale
            audio_query["prePhonemeLength"] = config.pre_phoneme_length
            audio_query["postPhonemeLength"] = config.post_phoneme_length

            synthesis_response = self.session.post(
                f"{self.base_url}/synthesis",
                params={"speaker": config.speaker_id},
                json=audio_query,
                timeout=180,
            )
            synthesis_response.raise_for_status()

            return synthesis_response.content

        except requests.exceptions.ConnectionError as error:
            raise RuntimeError(
                "VOICEVOX Engineに接続できません。"
            ) from error

        except requests.exceptions.HTTPError as error:
            response_text = ""

            if error.response is not None:
                response_text = error.response.text[:500]

            raise RuntimeError(
                "VOICEVOX APIでエラーが発生しました。\n\n"
                f"{error}\n{response_text}"
            ) from error

        except requests.exceptions.RequestException as error:
            raise RuntimeError(
                "VOICEVOXとの通信に失敗しました。\n\n"
                f"{error}"
            ) from error


def play_wav_bytes(
    wav_bytes: bytes,
    output_device_index: int,
    stop_event: threading.Event,
) -> None:
    wav_buffer = io.BytesIO(wav_bytes)

    try:
        with wave.open(wav_buffer, "rb") as wav_file:
            channels = wav_file.getnchannels()
            sample_width = wav_file.getsampwidth()
            sample_rate = wav_file.getframerate()
            frame_count = wav_file.getnframes()
            raw_audio = wav_file.readframes(frame_count)

    except wave.Error as error:
        raise RuntimeError(
            "VOICEVOXから返されたWAVを読み込めませんでした。"
        ) from error

    if sample_width == 1:
        audio = np.frombuffer(
            raw_audio,
            dtype=np.uint8,
        ).astype(np.float32)
        audio = (audio - 128.0) / 128.0

    elif sample_width == 2:
        audio = np.frombuffer(
            raw_audio,
            dtype="<i2",
        ).astype(np.float32)
        audio /= 32768.0

    elif sample_width == 4:
        audio = np.frombuffer(
            raw_audio,
            dtype="<i4",
        ).astype(np.float32)
        audio /= 2147483648.0

    else:
        raise RuntimeError(
            f"未対応のWAVビット幅です: {sample_width * 8}bit"
        )

    if channels > 1:
        audio = audio.reshape(-1, channels)

    try:
        sd.play(
            audio,
            samplerate=sample_rate,
            device=output_device_index,
            blocking=False,
        )

        while True:
            stream = sd.get_stream()

            if not stream.active:
                break

            if stop_event.is_set():
                sd.stop()
                return

            time.sleep(0.05)

    except sd.PortAudioError as error:
        raise RuntimeError(
            "選択したスピーカーで音声を再生できませんでした。\n\n"
            f"{error}"
        ) from error


# ============================================================
# Chrome・ココフォリア
# ============================================================

def create_chrome_options() -> Options:
    options = Options()

    options.add_argument("--disable-notifications")
    options.add_argument("--disable-popup-blocking")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--no-first-run")
    options.add_argument("--no-default-browser-check")
    options.add_argument("--start-maximized")

    return options


def create_ccfolia_driver(ccfolia_url: str) -> WebDriver:
    """
    Selenium Managerを使用するため、原則としてchromedriver.exeを
    CcVoice.exeと一緒に配布する必要はない。
    """
    service = Service()

    driver = WebDriver(
        service=service,
        options=create_chrome_options(),
    )

    driver.set_window_size(1200, 850)
    driver.set_window_position(0, 0)
    driver.get(ccfolia_url)

    return driver


def close_initial_dialog(driver: WebDriver) -> None:
    try:
        close_button = WebDriverWait(
            driver,
            5,
        ).until(
            EC.element_to_be_clickable(
                (
                    By.XPATH,
                    '//button[normalize-space()="閉じる"]',
                )
            )
        )

        close_button.click()

    except Exception:
        pass


@dataclass(frozen=True)
class CcfoliaMessage:
    speaker_name: str
    text: str


def get_latest_ccfolia_message(
    driver: WebDriver,
) -> CcfoliaMessage | None:
    """
    初版CcVoiceで動作していた方式を使用する。

    ・発言本文:
        MuiListItemText-secondary の最後の要素

    ・発言者名:
        h6.MuiTypography-subtitle2 の最後の要素
        childNodes[0].textContent のみ取得

    発言本文と発言者名は、それぞれ独立して取得する。
    """

    # -------------------------------------------------
    # 発言本文
    # 初版CcVoiceと同じ取得方法
    # -------------------------------------------------
    text_elements = driver.find_elements(
        By.CLASS_NAME,
        "MuiListItemText-secondary",
    )

    if not text_elements:
        return None

    latest_text_element = text_elements[-1]
    latest_text = latest_text_element.text.strip()

    if not latest_text:
        return None

    # -------------------------------------------------
    # 発言者名
    # ユーザー指定どおり、h6タグの最後を参照する
    # -------------------------------------------------
    elements = driver.find_elements(
        By.CSS_SELECTOR,
        "h6.MuiTypography-subtitle2",
    )

    if not elements:
        # 本文は取得できているため監視自体は止めない。
        # 発言者不明として返し、ログで確認できるようにする。
        return CcfoliaMessage(
            speaker_name="",
            text=latest_text,
        )

    latest_element = elements[-1]

    try:
        name = driver.execute_script(
            """
            return arguments[0].childNodes[0].textContent.trim();
            """,
            latest_element,
        )
    except Exception:
        name = ""

    name = str(name or "").strip()

    return CcfoliaMessage(
        speaker_name=name,
        text=latest_text,
    )


def get_message_textarea(driver: WebDriver):
    return WebDriverWait(
        driver,
        10,
    ).until(
        EC.element_to_be_clickable(
            (
                By.XPATH,
                '//textarea[@placeholder="メッセージを入力"]',
            )
        )
    )


def clear_textarea(textarea) -> None:
    textarea.click()
    textarea.send_keys(Keys.CONTROL, "a")
    textarea.send_keys(Keys.BACKSPACE)


def send_message_to_ccfolia(
    driver: WebDriver,
    message: str,
) -> bool:
    try:
        textarea = get_message_textarea(driver)
        clear_textarea(textarea)
        textarea.send_keys(message)

        try:
            submit_button = WebDriverWait(
                driver,
                5,
            ).until(
                EC.element_to_be_clickable(
                    (
                        By.XPATH,
                        '//button[normalize-space()="送信"]',
                    )
                )
            )

            submit_button.click()

        except Exception:
            textarea.send_keys(Keys.ENTER)

        return True

    except Exception as error:
        write_exception_log(
            "ココフォリアへの送信に失敗しました",
            error,
        )
        return False


# ============================================================
# GUI
# ============================================================

class CcVoiceApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root

        self.root.title(WINDOW_TITLE)
        self.root.geometry(WINDOW_SIZE)
        self.root.minsize(760, 580)

        self.ui_queue: queue.Queue[tuple[str, Any]] = queue.Queue()
        self.stop_event = threading.Event()
        self.worker_thread: threading.Thread | None = None

        self.driver: WebDriver | None = None
        self.voicevox_client = VoiceVoxClient(VOICEVOX_URL)

        self.character_configs: dict[
            str,
            CharacterVoiceConfig,
        ] = {}

        self.input_devices: list[AudioDevice] = []
        self.output_devices: list[AudioDevice] = []
        self.input_name_to_index: dict[str, int] = {}
        self.output_name_to_index: dict[str, int] = {}

        self.input_device_var = tk.StringVar()
        self.output_device_var = tk.StringVar()

        self.voice_output_var = tk.BooleanVar(value=True)
        self.voice_input_var = tk.BooleanVar(value=False)
        self.voice_input_stop_event = threading.Event()
        self.voice_input_thread: threading.Thread | None = None

        # ユーザー入力へ「」を付ける設定。デフォルトON。
        self.kakko_var = tk.BooleanVar(value=True)

        ccfolia_url = read_text_file(
            APP_DIR / "ccforia_url.txt",
            "",
        )
        self.ccfolia_url_var = tk.StringVar(value=ccfolia_url)

        self.status_var = tk.StringVar(value="起動中……")
        self.character_summary_var = tk.StringVar(value="")

        self.build_gui()
        self.load_devices()
        self.reload_character_configs()

        self.root.protocol(
            "WM_DELETE_WINDOW",
            self.exit_application,
        )

        self.root.after(50, self.process_ui_queue)
        self.status_var.set("準備完了")

    # --------------------------------------------------------
    # GUI構築
    # --------------------------------------------------------

    def build_gui(self) -> None:
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)

        main_frame = ttk.Frame(
            self.root,
            padding=12,
        )
        main_frame.grid(
            row=0,
            column=0,
            sticky="nsew",
        )

        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(6, weight=1)

        ttk.Label(
            main_frame,
            text="入力機器（マイク）",
        ).grid(
            row=0,
            column=0,
            sticky="w",
            padx=(0, 8),
            pady=4,
        )

        self.input_device_combo = ttk.Combobox(
            main_frame,
            textvariable=self.input_device_var,
            state="readonly",
        )
        self.input_device_combo.grid(
            row=0,
            column=1,
            columnspan=3,
            sticky="ew",
            pady=4,
        )

        ttk.Label(
            main_frame,
            text="出力機器（スピーカー）",
        ).grid(
            row=1,
            column=0,
            sticky="w",
            padx=(0, 8),
            pady=4,
        )

        self.output_device_combo = ttk.Combobox(
            main_frame,
            textvariable=self.output_device_var,
            state="readonly",
        )
        self.output_device_combo.grid(
            row=1,
            column=1,
            columnspan=3,
            sticky="ew",
            pady=4,
        )

        ttk.Label(
            main_frame,
            text="ココフォリアURL",
        ).grid(
            row=2,
            column=0,
            sticky="w",
            padx=(0, 8),
            pady=4,
        )

        self.ccfolia_url_entry = ttk.Entry(
            main_frame,
            textvariable=self.ccfolia_url_var,
        )
        self.ccfolia_url_entry.grid(
            row=2,
            column=1,
            columnspan=3,
            sticky="ew",
            pady=4,
        )

        option_frame = ttk.Frame(main_frame)
        option_frame.grid(
            row=3,
            column=0,
            columnspan=4,
            sticky="ew",
            pady=(8, 4),
        )

        self.voice_input_check = ttk.Checkbutton(
            option_frame,
            text="音声入力を使用する",
            variable=self.voice_input_var,
            command=self.toggle_voice_input,
        )
        self.voice_input_check.pack(
            side=tk.LEFT,
            padx=(0, 20),
        )

        self.voice_output_check = ttk.Checkbutton(
            option_frame,
            text="VOICEVOXで音声出力する",
            variable=self.voice_output_var,
        )
        self.voice_output_check.pack(
            side=tk.LEFT,
            padx=(0, 20),
        )

        # ユーザー要望の「ラジオボタン」に相当するON/OFF。
        # 2択のRadiobuttonとして実装。
        ttk.Label(
            option_frame,
            text="ユーザー発言のカッコ:",
        ).pack(
            side=tk.LEFT,
            padx=(0, 6),
        )

        self.kakko_on_radio = ttk.Radiobutton(
            option_frame,
            text="オン",
            variable=self.kakko_var,
            value=True,
        )
        self.kakko_on_radio.pack(
            side=tk.LEFT,
            padx=(0, 4),
        )

        self.kakko_off_radio = ttk.Radiobutton(
            option_frame,
            text="オフ",
            variable=self.kakko_var,
            value=False,
        )
        self.kakko_off_radio.pack(side=tk.LEFT)

        ttk.Label(
            main_frame,
            text="ユーザー発言",
        ).grid(
            row=4,
            column=0,
            sticky="nw",
            padx=(0, 8),
            pady=(8, 4),
        )

        self.input_text = ScrolledText(
            main_frame,
            height=5,
            wrap=tk.WORD,
            font=("", 11),
        )
        self.input_text.grid(
            row=4,
            column=1,
            columnspan=3,
            sticky="nsew",
            pady=(8, 4),
        )

        self.send_button = ttk.Button(
            main_frame,
            text="ココフォリアへ発言",
            command=self.send_user_message,
            width=20,
        )
        self.send_button.grid(
            row=5,
            column=3,
            sticky="e",
            pady=(2, 4),
        )

        ttk.Label(
            main_frame,
            text="監視ログ",
        ).grid(
            row=6,
            column=0,
            sticky="nw",
            padx=(0, 8),
            pady=(8, 4),
        )

        self.log_text = ScrolledText(
            main_frame,
            wrap=tk.WORD,
            font=("", 10),
            state=tk.DISABLED,
        )
        self.log_text.grid(
            row=6,
            column=1,
            columnspan=3,
            sticky="nsew",
            pady=(8, 4),
        )

        status_frame = ttk.Frame(main_frame)
        status_frame.grid(
            row=7,
            column=0,
            columnspan=4,
            sticky="ew",
            pady=(8, 4),
        )
        status_frame.columnconfigure(0, weight=1)

        ttk.Label(
            status_frame,
            textvariable=self.status_var,
        ).grid(
            row=0,
            column=0,
            sticky="w",
        )

        ttk.Label(
            status_frame,
            textvariable=self.character_summary_var,
        ).grid(
            row=1,
            column=0,
            sticky="w",
            pady=(2, 0),
        )

        button_frame = ttk.Frame(main_frame)
        button_frame.grid(
            row=8,
            column=0,
            columnspan=4,
            sticky="e",
            pady=(8, 0),
        )

        self.reload_button = ttk.Button(
            button_frame,
            text="キャラ再読込",
            command=self.reload_character_configs,
            width=14,
        )
        self.reload_button.pack(
            side=tk.LEFT,
            padx=4,
        )

        self.start_button = ttk.Button(
            button_frame,
            text="開始",
            command=self.start_monitoring,
            width=12,
        )
        self.start_button.pack(
            side=tk.LEFT,
            padx=4,
        )

        self.stop_button = ttk.Button(
            button_frame,
            text="中止",
            command=self.stop_monitoring,
            width=12,
            state=tk.DISABLED,
        )
        self.stop_button.pack(
            side=tk.LEFT,
            padx=4,
        )

        self.exit_button = ttk.Button(
            button_frame,
            text="終了",
            command=self.exit_application,
            width=12,
        )
        self.exit_button.pack(
            side=tk.LEFT,
            padx=4,
        )

    # --------------------------------------------------------
    # 音声機器
    # --------------------------------------------------------

    def load_devices(self) -> None:
        try:
            self.input_devices, self.output_devices = (
                get_audio_devices()
            )

            self.input_name_to_index = {
                device.display_name: device.index
                for device in self.input_devices
            }
            self.output_name_to_index = {
                device.display_name: device.index
                for device in self.output_devices
            }

            self.input_device_combo["values"] = [
                device.display_name
                for device in self.input_devices
            ]

            self.output_device_combo["values"] = [
                device.display_name
                for device in self.output_devices
            ]

            self.select_default_device(
                combo=self.input_device_combo,
                variable=self.input_device_var,
                devices=self.input_devices,
                default_index=get_default_device_index("input"),
            )

            self.select_default_device(
                combo=self.output_device_combo,
                variable=self.output_device_var,
                devices=self.output_devices,
                default_index=get_default_device_index("output"),
            )

        except Exception as error:
            messagebox.showerror(
                "音声機器エラー",
                "音声機器の一覧を取得できませんでした。\n\n"
                f"{error}",
            )

    @staticmethod
    def select_default_device(
        combo: ttk.Combobox,
        variable: tk.StringVar,
        devices: list[AudioDevice],
        default_index: int | None,
    ) -> None:
        for position, device in enumerate(devices):
            if device.index == default_index:
                combo.current(position)
                return

        if devices:
            combo.current(0)
        else:
            variable.set("利用可能な機器がありません")

    def get_selected_output_device(self) -> int | None:
        return self.output_name_to_index.get(
            self.output_device_var.get()
        )

    def get_selected_input_device(self) -> int | None:
        return self.input_name_to_index.get(
            self.input_device_var.get()
        )

    # --------------------------------------------------------
    # キャラクター設定
    # --------------------------------------------------------

    def reload_character_configs(self) -> None:
        configs, warnings = discover_character_voices()
        self.character_configs = configs

        names = list(configs.keys())

        self.character_summary_var.set(
            f"読込キャラクター: {len(names)}人"
            + (
                " / " + ", ".join(names)
                if names
                else ""
            )
        )

        self.append_log(
            "キャラクター設定を再読み込みしました。"
        )

        for name, config in configs.items():
            self.append_log(
                f"  {name} → {config.folder.name} "
                f"(speaker_id={config.speaker_id})"
            )

        for warning in warnings:
            self.append_log("警告: " + warning)

    # --------------------------------------------------------
    # GUI状態
    # --------------------------------------------------------

    def set_running_state(self, running: bool) -> None:
        if running:
            self.start_button.config(state=tk.DISABLED)
            self.stop_button.config(state=tk.NORMAL)
            self.reload_button.config(state=tk.DISABLED)
            self.output_device_combo.config(state=tk.DISABLED)
            self.ccfolia_url_entry.config(state=tk.DISABLED)

        else:
            self.start_button.config(state=tk.NORMAL)
            self.stop_button.config(state=tk.DISABLED)
            self.reload_button.config(state=tk.NORMAL)
            self.output_device_combo.config(state="readonly")
            self.ccfolia_url_entry.config(state=tk.NORMAL)

    def append_log(self, text: str) -> None:
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(
            tk.END,
            f"{time.strftime('%H:%M:%S')}  {text}\n",
        )
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)

    def put_status(self, text: str) -> None:
        self.ui_queue.put(("status", text))

    def put_log(self, text: str) -> None:
        self.ui_queue.put(("log", text))

    def put_error(self, title: str, message: str) -> None:
        self.ui_queue.put(
            ("error", (title, message))
        )

    def process_ui_queue(self) -> None:
        try:
            while True:
                event_name, event_data = self.ui_queue.get_nowait()

                if event_name == "status":
                    self.status_var.set(str(event_data))

                elif event_name == "log":
                    self.append_log(str(event_data))

                elif event_name == "set_input":
                    self.input_text.delete("1.0", tk.END)
                    self.input_text.insert("1.0", str(event_data))

                elif event_name == "error":
                    title, message = event_data
                    messagebox.showerror(title, message)

                elif event_name == "finished":
                    self.set_running_state(False)

        except queue.Empty:
            pass

        self.root.after(50, self.process_ui_queue)

    # --------------------------------------------------------
    # 音声入力
    # --------------------------------------------------------

    def toggle_voice_input(self) -> None:
        if self.voice_input_var.get():
            device_index = self.get_selected_input_device()

            if device_index is None:
                self.voice_input_var.set(False)
                messagebox.showerror(
                    "入力機器エラー",
                    "使用するマイクを選択してください。",
                )
                return

            self.voice_input_stop_event.clear()

            self.voice_input_thread = threading.Thread(
                target=self.voice_input_worker,
                args=(device_index,),
                daemon=True,
            )
            self.voice_input_thread.start()

        else:
            self.voice_input_stop_event.set()

    def voice_input_worker(self, device_index: int) -> None:
        """
        チェックがONの間、
        発話→無音検出→文字起こし→ココフォリア送信を繰り返す。
        """
        self.put_log("音声入力を開始しました。")

        try:
            while (
                self.voice_input_var.get()
                and not self.voice_input_stop_event.is_set()
            ):
                wav_bytes = record_until_silence(
                    device_index=device_index,
                    stop_event=self.voice_input_stop_event,
                    status_callback=self.put_status,
                )

                if self.voice_input_stop_event.is_set():
                    break

                if not wav_bytes:
                    # 30秒間発話なしなら、ONのまま再待機。
                    continue

                self.put_status("音声を文字に変換しています……")

                recognized_text = transcribe_with_windows_speech(
                    wav_bytes
                )

                if not recognized_text:
                    self.put_log(
                        "音声を認識できませんでした。"
                    )
                    continue

                self.put_log(
                    f"音声認識: {recognized_text}"
                )

                # 入力欄にも認識結果を表示
                self.ui_queue.put(
                    ("set_input", recognized_text)
                )

                output_text = recognized_text

                if self.kakko_var.get():
                    already_quoted = (
                        output_text.startswith("「")
                        and output_text.endswith("」")
                    )
                    if not already_quoted:
                        output_text = f"「{output_text}」"

                driver = self.driver

                if driver is None:
                    self.put_log(
                        "ココフォリア未接続のため、"
                        "音声認識結果は送信しませんでした。"
                    )
                    continue

                if send_message_to_ccfolia(
                    driver,
                    output_text,
                ):
                    self.put_log(
                        f"音声入力を送信: {output_text}"
                    )
                else:
                    self.put_log(
                        "音声入力の送信に失敗しました。"
                    )

        except Exception as error:
            write_exception_log(
                "音声入力エラー",
                error,
            )
            self.put_error(
                "音声入力エラー",
                str(error),
            )

        finally:
            self.voice_input_var.set(False)

            if not self.stop_event.is_set():
                self.put_status(
                    "ココフォリアを監視中"
                    if self.driver is not None
                    else "準備完了"
                )

            self.put_log("音声入力を停止しました。")

    # --------------------------------------------------------
    # ユーザー発言
    # --------------------------------------------------------

    def send_user_message(self) -> None:
        text = self.input_text.get(
            "1.0",
            tk.END,
        ).strip()

        if not text:
            messagebox.showwarning(
                "入力なし",
                "ココフォリアへ送る文章を入力してください。",
            )
            return

        if self.kakko_var.get():
            already_quoted = (
                text.startswith("「")
                and text.endswith("」")
            )

            if not already_quoted:
                text = f"「{text}」"

        driver = self.driver

        if driver is None:
            messagebox.showwarning(
                "未接続",
                "先に「開始」を押してココフォリアへ接続してください。",
            )
            return

        def worker() -> None:
            if send_message_to_ccfolia(driver, text):
                self.put_log(f"ユーザー発言を送信: {text}")
                self.ui_queue.put(("clear_input", None))
            else:
                self.put_error(
                    "送信エラー",
                    "ココフォリアへの発言送信に失敗しました。",
                )

        threading.Thread(
            target=worker,
            daemon=True,
        ).start()

    # --------------------------------------------------------
    # 開始・停止
    # --------------------------------------------------------

    def start_monitoring(self) -> None:
        if self.worker_thread and self.worker_thread.is_alive():
            return

        ccfolia_url = self.ccfolia_url_var.get().strip()

        if not ccfolia_url:
            messagebox.showwarning(
                "URL未設定",
                "ココフォリアのURLを入力してください。\n"
                "CcVoice.exeと同じ場所のccforia_url.txtからも読み込めます。",
            )
            return

        if not self.character_configs:
            messagebox.showwarning(
                "キャラクター未登録",
                f"{CHARACTER_FOLDER_PREFIX}* フォルダが見つからないか、"
                "character_name.txtを読み込めませんでした。",
            )
            return

        if self.voice_output_var.get():
            output_device_index = self.get_selected_output_device()

            if output_device_index is None:
                messagebox.showerror(
                    "出力機器エラー",
                    "使用するスピーカーを選択してください。",
                )
                return

        self.stop_event.clear()
        self.set_running_state(True)

        self.worker_thread = threading.Thread(
            target=self.monitor_worker,
            args=(ccfolia_url,),
            daemon=True,
        )
        self.worker_thread.start()

    def stop_monitoring(self) -> None:
        self.stop_event.set()
        self.voice_input_stop_event.set()
        self.voice_input_var.set(False)

        try:
            sd.stop()
        except Exception:
            pass

        self.status_var.set("中止しています……")

    def exit_application(self) -> None:
        self.stop_event.set()
        self.voice_input_stop_event.set()
        self.voice_input_var.set(False)

        try:
            sd.stop()
        except Exception:
            pass

        try:
            if self.driver is not None:
                self.driver.quit()
        except Exception:
            pass

        self.root.destroy()

    # --------------------------------------------------------
    # 監視
    # --------------------------------------------------------

    def monitor_worker(self, ccfolia_url: str) -> None:
        try:
            if self.voice_output_var.get():
                self.put_status(
                    "VOICEVOXとの接続を確認しています……"
                )
                self.voicevox_client.check_connection()

            self.put_status(
                "Chromeでココフォリアを開いています……"
            )

            driver = create_ccfolia_driver(ccfolia_url)
            self.driver = driver

            time.sleep(START_WAIT_SECONDS)
            close_initial_dialog(driver)

            self.put_status("ココフォリアを監視中")
            self.put_log(
                "監視を開始しました。起動時点の最新発言は読み上げません。"
            )

            before_signature = ""
            first_check = True

            while not self.stop_event.is_set():
                try:
                    latest = get_latest_ccfolia_message(driver)

                    if latest is None:
                        time.sleep(CHECK_INTERVAL_SECONDS)
                        continue

                    signature = (
                        f"{latest.speaker_name}\n{latest.text}"
                    )

                    if first_check:
                        before_signature = signature
                        first_check = False
                        time.sleep(CHECK_INTERVAL_SECONDS)
                        continue

                    if signature == before_signature:
                        time.sleep(CHECK_INTERVAL_SECONDS)
                        continue

                    # 同じ発言を二重処理しないよう先に保存。
                    before_signature = signature

                    display_name = (
                        latest.speaker_name
                        if latest.speaker_name
                        else "発言者名取得失敗"
                    )

                    self.put_log(
                        f"{display_name}: {latest.text}"
                    )

                    config = self.character_configs.get(
                        latest.speaker_name
                    )

                    if config is None:
                        if latest.speaker_name:
                            self.put_log(
                                f"「{latest.speaker_name}」は登録キャラクターではないため"
                                "音声出力しません。"
                            )
                        else:
                            self.put_log(
                                "発言本文は取得できましたが、最後のh6から"
                                "キャラクター名を取得できなかったため音声出力しません。"
                            )
                        time.sleep(CHECK_INTERVAL_SECONDS)
                        continue

                    if not self.voice_output_var.get():
                        time.sleep(CHECK_INTERVAL_SECONDS)
                        continue

                    output_device_index = (
                        self.get_selected_output_device()
                    )

                    if output_device_index is None:
                        raise RuntimeError(
                            "出力機器が選択されていません。"
                        )

                    self.speak_character_message(
                        text=latest.text,
                        config=config,
                        output_device_index=output_device_index,
                    )

                except StaleElementReferenceException:
                    time.sleep(CHECK_INTERVAL_SECONDS)

                except NoSuchElementException:
                    time.sleep(CHECK_INTERVAL_SECONDS)

                except WebDriverException as error:
                    if self.stop_event.is_set():
                        break

                    raise RuntimeError(
                        "Chromeまたはココフォリアの操作中に"
                        "エラーが発生しました。\n\n"
                        f"{error}"
                    ) from error

                except Exception as error:
                    write_exception_log(
                        "監視処理中のエラー",
                        error,
                    )
                    self.put_log(
                        f"監視処理エラー: {error}"
                    )
                    time.sleep(1)

        except Exception as error:
            if not self.stop_event.is_set():
                self.put_error(
                    "実行エラー",
                    str(error),
                )

        finally:
            driver = self.driver
            self.driver = None

            if driver is not None:
                try:
                    driver.quit()
                except Exception:
                    pass

            if self.stop_event.is_set():
                self.put_status("中止しました")
            else:
                self.put_status("準備完了")

            self.ui_queue.put(("finished", None))

    def speak_character_message(
        self,
        text: str,
        config: CharacterVoiceConfig,
        output_device_index: int,
    ) -> None:
        chunks = split_text_for_voicevox(text)

        for index, chunk in enumerate(chunks, start=1):
            if self.stop_event.is_set():
                return

            self.put_status(
                f"{config.character_name}: 音声生成中 "
                f"({index}/{len(chunks)})"
            )

            wav_bytes = self.voicevox_client.synthesize(
                chunk,
                config,
            )

            if self.stop_event.is_set():
                return

            self.put_status(
                f"{config.character_name}: 再生中 "
                f"({index}/{len(chunks)})"
            )

            play_wav_bytes(
                wav_bytes=wav_bytes,
                output_device_index=output_device_index,
                stop_event=self.stop_event,
            )

        self.put_status("ココフォリアを監視中")


# ============================================================
# エントリーポイント
# ============================================================

def main() -> None:
    root = tk.Tk()

    try:
        style = ttk.Style(root)

        if "vista" in style.theme_names():
            style.theme_use("vista")

    except tk.TclError:
        pass

    app = CcVoiceApp(root)

    # UIキュー内のclear_inputだけ追加処理するため、
    # 元メソッドをラップする。
    original_process = app.process_ui_queue

    def process_with_clear_input() -> None:
        try:
            while True:
                event_name, event_data = app.ui_queue.get_nowait()

                if event_name == "clear_input":
                    app.input_text.delete("1.0", tk.END)

                elif event_name == "status":
                    app.status_var.set(str(event_data))

                elif event_name == "log":
                    app.append_log(str(event_data))

                elif event_name == "set_input":
                    app.input_text.delete("1.0", tk.END)
                    app.input_text.insert("1.0", str(event_data))

                elif event_name == "error":
                    title, message = event_data
                    messagebox.showerror(title, message)

                elif event_name == "finished":
                    app.set_running_state(False)

        except queue.Empty:
            pass

        root.after(50, process_with_clear_input)

    # __init__で登録済みのafterも残るので、以後はこちらも動く。
    # clear_inputは元process_ui_queueでは無視されるため実害はない。
    root.after(50, process_with_clear_input)

    root.mainloop()


if __name__ == "__main__":
    main()
