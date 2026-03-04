# -*- coding: utf-8 -*-
"""
OpenClaw PARTS Spectrum Image Generator
使用 matplotlib 和 PIL 生成本地图片报告
"""

import os
import matplotlib.pyplot as plt
import numpy as np
from typing import Dict, List, Optional

# 设置中文字体，尝试常见的几种中文字体
plt.rcParams['font.sans-serif'] = ['Arial Unicode MS', 'SimHei', 'PingFang SC', 'Heiti TC', 'sans-serif']
plt.rcParams['axes.unicode_minus'] = False  # 解决负号显示问题

def _create_radar_chart(categories: List[str], values: List[float], title: str, filename: str, color: str = 'blue'):
    """
    生成雷达图
    """
    N = len(categories)

    # 角度
    angles = [n / float(N) * 2 * np.pi for n in range(N)]
    angles += angles[:1]

    # 值（闭合）
    values += values[:1]

    # 初始化图形
    fig, ax = plt.subplots(figsize=(6, 6), subplot_kw=dict(polar=True))

    # 绘制
    ax.plot(angles, values, linewidth=2, linestyle='solid', color=color)
    ax.fill(angles, values, color=color, alpha=0.25)

    # 设置标签
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(categories, size=12)

    # 设置范围
    ax.set_ylim(0, 1)
    
    # 移除y轴标签以保持整洁，或者设置少量刻度
    ax.set_yticks([0.2, 0.4, 0.6, 0.8])
    ax.set_yticklabels(["", "", "", ""], color="grey", size=7)

    # 标题
    plt.title(title, size=16, color=color, y=1.1)

    # 保存
    plt.tight_layout()
    plt.savefig(filename, dpi=100, bbox_inches='tight')
    plt.close()

def _create_bar_chart(categories: List[str], values: List[float], title: str, filename: str, color: str = 'blue', labels: List[str] = None):
    """
    生成水平条形图
    """
    fig, ax = plt.subplots(figsize=(8, 4))
    
    y_pos = np.arange(len(categories))
    
    ax.barh(y_pos, values, align='center', color=color, alpha=0.7)
    ax.set_yticks(y_pos)
    ax.set_yticklabels(categories)
    ax.invert_yaxis()  # labels read top-to-bottom
    ax.set_xlabel('Score')
    ax.set_xlim(0, 1)
    ax.set_title(title)
    
    # 在条形图上添加数值或标签
    if labels:
        for i, v in enumerate(values):
            ax.text(0.05, i, f"{labels[i]} ({v:.0%})", color='black', va='center', fontweight='bold')
    else:
        for i, v in enumerate(values):
            ax.text(v + 0.01, i, f"{v:.0%}", color='black', va='center')

    plt.tight_layout()
    plt.savefig(filename, dpi=100)
    plt.close()

def generate_bond_chart(bond_result: Dict, output_dir: str):
    """
    生成 BOND Profile 图片
    """
    # code = bond_result.get("code", "????")  <-- moved after normalization
    # name = bond_result.get("name", code)
    # dims = bond_result.get("dims", bond_result.get("scores", {}))
    
    # 维度顺序 T, E, C, F
    dim_keys = ["T", "E", "C", "F"]
    categories = ["节奏 (T)", "关系 (E)", "审查 (C)", "粒度 (F)"]
    
    values = []
    pole_labels = []
    
    try:
        from .card_generator import BOND_DIM_META, _get_dim_score, _normalize_bond
    except ImportError:
        from card_generator import BOND_DIM_META, _get_dim_score, _normalize_bond
    
    bond_result = _normalize_bond(bond_result)
    code = bond_result.get("code", "????")
    name = bond_result.get("name", code)
    dims = bond_result.get("dims", bond_result.get("scores", {}))
    
    for i, key in enumerate(dim_keys):
        score = _get_dim_score(dims, key)
        values.append(score)
        
        # 获取极性标签
        pole_letter = code[i].upper()
        meta = BOND_DIM_META[key]
        pole_info = meta["poles"].get(pole_letter)
        if pole_info:
             pole_labels.append(pole_info[0].split(' ')[0]) # 取英文部分
        else:
             pole_labels.append("")

    filename = os.path.join(output_dir, f"bond_chart_{code}.png")
    
    # 使用条形图展示双极维度可能更合适，但雷达图也行。这里用条形图展示倾向。
    # 为了直观，我们展示极性得分。
    
    _create_bar_chart(categories, values, f"BOND Profile: {name} ({code})", filename, color='purple', labels=pole_labels)
    return filename

