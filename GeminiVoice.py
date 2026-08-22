from __future__ import annotations

import io
import queue
import re
import sys
import threading
import time
import wave
from collections import deque
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import requests
import sounddevice as sd
import tkinter as tk

from google import genai
from google.genai import types
from tkinter import messagebox, ttk
from tkinter.scrolledtext import ScrolledText


# ============================================================
# 基本設定
# ============================================================

VOICEVOX_URL = "http://127.0.0.1:50021"

# マイク録音設定
SPEECH_THRESHOLD = 0.015
SILENCE_SECONDS = 1.2
WAITING_TIMEOUT_SECONDS = 30.0
MAX_RECORDING_SECONDS = 60.0
PRE_ROLL_SECONDS = 0.3
AUDIO_BLOCK_SECONDS = 0.05

# VOICEVOXへ一度に送る最大文字数
VOICEVOX_MAX_TEXT_LENGTH = 180

WINDOW_TITLE = "Gemini Voice"
WINDOW_SIZE = "900x700"


# ============================================================
# ファイル・設定
# ============================================================

def application_directory() -> Path:
    """
    通常実行時は.pyファイルのあるフォルダ、
    PyInstaller実行時は.exeファイルのあるフォルダを返します。
    """
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent

    return Path(__file__).resolve().parent


APP_DIR = application_directory()


def read_utf8_file(filename: str) -> str:
    path = APP_DIR / filename

    if not path.exists():
        raise FileNotFoundError(
            f"設定ファイルが見つかりません。\n\n{path}"
        )

    try:
        return path.read_text(encoding="utf-8").strip()
    except UnicodeDecodeError as error:
        raise ValueError(
            f"{filename}をUTF-8として読み込めませんでした。"
        ) from error


def read_float_file(filename: str) -> float:
    value = read_utf8_file(filename)

    try:
        return float(value)
    except ValueError as error:
        raise ValueError(
            f"{filename}には数値を記入してください。\n"
            f"現在の内容: {value}"
        ) from error


def read_int_file(filename: str) -> int:
    value = read_utf8_file(filename)

    try:
        return int(value)
    except ValueError as error:
        raise ValueError(
            f"{filename}には整数を記入してください。\n"
            f"現在の内容: {value}"
        ) from error


@dataclass(frozen=True)
class AppConfig:
    gemini_api_key: str
    gemini_model: str
    system_prompt: str

    speaker_id: int
    speed_scale: float
    pitch_scale: float
    intonation_scale: float
    volume_scale: float
    pre_phoneme_length: float
    post_phoneme_length: float


