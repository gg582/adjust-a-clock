"""오디오 읽기와 탈진기 소리 추출."""
import os
import subprocess
import tempfile

import numpy as np
import scipy.io.wavfile as wavfile
import scipy.signal as s

SAMPLE_RATE = 48000


class AudioError(RuntimeError):
    pass


def load_audio(path, sr=SAMPLE_RATE):
    """ffmpeg로 어떤 오디오/동영상이든 모노 float 배열로 읽는다."""
    with tempfile.TemporaryDirectory() as td:
        wav = os.path.join(td, 'a.wav')
        r = subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', path, '-vn', '-ac', '1', '-ar', str(sr), wav],
                           capture_output=True, text=True)
        if not os.path.exists(wav):
            raise AudioError(f'오디오를 읽을 수 없습니다: {r.stderr.strip() or path}')
        sr, x = wavfile.read(wav)
    return sr, x.astype(float) / 32768


def write_wav(path, sr, x):
    peak = np.abs(x).max() or 1.0
    wavfile.write(path, sr, (x / peak * 0.9 * 32767).astype(np.int16))


def denoise(x, sr):
    """대역통과(3.5–16 kHz) + 스펙트럴 게이팅. 틱 사이 조용한 구간을 잡음 기준으로 삼는다."""
    hi = min(16000, sr / 2 - 500)
    xb = s.sosfiltfilt(s.butter(6, [3500, hi], 'bandpass', fs=sr, output='sos'), x)
    nper = 512; nov = nper * 3 // 4
    _, _, Z = s.stft(xb, sr, nperseg=nper, noverlap=nov)
    P = np.abs(Z)
    noise = np.percentile(P, 30, axis=1, keepdims=True)
    gain = s.medfilt2d(np.clip(1 - (1.8 * noise / (P + 1e-12)) ** 2, 0, 1), (3, 1))
    _, xc = s.istft(Z * gain, sr, nperseg=nper, noverlap=nov)
    return xc[:len(x)]


def envelope(x, sr):
    """틱 검출용 포락선 (힐베르트 크기 + 400 Hz 저역통과)."""
    return s.sosfiltfilt(s.butter(2, 400, fs=sr, output='sos'), np.abs(s.hilbert(x)))
