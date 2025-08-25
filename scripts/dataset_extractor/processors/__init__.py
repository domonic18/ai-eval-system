#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据集处理器包
"""

from .base import BaseDatasetProcessor
from .ceval import CEvalProcessor
from .ocnli import OCNLIProcessor

__all__ = [
    'BaseDatasetProcessor',
    'CEvalProcessor', 
    'OCNLIProcessor'
]
