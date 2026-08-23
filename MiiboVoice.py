from __future__ import annotations

import io
import queue
import re
import sys
import threading
import time
import traceback
import wave
from collections import deque
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

import numpy as np
import requests
import sounddevice as sd
import tkinter as tk

from faster_whisper import WhisperModel
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
from tkinter import messagebox, ttk
from tkinter.scrolledtext import ScrolledText


# ============================================================
# 基本設定
# ============================================================

VOICEVOX_URL = "http://127.0.0.1:50021"
WINDOW_TITLE = "Miibo Voice"
WINDOW_SIZE = "920x760"

# マイク録音設定（GeminiVoiceの録音方式を継承）
SPEECH_THRESHOLD = 0.015
SILENCE_SECONDS = 1.2
WAITING_TIMEOUT_SECONDS = 30.0
MAX_RECORDING_SECONDS = 60.0
PRE_ROLL_SECONDS = 0.3
AUDIO_BLOCK_SECONDS = 0.05

# miibo返答待ち
MIIBO_RESPONSE_TIMEOUT = 60.0
MIIBO_POLL_INTERVAL = 0.35
MIIBO_SETTLE_SECONDS = 0.8

# VOICEVOXへ一度に送る最大文字数
VOICEVOX_MAX_TEXT_LENGTH = 180


# ============================================================
# パス・設定ファイル
# ============================================================

def application_directory() -> Path:
    """通常実行時は.py、PyInstaller時は.exeのあるフォルダを返す。"""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


APP_DIR = application_directory()


def read_utf8_file(filename: str, default: str | None = None) -> str:
    path = APP_DIR / filename
    if not path.exists():
        if default is not None:
            return default
        raise FileNotFoundError(f"設定ファイルが見つかりません。\n\n{path}")
    try:
        return path.read_text(encoding="utf-8").strip()
    except UnicodeDecodeError as error:
        raise ValueError(f"{filename}をUTF-8として読み込めませんでした。") from error


def read_int_file(filename: str, default: int | None = None) -> int:
    text_default = None if default is None else str(default)
    value = read_utf8_file(filename, text_default)
    try:
        return int(value)
    except ValueError as error:
        raise ValueError(f"{filename}には整数を記入してください。\n現在の内容: {value}") from error


def read_float_file(filename: str, default: float | None = None) -> float:
    text_default = None if default is None else str(default)
    value = read_utf8_file(filename, text_default)
    try:
        return float(value)
    except ValueError as error:
        raise ValueError(f"{filename}には数値を記入してください。\n現在の内容: {value}") from error


@dataclass(frozen=True)
class AppConfig:
    miibo_url: str
    whisper_model: str
    speaker_id: int
    speed_scale: float
    pitch_scale: float
    intonation_scale: float
    volume_scale: float
    pre_phoneme_length: float
    post_phoneme_length: float


def load_config() -> AppConfig:
    miibo_url = read_utf8_file("miibo_url.txt")
    whisper_model = read_utf8_file("whisper_model.txt", "small")

    if not miibo_url.startswith(("http://", "https://")):
        raise ValueError("miibo_url.txtに正しいURLを入力してください。")
    if not whisper_model:
        raise ValueError("whisper_model.txtが空です。")

    return AppConfig(
        miibo_url=miibo_url,
        whisper_model=whisper_model,
        speaker_id=read_int_file("speaker_id.txt", 3),
        speed_scale=read_float_file("speedScale.txt", 1.0),
        pitch_scale=read_float_file("pitchScale.txt", 0.0),
        intonation_scale=read_float_file("intonationScale.txt", 1.0),
        volume_scale=read_float_file("volumeScale.txt", 1.0),
        pre_phoneme_length=read_float_file("prePhonemeLength.txt", 0.1),
        post_phoneme_length=read_float_file("postPhonemeLength.txt", 0.1),
    )


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
            input_devices.append(AudioDevice(index, display_name))
        if int(device.get("max_output_channels", 0)) > 0:
            output_devices.append(AudioDevice(index, display_name))

    return input_devices, output_devices


def get_default_device_index(kind: str) -> int | None:
    try:
        defaults = sd.default.device
        if isinstance(defaults, (list, tuple)):
            index = defaults[0] if kind == "input" else defaults[1]
        else:
            index = defaults
        index = int(index)
        return index if index >= 0 else None
    except Exception:
        return None


