#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据集下载器包
"""

from .base import BaseDatasetDownloader
from .opencompass import OpenCompassDownloader
from .truthfulqa import TruthfulQADownloader

__all__ = [
    'BaseDatasetDownloader',
    'OpenCompassDownloader',
    'TruthfulQADownloader'
]
