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

# 常用繁体转简体映射表（精简版）

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


def extract_audio(video_path, audio_path):
    """从视频中提取音频"""
    cmd = [
        'ffmpeg', '-i', video_path,
        '-vn', '-acodec', 'pcm_s16le', '-ar', '16000', '-ac', '1',
        '-y', audio_path
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"FFmpeg stdout: {result.stdout}")
        print(f"FFmpeg stderr: {result.stderr}")
        raise Exception(f"FFmpeg 错误: {result.stderr}")
    return audio_path


def run_whisper(audio_path, output_dir, basename, whisper_dir, model_name='ggml-small.bin'):
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
    subprocess.run(cmd, check=True, capture_output=True)
    
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


def burn_subtitles(video_path, srt_path, output_path, font_path=None, progress_callback=None, log_callback=None):
    """烧录字幕到视频（包含音频）"""
    if font_path is None:
        font_path = find_chinese_font()
        if not font_path:
            if log_callback:
                log_callback("警告：未找到中文字体，将使用默认字体")
            else:
                print("警告：未找到中文字体，将使用默认字体")
    
    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    
    # 根据视频尺寸智能调整字体大小
    # 竖屏视频（高度大于宽度）通常需要更小的字体
    if height > width:
        font_size = max(28, int(width * 0.05))  # 竖屏：视频宽度的 5%，最小 28
    else:
        font_size = max(36, int(width * 0.04))  # 横屏：视频宽度的 4%，最小 36
    
    # 边距也根据视频尺寸调整
    margin = int(width * 0.08)  # 左右边距：视频宽度的 8%
    bottom_margin = int(height * 0.06)  # 底边距：视频高度的 6%
    
    if log_callback:
        log_callback(f"视频信息：{width}x{height}, {fps}fps, {total_frames}帧")
        log_callback(f"使用字体：{font_path}")
        log_callback(f"字体大小：{font_size}px")
    else:
        print(f"视频信息：{width}x{height}, {fps}fps, {total_frames}帧")
        print(f"使用字体：{font_path}")
        print(f"字体大小：{font_size}px")
    
    subtitles = parse_srt(srt_path)
    if log_callback:
        log_callback(f"字幕数量：{len(subtitles)}")
    else:
        print(f"字幕数量：{len(subtitles)}")
    
    # 先生成无音频的临时视频
    temp_video_no_audio = output_path.replace('.mp4', '_no_audio.mp4')
    
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(temp_video_no_audio, fourcc, fps, (width, height))
    
    frame_idx = 0
    sub_idx = 0
    
    if log_callback:
        log_callback("开始烧录字幕...")
    else:
        print("开始烧录字幕...")
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        current_time = frame_idx / fps
        
        while sub_idx < len(subtitles):
            start, end, text = subtitles[sub_idx]
            start_frame = time_to_frame(start, fps)
            end_frame = time_to_frame(end, fps)
            
            if start_frame <= frame_idx < end_frame:
                # 字幕最大宽度 = 视频宽度 - 左右边距
                max_subtitle_width = width - margin * 2
                
                pil_img = render_subtitle(text, font_path, font_size, max_subtitle_width)
                
                img_cv = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGBA2BGRA)
                
                subtitle_width = img_cv.shape[1]
                subtitle_height = img_cv.shape[0]
                
                # 居中显示在底部
                x = (width - subtitle_width) // 2
                y = height - subtitle_height - bottom_margin
                
                # 确保在视频范围内
                x = max(0, min(x, width - subtitle_width))
                y = max(0, min(y, height - subtitle_height))
                
                h, w = img_cv.shape[:2]
                if x + w <= width and y + h <= height and x >= 0 and y >= 0:
                    roi = frame[y:y+h, x:x+w]
                    
                    alpha = img_cv[:, :, 3] / 255.0
                    alpha = np.expand_dims(alpha, axis=2)
                    
                    blended = (1 - alpha) * roi + alpha * img_cv[:, :, :3]
                    frame[y:y+h, x:x+w] = blended.astype(np.uint8)
                
                break
            elif frame_idx >= end_frame:
                sub_idx += 1
            else:
                break
        
        out.write(frame)
        frame_idx += 1
        
        if progress_callback and frame_idx % 10 == 0:
            progress = 50 + int((frame_idx / total_frames) * 40)
            progress_callback(min(progress, 90), f"烧录字幕: {frame_idx}/{total_frames}")
        
        if frame_idx % 100 == 0 and not progress_callback:
            print(f"进度：{frame_idx}/{total_frames} ({frame_idx*100//total_frames}%)")
    
    cap.release()
    out.release()
    
    # 使用 FFmpeg 合并原始音频和字幕视频
    if log_callback:
        log_callback("正在合并音频...")
    else:
        print("正在合并音频...")
    
    if progress_callback:
        progress_callback(95, "正在合并音频...")
    
    merge_cmd = [
        'ffmpeg', '-i', temp_video_no_audio, '-i', video_path,
        '-c:v', 'copy', '-c:a', 'aac', '-map', '0:v:0', '-map', '1:a:0',
        '-y', output_path
    ]
    subprocess.run(merge_cmd, check=True, capture_output=True)
    
    # 删除临时文件
    os.remove(temp_video_no_audio)
    
    if log_callback:
        log_callback(f"完成！输出文件：{output_path}")
    else:
        print(f"完成！输出文件：{output_path}")


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
        
        burn_subtitles(video_path, srt_path, output_path)
        
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