def choose_recording_sample_rate(device_index: int) -> int:
    try:
        sd.check_input_settings(
            device=device_index,
            samplerate=16000,
            channels=1,
            dtype="float32",
        )
        return 16000
    except Exception:
        info = sd.query_devices(device_index, "input")
        return int(round(float(info["default_samplerate"])))


# ============================================================
# マイク録音
# ============================================================

def convert_float_audio_to_wav(audio: np.ndarray, sample_rate: int) -> bytes:
    audio = np.asarray(audio, dtype=np.float32)
    audio = np.clip(audio, -1.0, 1.0)
    pcm16 = (audio * 32767.0).astype(np.int16)

    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(pcm16.tobytes())
    return buffer.getvalue()


def record_until_silence(
    device_index: int,
    stop_event: threading.Event,
    status_callback: Callable[[str], None],
) -> bytes | None:
    """音声を検出してから一定時間無音になるまで録音する。"""
    sample_rate = choose_recording_sample_rate(device_index)
    block_size = max(1, int(sample_rate * AUDIO_BLOCK_SECONDS))
    audio_queue: queue.Queue[np.ndarray] = queue.Queue()

    pre_roll_count = max(1, int(PRE_ROLL_SECONDS / AUDIO_BLOCK_SECONDS))
    pre_roll: deque[np.ndarray] = deque(maxlen=pre_roll_count)

    def callback(indata, frames, callback_time, status):
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
            callback=callback,
        ):
            while not stop_event.is_set():
                try:
                    block = audio_queue.get(timeout=0.2)
                except queue.Empty:
                    continue

                mono = block[:, 0]
                rms = float(np.sqrt(np.mean(np.square(mono.astype(np.float64)))))
                now = time.monotonic()

                if not speech_started:
                    pre_roll.append(mono.copy())
                    if rms >= SPEECH_THRESHOLD:
                        speech_started = True
                        recording_started_at = now
                        last_voice_at = now
                        recorded_blocks.extend(list(pre_roll))
                        pre_roll.clear()
                        status_callback("音声を録音しています……")
                    elif now - waiting_started_at >= WAITING_TIMEOUT_SECONDS:
                        status_callback("音声が検出されませんでした。")
                        return None
                else:
                    recorded_blocks.append(mono.copy())
                    if rms >= SPEECH_THRESHOLD:
                        last_voice_at = now
                    if last_voice_at is not None and now - last_voice_at >= SILENCE_SECONDS:
                        break
                    if (
                        recording_started_at is not None
                        and now - recording_started_at >= MAX_RECORDING_SECONDS
                    ):
                        break

    except sd.PortAudioError as error:
        raise RuntimeError(
            "マイクを開けませんでした。\n"
            "別の入力機器を選択するか、Windowsのマイク使用許可を確認してください。\n\n"
            f"詳細: {error}"
        ) from error

    if stop_event.is_set() or not recorded_blocks:
        return None

    audio = np.concatenate(recorded_blocks)
    return convert_float_audio_to_wav(audio, sample_rate) if audio.size else None


# ============================================================
# faster-whisper ローカル音声文字起こし
# ============================================================

