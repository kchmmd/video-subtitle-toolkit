#!/usr/bin/env python3
"""
视频字幕编辑器 - Web 界面版本
使用 Python 内置 HTTP 服务器，无需额外 GUI 依赖
"""

import http.server
import socketserver
import json
import os
import sys
import threading
import tempfile
import shutil
import urllib.parse
import subprocess
from pathlib import Path
from datetime import datetime

# 添加当前目录到路径
script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, script_dir)

from video_subtitle_editor import (
    extract_audio, run_whisper, parse_srt, time_to_frame,
    find_chinese_font, render_subtitle, burn_subtitles, burn_subtitles_hard,
    gpu_info
)

# 全局状态
processing_status = {
    "running": False,
    "progress": 0,
    "status": "就绪",
    "logs": [],
    "output_files": None,
    "should_stop": False,
    "srt_path": None,
    "video_path": None,
    "basename": None,
    "log_file": None
}

lock = threading.Lock()


def append_log_file(message):
    log_path = processing_status.get("log_file")
    if not log_path:
        return
    try:
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(log_path, 'a', encoding='utf-8') as f:
            f.write(f"[{ts}] {message}\n")
    except Exception:
        pass

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>视频加字幕</title>
    <style>
        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 10px;
        }
        .container {
            max-width: 900px;
            margin: 0 auto;
            background: white;
            border-radius: 12px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.2);
            overflow: hidden;
        }
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 25px 20px;
            text-align: center;
        }
        .header h1 {
            font-size: 24px;
            margin-bottom: 8px;
        }
        .header p {
            font-size: 13px;
            opacity: 0.9;
        }
        .content {
            padding: 20px;
        }
        .upload-section {
            border: 2px dashed #ddd;
            border-radius: 8px;
            padding: 30px 20px;
            text-align: center;
            margin-bottom: 15px;
            transition: all 0.3s;
        }
        .upload-section:hover {
            border-color: #667eea;
            background: #f8f9ff;
        }
        .upload-section.dragover {
            border-color: #667eea;
            background: #f0f4ff;
        }
        .file-input-wrapper {
            position: relative;
            overflow: hidden;
            display: inline-block;
        }
        .file-input-wrapper input[type=file] {
            position: absolute;
            left: 0;
            top: 0;
            opacity: 0;
            cursor: pointer;
            width: 100%;
            height: 100%;
        }
        .btn {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            padding: 10px 20px;
            font-size: 15px;
            border-radius: 6px;
            cursor: pointer;
            transition: all 0.3s;
        }
        .btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 5px 20px rgba(102, 126, 234, 0.4);
        }
        .btn:disabled {
            opacity: 0.5;
            cursor: not-allowed;
            transform: none;
        }
        .btn-success {
            background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
        }
        .btn-success:hover {
            box-shadow: 0 5px 20px rgba(56, 239, 125, 0.4);
        }
        .btn-warning {
            background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
        }
        .btn-warning:hover {
            box-shadow: 0 5px 20px rgba(245, 87, 108, 0.4);
        }
        .btn-small {
            padding: 8px 16px;
            font-size: 14px;
        }
        .progress-section {
            margin: 15px 0;
        }
        .progress-bar {
            width: 100%;
            height: 28px;
            background: #eee;
            border-radius: 14px;
            overflow: hidden;
        }
        .progress-fill {
            height: 100%;
            background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
            transition: width 0.3s;
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-weight: bold;
            font-size: 13px;
        }
        .status-text {
            text-align: center;
            margin: 12px 0;
            font-size: 15px;
            color: #333;
        }
        .logs-section {
            margin-top: 15px;
        }
        .logs-title {
            font-size: 15px;
            font-weight: bold;
            color: #333;
            margin-bottom: 8px;
        }
        .logs-box {
            background: #1e1e1e;
            color: #d4d4d4;
            padding: 12px;
            border-radius: 8px;
            height: 250px;
            overflow-y: auto;
            font-family: 'Monaco', 'Menlo', monospace;
            font-size: 12px;
            line-height: 1.6;
        }
        .logs-box .log-line {
            margin-bottom: 4px;
        }
        .logs-box .log-success {
            color: #4ec9b0;
        }
        .logs-box .log-error {
            color: #f44747;
        }
        .logs-box .log-info {
            color: #569cd6;
        }
        .file-info {
            background: #f8f9ff;
            border: 1px solid #e0e4ff;
            border-radius: 8px;
            padding: 18px;
            margin-top: 15px;
            display: none;
        }
        .file-info.show {
            display: block;
        }
        .file-info h3 {
            color: #667eea;
            margin-bottom: 12px;
            font-size: 17px;
        }
        .file-list {
            list-style: none;
        }
        .file-list li {
            padding: 10px 0;
            border-bottom: 1px solid #e0e4ff;
            display: flex;
            flex-direction: column;
            gap: 8px;
            align-items: flex-start;
        }
        .file-list li:last-child {
            border-bottom: none;
        }
        .file-name {
            font-weight: 500;
            width: 100%;
            word-break: break-all;
        }
        .download-btn {
            background: #667eea;
            color: white;
            text-decoration: none;
            padding: 8px 16px;
            border-radius: 4px;
            font-size: 14px;
            width: 100%;
            text-align: center;
            display: block;
        }
        .download-btn:hover {
            background: #5568d3;
        }
        .button-group {
            display: flex;
            flex-wrap: wrap;
            gap: 10px;
            justify-content: center;
            margin-top: 15px;
        }
        .selected-file {
            margin-top: 12px;
            padding: 10px;
            background: #f0f4ff;
            border-radius: 6px;
            color: #667eea;
            font-weight: 500;
            font-size: 14px;
        }
        .subtitle-editor {
            margin-top: 15px;
            background: #fff9e6;
            border: 1px solid #ffe066;
            border-radius: 8px;
            padding: 15px;
            display: none;
        }
        .subtitle-editor.show {
            display: block;
        }
        .subtitle-editor h3 {
            color: #cc8800;
            margin-bottom: 10px;
            font-size: 16px;
        }
        .subtitle-textarea {
            width: 100%;
            min-height: 200px;
            font-family: 'Monaco', 'Menlo', monospace;
            font-size: 13px;
            padding: 12px;
            border: 1px solid #ddd;
            border-radius: 6px;
            resize: vertical;
            margin-bottom: 10px;
        }
        .mode-buttons {
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
            justify-content: center;
            margin-bottom: 12px;
        }
        .mode-btn {
            background: #f0f0f0;
            color: #333;
            border: 2px solid #ddd;
            padding: 10px 16px;
            font-size: 14px;
            border-radius: 6px;
            cursor: pointer;
            transition: all 0.3s;
        }
        .mode-btn:hover {
            background: #e0e0e0;
        }
        .mode-btn.active {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border-color: #667eea;
        }
        .mode-description {
            background: #f8f9ff;
            padding: 12px;
            border-radius: 6px;
            margin-bottom: 15px;
            font-size: 13px;
            color: #555;
        }
        /* 桌面端：文件列表横向排列 */
        @media (min-width: 601px) {
            .file-list li {
                flex-direction: row;
                align-items: center;
            }
            .file-name {
                width: auto;
                flex: 1;
            }
            .download-btn {
                width: auto;
                display: inline-block;
            }
        }
        /* 手机端优化 */
        @media (max-width: 600px) {
            body {
                padding: 8px;
            }
            .container {
                border-radius: 8px;
            }
            .header {
                padding: 20px 15px;
            }
            .header h1 {
                font-size: 20px;
            }
            .content {
                padding: 15px;
            }
            .upload-section {
                padding: 25px 15px;
            }
            .btn {
                padding: 10px 18px;
                font-size: 14px;
            }
            .button-group {
                gap: 8px;
            }
            .logs-box {
                height: 200px;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🎬 视频加字幕</h1>
            <p>自动语音识别 + 字幕烧录</p>
        </div>
        <div class="content">
            <div class="mode-buttons">
                <button class="mode-btn active" onclick="setMode('oneclick')">一键生成</button>
                <button class="mode-btn" onclick="setMode('stepbystep')">分步生成</button>
            </div>
            <div class="mode-description" id="modeDescription">
                <strong>一键生成：</strong>上传视频后自动完成：提取音频 → 语音识别 → 字幕烧录，一步到位！
            </div>
            
            <div class="model-section" id="modelSection" style="margin: 15px 0; padding: 12px; background: #f8f9fa; border-radius: 8px;">
                <label for="modelSelect" style="font-size: 14px; color: #555; margin-right: 10px;">🤖 选择模型：</label>
                <select id="modelSelect" style="padding: 8px 12px; font-size: 14px; border: 1px solid #ddd; border-radius: 6px; background: white; min-width: 200px;">
                    <!-- 模型选项将通过 JavaScript 动态加载 -->
                </select>
                <span id="modelLoading" style="font-size: 12px; color: #888; margin-left: 10px;">加载中...</span>
                <span class="model-hint-icon" onclick="showModelHint()" style="margin-left: 10px; cursor: pointer; font-size: 14px; color: white; display: inline-flex; align-items: center; justify-content: center; width: 22px; height: 22px; border-radius: 50%; background: #4a90e2; transition: background 0.2s; font-weight: bold;" onmouseover="this.style.background='#357abd'" onmouseout="this.style.background='#4a90e2'">?</span>
            </div>
            
            <div id="gpuStatus" style="margin: 10px 0; padding: 10px; background: #e8f5e8; border-radius: 6px; font-size: 13px; color: #2e7d32;">
                <span id="gpuInfo">正在检测 GPU 支持...</span>
            </div>
            
            <!-- 模型提示弹窗遮罩 -->
            <div id="modelHintOverlay" style="display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.5); z-index: 9998;" onclick="hideModelHint()"></div>
            
            <!-- 模型提示弹窗 -->
            <div id="modelHintPopup" style="display: none; position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%); padding: 25px; background: white; border-radius: 12px; box-shadow: 0 8px 32px rgba(0,0,0,0.3); z-index: 9999; width: 90%; max-width: 480px; font-size: 14px; line-height: 1.6;">
                <div style="font-weight: bold; margin-bottom: 15px; color: #333; font-size: 16px;">📥 如何获取更多模型</div>
                <div style="margin-bottom: 12px;">
                    1. 访问 Hugging Face 下载更多模型：<br>
                    <a href="https://huggingface.co/ggerganov/whisper.cpp/tree/main" target="_blank" style="color: #4a90e2; word-break: break-all;">https://huggingface.co/ggerganov/whisper.cpp/tree/main</a>
                </div>
                <div style="margin-bottom: 12px;">
                    2. 下载以 <code style="background: #f5f5f5; padding: 2px 6px; border-radius: 3px;">ggml-</code> 开头、<code style="background: #f5f5f5; padding: 2px 6px; border-radius: 3px;">.bin</code> 结尾的模型文件
                </div>
                <div style="margin-bottom: 12px;">
                    3. 将模型文件放到以下目录：<br>
                    <code style="background: #f5f5f5; padding: 4px 8px; border-radius: 4px; display: inline-block; margin-top: 6px; font-size: 13px;">Release\models\</code>
                </div>
                <div style="margin-top: 15px; padding-top: 15px; border-top: 1px solid #eee; color: #666; font-size: 13px;">
                    💡 提示：模型越大，识别精度越高，但处理速度越慢
                </div>
                <div style="text-align: center; margin-top: 20px;">
                    <button onclick="hideModelHint()" style="padding: 10px 32px; background: #4a90e2; color: white; border: none; border-radius: 6px; cursor: pointer; font-size: 14px; font-weight: 500;">知道了</button>
                </div>
            </div>
            
            <div class="upload-section" id="uploadSection">
                <p style="font-size: 17px; margin-bottom: 18px; color: #666;">📁 选择视频文件</p>
                <div class="file-input-wrapper">
                    <button class="btn">选择文件</button>
                    <input type="file" id="fileInput" accept="video/*">
                </div>
                <div class="selected-file" id="selectedFile" style="display: none;"></div>
            </div>
            
            <div class="button-group">
                <button class="btn" id="startBtn" onclick="startProcessing()" disabled id="generateBtn">生成字幕</button>
                <button class="btn btn-warning" id="renderBtn" onclick="startRendering()" disabled style="display: none;">烧录字幕</button>
                <button class="btn btn-warning" id="stopBtn" onclick="stopProcessing()" disabled>停止</button>
            </div>
            
            <div class="progress-section" id="progressSection" style="display: none;">
                <div class="progress-bar">
                    <div class="progress-fill" id="progressFill">0%</div>
                </div>
                <div class="status-text" id="statusText">准备中...</div>
            </div>
            
            <div class="logs-section" id="logsSection" style="display: none;">
                <div class="logs-title">📋 处理日志</div>
                <div class="logs-box" id="logsBox"></div>
            </div>
            
            <div class="subtitle-editor" id="subtitleEditor">
                <h3>✏️ 编辑字幕 (SRT)</h3>
                <p style="font-size: 13px; color: #886600; margin-bottom: 8px;">修改后点击「保存并烧录」生成最终视频</p>
                <textarea class="subtitle-textarea" id="subtitleTextarea"></textarea>
                <div class="button-group">
                    <button class="btn btn-success" onclick="saveAndRender()">保存并烧录</button>
                    <button class="btn btn-small" onclick="downloadSrt()">下载 SRT</button>
                </div>
            </div>
            
            <div class="file-info" id="fileInfo">
                <h3>✅ 处理完成！</h3>
                <ul class="file-list" id="fileList"></ul>
            </div>
        </div>
    </div>

    <script>
        let selectedFile = null;
        let statusInterval = null;
        let currentMode = 'oneclick';
        let currentSrtContent = '';
        
        // 页面加载时获取可用模型列表
        async function loadModels() {
            try {
                const response = await fetch('/models');
                const data = await response.json();
                const select = document.getElementById('modelSelect');
                const loading = document.getElementById('modelLoading');
                
                if (data.models && data.models.length > 0) {
                    select.innerHTML = '';
                    data.models.forEach(model => {
                        const option = document.createElement('option');
                        option.value = model.file;
                        option.textContent = model.name;
                        select.appendChild(option);
                    });
                    // 默认选择第一个模型
                    select.selectedIndex = 0;
                    loading.style.display = 'none';
                } else {
                    loading.textContent = '未找到模型文件';
                }
            } catch (error) {
                console.error('加载模型列表失败:', error);
                document.getElementById('modelLoading').textContent = '加载失败';
            }
        }
        
        // 页面加载时调用
        loadModels();
        loadGpuInfo();
        
        // 显示/隐藏模型提示框
        
        // 加载GPU信息
        async function loadGpuInfo() {
            try {
                const response = await fetch('/gpu');
                const data = await response.json();
                const gpuInfo = document.getElementById('gpuInfo');
                const gpuStatus = document.getElementById('gpuStatus');
                
                let statusText = '';
                let statusClass = '';
                
                if (data.cuda_available || data.metal_available || data.opencl_available) {
                    const gpuTypes = [];
                    if (data.cuda_available) gpuTypes.push('NVIDIA GPU (CUDA)');
                    if (data.metal_available) gpuTypes.push('Apple Silicon (Metal)');
                    if (data.opencl_available) gpuTypes.push('OpenCL GPU');
                    
                    statusText = `✅ GPU 加速可用：${gpuTypes.join(', ')}`;
                    statusClass = 'background: #e8f5e8; color: #2e7d32;';
                } else {
                    statusText = 'ℹ️ 使用 CPU 处理（未检测到 GPU 支持）';
                    statusClass = 'background: #fff3e0; color: #ef6c00;';
                }
                
                gpuInfo.textContent = statusText;
                gpuStatus.style = statusClass + ' margin: 10px 0; padding: 10px; border-radius: 6px; font-size: 13px;';
            } catch (error) {
                console.error('加载 GPU 信息失败:', error);
                document.getElementById('gpuInfo').textContent = '无法检测 GPU 状态';
            }
        }
        function showModelHint() {
            document.getElementById('modelHintOverlay').style.display = 'block';
            document.getElementById('modelHintPopup').style.display = 'block';
        }
        
        function hideModelHint() {
            document.getElementById('modelHintOverlay').style.display = 'none';
            document.getElementById('modelHintPopup').style.display = 'none';
        }
        
        document.getElementById('fileInput').addEventListener('change', function(e) {
            selectedFile = e.target.files[0];
            if (selectedFile) {
                document.getElementById('selectedFile').textContent = '已选择: ' + selectedFile.name;
                document.getElementById('selectedFile').style.display = 'block';
                updateStartButton();
            }
        });
        
        function setMode(mode) {
            currentMode = mode;
            document.querySelectorAll('.mode-btn').forEach(btn => btn.classList.remove('active'));
            event.target.classList.add('active');
            
            const desc = document.getElementById('modeDescription');
            if (mode === 'oneclick') {
                desc.innerHTML = '<strong>一键生成：</strong>上传视频后自动完成：提取音频 → 语音识别 → 字幕烧录，一步到位！';
            } else {
                desc.innerHTML = '<strong>分步生成：</strong>1) 先生成字幕 (SRT) → 2) 可编辑修改 → 3) 最后烧录到视频，更灵活！';
            }
            
            updateStartButton();
        }
        
        function updateStartButton() {
            const startBtn = document.getElementById('startBtn');
            startBtn.disabled = !selectedFile;
            startBtn.textContent = currentMode === 'oneclick' ? '开始处理' : '生成字幕';
        }
        
        // 拖拽支持
        const uploadSection = document.getElementById('uploadSection');
        
        uploadSection.addEventListener('dragover', function(e) {
            e.preventDefault();
            uploadSection.classList.add('dragover');
        });
        
        uploadSection.addEventListener('dragleave', function(e) {
            e.preventDefault();
            uploadSection.classList.remove('dragover');
        });
        
        uploadSection.addEventListener('drop', function(e) {
            e.preventDefault();
            uploadSection.classList.remove('dragover');
            const files = e.dataTransfer.files;
            if (files.length > 0) {
                document.getElementById('fileInput').files = files;
                selectedFile = files[0];
                document.getElementById('selectedFile').textContent = '已选择: ' + selectedFile.name;
                document.getElementById('selectedFile').style.display = 'block';
                updateStartButton();
            }
        });
        
        async function startProcessing() {
            if (!selectedFile) return;
            
            const formData = new FormData();
            formData.append('video', selectedFile);
            formData.append('mode', currentMode);
            formData.append('model', document.getElementById('modelSelect').value);
            
            document.getElementById('startBtn').disabled = true;
            document.getElementById('stopBtn').disabled = false;
            document.getElementById('progressSection').style.display = 'block';
            document.getElementById('logsSection').style.display = 'block';
            document.getElementById('fileInfo').classList.remove('show');
            document.getElementById('subtitleEditor').classList.remove('show');
            document.getElementById('renderBtn').style.display = 'none';
            
            try {
                const response = await fetch('/upload', {
                    method: 'POST',
                    body: formData
                });
                const result = await response.json();
                
                if (result.success) {
                    startStatusPolling();
                } else {
                    alert('上传失败: ' + result.error);
                }
            } catch (error) {
                alert('请求失败: ' + error);
            }
        }
        
        async function startRendering() {
            try {
                const response = await fetch('/render', {
                    method: 'POST'
                });
                const result = await response.json();
                
                if (result.success) {
                    document.getElementById('renderBtn').disabled = true;
                    document.getElementById('stopBtn').disabled = false;
                    startStatusPolling();
                } else {
                    alert('失败: ' + result.error);
                }
            } catch (error) {
                alert('请求失败: ' + error);
            }
        }
        
        async function saveAndRender() {
            const content = document.getElementById('subtitleTextarea').value;
            try {
                const response = await fetch('/save_srt', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ content: content })
                });
                const result = await response.json();
                
                if (result.success) {
                    startRendering();
                } else {
                    alert('保存失败: ' + result.error);
                }
            } catch (error) {
                alert('请求失败: ' + error);
            }
        }
        
        async function downloadSrt() {
            try {
                const response = await fetch('/status');
                const status = await response.json();
                if (status.srt_path) {
                    window.location.href = '/download/' + encodeURIComponent(status.srt_path);
                }
            } catch (error) {
                alert('下载失败: ' + error);
            }
        }
        
        async function stopProcessing() {
            try {
                await fetch('/stop', { method: 'POST' });
            } catch (error) {
                console.error('停止失败:', error);
            }
        }
        
        function startStatusPolling() {
            statusInterval = setInterval(async () => {
                try {
                    const response = await fetch('/status');
                    const status = await response.json();
                    
                    updateUI(status);
                    
                    if (!status.running) {
                        clearInterval(statusInterval);
                        
                        if (status.srt_path && currentMode === 'stepbystep' && !status.output_files) {
                            // 分步模式，显示编辑器
                            showSubtitleEditor(status.srt_path);
                            document.getElementById('renderBtn').style.display = 'inline-block';
                            document.getElementById('renderBtn').disabled = false;
                        } else if (status.output_files) {
                            showOutputFiles(status.output_files);
                        }
                    }
                } catch (error) {
                    console.error('获取状态失败:', error);
                }
            }, 500);
        }
        
        async function showSubtitleEditor(srtPath) {
            try {
                const response = await fetch('/download/' + encodeURIComponent(srtPath));
                const text = await response.text();
                currentSrtContent = text;
                document.getElementById('subtitleTextarea').value = text;
                document.getElementById('subtitleEditor').classList.add('show');
            } catch (error) {
                console.error('加载字幕失败:', error);
            }
        }
        
        function updateUI(status) {
            document.getElementById('progressFill').style.width = status.progress + '%';
            document.getElementById('progressFill').textContent = status.progress + '%';
            document.getElementById('statusText').textContent = status.status;
            
            const logsBox = document.getElementById('logsBox');
            logsBox.innerHTML = status.logs.map(log => {
                let className = 'log-line';
                if (log.includes('✓') || log.includes('完成')) className += ' log-success';
                else if (log.includes('错误') || log.includes('失败')) className += ' log-error';
                else className += ' log-info';
                return '<div class="' + className + '">' + escapeHtml(log) + '</div>';
            }).join('');
            logsBox.scrollTop = logsBox.scrollHeight;
            
            document.getElementById('stopBtn').disabled = !status.running;
        }
        
        function showOutputFiles(files) {
            const fileInfo = document.getElementById('fileInfo');
            const fileList = document.getElementById('fileList');
            
            fileList.innerHTML = files.map(file => 
                '<li>' +
                '<span class="file-name">' + file.name + '</span>' +
                '<a href="/download/' + encodeURIComponent(file.path) + '" class="download-btn">下载</a>' +
                '</li>'
            ).join('');
            
            fileInfo.classList.add('show');
            document.getElementById('startBtn').disabled = false;
            document.getElementById('stopBtn').disabled = true;
        }
        
        function escapeHtml(text) {
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }
    </script>
