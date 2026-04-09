#!/usr/bin/env python3
"""
视频字幕编辑器 - 简化版（无拼音）
功能：
1. 从视频中提取音频
2. 使用 Whisper 进行语音识别（生成中文字幕）
3. 繁体转简体
4. 使用 Pillow 渲染字幕（白色字体 + 黑色描边）
5. 烧录字幕到视频

用法：
    python video_subtitle_editor.py <视频文件.mp4>
"""

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import sys
import os
import subprocess
import tempfile
import platform
import threading
import queue

# 常用繁体转简体映射表（精简版）

def detect_gpu():
    """检测GPU支持情况"""
    gpu_info = {
        'cuda_available': False,
        'metal_available': False,
        'opencl_available': False,
        'platform': platform.system()
    }
    
    # 检测CUDA (NVIDIA GPU)
    try:
        result = subprocess.run(
            ['nvidia-smi'], 
            capture_output=True, 
            text=True
        )
        if result.returncode == 0:
            gpu_info['cuda_available'] = True
    except:
        pass
    
    # 检测Metal (Apple Silicon)
    if platform.system() == 'Darwin':
        try:
            result = subprocess.run(
                ['system_profiler', 'SPDisplaysDataType'], 
                capture_output=True, 
                text=True
            )
            if 'Metal' in result.stdout:
                gpu_info['metal_available'] = True
        except:
            pass
    
    # 检测OpenCL (通用GPU)
    try:
        result = subprocess.run(
            ['clinfo'], 
            capture_output=True, 
            text=True
        )
        if result.returncode == 0:
            gpu_info['opencl_available'] = True
    except:
        pass
    
    return gpu_info


gpu_info = detect_gpu()

TRADITIONAL_TO_SIMPLIFIED = {
    '後': '后', '裏': '里', '麼': '么', '纔': '才', '讓': '让',
    '這': '这', '個': '个', '們': '们', '來': '来', '說': '说',
    '時': '时', '爲': '为', '對': '对', '會': '会', '於': '于',
    '與': '与', '學': '学', '習': '习', '愛': '爱', '見': '见',
    '親': '亲', '寫': '写', '書': '书', '車': '车', '東': '东',
    '動': '动', '詞': '词', '語': '语', '頁': '页', '邊': '边',
    '進': '进', '門': '门', '開': '开', '關': '关', '電': '电',
    '話': '话', '視': '视', '頻': '频', '網': '网', '絡': '络',
    '腦': '脑', '鍵': '键', '盤': '盘', '軟': '软', '件': '件',
    '硬': '硬', '體': '体', '遊': '游', '戲': '戏', '樂': '乐',
    '圖': '图', '畫': '画', '顏': '颜', '色': '色', '長': '长',
    '舊': '旧', '兩': '两', '從': '从', '眾': '众', '裡': '里',
    '麼': '么', '樣': '样', '夠': '够', '認': '认', '識': '识',
    '記': '记', '還': '还', '幾': '几', '麼': '么', '麼': '么',
}

def traditional_to_simplified(text):
    """将繁体中文转换为简体中文"""
    result = []
    for char in text:
        result.append(TRADITIONAL_TO_SIMPLIFIED.get(char, char))
    return ''.join(result)