class WhisperTranscriber:
    """
    faster-whisperを使ってローカルで音声認識する。
    初回のみモデルをダウンロードし、以後はローカルキャッシュを利用する。
    """

    def __init__(self, model_name: str) -> None:
        self.model_name = model_name
        self.model: WhisperModel | None = None

    def load_model(self) -> None:
        if self.model is not None:
            return

        try:
            self.model = WhisperModel(
                self.model_name,
                device="cpu",
                compute_type="int8",
            )
        except Exception as error:
            raise RuntimeError(
                "faster-whisperモデルを読み込めませんでした。\n\n"
                "初回起動時はモデルのダウンロードにインターネット接続が必要です。\n"
                f"モデル: {self.model_name}\n\n"
                f"詳細: {error}"
            ) from error

    @staticmethod
    def wav_bytes_to_float32(wav_bytes: bytes) -> tuple[np.ndarray, int]:
        try:
            with wave.open(io.BytesIO(wav_bytes), "rb") as wav_file:
                channels = wav_file.getnchannels()
                sample_width = wav_file.getsampwidth()
                sample_rate = wav_file.getframerate()
                raw = wav_file.readframes(wav_file.getnframes())
        except wave.Error as error:
            raise RuntimeError("録音WAVを読み込めませんでした。") from error

        if sample_width == 1:
            audio = np.frombuffer(raw, dtype=np.uint8).astype(np.float32)
            audio = (audio - 128.0) / 128.0
        elif sample_width == 2:
            audio = np.frombuffer(raw, dtype="<i2").astype(np.float32)
            audio /= 32768.0
        elif sample_width == 4:
            audio = np.frombuffer(raw, dtype="<i4").astype(np.float32)
            audio /= 2147483648.0
        else:
            raise RuntimeError(
                f"文字起こしで未対応のWAVビット幅です: {sample_width * 8}bit"
            )

        if channels > 1:
            audio = audio.reshape(-1, channels).mean(axis=1)

        if sample_rate != 16000:
            old_length = len(audio)
            new_length = max(1, int(round(old_length * 16000 / sample_rate)))
            old_x = np.linspace(0.0, 1.0, old_length, endpoint=False)
            new_x = np.linspace(0.0, 1.0, new_length, endpoint=False)
            audio = np.interp(new_x, old_x, audio).astype(np.float32)
            sample_rate = 16000

        return np.ascontiguousarray(audio, dtype=np.float32), sample_rate

    def transcribe(self, wav_bytes: bytes) -> str:
        self.load_model()
        assert self.model is not None

        audio, _sample_rate = self.wav_bytes_to_float32(wav_bytes)

        if audio.size == 0:
            raise RuntimeError("録音データが空です。")

        if not np.isfinite(audio).all():
            raise RuntimeError("録音データに不正な数値が含まれています。")

        try:
            segments, _info = self.model.transcribe(
                audio,
                language="ja",
                beam_size=5,
                vad_filter=False,
                condition_on_previous_text=False,
            )

            parts: list[str] = []
            for segment in segments:
                segment_text = (segment.text or "").strip()
                if segment_text:
                    parts.append(segment_text)

        except Exception as error:
            log_path = APP_DIR / "whisper_error_log.txt"
            try:
                log_path.write_text(
                    traceback.format_exc(),
                    encoding="utf-8",
                )
            except Exception:
                pass

            raise RuntimeError(
                "faster-whisperで音声を文字起こしできませんでした。\n\n"
                f"詳細: {type(error).__name__}: {error}\n\n"
                f"詳細ログ: {log_path}"
            ) from error

        text = "".join(parts).strip()

        if not text:
            raise RuntimeError(
                "音声を認識できませんでした。\n"
                "マイク音量を確認するか、もう少し大きな声で話してください。"
            )

        return text

# ============================================================
# VOICEVOX
# ============================================================

def split_text_for_voicevox(text: str, max_length: int = VOICEVOX_MAX_TEXT_LENGTH) -> list[str]:
    normalized = re.sub(r"\s+", " ", text).strip()
    if not normalized:
        return []

    sentences = re.split(r"(?<=[。！？!?])", normalized)
    chunks: list[str] = []
    current = ""

    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue
        if len(current) + len(sentence) <= max_length:
            current += sentence
            continue
        if current:
            chunks.append(current)
            current = ""
        while len(sentence) > max_length:
            chunks.append(sentence[:max_length])
            sentence = sentence[max_length:]
        current = sentence

    if current:
        chunks.append(current)
    return chunks


class VoiceVoxClient:
    def __init__(self, base_url: str, config: AppConfig) -> None:
        self.base_url = base_url.rstrip("/")
        self.config = config
        self.session = requests.Session()

    def check_connection(self) -> None:
        try:
            response = self.session.get(f"{self.base_url}/version", timeout=5)
            response.raise_for_status()
        except requests.exceptions.RequestException as error:
            raise RuntimeError(
                "VOICEVOX Engineに接続できません。\n"
                "VOICEVOXを起動してから再度お試しください。\n\n"
                f"詳細: {error}"
            ) from error

    def synthesize(self, text: str) -> bytes:
        try:
            q = self.session.post(
                f"{self.base_url}/audio_query",
                params={"text": text, "speaker": self.config.speaker_id},
                timeout=60,
            )
            q.raise_for_status()
            query = q.json()
            query["speedScale"] = self.config.speed_scale
            query["pitchScale"] = self.config.pitch_scale
            query["intonationScale"] = self.config.intonation_scale
            query["volumeScale"] = self.config.volume_scale
            query["prePhonemeLength"] = self.config.pre_phoneme_length
            query["postPhonemeLength"] = self.config.post_phoneme_length

            r = self.session.post(
                f"{self.base_url}/synthesis",
                params={"speaker": self.config.speaker_id},
                json=query,
                timeout=180,
            )
            r.raise_for_status()
            return r.content
        except requests.exceptions.RequestException as error:
            raise RuntimeError(f"VOICEVOXとの通信に失敗しました。\n\n{error}") from error


