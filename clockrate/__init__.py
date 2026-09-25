"""기계식 시계 녹음으로 하루 오차(초/일)를 측정하는 타임그래퍼."""
from .analysis import Analysis, AnalysisError, Segment, analyze_signal
from .audio import load_audio

__all__ = ['Analysis', 'AnalysisError', 'Segment', 'analyze_signal', 'load_audio']
__version__ = '0.1.0'