def find_ffmpeg():
    """查找 FFmpeg 可执行文件"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 检查各种可能的路径
    possible_paths = [
        # Release 打包结构（ffmpeg 在当前目录）
        os.path.join(script_dir, 'ffmpeg.exe'),
        os.path.join(script_dir, 'ffmpeg', 'ffmpeg.exe'),
        os.path.join(script_dir, 'ffmpeg', 'bin', 'ffmpeg.exe'),
        # Linux/macOS
        os.path.join(script_dir, 'ffmpeg'),
        os.path.join(script_dir, 'ffmpeg', 'ffmpeg'),
        os.path.join(script_dir, 'ffmpeg', 'bin', 'ffmpeg'),
        # 系统 PATH
        'ffmpeg',
    ]
    
    for path in possible_paths:
        # 不能把目录当成可执行文件（macOS 会报 Permission denied）
        if os.path.isfile(path) and os.access(path, os.X_OK):
            return path
    
    # 尝试使用系统 PATH 中的 ffmpeg
    return 'ffmpeg'


def extract_audio(video_path, audio_path, stop_callback=None, log_callback=None):
    """从视频中提取音频"""
    import time
    
    ffmpeg_path = find_ffmpeg()
    cmd = [
        ffmpeg_path, '-i', video_path,
        '-vn', '-acodec', 'pcm_s16le', '-ar', '16000', '-ac', '1',
        '-y', audio_path
    ]
    
    # 音频提取通常不需要 GPU 加速，这里保持不变
    
    # 记录开始时间
    start_time = time.time()
    
    # 使用 Popen 以便支持停止
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    
    # 等待进程完成，期间定期检查停止标志
    while process.poll() is None:
        if stop_callback and stop_callback():
            process.terminate()
            process.wait()
            raise InterruptedError("音频提取已停止")
        # 短暂等待后再次检查
        time.sleep(0.1)
    
    result_stdout, result_stderr = process.communicate()
    
    # 计算耗时
    elapsed_time = time.time() - start_time
    
    # 输出耗时
    msg = f"音频提取完成，耗时：{elapsed_time:.2f}秒"
    if log_callback:
        log_callback(msg)
    else:
        print(msg)
    
    if process.returncode != 0:
        print(f"FFmpeg stdout: {result_stdout.decode() if result_stdout else ''}")
        print(f"FFmpeg stderr: {result_stderr.decode() if result_stderr else ''}")
        raise Exception(f"FFmpeg 错误：{result_stderr.decode() if result_stderr else ''}")
    return audio_path


def run_whisper(
    audio_path,
    output_dir,
    basename,
    whisper_dir,
    model_name='ggml-small.bin',
    stop_callback=None,
    log_callback=None,
    progress_callback=None
):
    """运行 Whisper 进行语音识别"""
    whisper_bin = None
    
    # 获取当前脚本所在目录（用于 Release 打包结构）
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 检查各种可能的路径（支持不同平台和构建配置）
    possible_paths = [
        # Release 打包结构（whisper-cli.exe 在当前目录）
        os.path.join(script_dir, 'whisper-cli.exe'),
        os.path.join(script_dir, 'main.exe'),
        os.path.join(script_dir, 'whisper-cli'),
        os.path.join(script_dir, 'main'),
        # Windows Release 构建
        os.path.join(whisper_dir, 'build/bin/Release/whisper-cli.exe'),
        os.path.join(whisper_dir, 'build/bin/Release/main.exe'),
        # Linux/macOS 默认构建
        os.path.join(whisper_dir, 'build/bin/whisper-cli'),
        os.path.join(whisper_dir, 'build/bin/main'),
        # 旧版本兼容
        os.path.join(whisper_dir, 'build/Release/whisper-cli.exe'),
        os.path.join(whisper_dir, 'build/Release/main.exe'),
    ]
    
    for path in possible_paths:
        if os.path.exists(path):
            whisper_bin = path
            break
    
    if not whisper_bin:
        raise FileNotFoundError("未找到 whisper.cpp 可执行文件，请确保已正确编译")
    
    # 查找模型文件（支持 Release 打包结构）
    possible_model_paths = [
        # Release 打包结构（models 在当前目录）
        os.path.join(script_dir, 'models', model_name),
        # 标准 whisper.cpp 结构
        os.path.join(whisper_dir, 'models', model_name),
    ]
    
    model_file = None
    for path in possible_model_paths:
        if os.path.exists(path):
            model_file = path
            break
    
    if not model_file:
        raise FileNotFoundError(f"未找到模型文件：{model_name}，请确保模型已下载到 models 目录")
    
    output_prefix = os.path.join(output_dir, basename)
    cmd = [
        whisper_bin,
        '-m', model_file,
        '-f', audio_path,
        '-osrt', '-otxt',
        '-of', output_prefix,
        '-l', 'zh',
        '-t', '8'
    ]
    
    # 添加 GPU 支持
    # 注意：whisper-cli 的 -ng/--no-gpu 是布尔开关，出现即禁用 GPU
    # 因此，GPU 模式下不要传 -ng；CPU 模式才传 -ng
    if gpu_info['cuda_available']:
        # NVIDIA CUDA GPU: 保持默认（不传 -ng）
        if log_callback:
            log_callback("使用 NVIDIA GPU 加速语音识别 (CUDA)")
        else:
            print("使用 NVIDIA GPU 加速语音识别 (CUDA)")
    elif gpu_info['metal_available']:
        # Apple Metal GPU: 保持默认（不传 -ng）
        if log_callback:
            log_callback("使用 Apple Silicon GPU 加速语音识别 (Metal)")
        else:
            print("使用 Apple Silicon GPU 加速语音识别 (Metal)")
    elif gpu_info['opencl_available']:
        # OpenCL GPU: 保持默认（不传 -ng）
        if log_callback:
            log_callback("使用 OpenCL GPU 加速语音识别")
        else:
            print("使用 OpenCL GPU 加速语音识别")
    else:
        # CPU 模式：显式禁用 GPU
        cmd.append('-ng')
        if log_callback:
            log_callback("使用 CPU 进行语音识别")
        else:
            print("使用 CPU 进行语音识别")
    
    # 记录开始时间
    import time
    start_time = time.time()
    
    # 输出执行的命令（用于调试）
    cmd_str = ' '.join(cmd)
    if log_callback:
        log_callback(f"执行命令: {cmd_str}")
    else:
        print(f"执行命令: {cmd_str}")
    
    # 使用 Popen 以便支持停止，并实时读取输出
    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding='utf-8',
        errors='replace',
        bufsize=1
    )

    output_queue = queue.Queue()

    def stream_reader(stream, stream_name):
        try:
            for line in iter(stream.readline, ''):
                line = line.strip()
                if line:
                    output_queue.put((stream_name, line))
        finally:
            stream.close()

    stdout_thread = threading.Thread(target=stream_reader, args=(process.stdout, 'stdout'), daemon=True)
    stderr_thread = threading.Thread(target=stream_reader, args=(process.stderr, 'stderr'), daemon=True)
    stdout_thread.start()
    stderr_thread.start()

    last_heartbeat_time = start_time

    # 等待进程完成，期间定期检查停止标志、回传实时日志、上报心跳进度
    while process.poll() is None:
        if stop_callback and stop_callback():
            process.terminate()
            process.wait()
            raise InterruptedError("语音识别已停止")

        while True:
            try:
                stream_name, line = output_queue.get_nowait()
            except queue.Empty:
                break

            if log_callback:
                log_callback(f"[whisper/{stream_name}] {line}")

        now = time.time()
        if now - last_heartbeat_time >= 2:
            elapsed = int(now - start_time)
            if progress_callback:
                heartbeat_progress = min(48, 20 + elapsed // 2)
                progress_callback(heartbeat_progress, f"语音识别中... 已运行 {elapsed} 秒")
            if log_callback:
                log_callback(f"语音识别进行中... 已运行 {elapsed} 秒")
            last_heartbeat_time = now

        time.sleep(0.1)

    stdout_thread.join(timeout=1)
    stderr_thread.join(timeout=1)

    # 收尾读取队列里的剩余输出
    while True:
        try:
            stream_name, line = output_queue.get_nowait()
        except queue.Empty:
            break
        if log_callback:
            log_callback(f"[whisper/{stream_name}] {line}")
    
    # 计算耗时
    elapsed_time = time.time() - start_time
    
    # 输出耗时
    msg = f"语音识别完成，耗时：{elapsed_time:.2f}秒"
    if log_callback:
        log_callback(msg)
    else:
        print(msg)
    
    if process.returncode != 0:
        raise Exception(f"Whisper 进程退出码异常：{process.returncode}")
    
    srt_file = f"{output_prefix}.srt"
    if os.path.exists(srt_file):
        return srt_file
    else:
        temp_srt = f"{audio_path}.srt"
        if os.path.exists(temp_srt):
            os.rename(temp_srt, srt_file)
            return srt_file
        raise FileNotFoundError("Whisper 未生成 SRT 文件")


def parse_srt(srt_file):
    """解析 SRT 文件（并进行繁简转换）"""
    subtitles = []
    
    with open(srt_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    blocks = content.strip().split('\n\n')
    
    for block in blocks:
        lines = block.strip().split('\n')
        if len(lines) >= 3:
            idx_line = lines[0]
            time_line = lines[1]
            text_lines = lines[2:]
            
            if ' --> ' in time_line:
                start_time, end_time = time_line.split(' --> ')
                text = '\n'.join(text_lines)
                text = text.strip()
                
                if text:
                    text = traditional_to_simplified(text)
                    subtitles.append((start_time, end_time, text))
    
    return subtitles


def time_to_frame(time_str, fps):
    """将时间字符串转换为帧号"""
    time_str = time_str.replace(',', '.')
    parts = time_str.split(':')
    hours = int(parts[0])
    minutes = int(parts[1])
    seconds = float(parts[2])
    
    total_seconds = hours * 3600 + minutes * 60 + seconds
    return int(total_seconds * fps)


def srt_time_to_seconds(time_str):
    """SRT 时间转秒"""
    time_str = time_str.replace(',', '.')
    h, m, s = time_str.split(':')
    return int(h) * 3600 + int(m) * 60 + float(s)


def seconds_to_ass_time(seconds_value):
    """秒转 ASS 时间（H:MM:SS.cc）"""
    if seconds_value < 0:
        seconds_value = 0
    hours = int(seconds_value // 3600)
    minutes = int((seconds_value % 3600) // 60)
    seconds = seconds_value % 60
    centis = int(round((seconds - int(seconds)) * 100))
    whole_seconds = int(seconds)
    if centis >= 100:
        centis -= 100
        whole_seconds += 1
    if whole_seconds >= 60:
        whole_seconds -= 60
        minutes += 1
    if minutes >= 60:
        minutes -= 60
        hours += 1
    return f"{hours}:{minutes:02d}:{whole_seconds:02d}.{centis:02d}"


def draw_text_with_outline(draw, position, text, font, fill_color, outline_color, outline_width=2):
    """绘制带描边的文本"""
    x, y = position
    for dx in range(-outline_width, outline_width + 1):
        for dy in range(-outline_width, outline_width + 1):
            if dx != 0 or dy != 0:
                draw.text((x + dx, y + dy), text, font=font, fill=outline_color)
    draw.text((x, y), text, font=font, fill=fill_color)


def wrap_text(text, font, max_width, draw):
    """自动换行文本"""
    words = list(text)
    lines = []
    current_line = ""
    
    for char in words:
        test_line = current_line + char
        bbox = draw.textbbox((0, 0), test_line, font=font)
        line_width = bbox[2] - bbox[0]
        
        if line_width > max_width and current_line:
            lines.append(current_line)
            current_line = char
        else:
            current_line = test_line
    
    if current_line:
        lines.append(current_line)
    
    return lines

def render_subtitle(text, font_path, font_size, max_width):
    """
    渲染字幕
    白色字体带黑色描边，支持自动换行
    """
    lines = text.split('\n')
    lines = [line.strip() for line in lines if line.strip()]
    
    try:
        font = ImageFont.truetype(font_path, font_size)
    except:
        font = ImageFont.load_default()
    
    temp_img = Image.new('RGBA', (max_width, 300), (0, 0, 0, 0))
    temp_draw = ImageDraw.Draw(temp_img)
    
    # 自动换行处理
    wrapped_lines = []
    available_width = max_width - 80  # 留出边距
    
    for line in lines:
        bbox = temp_draw.textbbox((0, 0), line, font=font)
        line_width = bbox[2] - bbox[0]
        
        if line_width > available_width:
            # 需要换行
            wrapped = wrap_text(line, font, available_width, temp_draw)
            wrapped_lines.extend(wrapped)
        else:
            wrapped_lines.append(line)
    
    # 计算尺寸
    max_line_width = 0
    total_height = 10
    
    for line in wrapped_lines:
        bbox = temp_draw.textbbox((0, 0), line, font=font)
        line_width = bbox[2] - bbox[0]
        if line_width > max_line_width:
            max_line_width = line_width
        total_height += font_size + 5
    
    total_height += 10
    
    actual_width = min(int(max_line_width) + 40, max_width)
    
    img = Image.new('RGBA', (actual_width, int(total_height)), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    y = 10
    for line in wrapped_lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        line_width = bbox[2] - bbox[0]
        x = (actual_width - line_width) // 2
        draw_text_with_outline(draw, (x, y), line, font,
                               (255, 255, 255, 255), (0, 0, 0, 255), 3)
        y += font_size + 5
    
    return img


def find_chinese_font():
    """查找系统中的中文字体（支持 Windows 和 macOS）"""
    import platform
    system = platform.system()
    
    if system == "Windows":
        font_paths = [
            "C:\\Windows\\Fonts\\msyh.ttc",      # 微软雅黑
            "C:\\Windows\\Fonts\\simhei.ttf",    # 黑体
            "C:\\Windows\\Fonts\\simsun.ttc",    # 宋体
            "C:\\Windows\\Fonts\\simkai.ttf",    # 楷体
        ]
    elif system == "Darwin":  # macOS
        font_paths = [
            "/System/Library/Fonts/STHeiti Light.ttc",
            "/System/Library/Fonts/STHeiti Medium.ttc",
            "/System/Library/Fonts/PingFang.ttc",
            "/System/Library/Fonts/Heiti.ttc",
            "/System/Library/Fonts/Helvetica.ttc",
        ]
    else:  # Linux
        font_paths = [
            "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
            "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        ]
    
    for fp in font_paths:
        if os.path.exists(fp):
            return fp
    return None


def burn_subtitles(video_path, srt_path, output_path, font_path=None, progress_callback=None, log_callback=None, stop_callback=None):
    """Create soft-subtitle output (stable mode)."""
    import time

    start_time = time.time()
    ffmpeg_path = find_ffmpeg()
    if progress_callback:
        progress_callback(50, "正在封装软字幕...")

    cmd = [
        ffmpeg_path, '-hide_banner', '-loglevel', 'error',
        '-i', video_path, '-i', srt_path,
        '-map', '0:v:0', '-map', '0:a?', '-map', '1:0',
        '-c:v', 'copy', '-c:a', 'copy', '-c:s', 'mov_text',
        '-metadata:s:s:0', 'language=chi',
        '-movflags', '+faststart',
        '-y', output_path
    ]
    if log_callback:
        log_callback("模式：软字幕（稳定优先，视频/音频均 copy）")
        log_callback(f"执行命令: {' '.join(cmd)}")

    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    while process.poll() is None:
        if stop_callback and stop_callback():
            process.terminate()
            process.wait()
            raise InterruptedError("字幕封装已停止")
        time.sleep(0.1)
    out, err = process.communicate()
    if process.returncode != 0:
        raise Exception(f"FFmpeg 软字幕封装失败：{err or out}")

    if progress_callback:
        progress_callback(90, "软字幕封装完成")
    elapsed_time = time.time() - start_time
    if log_callback:
        log_callback(f"软字幕完成，耗时：{elapsed_time:.2f}秒")


def burn_subtitles_hard(video_path, srt_path, output_path, progress_callback=None, log_callback=None, stop_callback=None):
    """Create hard-subtitle output (optional mode)."""
    import time

    start_time = time.time()
    ffmpeg_path = find_ffmpeg()
    if progress_callback:
        progress_callback(92, "正在生成硬字幕...")

    cap = cv2.VideoCapture(video_path)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    cap.release()
    if width <= 0 or height <= 0:
        width, height = 1920, 1080

    # 字号按视频宽度自适应：解决高分辨率/宽屏下字幕偏小问题
    if height > width:
        # 竖屏适度放大，避免遮挡主体
        font_size = max(26, min(52, int(width * 0.050)))
    else:
        # 横屏随宽度增长
        font_size = max(30, min(64, int(width * 0.038)))
    margin_v = max(18, int(height * 0.050))
    outline = 1
    system_name = platform.system()
    if system_name == "Windows":
        ass_font_name = "Microsoft YaHei"
    elif system_name == "Darwin":
        ass_font_name = "PingFang SC"
    else:
        ass_font_name = "Noto Sans CJK SC"

    parsed = parse_srt(srt_path)
    if not parsed:
        raise Exception("SRT 解析后无有效字幕，无法烧录硬字幕")

    temp_ass = None
    try:
        min_duration = 0.12
        with tempfile.NamedTemporaryFile(delete=False, suffix='.ass', mode='w', encoding='utf-8') as tf:
            temp_ass = tf.name
            tf.write("[Script Info]\n")
            tf.write("ScriptType: v4.00+\n")
            tf.write("WrapStyle: 2\n")
            tf.write(f"PlayResX: {width}\n")
            tf.write(f"PlayResY: {height}\n")
            tf.write("\n[V4+ Styles]\n")
            tf.write("Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, "
                     "Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, "
                     "Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n")
            tf.write(
                f"Style: Default,{ass_font_name},{font_size},&H00FFFFFF,&H000000FF,&H00000000,&H64000000,"
                f"0,0,0,0,100,100,0,0,1,{outline},0,2,20,20,{margin_v},1\n"
            )
            tf.write("\n[Events]\n")
            tf.write("Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n")
            for start, end, text in parsed:
                start_s = srt_time_to_seconds(start)
                end_s = srt_time_to_seconds(end)
                if end_s <= start_s:
                    end_s = start_s + min_duration
                elif end_s - start_s < min_duration:
                    end_s = start_s + min_duration
                ass_text = text.replace('\\', r'\\').replace('{', r'\{').replace('}', r'\}').replace('\n', r'\N')
                tf.write(
                    f"Dialogue: 0,{seconds_to_ass_time(start_s)},{seconds_to_ass_time(end_s)},Default,,0,0,0,,{ass_text}\n"
                )

        sub_path = os.path.abspath(temp_ass).replace('\\', '/')
        # ffmpeg filter 参数需要转义冒号
        if len(sub_path) >= 2 and sub_path[1] == ':':
            sub_path = sub_path[0] + '\\:' + sub_path[2:]
        if system_name == 'Windows':
            vf_filter = f"ass=filename={sub_path}:fontsdir=C\\:/Windows/Fonts"
        else:
            vf_filter = f"ass=filename={sub_path}"

        if system_name == "Darwin":
            # macOS 使用 VideoToolbox 硬件编码，显著提升速度
            video_encode_args = ['-c:v', 'h264_videotoolbox', '-b:v', '8M', '-maxrate', '12M', '-bufsize', '24M']
        else:
            video_encode_args = ['-c:v', 'libx264', '-preset', 'medium', '-crf', '20']

        cmd = [
            ffmpeg_path, '-hide_banner', '-loglevel', 'error',
            '-i', video_path,
            '-vf', vf_filter,
            *video_encode_args,
            '-c:a', 'copy',
            '-fps_mode', 'passthrough',
            '-movflags', '+faststart',
            '-y', output_path
        ]
        if log_callback:
            log_callback("模式：硬字幕（默认）")
            if system_name == "Darwin":
                log_callback("编码器：h264_videotoolbox（macOS 硬件加速）")
            else:
                log_callback("编码器：libx264（CPU）")
            log_callback(f"硬字幕样式：Font={ass_font_name}, FontSize={font_size}, Outline={outline}, MarginV={margin_v}")
            log_callback(f"执行命令: {' '.join(cmd)}")

        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        while process.poll() is None:
            if stop_callback and stop_callback():
                process.terminate()
                process.wait()
                raise InterruptedError("硬字幕生成已停止")
            time.sleep(0.1)
        out, err = process.communicate()
        if process.returncode != 0:
            raise Exception(f"FFmpeg 硬字幕生成失败：{err or out}")
    finally:
        if temp_ass and os.path.exists(temp_ass):
            try:
                os.remove(temp_ass)
            except OSError:
                pass

    elapsed_time = time.time() - start_time
    if log_callback:
        log_callback(f"硬字幕完成，耗时：{elapsed_time:.2f}秒")


def main():
    if len(sys.argv) < 2:
        print("用法：python video_subtitle_editor.py <视频文件.mp4>")
        sys.exit(1)
    
    video_path = sys.argv[1]
    if not os.path.exists(video_path):
        print(f"错误：文件不存在：{video_path}")
        sys.exit(1)
    
    basename = os.path.splitext(os.path.basename(video_path))[0]
    dirname = os.path.dirname(video_path)
    
    script_dir = os.path.dirname(os.path.abspath(__file__))
    whisper_dir = os.environ.get('WHISPER_DIR', os.path.join(script_dir, 'whisper.cpp'))
    
    if not os.path.exists(whisper_dir):
        import platform
        if platform.system() == "Darwin":
            whisper_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'whisper.cpp')
        elif platform.system() == "Windows":
            whisper_dir = os.path.join(os.path.dirname(script_dir), 'whisper.cpp')
    
    print("======================================")
    print("视频字幕编辑器")
    print("======================================")
    print(f"输入视频：{video_path}")
    print()
    
    temp_dir = tempfile.mkdtemp()
    try:
        audio_path = os.path.join(temp_dir, f"{basename}_audio.wav")
        
        print("[1/3] 提取音频...")
        extract_audio(video_path, audio_path)
        print("  ✓ 音频提取完成")
        
        print("[2/3] 语音识别（Whisper）...")
        srt_path = run_whisper(audio_path, dirname, basename, whisper_dir)
        print(f"  ✓ 字幕生成：{srt_path}")
        
        print("[3/3] 渲染字幕...")
        output_path = os.path.join(dirname, f"{basename}_with_subtitles.mp4")
        
        burn_subtitles_hard(video_path, srt_path, output_path)
        
        print()
        print("======================================")
        print("处理完成！")
        print("======================================")
        print()
        print(f"生成的文件：")
        print(f"  - {srt_path} (原始字幕)")
        print(f"  - {output_path} (最终视频)")
        print()
        
        if os.path.exists(output_path):
            size_mb = os.path.getsize(output_path) / (1024 * 1024)
            print(f"文件大小：{size_mb:.1f} MB")
        
    finally:
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == '__main__':
    main()


