# -*- coding: utf-8 -*-
"""
图片下载模块
"""
from .base import BaseDownloader
from .cover_downloader import CoverDownloader
from .avatar_downloader import AvatarDownloader

__all__ = ['BaseDownloader', 'CoverDownloader', 'AvatarDownloader']