def load_config() -> AppConfig:
    api_key = read_utf8_file("gemini_api_key.txt")
    model = read_utf8_file("gemini_model.txt")
    system_prompt = read_utf8_file("system_prompt.txt")

    if not api_key:
        raise ValueError("gemini_api_key.txtが空です。")

    if not model:
        raise ValueError("gemini_model.txtが空です。")

    if not system_prompt:
        raise ValueError("system_prompt.txtが空です。")

    return AppConfig(
        gemini_api_key=api_key,
        gemini_model=model,
        system_prompt=system_prompt,
        speaker_id=read_int_file("speaker_id.txt"),
        speed_scale=read_float_file("speedScale.txt"),
        pitch_scale=read_float_file("pitchScale.txt"),
        intonation_scale=read_float_file("intonationScale.txt"),
        volume_scale=read_float_file("volumeScale.txt"),
        pre_phoneme_length=read_float_file(
            "prePhonemeLength.txt"
        ),
        post_phoneme_length=read_float_file(
            "postPhonemeLength.txt"
        ),
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
            input_devices.append(
                AudioDevice(
                    index=index,
                    display_name=display_name,
                )
            )

        if int(device.get("max_output_channels", 0)) > 0:
            output_devices.append(
                AudioDevice(
                    index=index,
                    display_name=display_name,
                )
            )

    return input_devices, output_devices


def get_default_device_index(kind: str) -> int | None:
    try:
        default_devices = sd.default.device

        if isinstance(default_devices, (list, tuple)):
            index = default_devices[0] if kind == "input" else default_devices[1]
        else:
            index = default_devices

        index = int(index)

        if index >= 0:
            return index

    except Exception:
        pass

    return None


def choose_recording_sample_rate(device_index: int) -> int:
    """
    可能なら16kHzを使用し、非対応の場合は機器の既定値を使用します。
    """
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


# ============================================================
# マイク録音
# ============================================================

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
    音声を検出してから、一定時間無音が続くまで録音します。
    """
    sample_rate = choose_recording_sample_rate(device_index)
    block_size = max(
        1,
        int(sample_rate * AUDIO_BLOCK_SECONDS),
    )

    audio_queue: queue.Queue[np.ndarray] = queue.Queue()

    pre_roll_block_count = max(
        1,
        int(PRE_ROLL_SECONDS / AUDIO_BLOCK_SECONDS),
    )
    pre_roll: deque[np.ndarray] = deque(
        maxlen=pre_roll_block_count
    )

    def audio_callback(
        indata: np.ndarray,
        frames: int,
        callback_time: Any,
        status: sd.CallbackFlags,
    ) -> None:
        del frames, callback_time

        if status:
            # callback内でGUI操作や例外送出は行わない
            pass

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

                        recorded_blocks.extend(
                            list(pre_roll)
                        )
                        pre_roll.clear()

                        status_callback("音声を録音しています……")

                    elif now - waiting_started_at >= WAITING_TIMEOUT_SECONDS:
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
            "マイクを開けませんでした。\n"
            "別の入力機器を選択するか、Windowsの"
            "マイク使用許可を確認してください。\n\n"
            f"詳細: {error}"
        ) from error

    if stop_event.is_set():
        return None

    if not recorded_blocks:
        return None

    audio = np.concatenate(recorded_blocks)

    if audio.size == 0:
        return None

    return convert_float_audio_to_wav(
        audio=audio,
        sample_rate=sample_rate,
    )


# ============================================================
# VOICEVOX
# ============================================================

def split_text_for_voicevox(
    text: str,
    max_length: int = VOICEVOX_MAX_TEXT_LENGTH,
) -> list[str]:
    """
    長い返答を句読点付近で分割します。
    """
    normalized = re.sub(r"\s+", " ", text).strip()

    if not normalized:
        return []

    sentences = re.split(
        r"(?<=[。！？!?])",
        normalized,
    )

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
    def __init__(
        self,
        base_url: str,
        config: AppConfig,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.config = config
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
                "VOICEVOXを起動し、ブラウザで次のURLが"
                "開けることを確認してください。\n"
                f"{self.base_url}/docs"
            ) from error

        except requests.exceptions.RequestException as error:
            raise RuntimeError(
                f"VOICEVOX Engineの確認に失敗しました。\n\n{error}"
            ) from error

    def synthesize(self, text: str) -> bytes:
        try:
            query_response = self.session.post(
                f"{self.base_url}/audio_query",
                params={
                    "text": text,
                    "speaker": self.config.speaker_id,
                },
                timeout=60,
            )
            query_response.raise_for_status()

            audio_query = query_response.json()

            audio_query["speedScale"] = (
                self.config.speed_scale
            )
            audio_query["pitchScale"] = (
                self.config.pitch_scale
            )
            audio_query["intonationScale"] = (
                self.config.intonation_scale
            )
            audio_query["volumeScale"] = (
                self.config.volume_scale
            )
            audio_query["prePhonemeLength"] = (
                self.config.pre_phoneme_length
            )
            audio_query["postPhonemeLength"] = (
                self.config.post_phoneme_length
            )

            synthesis_response = self.session.post(
                f"{self.base_url}/synthesis",
                params={
                    "speaker": self.config.speaker_id,
                },
                json=audio_query,
                timeout=180,
            )
            synthesis_response.raise_for_status()

            return synthesis_response.content

        except requests.exceptions.ConnectionError as error:
            raise RuntimeError(
                "VOICEVOX Engineに接続できません。\n"
                "VOICEVOXが起動しているか確認してください。"
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
                f"VOICEVOXとの通信に失敗しました。\n\n{error}"
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

        while sd.get_stream().active:
            if stop_event.is_set():
                sd.stop()
                return

            time.sleep(0.05)

    except sd.PortAudioError as error:
        raise RuntimeError(
            "選択したスピーカーで音声を再生できませんでした。\n\n"
            f"詳細: {error}"
        ) from error


# ============================================================
# GUI
# ============================================================

class GeminiVoiceApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root

        self.root.title(WINDOW_TITLE)
        self.root.geometry(WINDOW_SIZE)
        self.root.minsize(760, 580)

        self.ui_queue: queue.Queue[tuple[str, Any]] = queue.Queue()
        self.stop_event = threading.Event()
        self.worker_thread: threading.Thread | None = None

        self.input_devices: list[AudioDevice] = []
        self.output_devices: list[AudioDevice] = []

        self.input_name_to_index: dict[str, int] = {}
        self.output_name_to_index: dict[str, int] = {}

        self.config: AppConfig | None = None
        self.gemini_client: genai.Client | None = None
        self.gemini_chat: Any = None
        self.voicevox_client: VoiceVoxClient | None = None

        self.voice_input_var = tk.BooleanVar(value=False)
        self.voice_output_var = tk.BooleanVar(value=False)
        self.status_var = tk.StringVar(value="起動中……")
        self.input_device_var = tk.StringVar()
        self.output_device_var = tk.StringVar()

        self.build_gui()
        self.load_devices()
        self.initialize_clients()

        self.root.protocol(
            "WM_DELETE_WINDOW",
            self.exit_application,
        )

        self.root.after(50, self.process_ui_queue)

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
        main_frame.rowconfigure(5, weight=1)

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

        option_frame = ttk.Frame(main_frame)
        option_frame.grid(
            row=2,
            column=0,
            columnspan=4,
            sticky="ew",
            pady=(8, 4),
        )

        self.voice_input_check = ttk.Checkbutton(
            option_frame,
            text="音声入力を使用する",
            variable=self.voice_input_var,
            command=self.update_input_state,
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
        self.voice_output_check.pack(side=tk.LEFT)

        ttk.Label(
            main_frame,
            text="入力",
        ).grid(
            row=3,
            column=0,
            sticky="nw",
            padx=(0, 8),
            pady=(8, 4),
        )

        self.input_text = ScrolledText(
            main_frame,
            height=6,
            wrap=tk.WORD,
            font=("", 11),
        )
        self.input_text.grid(
            row=3,
            column=1,
            columnspan=3,
            sticky="nsew",
            pady=(8, 4),
        )

        ttk.Label(
            main_frame,
            text="Geminiの返答",
        ).grid(
            row=5,
            column=0,
            sticky="nw",
            padx=(0, 8),
            pady=(8, 4),
        )

        self.response_text = ScrolledText(
            main_frame,
            wrap=tk.WORD,
            font=("", 11),
            state=tk.DISABLED,
        )
        self.response_text.grid(
            row=5,
            column=1,
            columnspan=3,
            sticky="nsew",
            pady=(8, 4),
        )

        status_frame = ttk.Frame(main_frame)
        status_frame.grid(
            row=6,
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

        button_frame = ttk.Frame(main_frame)
        button_frame.grid(
            row=7,
            column=0,
            columnspan=4,
            sticky="e",
            pady=(8, 0),
        )

        self.start_button = ttk.Button(
            button_frame,
            text="開始",
            command=self.start_conversation,
            width=12,
        )
        self.start_button.pack(
            side=tk.LEFT,
            padx=4,
        )

        self.stop_button = ttk.Button(
            button_frame,
            text="中止",
            command=self.stop_conversation,
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
    # 初期化
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

            input_names = [
                device.display_name
                for device in self.input_devices
            ]
            output_names = [
                device.display_name
                for device in self.output_devices
            ]

            self.input_device_combo["values"] = input_names
            self.output_device_combo["values"] = output_names

            default_input = get_default_device_index("input")
            default_output = get_default_device_index("output")

            self.select_default_device(
                combo=self.input_device_combo,
                variable=self.input_device_var,
                devices=self.input_devices,
                default_index=default_input,
            )
            self.select_default_device(
                combo=self.output_device_combo,
                variable=self.output_device_var,
                devices=self.output_devices,
                default_index=default_output,
            )

        except Exception as error:
            messagebox.showerror(
                "音声機器エラー",
                f"音声機器の一覧を取得できませんでした。\n\n{error}",
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

    def initialize_clients(self) -> None:
        try:
            self.config = load_config()

            self.gemini_client = genai.Client(
                api_key=self.config.gemini_api_key
            )

            generation_config = types.GenerateContentConfig(
                system_instruction=self.config.system_prompt,
            )

            self.gemini_chat = self.gemini_client.chats.create(
                model=self.config.gemini_model,
                config=generation_config,
            )

            self.voicevox_client = VoiceVoxClient(
                base_url=VOICEVOX_URL,
                config=self.config,
            )

            self.status_var.set("準備完了")

        except Exception as error:
            self.status_var.set("初期化エラー")
            self.start_button.config(state=tk.DISABLED)

            messagebox.showerror(
                "初期化エラー",
                str(error),
            )

    # --------------------------------------------------------
    # GUI操作
    # --------------------------------------------------------

    def update_input_state(self) -> None:
        if self.voice_input_var.get():
            self.input_text.config(state=tk.DISABLED)
        else:
            self.input_text.config(state=tk.NORMAL)

    def set_running_state(self, running: bool) -> None:
        if running:
            self.start_button.config(state=tk.DISABLED)
            self.stop_button.config(state=tk.NORMAL)
            self.voice_input_check.config(state=tk.DISABLED)
            self.voice_output_check.config(state=tk.DISABLED)
            self.input_device_combo.config(state=tk.DISABLED)
            self.output_device_combo.config(state=tk.DISABLED)

        else:
            self.start_button.config(state=tk.NORMAL)
            self.stop_button.config(state=tk.DISABLED)
            self.voice_input_check.config(state=tk.NORMAL)
            self.voice_output_check.config(state=tk.NORMAL)
            self.input_device_combo.config(state="readonly")
            self.output_device_combo.config(state="readonly")
            self.update_input_state()

    def clear_response(self) -> None:
        self.response_text.config(state=tk.NORMAL)
        self.response_text.delete("1.0", tk.END)
        self.response_text.config(state=tk.DISABLED)

    def append_response(self, text: str) -> None:
        self.response_text.config(state=tk.NORMAL)
        self.response_text.insert(tk.END, text)
        self.response_text.see(tk.END)
        self.response_text.config(state=tk.DISABLED)

    def put_status(self, text: str) -> None:
        self.ui_queue.put(("status", text))

    def put_error(self, title: str, message: str) -> None:
        self.ui_queue.put(
            (
                "error",
                (title, message),
            )
        )

    def process_ui_queue(self) -> None:
        try:
            while True:
                event_name, event_data = self.ui_queue.get_nowait()

                if event_name == "status":
                    self.status_var.set(str(event_data))

                elif event_name == "clear_response":
                    self.clear_response()

                elif event_name == "append_response":
                    self.append_response(str(event_data))

                elif event_name == "error":
                    title, message = event_data
                    messagebox.showerror(title, message)

                elif event_name == "finished":
                    self.set_running_state(False)

        except queue.Empty:
            pass

        self.root.after(50, self.process_ui_queue)

    # --------------------------------------------------------
    # 開始・停止
    # --------------------------------------------------------

    def start_conversation(self) -> None:
        if self.worker_thread and self.worker_thread.is_alive():
            return

        if self.gemini_chat is None or self.config is None:
            messagebox.showerror(
                "エラー",
                "Geminiが初期化されていません。",
            )
            return

        voice_input = self.voice_input_var.get()
        voice_output = self.voice_output_var.get()

        input_device_index = self.get_selected_input_device()
        output_device_index = self.get_selected_output_device()

        if voice_input and input_device_index is None:
            messagebox.showerror(
                "入力機器エラー",
                "使用するマイクを選択してください。",
            )
            return

        if voice_output and output_device_index is None:
            messagebox.showerror(
                "出力機器エラー",
                "使用するスピーカーを選択してください。",
            )
            return

        text = ""

        if not voice_input:
            text = self.input_text.get(
                "1.0",
                tk.END,
            ).strip()

            if not text:
                messagebox.showwarning(
                    "入力なし",
                    "Geminiへ送る文章を入力してください。",
                )
                return

        self.stop_event.clear()
        self.set_running_state(True)

        self.worker_thread = threading.Thread(
            target=self.conversation_worker,
            args=(
                voice_input,
                voice_output,
                text,
                input_device_index,
                output_device_index,
            ),
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

    def exit_application(self) -> None:
        self.stop_event.set()

        try:
            sd.stop()
        except Exception:
            pass

        self.root.destroy()

    def get_selected_input_device(self) -> int | None:
        return self.input_name_to_index.get(
            self.input_device_var.get()
        )

    def get_selected_output_device(self) -> int | None:
        return self.output_name_to_index.get(
            self.output_device_var.get()
        )

    # --------------------------------------------------------
    # 会話処理
    # --------------------------------------------------------

    def conversation_worker(
        self,
        voice_input: bool,
        voice_output: bool,
        initial_text: str,
        input_device_index: int | None,
        output_device_index: int | None,
    ) -> None:
        try:
            if voice_output:
                if self.voicevox_client is None:
                    raise RuntimeError(
                        "VOICEVOXが初期化されていません。"
                    )

                self.put_status(
                    "VOICEVOXとの接続を確認しています……"
                )
                self.voicevox_client.check_connection()

            if voice_input:
                if input_device_index is None:
                    raise RuntimeError(
                        "入力機器が選択されていません。"
                    )

                self.run_voice_input_loop(
                    input_device_index=input_device_index,
                    voice_output=voice_output,
                    output_device_index=output_device_index,
                )

            else:
                self.send_text_to_gemini(
                    user_text=initial_text,
                    voice_output=voice_output,
                    output_device_index=output_device_index,
                )

        except Exception as error:
            if not self.stop_event.is_set():
                self.put_error(
                    "実行エラー",
                    str(error),
                )

        finally:
            if self.stop_event.is_set():
                self.put_status("中止しました")
            else:
                self.put_status("準備完了")

            self.ui_queue.put(("finished", None))

    def run_voice_input_loop(
        self,
        input_device_index: int,
        voice_output: bool,
        output_device_index: int | None,
    ) -> None:
        """
        中止ボタンが押されるまで、
        録音→Gemini→VOICEVOXを繰り返します。
        """
        while not self.stop_event.is_set():
            audio_bytes = record_until_silence(
                device_index=input_device_index,
                stop_event=self.stop_event,
                status_callback=self.put_status,
            )

            if self.stop_event.is_set():
                return

            if audio_bytes is None:
                continue

            self.send_audio_to_gemini(
                audio_bytes=audio_bytes,
                voice_output=voice_output,
                output_device_index=output_device_index,
            )

    def send_text_to_gemini(
        self,
        user_text: str,
        voice_output: bool,
        output_device_index: int | None,
    ) -> None:
        self.stream_gemini_response(
            message=user_text,
            voice_output=voice_output,
            output_device_index=output_device_index,
        )

    def send_audio_to_gemini(
        self,
        audio_bytes: bytes,
        voice_output: bool,
        output_device_index: int | None,
    ) -> None:
        audio_part = types.Part.from_bytes(
            data=audio_bytes,
            mime_type="audio/wav",
        )

        self.stream_gemini_response(
            message=[audio_part],
            voice_output=voice_output,
            output_device_index=output_device_index,
        )

    def stream_gemini_response(
        self,
        message: Any,
        voice_output: bool,
        output_device_index: int | None,
    ) -> None:
        if self.gemini_chat is None:
            raise RuntimeError(
                "Geminiチャットが初期化されていません。"
            )

        self.ui_queue.put(("clear_response", None))
        self.put_status("Geminiが返答を生成しています……")

        response_parts: list[str] = []

        try:
            stream = self.gemini_chat.send_message_stream(
                message
            )

            for chunk in stream:
                if self.stop_event.is_set():
                    return

                chunk_text = getattr(chunk, "text", None)

                if not chunk_text:
                    continue

                response_parts.append(chunk_text)
                self.ui_queue.put(
                    (
                        "append_response",
                        chunk_text,
                    )
                )

        except Exception as error:
            raise RuntimeError(
                "Gemini APIへの送信に失敗しました。\n\n"
                f"{error}"
            ) from error

        if self.stop_event.is_set():
            return

        full_response = "".join(response_parts).strip()

        if not full_response:
            raise RuntimeError(
                "Geminiからテキストの返答を取得できませんでした。"
            )

        if voice_output:
            if output_device_index is None:
                raise RuntimeError(
                    "出力機器が選択されていません。"
                )

            self.speak_response(
                text=full_response,
                output_device_index=output_device_index,
            )

    def speak_response(
        self,
        text: str,
        output_device_index: int,
    ) -> None:
        if self.voicevox_client is None:
            raise RuntimeError(
                "VOICEVOXが初期化されていません。"
            )

        text_chunks = split_text_for_voicevox(text)

        for index, text_chunk in enumerate(
            text_chunks,
            start=1,
        ):
            if self.stop_event.is_set():
                return

            self.put_status(
                f"VOICEVOXで音声を生成しています……"
                f"（{index}/{len(text_chunks)}）"
            )

            wav_bytes = self.voicevox_client.synthesize(
                text_chunk
            )

            if self.stop_event.is_set():
                return

            self.put_status(
                f"VOICEVOXで再生しています……"
                f"（{index}/{len(text_chunks)}）"
            )

            play_wav_bytes(
                wav_bytes=wav_bytes,
                output_device_index=output_device_index,
                stop_event=self.stop_event,
            )


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

    GeminiVoiceApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