def play_wav_bytes(
    wav_bytes: bytes,
    output_device_index: int,
    stop_event: threading.Event,
) -> None:
    buffer = io.BytesIO(wav_bytes)
    try:
        with wave.open(buffer, "rb") as wav_file:
            channels = wav_file.getnchannels()
            sample_width = wav_file.getsampwidth()
            sample_rate = wav_file.getframerate()
            raw_audio = wav_file.readframes(wav_file.getnframes())
    except wave.Error as error:
        raise RuntimeError("VOICEVOXのWAVを読み込めませんでした。") from error

    if sample_width == 1:
        audio = np.frombuffer(raw_audio, dtype=np.uint8).astype(np.float32)
        audio = (audio - 128.0) / 128.0
    elif sample_width == 2:
        audio = np.frombuffer(raw_audio, dtype="<i2").astype(np.float32) / 32768.0
    elif sample_width == 4:
        audio = np.frombuffer(raw_audio, dtype="<i4").astype(np.float32) / 2147483648.0
    else:
        raise RuntimeError(f"未対応のWAVビット幅です: {sample_width * 8}bit")

    if channels > 1:
        audio = audio.reshape(-1, channels)

    try:
        sd.play(audio, samplerate=sample_rate, device=output_device_index, blocking=False)
        while True:
            stream = sd.get_stream()
            if not stream.active:
                break
            if stop_event.is_set():
                sd.stop()
                return
            time.sleep(0.05)
    except sd.PortAudioError as error:
        raise RuntimeError(f"選択したスピーカーで再生できませんでした。\n\n{error}") from error


# ============================================================
# Selenium / miibo
# ============================================================

def create_chrome_options() -> Options:
    options = Options()
    options.add_argument("--disable-notifications")
    options.add_argument("--disable-popup-blocking")
    options.add_argument("--disable-background-networking")
    options.add_argument("--disable-features=Translate")
    options.add_argument("--no-first-run")
    options.add_argument("--no-default-browser-check")
    options.add_experimental_option("excludeSwitches", ["enable-automation", "enable-logging"])
    options.add_experimental_option("useAutomationExtension", False)
    return options


def create_chrome_driver() -> ChromeWebDriver:
    try:
        driver = ChromeWebDriver(options=create_chrome_options(), service=Service())
        driver.set_window_size(650, 820)
        driver.set_window_position(950, 0)
        driver.set_page_load_timeout(60)
        return driver
    except WebDriverException as error:
        raise RuntimeError(
            "Chromeの起動に失敗しました。\n\n"
            "Chromeがインストールされ、インターネットに接続できることを確認してください。\n"
            "Selenium ManagerがChromeDriverを自動取得します。\n\n"
            f"詳細: {error}"
        ) from error


def switch_to_miibo_frame(driver: ChromeWebDriver) -> bool:
    """miibo iframeへ切り替える。複数iframeがある場合も入力欄を持つものを探す。"""
    try:
        driver.switch_to.default_content()
        frames = WebDriverWait(driver, 15).until(
            EC.presence_of_all_elements_located((By.TAG_NAME, "iframe"))
        )

        for frame in frames:
            try:
                driver.switch_to.default_content()
                driver.switch_to.frame(frame)
                if driver.find_elements(By.ID, "chat-id-2-input") or driver.find_elements(By.CLASS_NAME, "message-content"):
                    return True
            except (NoSuchFrameException, StaleElementReferenceException):
                continue

        # CcMiiboとの互換用: 最初のiframeへ入る
        driver.switch_to.default_content()
        driver.switch_to.frame(frames[0])
        return True

    except (TimeoutException, NoSuchFrameException, StaleElementReferenceException):
        try:
            driver.switch_to.default_content()
        except Exception:
            pass
        return False


