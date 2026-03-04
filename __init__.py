"""OpenClaw PARTS Spectrum Profiler — scripts package."""

# 主入口
from .profiler import run_profile, compute_lexicons

# 特征提取
from .feature_extractor import extract_features, FeatureExtractor

# 数据解析
from .data_parser import DataParser

# 三层分类器
from .bond_classifier import compute_bond_profile, classify as bond_classify
from .echo_classifier import compute_echo_profile, classify as echo_classify
from .sync_matcher import run_parts_spectrum, run_sync_spectrum, classify as sync_classify

# 报告生成
from .card_generator import generate_markdown_report

__all__ = [
    # 主入口
    "run_profile",
    "compute_lexicons",
    # 特征提取
    "extract_features",
    "FeatureExtractor",
    # 数据解析
    "DataParser",
    # 分类器 (兼容接口)
    "compute_bond_profile",
    "compute_echo_profile",
    "run_parts_spectrum",
    "run_sync_spectrum",  # 向后兼容
    # 分类器 (新接口)
    "bond_classify",
    "echo_classify",
    "sync_classify",
    # 报告生成
    "generate_markdown_report",
]