def generate_echo_chart(echo_result: Dict, output_dir: str):
    """
    生成 ECHO Matrix 图片
    """
    # code = echo_result.get("code", "????")
    # name = echo_result.get("name", code)
    # dims = echo_result.get("dims", echo_result.get("scores", {}))
    
    # 维度顺序 I, S, T, M
    dim_keys = ["I", "S", "T", "M"]
    categories = ["主动 (I)", "能力 (S)", "温度 (T)", "记忆 (M)"]
    
    values = []
    pole_labels = []
    
    try:
        from .card_generator import ECHO_DIM_META, _get_dim_score, _normalize_echo
    except ImportError:
        from card_generator import ECHO_DIM_META, _get_dim_score, _normalize_echo
    
    echo_result = _normalize_echo(echo_result)
    code = echo_result.get("code", "????")
    name = echo_result.get("name", code)
    dims = echo_result.get("dims", echo_result.get("scores", {}))
    
    for i, key in enumerate(dim_keys):
        score = _get_dim_score(dims, key)
        values.append(score)
        
        # 获取极性标签
        pole_letter = code[i].upper()
        meta = ECHO_DIM_META[key]
        pole_info = meta["poles"].get(pole_letter)
        if pole_info:
             pole_labels.append(pole_info[0].split(' ')[0])
        else:
             pole_labels.append("")

    filename = os.path.join(output_dir, f"echo_chart_{code}.png")
    _create_bar_chart(categories, values, f"ECHO Matrix: {name} ({code})", filename, color='orange', labels=pole_labels)
    return filename

def generate_sync_chart(sync_result: Dict, output_dir: str):
    """
    生成 PARTS Spectrum 图片
    """
    try:
        from .card_generator import _normalize_sync
    except ImportError:
        from card_generator import _normalize_sync

    sync_result = _normalize_sync(sync_result)
    primary = sync_result.get("primary", sync_result.get("primary_type", {}))
    parts = sync_result.get("parts", {})
    name = primary.get("name", primary.get("name_zh", "Unknown"))
    
    categories = ["共振 (R)", "节奏 (T)", "主导 (A)", "精度 (P)", "协同 (S)"]
    keys = ["R", "T", "A", "P", "S"]
    values = [parts.get(k, 0.5) for k in keys]
    
    filename = os.path.join(output_dir, f"sync_chart_{name}.png")
    _create_radar_chart(categories, values, f"SYNC Relationship: {name}", filename, color='blue')
    return filename

def generate_all_charts(bond_result: Dict, echo_result: Dict, sync_result: Dict, output_dir: str) -> Dict[str, str]:
    """
    生成所有图表并返回路径字典
    """
    os.makedirs(output_dir, exist_ok=True)
    
    paths = {}
    try:
        paths['bond'] = generate_bond_chart(bond_result, output_dir)
    except Exception as e:
        print(f"Error generating BOND chart: {e}")
        
    try:
        paths['echo'] = generate_echo_chart(echo_result, output_dir)
    except Exception as e:
        print(f"Error generating ECHO chart: {e}")
        
    try:
        paths['sync'] = generate_sync_chart(sync_result, output_dir)
    except Exception as e:
        print(f"Error generating SYNC chart: {e}")
        
    return paths
