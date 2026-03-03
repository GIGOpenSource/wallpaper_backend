import os

from NoBad.settings.pro import FONT_DIR, IMAGE_DIR,SIGN_DIR
from PIL import Image, ImageDraw, ImageFont

from tool.tools import logger, uploadFile
from tool.uploader_data import bucket_name
from django.utils.translation import gettext as _

def generate_image(upload_path: str, answer_obj, user_question: str, language: str) -> str:
    """
    生成答案之书拼图并保存到本地（严格按比例布局，保证图片长宽比不变）
    :param upload_path: 上传根路径（FILE_UPLOAD_PATH）
    :param answer_obj: AnswerBook对象（已通过id查询）
    :param user_question: 用户问题
    :return: 本地图片完整路径
    """
    try:
        # 1. 基础配置（保证图片比例不修改）
        bg_path = os.path.join(SIGN_DIR, "answerbook_bg.png")
        font_Ping_path = f"{FONT_DIR}/PingFang.ttc"
        font_Yre_path = f"{FONT_DIR}/YreZsl-Regular.ttf"
        if "zh" not in language:
            font_Yre_path = f"{FONT_DIR}/PingFang.ttc"
        save_dir = os.path.join(IMAGE_DIR)
        os.makedirs(save_dir, exist_ok=True)  # 自动创建目录

        # 2. 打开背景图（严格保留原始尺寸和比例）
        with Image.open(bg_path).convert("RGBA") as an_bg:
            # 关键修复：创建新的透明图层绘制文字，避免背景图层不支持透明叠加
            text_layer = Image.new('RGBA', an_bg.size, (0, 0, 0, 0))
            draw = ImageDraw.Draw(text_layer)
            bg_width, bg_height = an_bg.size
            logger.info(f"背景图原始尺寸：{bg_width}x{bg_height}（比例：{bg_width / bg_height:.4f}）")
            # 核心比例配置（上半部分:下半部分 = 244:460）
            total_split = 244 + 460
            upper_height = (bg_height * 244) / total_split  # 上半部分高度
            line_y = upper_height  # 分割线y坐标（上下部分分界处）
            # 字体配置（适配背景图尺寸，避免乱码）
            try:
                fontUser = ImageFont.truetype(font_Ping_path, 38)  # 用户问题字体
                fontAnswer = ImageFont.truetype(font_Yre_path, 50)  # 答案字体
            except IOError:
                fontUser = ImageFont.load_default(size=100)
                fontAnswer = ImageFont.load_default(size=100)
                logger.warning("未找到中文字体文件，可能出现中文乱码！")

            # 颜色/线条配置
            text_color = "#664B1F"  # 基础文字颜色（答案不透明，用户问题50%透明）
            line_color = "#7F663E"  # 分割线颜色
            line_width = 3  # 分割线宽度（3px）
            line_padding = 20  # 分割线左右内边距（20px）
            # —— 1. 绘制分割线（3px宽，左右各20px） ——
            line_start = (line_padding, line_y)  # 左偏移20px
            line_end = (bg_width - line_padding, line_y)  # 右偏移20px
            draw.line([line_start, line_end], fill=line_color, width=line_width)

            # —— 2. 绘制用户问题（上半部分中间往下15px，水平居中，50%透明） ——
            # 计算文字居中坐标（兼容不同长度的问题）
            question_bbox = draw.textbbox((0, 0), user_question, font=fontUser)
            question_width = question_bbox[2] - question_bbox[0]
            question_x = (bg_width - question_width) // 2  # 水平居中
            # 垂直位置：上半部分中间位置往下15px
            question_y = (upper_height // 2) + 150
            # 转换颜色为RGBA（50%透明度 = alpha值128，范围0-255）
            r, g, b = tuple(int(text_color.lstrip('#')[i:i + 2], 16) for i in (0, 2, 4))
            user_text_color = (r, g, b, 200)  # 50%透明
            draw.text((question_x, question_y), user_question, font=fontUser, fill=user_text_color)
            # —— 3. 绘制答案内容（距离分割线180px，水平居中，带引号，不透明） ——
            answer_content = '“' + str(answer_obj.content) + '”'

            max_chars_per_line = 12  # 每行最多15个字符，可根据需要调整
            lines = []
            current_line = ""
            for char in answer_content:
                current_line += char
                if len(current_line) >= max_chars_per_line:
                    lines.append(current_line)
                    current_line = ""
            if current_line:  # 添加最后一行
                lines.append(current_line)
            content_start_y = line_y + 180
            line_height = 60  # 行高
            r, g, b = tuple(int(text_color.lstrip('#')[i:i + 2], 16) for i in (0, 2, 4))
            answer_text_color = (r, g, b, 255)
            for i, line in enumerate(lines):
                # 计算每行的居中位置
                content_bbox = draw.textbbox((0, 0), line, font=fontAnswer)
                content_width = content_bbox[2] - content_bbox[0]
                content_x = (bg_width - content_width) // 2
                content_y = content_start_y + i * line_height
                draw.text((content_x, content_y), line, font=fontAnswer, fill=answer_text_color)
            # 关键修复：将文字图层叠加到背景图上（合并RGBA图层）
            combined = Image.alpha_composite(an_bg, text_layer)
            # 3. 保存图片（严格保留原始比例，不修改尺寸）
            local_img_path = os.path.join(save_dir, f"answer_{answer_obj.id}.png")
            # 保存时转换为RGB（避免部分查看器不支持RGBA透明）
            combined.convert("RGB").save(local_img_path, format="PNG")
            logger.info(f"图片生成成功，路径：{local_img_path}（原始比例未修改）")
            # 注释的上传逻辑可保留，按需启用
            with open(local_img_path, "rb") as local_file:
                response = uploadFile(local_img_path, upload_path, bucket_name)
                logger.info("图片上传成功")
            return response


    except Exception as e:
        logger.error(f"拼图生成失败：{str(e)}", exc_info=True)
        raise Exception(f"拼图生成失败：{str(e)}")

def generate_deep_image(upload_path: str, answer_obj, user_question: str, deep_analysis_text,language) -> str:
    """
    生成包含深度解析的答案之书图片并保存/上传
    :param upload_path: 上传根路径（FILE_UPLOAD_PATH）
    :param answer_obj: AnswerBook对象（已通过id查询）
    :param user_question: 用户问题
    :param deep_analysis_text: 深度解析文案
    :return: 上传后的文件路径/URL
    """
    try:

        # 1. 基础配置
        bg_path = os.path.join(SIGN_DIR, "answerbook_bg.png")
        # 字体路径（严格按要求指定）
        font_Yre_path = f"{FONT_DIR}/YreZsl-Regular.ttf"  # answer.content 字体
        if "zh" not in language:
            font_Yre_path = f"{FONT_DIR}/PingFang.ttc"
        font_PingSc_path = f"{FONT_DIR}/PingFangSc.ttc"  # Ai分析 字体
        font_Ping_path = f"{FONT_DIR}/PingFang.ttc"  # summary 字体

        save_dir = os.path.join(IMAGE_DIR)
        os.makedirs(save_dir, exist_ok=True)

        # 2. 打开背景图并创建绘制图层
        with Image.open(bg_path).convert("RGBA") as an_bg:
            text_layer = Image.new('RGBA', an_bg.size, (0, 0, 0, 0))
            draw = ImageDraw.Draw(text_layer)
            bg_width, bg_height = an_bg.size
            logger.info(f"背景图尺寸：{bg_width}x{bg_height}")

            # 核心比例：分割线按103:601定位
            total_split = 103 + 601
            original_line_y = (bg_height * 103) / total_split
            line_padding = 20  # 分割线距离两端20px
            text_padding = 32  # 文字内容距离两端32px

            # 字体大小（统一38号，按要求）
            font_size = 38

            # 加载指定字体（兼容IO错误）
            def load_specified_font(font_path, size):
                try:
                    return ImageFont.truetype(font_path, size)
                except IOError:
                    logger.warning(f"未找到字体 {font_path}，使用默认字体")
                    return ImageFont.load_default(size=size)

            # 加载各部分指定字体
            font_answer = load_specified_font(font_Yre_path, font_size)  # answer.content 字体
            font_ai_title = load_specified_font(font_PingSc_path, font_size)  # Ai分析 字体
            font_summary = load_specified_font(font_Ping_path, font_size)  # summary 字体

            # 颜色配置
            text_color = "#332211"  # answer颜色
            analysis_title_color = "#554433"  # Ai分析标题颜色
            summary_color = "#554433"  # summary颜色
            line_color = "#7F663E"  # 分割线颜色
            line_width = 3  # 分割线宽度3px

            # —— 1. 绘制answer.content（上半部分，距顶部150px，水平居中，文字距离两端32px） ——
            answer_content = str(answer_obj.content)
            max_answer_width = bg_width - 3 * text_padding
            answer_lines = []
            current_line = ""
            for char in answer_content:
                test_bbox = draw.textbbox((0, 0), current_line + char, font=font_answer)
                test_width = test_bbox[2] - test_bbox[0]
                if test_width > max_answer_width:
                    if current_line:  # 如果当前行已有内容，先保存
                        answer_lines.append(current_line)
                    current_line = char  # 开新行
                else:
                    current_line += char
            if current_line:  # 添加最后一行
                answer_lines.append(current_line)
            # 绘制多行answer内容
            answer_y = 100  # 起始y坐标
            line_spacing = 46  # 行间距
            for i, line in enumerate(answer_lines):
                answer_bbox = draw.textbbox((0, 0), line, font=font_answer)
                answer_x = (bg_width - (answer_bbox[2] - answer_bbox[0])) // 2
                draw.text((answer_x, answer_y + i * line_spacing), line, font=font_answer, fill=text_color)
            # 计算answer占用的总高度，用于确定下方内容起始位置
            answer_total_height = len(answer_lines) * line_spacing

            if len(answer_lines) > 1:
                # 如果有多行内容，则使用answer内容下方的位置
                line_y = answer_y + answer_total_height + 30
            else:
                # 如果只有一行内容，则使用原始比例定位
                line_y = original_line_y
            # —— 2. 绘制分割线（距离两端20px，宽度3px） ——
            draw.line([(line_padding, line_y), (bg_width - line_padding, line_y)],
                      fill=line_color, width=line_width)

            # —— 3. 绘制Ai分析 + summary（下半部分，左对齐，文字距离两端32px） ——
            # 3.1 Ai分析标题（左对齐，分割线下方20px，左侧留边=text_padding）
            ai_title = _("Ai分析：")
            title_x = text_padding  # 文字距离左端32px
            # title_y = line_y + 50
            title_y = line_y + 30
            draw.text((title_x, title_y), ai_title, font=font_ai_title, fill=analysis_title_color)

            # 3.2 处理summary换行（左对齐，最大宽度=背景宽度-2*text_padding）
            summary_text = deep_analysis_text["summary"]
            max_summary_width = bg_width - 2 * text_padding  # 文字距离两端32px
            summary_lines = []
            current_line = ""

            for char in summary_text:
                test_bbox = draw.textbbox((0, 0), current_line + char, font=font_summary)
                test_width = test_bbox[2] - test_bbox[0]
                if test_width > max_summary_width:
                    summary_lines.append(current_line)
                    current_line = char
                else:
                    current_line += char
            if current_line:
                summary_lines.append(current_line)

            # 3.3 绘制换行后的summary（左对齐，Ai分析标题下方30px，行间距+2px=44px）
            summary_y = title_y + 100  # Ai分析与文字距离30px
            line_spacing = 42 + 2  # 原行间距42px +2px
            for line in summary_lines:
                draw.text((title_x, summary_y), line, font=font_summary, fill=summary_color)
                summary_y += line_spacing

            # 合并图层并保存
            combined = Image.alpha_composite(an_bg, text_layer)
            local_img_path = os.path.join(save_dir, f"answer_deep_analysis_{answer_obj.id}.png")
            combined.convert("RGB").save(local_img_path, format="PNG")
            logger.info(f"深度解析图片生成成功：{local_img_path}")
            # 4. 上传图片（复用原有上传逻辑）
            with open(local_img_path, "rb") as local_file:
                logger.info(f"深度解析图片生成成功：{local_img_path}")
                upload_response = uploadFile(local_img_path, upload_path, bucket_name)
                logger.info("深度解析图片上传成功")
            return upload_response
    except Exception as e:
        raise Exception(f"深度解析图片生成失败：{str(e)}")