</body>
</html>
"""


class VideoProcessingThread(threading.Thread):
    def __init__(self, video_path, whisper_dir, upload_dir, mode='oneclick', model_name=None):
        super().__init__()
        self.video_path = video_path
        self.whisper_dir = whisper_dir
        self.upload_dir = upload_dir
        self.mode = mode
        self.model_name = model_name

    def is_stopped(self):
        with lock:
            return processing_status.get("should_stop", False)

    def log(self, message):
        with lock:
            processing_status["logs"].append(message)
            append_log_file(message)

    def set_progress(self, value, status):
        with lock:
            processing_status["progress"] = value
            processing_status["status"] = status

    def run(self):
        try:
            video_path = self.video_path
            basename = os.path.splitext(os.path.basename(video_path))[0]
            dirname = os.path.dirname(video_path)

            with lock:
                processing_status["video_path"] = video_path
                processing_status["basename"] = basename

            # 如果没有指定模型，使用第一个可用的模型
            if not self.model_name:
                models_dir = os.path.join(self.whisper_dir, 'models')
                if os.path.exists(models_dir):
                    available_models = [f for f in os.listdir(models_dir) if f.endswith('.bin') and f.startswith('ggml-')]
                    if available_models:
                        self.model_name = available_models[0]
                    else:
                        self.log("错误：未找到可用的模型文件")
                        return
                else:
                    self.log("错误：未找到模型目录")
                    return

            self.log("======================================")
            self.log("视频加字幕")
            self.log("======================================")
            self.log(f"输入视频：{video_path}")
            self.log(f"处理模式：{'一键生成' if self.mode == 'oneclick' else '分步生成'}")
            self.log(f"当前模型：{self.model_name}")
            self.log("")

            temp_dir = tempfile.mkdtemp()

            try:
                audio_path = os.path.join(temp_dir, f"{basename}_audio.wav")

                # 步骤 1: 提取音频
                self.log("[1/3] 提取音频...")
                self.set_progress(5, "正在提取音频...")
                extract_audio(video_path, audio_path, self.is_stopped, self.log)
                self.log("  ✓ 音频提取完成")
                self.set_progress(15, "音频提取完成")

                if self.is_stopped():
                    self.log("处理已停止")
                    return

                # 步骤 2: 语音识别
                self.log(f"[2/3] 语音识别（Whisper）...")
                self.log(f"  使用模型：{self.model_name}")
                self.set_progress(20, "正在语音识别...")
                srt_path = os.path.join(self.upload_dir, f"{basename}.srt")
                srt_path = run_whisper(
                    audio_path,
                    self.upload_dir,
                    basename,
                    self.whisper_dir,
                    self.model_name,
                    self.is_stopped,
                    self.log,
                    self.set_progress
                )
                self.log(f"  ✓ 字幕生成：{srt_path}")
                self.set_progress(50, "语音识别完成")

                with lock:
                    processing_status["srt_path"] = srt_path

                if self.is_stopped():
                    self.log("处理已停止")
                    return

                # 如果是分步模式，先停在这里，不继续烧录
                if self.mode == 'stepbystep':
                    self.log("")
                    self.log("======================================")
                    self.log("字幕生成完成！")
                    self.log("======================================")
                    self.log("")
                    self.log("下一步：")
                    self.log("  1. 可以编辑 SRT 字幕文件")
                    self.log("  2. 点击「保存并烧录」生成最终视频")
                    self.log("")

                    with lock:
                        processing_status["output_files"] = None

                    self.set_progress(100, "字幕生成完成！")
                    return

                # 步骤3: 字幕合成（默认硬字幕）
                self.log("[3/3] 合成字幕...")
                self.set_progress(50, "正在生成硬字幕（默认）...")
                hard_output_path = os.path.join(self.upload_dir, f"{basename}_hard_subs.mp4")

                burn_subtitles_hard(
                    video_path,
                    srt_path,
                    hard_output_path,
                    progress_callback=self.set_progress,
                    log_callback=self.log,
                    stop_callback=self.is_stopped
                )

                if self.is_stopped():
                    self.log("处理已停止")
                    return

                self.set_progress(100, "处理完成！")
                self.log(f"完成！输出文件：{hard_output_path}")

                self.log("")
                self.log("======================================")
                self.log("处理完成！")
                self.log("======================================")
                self.log("")
                self.log(f"生成的文件：")
                self.log(f"  - {srt_path} (原始字幕)")
                self.log(f"  - {hard_output_path} (最终视频-默认硬字幕)")
                self.log("")

                if os.path.exists(hard_output_path):
                    size_mb = os.path.getsize(hard_output_path) / (1024 * 1024)
                    self.log(f"文件大小：{size_mb:.1f} MB")

                with lock:
                    log_file = processing_status.get("log_file")
                    processing_status["output_files"] = [
                        {"name": f"{basename}.srt (原始字幕)", "path": srt_path},
                        {"name": f"{basename}_hard_subs.mp4 (最终视频-默认硬字幕)", "path": hard_output_path}
                    ]
                    if log_file and os.path.exists(log_file):
                        processing_status["output_files"].append({"name": f"{basename}.log (处理日志)", "path": log_file})

            finally:
                shutil.rmtree(temp_dir, ignore_errors=True)

        except InterruptedError as e:
            self.log(f"已停止：{str(e)}")
            self.set_progress(0, "已停止")

        except Exception as e:
            self.log(f"错误：{str(e)}")
            self.set_progress(0, "处理出错")

        finally:
            with lock:
                processing_status["running"] = False
                processing_status["should_stop"] = False


class RenderingThread(threading.Thread):
    def __init__(self, whisper_dir, upload_dir):
        super().__init__()
        self.whisper_dir = whisper_dir
        self.upload_dir = upload_dir

    def is_stopped(self):
        with lock:
            return processing_status.get("should_stop", False)

    def log(self, message):
        with lock:
            processing_status["logs"].append(message)
            append_log_file(message)

    def set_progress(self, value, status):
        with lock:
            processing_status["progress"] = value
            processing_status["status"] = status

    def run(self):
        try:
            with lock:
                video_path = processing_status.get("video_path")
                srt_path = processing_status.get("srt_path")
                basename = processing_status.get("basename")

            if not video_path or not srt_path or not basename:
                self.log("错误：缺少必要信息")
                return

            self.log("======================================")
            self.log("烧录字幕到视频")
            self.log("======================================")
            self.log(f"输入视频：{video_path}")
            self.log(f"字幕文件：{srt_path}")
            self.log("")

            hard_output_path = os.path.join(self.upload_dir, f"{basename}_hard_subs.mp4")

            burn_subtitles_hard(
                video_path,
                srt_path,
                hard_output_path,
                progress_callback=self.set_progress,
                log_callback=self.log,
                stop_callback=self.is_stopped
            )

            if self.is_stopped():
                self.log("处理已停止")
                return

            self.set_progress(100, "处理完成！")
            self.log(f"完成！输出文件：{hard_output_path}")

            self.log("")
            self.log("======================================")
            self.log("处理完成！")
            self.log("======================================")
            self.log("")
            self.log(f"生成的文件：")
            self.log(f"  - {srt_path} (原始字幕)")
            self.log(f"  - {hard_output_path} (最终视频-默认硬字幕)")
            self.log("")

            if os.path.exists(hard_output_path):
                size_mb = os.path.getsize(hard_output_path) / (1024 * 1024)
                self.log(f"文件大小：{size_mb:.1f} MB")

            with lock:
                log_file = processing_status.get("log_file")
                processing_status["output_files"] = [
                    {"name": f"{basename}.srt (原始字幕)", "path": srt_path},
                    {"name": f"{basename}_hard_subs.mp4 (最终视频-默认硬字幕)", "path": hard_output_path}
                ]
                if log_file and os.path.exists(log_file):
                    processing_status["output_files"].append({"name": f"{basename}.log (处理日志)", "path": log_file})

        except InterruptedError as e:
            self.log(f"已停止：{str(e)}")
            self.set_progress(0, "已停止")

        except Exception as e:
            self.log(f"错误：{str(e)}")
            self.set_progress(0, "处理出错")

        finally:
            with lock:
                processing_status["running"] = False
                processing_status["should_stop"] = False


class VideoEditorHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        self.upload_dir = kwargs.pop('upload_dir')
        self.whisper_dir = kwargs.pop('whisper_dir')
        super().__init__(*args, **kwargs)
    
    def log_message(self, format, *args):
        """重写日志方法，忽略连接重置错误"""
        # 忽略常见的网络连接错误
        if "ConnectionResetError" in str(args) or "forcibly closed" in str(args):
            return
        # 其他消息正常输出
        print(f"{self.address_string()} - - [{self.log_date_time_string()}] {format % args}")

    def get_available_models(self):
        """获取可用的模型列表"""
        models = []
        models_dir = os.path.join(self.whisper_dir, 'models')
        
        if os.path.exists(models_dir):
            for file in os.listdir(models_dir):
                if file.endswith('.bin') and file.startswith('ggml-'):
                    # 从文件名提取模型名称，如 ggml-small.bin -> small
                    model_name = file.replace('ggml-', '').replace('.bin', '')
                    models.append({
                        'name': model_name,
                        'file': file
                    })
        
        return models

    def do_GET(self):
        try:
            if self.path == '/':
                self.send_response(200)
                self.send_header('Content-type', 'text/html; charset=utf-8')
                self.end_headers()
                self.wfile.write(HTML_TEMPLATE.encode('utf-8'))
            elif self.path == '/models':
                # 返回可用模型列表
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                models = self.get_available_models()
                self.wfile.write(json.dumps({'models': models}).encode('utf-8'))
            elif self.path == '/gpu':
                # 返回 GPU 信息
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps(gpu_info).encode('utf-8'))
            elif self.path.startswith('/download/'):
                file_path = urllib.parse.unquote(self.path[len('/download/'):])
                if os.path.exists(file_path):
                    self.send_response(200)
                    self.send_header('Content-type', 'application/octet-stream')
                    self.send_header('Content-Disposition', f'attachment; filename="{os.path.basename(file_path)}"')
                    self.end_headers()
                    with open(file_path, 'rb') as f:
                        self.wfile.write(f.read())
                else:
                    self.send_error(404, 'File not found')
            elif self.path == '/status':
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                with lock:
                    self.wfile.write(json.dumps(processing_status).encode('utf-8'))
            else:
                super().do_GET()
        except (ConnectionResetError, BrokenPipeError):
            # 客户端断开连接，忽略此错误，任务会继续在后台运行
            pass
        except Exception as e:
            # 其他错误，记录日志
            self.log_message(f"GET 错误：{e}")

    def do_POST(self):
        try:
            if self.path == '/upload':
                content_type = self.headers.get('Content-Type')
                if content_type and 'multipart/form-data' in content_type:
                    content_length = int(self.headers.get('Content-Length', 0))
                    
                    if content_length > 0:
                        data = self.rfile.read(content_length)
                        
                        boundary = content_type.split('boundary=')[1].encode('utf-8')
                        parts = data.split(b'--' + boundary)
                        
                        filename = None
                        file_content = None
                        mode = 'oneclick'
                        model_name = 'ggml-small.bin'  # 默认模型
                        
                        for part in parts:
                            if b'Content-Disposition: form-data' in part:
                                if b'name="video"' in part:
                                    # 找到 filename
                                    fname_match = part.find(b'filename="')
                                    if fname_match != -1:
                                        fname_start = fname_match + 10
                                        fname_end = part.find(b'"', fname_start)
                                        filename = part[fname_start:fname_end].decode('utf-8')
                                    
                                    # 找到内容开始
                                    header_end = part.find(b'\r\n\r\n')
                                    if header_end != -1:
                                        content_start = header_end + 4
                                        # 从内容开始到结尾，去掉最后的 \r\n
                                        content = part[content_start:]
                                        if content.endswith(b'\r\n'):
                                            content = content[:-2]
                                        file_content = content
                                elif b'name="mode"' in part:
                                    header_end = part.find(b'\r\n\r\n')
                                    if header_end != -1:
                                        content_start = header_end + 4
                                        content = part[content_start:]
                                        if content.endswith(b'\r\n'):
                                            content = content[:-2]
                                        mode = content.decode('utf-8')
                                elif b'name="model"' in part:
                                    header_end = part.find(b'\r\n\r\n')
                                    if header_end != -1:
                                        content_start = header_end + 4
                                        content = part[content_start:]
                                        if content.endswith(b'\r\n'):
                                            content = content[:-2]
                                        model_name = content.decode('utf-8')
                    
                    if filename and file_content:
                        # 先检查是否有任务在运行
                        with lock:
                            if processing_status["running"]:
                                self.send_response(400)
                                self.send_header('Content-type', 'application/json')
                                self.end_headers()
                                self.wfile.write(json.dumps({"success": False, "error": "已有任务正在运行，请先停止或等待完成"}).encode('utf-8'))
                                return
                            
                            # 重置状态
                            processing_status["running"] = True
                            processing_status["progress"] = 0
                            processing_status["status"] = "准备中..."
                            processing_status["logs"] = []
                            processing_status["output_files"] = None
                            processing_status["should_stop"] = False
                            processing_status["srt_path"] = None
                            processing_status["video_path"] = None
                            processing_status["basename"] = None
                            processing_status["log_file"] = None
                        
                        # 清理旧文件
                        for old_file in os.listdir(self.upload_dir):
                            old_path = os.path.join(self.upload_dir, old_file)
                            try:
                                if os.path.isfile(old_path):
                                    os.remove(old_path)
                            except:
                                pass
                        
                        filepath = os.path.join(self.upload_dir, os.path.basename(filename))
                        
                        with open(filepath, 'wb') as f:
                            f.write(file_content)

                        basename = os.path.splitext(os.path.basename(filepath))[0]
                        log_filename = f"{basename}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
                        with lock:
                            processing_status["log_file"] = os.path.join(self.upload_dir, log_filename)
                        
                        thread = VideoProcessingThread(filepath, self.whisper_dir, self.upload_dir, mode, model_name)
                        thread.start()
                        
                        self.send_response(200)
                        self.send_header('Content-type', 'application/json')
                        self.end_headers()
                        self.wfile.write(json.dumps({"success": True}).encode('utf-8'))
                        return
                else:
                    self.send_response(400)
                    self.send_header('Content-type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps({"success": False, "error": "Invalid upload"}).encode('utf-8'))
            elif self.path == '/render':
                with lock:
                    if processing_status["running"]:
                        self.send_response(400)
                        self.send_header('Content-type', 'application/json')
                        self.end_headers()
                        self.wfile.write(json.dumps({"success": False, "error": "已有任务正在运行"}).encode('utf-8'))
                        return
                    
                    processing_status["running"] = True
                    processing_status["progress"] = 0
                    processing_status["status"] = "准备烧录..."
                    processing_status["logs"] = []
                    processing_status["output_files"] = None
                    processing_status["should_stop"] = False
                    basename = processing_status.get("basename") or "render"
                    log_filename = f"{basename}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
                    processing_status["log_file"] = os.path.join(self.upload_dir, log_filename)
                
                thread = RenderingThread(self.whisper_dir, self.upload_dir)
                thread.start()
                
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"success": True}).encode('utf-8'))
            elif self.path == '/save_srt':
                content_length = int(self.headers.get('Content-Length', 0))
                data = self.rfile.read(content_length)
                try:
                    request_data = json.loads(data.decode('utf-8'))
                    content = request_data.get('content', '')
                    
                    with lock:
                        srt_path = processing_status.get("srt_path")
                    
                    if srt_path:
                        with open(srt_path, 'w', encoding='utf-8') as f:
                            f.write(content)
                        
                        self.send_response(200)
                        self.send_header('Content-type', 'application/json')
                        self.end_headers()
                        self.wfile.write(json.dumps({"success": True}).encode('utf-8'))
                    else:
                        self.send_response(400)
                        self.send_header('Content-type', 'application/json')
                        self.end_headers()
                        self.wfile.write(json.dumps({"success": False, "error": "没有找到字幕文件"}).encode('utf-8'))
                except Exception as e:
                    self.send_response(400)
                    self.send_header('Content-type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps({"success": False, "error": str(e)}).encode('utf-8'))
            elif self.path == '/stop':
                with lock:
                    if processing_status["running"]:
                        processing_status["should_stop"] = True
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"success": True}).encode('utf-8'))
        except (ConnectionResetError, BrokenPipeError):
            # 客户端断开连接，忽略此错误，任务会继续在后台运行
            pass
        except Exception as e:
            # 其他错误，记录日志
            self.log_message(f"POST 错误：{e}")


def get_whisper_dir():
    """获取 Whisper 目录（即脚本所在目录，包含 whisper-cli.exe）"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    return script_dir


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='视频加字幕 - Web 界面')
    parser.add_argument('--port', type=int, default=8000, help='服务器端口 (默认: 8000)')
    args = parser.parse_args()
    
    # 获取脚本所在目录
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 上传目录放在脚本所在目录下的 uploads 文件夹
    upload_dir = os.path.join(script_dir, 'uploads')
    os.makedirs(upload_dir, exist_ok=True)
    
    whisper_dir = get_whisper_dir()
    
    print("=" * 50)
    print("视频加字幕 - Web 界面")
    print("=" * 50)
    print(f"上传目录: {upload_dir}")
    print(f"Whisper 目录: {whisper_dir}")
    print()
    print("请在浏览器中打开:")
    print(f"  http://localhost:{args.port}")
    print()
    print("按 Ctrl+C 停止服务器")
    print("=" * 50)
    print()
    
    def handler(*args, **kwargs):
        VideoEditorHandler(*args, upload_dir=upload_dir, whisper_dir=whisper_dir, **kwargs)
    
    with socketserver.TCPServer(("", args.port), handler) as httpd:
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n正在停止服务器...")
            httpd.shutdown()
            shutil.rmtree(upload_dir, ignore_errors=True)
            print("服务器已停止")
        except Exception as e:
            # 处理其他异常（如连接重置）
            if "ConnectionResetError" in str(type(e).__name__) or "forcibly closed" in str(e):
                # 忽略连接重置错误，这是正常的网络行为
                pass
            else:
                print(f"\n服务器错误：{e}")
                httpd.shutdown()
                shutil.rmtree(upload_dir, ignore_errors=True)


if __name__ == '__main__':
    main()