def get_character_name(driver: ChromeWebDriver) -> str:
    if not switch_to_miibo_frame(driver):
        return ""
    try:
        card_bodies = driver.find_elements(By.CLASS_NAME, "card-body")
        for body in card_bodies:
            h5s = body.find_elements(By.TAG_NAME, "h5")
            if h5s and h5s[0].text.strip():
                return h5s[0].text.strip()
        return ""
    except (NoSuchElementException, StaleElementReferenceException):
        return ""
    finally:
        try:
            driver.switch_to.default_content()
        except Exception:
            pass


def get_miibo_messages(driver: ChromeWebDriver) -> list[str]:
    if not switch_to_miibo_frame(driver):
        return []
    try:
        results: list[str] = []
        for element in driver.find_elements(By.CLASS_NAME, "message-content"):
            text = element.text.strip()
            if text:
                results.append(text)
        return results
    except StaleElementReferenceException:
        return []
    finally:
        try:
            driver.switch_to.default_content()
        except Exception:
            pass


def send_to_miibo(driver: ChromeWebDriver, text: str) -> None:
    if not switch_to_miibo_frame(driver):
        raise RuntimeError("miiboのチャットiframeが見つかりませんでした。")
    try:
        textarea = WebDriverWait(driver, 15).until(
            EC.element_to_be_clickable((By.ID, "chat-id-2-input"))
        )
        textarea.click()
        textarea.send_keys(text)
        textarea.send_keys(Keys.ENTER)
    except (TimeoutException, NoSuchElementException, StaleElementReferenceException) as error:
        raise RuntimeError(f"miiboへの送信に失敗しました。\n\n{error}") from error
    finally:
        try:
            driver.switch_to.default_content()
        except Exception:
            pass


def wait_for_miibo_response(
    driver: ChromeWebDriver,
    previous_messages: list[str],
    stop_event: threading.Event,
    status_callback: Callable[[str], None],
    timeout: float = MIIBO_RESPONSE_TIMEOUT,
) -> str:
    """送信前と異なる新規メッセージを待ち、最後のものを返す。"""
    deadline = time.monotonic() + timeout
    previous_count = len(previous_messages)
    previous_last = previous_messages[-1] if previous_messages else ""
    candidate = ""
    candidate_since = 0.0

    while time.monotonic() < deadline and not stop_event.is_set():
        messages = get_miibo_messages(driver)
        if messages:
            last = messages[-1].strip()
            is_new = len(messages) > previous_count or (last and last != previous_last)
            if is_new and last:
                if last != candidate:
                    candidate = last
                    candidate_since = time.monotonic()
                elif time.monotonic() - candidate_since >= MIIBO_SETTLE_SECONDS:
                    return candidate

        status_callback("miiboの返答を待っています……")
        time.sleep(MIIBO_POLL_INTERVAL)

    if stop_event.is_set():
        return ""
    if candidate:
        return candidate
    raise RuntimeError("miiboの返答を時間内に取得できませんでした。")


# ============================================================
# GUI
# ============================================================

class MiiboVoiceApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title(WINDOW_TITLE)
        self.root.geometry(WINDOW_SIZE)
        self.root.minsize(780, 620)

        self.ui_queue: queue.Queue[tuple[str, Any]] = queue.Queue()
        self.stop_event = threading.Event()
        self.worker_thread: threading.Thread | None = None
        self.driver: ChromeWebDriver | None = None

        self.config: AppConfig | None = None
        self.transcriber: WhisperTranscriber | None = None
        self.voicevox_client: VoiceVoxClient | None = None

        self.input_devices: list[AudioDevice] = []
        self.output_devices: list[AudioDevice] = []
        self.input_name_to_index: dict[str, int] = {}
        self.output_name_to_index: dict[str, int] = {}

        self.voice_input_var = tk.BooleanVar(value=True)
        self.voice_output_var = tk.BooleanVar(value=True)
        self.continuous_var = tk.BooleanVar(value=True)
        self.status_var = tk.StringVar(value="起動中……")
        self.character_var = tk.StringVar(value="未接続")
        self.input_device_var = tk.StringVar()
        self.output_device_var = tk.StringVar()

        self.build_gui()
        self.load_devices()
        self.initialize_clients()
        self.root.protocol("WM_DELETE_WINDOW", self.exit_application)
        self.root.after(50, self.process_ui_queue)

    def build_gui(self) -> None:
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)

        main = ttk.Frame(self.root, padding=12)
        main.grid(row=0, column=0, sticky="nsew")
        main.columnconfigure(1, weight=1)
        main.rowconfigure(7, weight=1)

        ttk.Label(main, text="miiboキャラクター").grid(row=0, column=0, sticky="w", padx=(0, 8), pady=4)
        ttk.Label(main, textvariable=self.character_var).grid(row=0, column=1, sticky="w", pady=4)
        ttk.Button(main, text="miiboを開く", command=self.open_miibo, width=14).grid(row=0, column=2, sticky="e", padx=4)

        ttk.Label(main, text="入力機器（マイク）").grid(row=1, column=0, sticky="w", padx=(0, 8), pady=4)
        self.input_combo = ttk.Combobox(main, textvariable=self.input_device_var, state="readonly")
        self.input_combo.grid(row=1, column=1, columnspan=2, sticky="ew", pady=4)

        ttk.Label(main, text="出力機器（スピーカー）").grid(row=2, column=0, sticky="w", padx=(0, 8), pady=4)
        self.output_combo = ttk.Combobox(main, textvariable=self.output_device_var, state="readonly")
        self.output_combo.grid(row=2, column=1, columnspan=2, sticky="ew", pady=4)

        options = ttk.Frame(main)
        options.grid(row=3, column=0, columnspan=3, sticky="ew", pady=(8, 4))
        ttk.Checkbutton(options, text="音声入力", variable=self.voice_input_var, command=self.update_input_state).pack(side=tk.LEFT, padx=(0, 18))
        ttk.Checkbutton(options, text="VOICEVOXで読み上げ", variable=self.voice_output_var).pack(side=tk.LEFT, padx=(0, 18))
        ttk.Checkbutton(options, text="連続会話", variable=self.continuous_var).pack(side=tk.LEFT)

        ttk.Label(main, text="音声認識").grid(
            row=4, column=0, sticky="w", padx=(0, 8), pady=(8, 4)
        )
        ttk.Label(
            main,
            text="faster-whisper / CPU int8（モデル: whisper_model.txt）",
        ).grid(row=4, column=1, columnspan=2, sticky="w", pady=(8, 4))

        ttk.Label(main, text="入力 / 文字起こし").grid(
            row=5, column=0, sticky="nw", padx=(0, 8), pady=(8, 4)
        )
        self.input_text = ScrolledText(main, height=5, wrap=tk.WORD, font=("", 11))
        self.input_text.grid(row=5, column=1, columnspan=2, sticky="nsew", pady=(8, 4))

        ttk.Label(main, text="miiboの返答").grid(row=8, column=0, sticky="nw", padx=(0, 8), pady=(8, 4))
        self.response_text = ScrolledText(main, wrap=tk.WORD, font=("", 11), state=tk.DISABLED)
        self.response_text.grid(row=8, column=1, columnspan=2, sticky="nsew", pady=(8, 4))

        ttk.Label(main, textvariable=self.status_var).grid(row=9, column=0, columnspan=2, sticky="w", pady=(8, 4))

        buttons = ttk.Frame(main)
        buttons.grid(row=10, column=0, columnspan=3, sticky="e", pady=(8, 0))
        self.start_button = ttk.Button(buttons, text="会話開始", command=self.start_conversation, width=13)
        self.start_button.pack(side=tk.LEFT, padx=4)
        self.stop_button = ttk.Button(buttons, text="中止", command=self.stop_conversation, width=10, state=tk.DISABLED)
        self.stop_button.pack(side=tk.LEFT, padx=4)
        ttk.Button(buttons, text="終了", command=self.exit_application, width=10).pack(side=tk.LEFT, padx=4)

    def load_devices(self) -> None:
        try:
            self.input_devices, self.output_devices = get_audio_devices()
            self.input_name_to_index = {d.display_name: d.index for d in self.input_devices}
            self.output_name_to_index = {d.display_name: d.index for d in self.output_devices}
            self.input_combo["values"] = [d.display_name for d in self.input_devices]
            self.output_combo["values"] = [d.display_name for d in self.output_devices]
            self.select_default(self.input_combo, self.input_devices, get_default_device_index("input"))
            self.select_default(self.output_combo, self.output_devices, get_default_device_index("output"))
        except Exception as error:
            messagebox.showerror("音声機器エラー", str(error))

    @staticmethod
    def select_default(combo: ttk.Combobox, devices: list[AudioDevice], default_index: int | None) -> None:
        for pos, device in enumerate(devices):
            if device.index == default_index:
                combo.current(pos)
                return
        if devices:
            combo.current(0)

    def initialize_clients(self) -> None:
        try:
            self.config = load_config()
            self.transcriber = WhisperTranscriber(self.config.whisper_model)
            self.voicevox_client = VoiceVoxClient(VOICEVOX_URL, self.config)
            self.status_var.set("準備完了。音声認識はfaster-whisperです。まず「miiboを開く」を押してください。")
        except Exception as error:
            self.status_var.set("初期化エラー")
            self.start_button.config(state=tk.DISABLED)
            messagebox.showerror("初期化エラー", str(error))

    def open_miibo(self) -> None:
        if self.driver is not None:
            try:
                self.driver.current_url
                self.status_var.set("miiboはすでに開いています。")
                return
            except Exception:
                self.driver = None

        def worker() -> None:
            try:
                if self.config is None:
                    raise RuntimeError("設定が読み込まれていません。")
                self.ui_queue.put(("status", "Chromeでmiiboを開いています……"))
                self.driver = create_chrome_driver()
                self.driver.get(self.config.miibo_url)
                time.sleep(2)
                name = get_character_name(self.driver)
                self.ui_queue.put(("character", name or "接続済み（名前未取得）"))
                self.ui_queue.put(("status", "miibo接続完了。必要ならブラウザ側でログインしてください。"))
            except Exception as error:
                self.ui_queue.put(("error", ("miibo接続エラー", str(error))))
                self.ui_queue.put(("status", "miibo接続エラー"))

        threading.Thread(target=worker, daemon=True).start()

    def update_input_state(self) -> None:
        self.input_text.config(state=tk.DISABLED if self.voice_input_var.get() else tk.NORMAL)

    def set_running_state(self, running: bool) -> None:
        self.start_button.config(state=tk.DISABLED if running else tk.NORMAL)
        self.stop_button.config(state=tk.NORMAL if running else tk.DISABLED)
        self.input_combo.config(state=tk.DISABLED if running else "readonly")
        self.output_combo.config(state=tk.DISABLED if running else "readonly")
        if not running:
            self.update_input_state()

    def set_input_text(self, text: str) -> None:
        self.input_text.config(state=tk.NORMAL)
        self.input_text.delete("1.0", tk.END)
        self.input_text.insert("1.0", text)
        if self.voice_input_var.get():
            self.input_text.config(state=tk.DISABLED)

    def set_response_text(self, text: str) -> None:
        self.response_text.config(state=tk.NORMAL)
        self.response_text.delete("1.0", tk.END)
        self.response_text.insert("1.0", text)
        self.response_text.config(state=tk.DISABLED)

    def process_ui_queue(self) -> None:
        try:
            while True:
                event, data = self.ui_queue.get_nowait()
                if event == "status":
                    self.status_var.set(str(data))
                elif event == "character":
                    self.character_var.set(str(data))
                elif event == "input":
                    self.set_input_text(str(data))
                elif event == "response":
                    self.set_response_text(str(data))
                elif event == "error":
                    title, message = data
                    messagebox.showerror(title, message)
                elif event == "finished":
                    self.set_running_state(False)
        except queue.Empty:
            pass
        if self.root.winfo_exists():
            self.root.after(50, self.process_ui_queue)

    def start_conversation(self) -> None:
        if self.worker_thread and self.worker_thread.is_alive():
            return
        if self.driver is None:
            messagebox.showwarning("miibo未接続", "先に「miiboを開く」を押してください。")
            return
        try:
            self.driver.current_url
        except Exception:
            self.driver = None
            messagebox.showwarning("miibo未接続", "miiboのChromeが閉じられています。もう一度開いてください。")
            return

        voice_input = self.voice_input_var.get()
        voice_output = self.voice_output_var.get()
        input_device = self.input_name_to_index.get(self.input_device_var.get())
        output_device = self.output_name_to_index.get(self.output_device_var.get())

        if voice_input and input_device is None:
            messagebox.showerror("入力機器エラー", "マイクを選択してください。")
            return
        if voice_output and output_device is None:
            messagebox.showerror("出力機器エラー", "スピーカーを選択してください。")
            return

        initial_text = ""
        if not voice_input:
            initial_text = self.input_text.get("1.0", tk.END).strip()
            if not initial_text:
                messagebox.showwarning("入力なし", "miiboへ送る文章を入力してください。")
                return

        self.stop_event.clear()
        self.set_running_state(True)
        self.worker_thread = threading.Thread(
            target=self.conversation_worker,
            args=(voice_input, voice_output, self.continuous_var.get(), initial_text, input_device, output_device),
            daemon=True,
        )
        self.worker_thread.start()

    def stop_conversation(self) -> None:
        self.stop_event.set()
        try:
            sd.stop()
        except Exception:
            pass
        self.status_var.set("中止しています……")

    def conversation_worker(
        self,
        voice_input: bool,
        voice_output: bool,
        continuous: bool,
        initial_text: str,
        input_device: int | None,
        output_device: int | None,
    ) -> None:
        try:
            if self.driver is None:
                raise RuntimeError("miiboが開かれていません。")
            if voice_output:
                if self.voicevox_client is None:
                    raise RuntimeError("VOICEVOXが初期化されていません。")
                self.ui_queue.put(("status", "VOICEVOX接続確認中……"))
                self.voicevox_client.check_connection()

            if voice_input:
                if input_device is None:
                    raise RuntimeError("入力機器が選択されていません。")
                while not self.stop_event.is_set():
                    audio_bytes = record_until_silence(input_device, self.stop_event, self.put_status)
                    if self.stop_event.is_set():
                        break
                    if audio_bytes is None:
                        if not continuous:
                            break
                        continue

                    if self.transcriber is None:
                        raise RuntimeError("faster-whisper文字起こしが初期化されていません。")
                    self.put_status("faster-whisperで音声を文字起こししています……")
                    user_text = self.transcriber.transcribe(audio_bytes)
                    self.ui_queue.put(("input", user_text))
                    self.exchange_with_miibo(user_text, voice_output, output_device)
                    if not continuous:
                        break
            else:
                self.exchange_with_miibo(initial_text, voice_output, output_device)

        except Exception as error:
            if not self.stop_event.is_set():
                self.ui_queue.put(("error", ("実行エラー", str(error))))
                self.write_error_log(error)
        finally:
            self.put_status("中止しました" if self.stop_event.is_set() else "準備完了")
            self.ui_queue.put(("finished", None))

    def exchange_with_miibo(self, user_text: str, voice_output: bool, output_device: int | None) -> None:
        if self.driver is None:
            raise RuntimeError("miiboが開かれていません。")

        previous = get_miibo_messages(self.driver)
        self.put_status("miiboへ送信しています……")
        send_to_miibo(self.driver, user_text)
        response = wait_for_miibo_response(
            self.driver,
            previous,
            self.stop_event,
            self.put_status,
        )
        if not response or self.stop_event.is_set():
            return

        self.ui_queue.put(("response", response))

        if voice_output:
            if output_device is None:
                raise RuntimeError("出力機器が選択されていません。")
            self.speak_response(response, output_device)

    def speak_response(self, text: str, output_device: int) -> None:
        if self.voicevox_client is None:
            raise RuntimeError("VOICEVOXが初期化されていません。")
        chunks = split_text_for_voicevox(text)
        for index, chunk in enumerate(chunks, start=1):
            if self.stop_event.is_set():
                return
            self.put_status(f"VOICEVOXで音声生成中……（{index}/{len(chunks)}）")
            wav_bytes = self.voicevox_client.synthesize(chunk)
            if self.stop_event.is_set():
                return
            self.put_status(f"VOICEVOXで再生中……（{index}/{len(chunks)}）")
            play_wav_bytes(wav_bytes, output_device, self.stop_event)

    def put_status(self, text: str) -> None:
        self.ui_queue.put(("status", text))

    @staticmethod
    def write_error_log(error: Exception) -> None:
        try:
            path = APP_DIR / "error_log.txt"
            with path.open("w", encoding="utf-8") as f:
                f.write(f"{type(error).__name__}: {error}\n\n")
                f.write(traceback.format_exc())
        except Exception:
            pass

    def exit_application(self) -> None:
        self.stop_event.set()
        try:
            sd.stop()
        except Exception:
            pass
        if self.driver is not None:
            try:
                self.driver.quit()
            except Exception:
                pass
            self.driver = None
        self.root.destroy()


def main() -> None:
    root = tk.Tk()
    try:
        style = ttk.Style(root)
        if "vista" in style.theme_names():
            style.theme_use("vista")
    except tk.TclError:
        pass
    MiiboVoiceApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
