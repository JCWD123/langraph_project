import uuid
from dotenv import load_dotenv
from langchain_core.messages import AIMessage, HumanMessage
from graph.graph import create_graph, stream_graph_updates
from graph.state import plan_state
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.colors import HexColor, blue, red, green, black, white
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from langchain_core.globals import set_debug
from datetime import datetime
import pandas as pd
import os
import sys
import re
from suppliers_config import DEFAULT_SUPPLIERS, QUERY_TEMPLATE

def register_chinese_font():
    """注册中文字体"""
    try:
        # 尝试注册系统中的中文字体
        font_paths = [
            '/System/Library/Fonts/STHeiti Light.ttc',  # macOS
            '/System/Library/Fonts/Helvetica.ttc'     # macOS备选
        ]
        
        for font_path in font_paths:
            if os.path.exists(font_path):
                pdfmetrics.registerFont(TTFont('ChineseFont', font_path))
                return True
    except:
        pass
    return False

def clean_content(content):
    """增强版内容清洗，去除调试信息和格式化问题"""
    if not isinstance(content, str):
        content = str(content)
    
    # 去除steps等调试信息
    content = re.sub(r'"steps":\s*\[.*?\]', '', content, flags=re.DOTALL)
    content = re.sub(r'\{[^}]*"steps"[^}]*\}', '', content, flags=re.DOTALL)
    content = re.sub(r'{"steps"[^}]*}', '', content, flags=re.DOTALL)
    
    # 去除HTML标签和链接片段  
    content = re.sub(r'<[^>]+>', '', content)
    content = re.sub(r'\[!\[Image \d+\].*?\]', '', content)
    # content = re.sub(r'https?://[^\s\]]+', '', content)
    
    # 清理乱码字符（UTF-8编码问题导致的乱码）
    content = re.sub(r'[å ¬å¸æ¥æå½å ä¸æµçå¶é åºå°ä¸ç åå¹³å°ï¼ä¸ä¸çææ¯éä¼ï¼å®åçå·¥ç¨é¡¹ç®åå¯ãçåãè®¾è®¡ãæ½å·¥ãè°è¯ãç»´æ¤ç®¡çä¸ºä¸ä½çæ¶æä½ç³»ï¼å»ºè®¾æå æ¬å¨ææ¨¡æå®éªå°æ¶ãåç¦»æ§è½æµè¯å¹³å°ãåå¨æºè¯éªå°æ¶å¨å çåè¿å·¥èºè®¾å¤ï¼é ç½®æå®åçæ£æµãåæä»ªå¨åFLUENTãASPENãANSYSä»¥åSOLIDWORKSçåè¿çåæãæ¨¡æãä»¿çãä¸ç»´è®¾è®¡è½¯ä»¶ï¼å¹¶å¨é¿æççäº§å®è·µä¸æ»ç»åºäºä¸å¥ç§å]+', '', content)
    
    # 清理其他类型的乱码和无意义字符
    content = re.sub(r'[+克+免+児+兑+兔+兖+党+兜+兢+入+全+八+公+六+兮+兰+共+关+兴+兵+其+具+典+兹]+', '', content)
    content = re.sub(r'9\.78\d+E\+\d+', '', content)  # 去除科学计数法的无意义数字
    content = re.sub(r'ISBN[\s\d\-]+', '', content)  # 去除ISBN号
    content = re.sub(r'\$\d+,\d+\.\d+', '', content)  # 去除美元金额
    
    # 清理错误的引用格式和列表
    content = re.sub(r'\[".*?"\]', '', content, flags=re.DOTALL)
    content = re.sub(r'\[.*?\.\.\.\]', '', content, flags=re.DOTALL)
    
    # 清理无标点的长文本（如"学指三菱化学株式会社天赐材料指..."）
    def fix_company_definitions(text):
        """修复公司名称定义文本的格式"""
        # 识别"A指B公司"的模式并添加标点
        text = re.sub(r'([^。，；,;.]\w+)指([^指]{10,}?)([指])', r'\1指\2。\3', text)
        text = re.sub(r'([^。，；,;.]\w+)指([^指。]{15,}?)([A-Z])', r'\1指\2。\3', text)
        return text
    
    content = fix_company_definitions(content)
    
    # 清理过长的无标点段落（超过100字符且无标点）
    lines = content.split('\n')
    cleaned_lines = []
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        # 检查是否是无标点的超长文本
        if len(line) > 100:
            # 计算标点符号比例
            punctuation_count = len(re.findall(r'[。，；,;.!?]', line))
            char_count = len(line)
            punctuation_ratio = punctuation_count / char_count if char_count > 0 else 0
            
            # 如果标点符号比例小于1%，认为是无意义的长文本
            if punctuation_ratio < 0.01:
                continue  # 跳过这种无标点的长文本
                
        # 检查是否包含大量重复的订单信息
        if ('订单编号' in line and len(line) > 200) or ('合同金额' in line and len(line) > 200):
            continue  # 跳过表格式的订单信息
            
        # 检查是否是乱码行（包含大量特殊字符）
        special_char_count = len(re.findall(r'[ï¼ãåæ]', line))
        if special_char_count > len(line) * 0.3:  # 如果特殊字符超过30%
            continue
            
        cleaned_lines.append(line)
    
    content = '\n'.join(cleaned_lines)
    
    # 清理多余的符号和空行
    content = re.sub(r'\*\s*\*', '', content)
    content = re.sub(r'\.{3,}', '...', content)  # 标准化省略号
    content = re.sub(r'\n\s*\n\s*\n+', '\n\n', content)  # 合并多个空行
    content = re.sub(r'^\s*[\*\-\+]\s*$', '', content, flags=re.MULTILINE)
    
    # 智能添加段落分隔
    content = re.sub(r'([。！？])\s*([A-Z])', r'\1\n\2', content)  # 中文句号后跟英文字母的换行
    content = re.sub(r'([a-zA-Z])\s*([（一二三四五六七八九十])', r'\1\n\2', content)  # 英文后跟中文编号的换行
    content = re.sub(r'([。！？])\s*([（一二三四五六七八九十])', r'\1\n\n\2', content)  # 中文句号后跟编号增加空行
    
    return content.strip()

def extract_references(content):
    """提取内容中的链接引用"""
    if not isinstance(content, str):
        content = str(content)
        
    # 提取所有URL链接
    urls = re.findall(r'https?://[^\s\]]+', content)
    
    # 去重并按域名分类
    unique_urls = list(set(urls))
    
    # 简单的重要性排序（可根据需要调整）
    priority_domains = ['official', 'gov', 'edu', 'org', 'com']
    sorted_urls = []
    
    for domain in priority_domains:
        domain_urls = [url for url in unique_urls if domain in url.lower()]
        sorted_urls.extend(domain_urls)
    
    # 添加剩余的URL
    remaining_urls = [url for url in unique_urls if url not in sorted_urls]
    sorted_urls.extend(remaining_urls)
    
    return sorted_urls[:10]  # 最多保留10个链接

def create_enhanced_styles():
    """创建增强的PDF样式"""
    styles = getSampleStyleSheet()
    font_registered = register_chinese_font()
    font_name = 'ChineseFont' if font_registered else 'Helvetica'
    
    # 标题样式（加粗+颜色）
    title_style = ParagraphStyle(
        'EnhancedTitle',
        parent=styles['Title'],
        fontName=font_name,
        fontSize=20,
        textColor=HexColor('#2E4057'),
        spaceAfter=24,
        spaceBefore=12,
        alignment=1,  # 居中
    )
    
    # 主标题样式
    heading1_style = ParagraphStyle(
        'EnhancedHeading1',
        parent=styles['Heading1'],
        fontName=font_name,
        fontSize=16,
        textColor=HexColor('#1B4F72'),
        spaceAfter=12,
        spaceBefore=18,
        leftIndent=0,
    )
    
    # 二级标题样式
    heading2_style = ParagraphStyle(
        'EnhancedHeading2',
        parent=styles['Heading2'],
        fontName=font_name,
        fontSize=14,
        textColor=HexColor('#2874A6'),
        spaceAfter=8,
        spaceBefore=12,
        leftIndent=12,
    )
    
    # 编号段落样式
    numbered_style = ParagraphStyle(
        'NumberedSection',
        parent=styles['Normal'],
        fontName=font_name,
        fontSize=12,
        textColor=HexColor('#1B4F72'),
        spaceAfter=10,
        spaceBefore=10,
        leftIndent=0,
        firstLineIndent=0,
        leading=18,
    )
    
    # 正文样式（首行缩进）
    body_style = ParagraphStyle(
        'EnhancedBody',
        parent=styles['Normal'],
        fontName=font_name,
        fontSize=11,
        spaceAfter=6,
        spaceBefore=3,
        leftIndent=12,
        firstLineIndent=24,  # 首行缩进
        leading=16,
    )
    
    # 高亮框样式
    highlight_style = ParagraphStyle(
        'HighlightBox',
        parent=styles['Normal'],
        fontName=font_name,
        fontSize=10,
        textColor=HexColor('#D35400'),
        backColor=HexColor('#FEF9E7'),
        borderColor=HexColor('#F39C12'),
        borderWidth=1,
        spaceAfter=6,
        spaceBefore=3,
        leftIndent=24,
        rightIndent=24,
        borderPadding=8,
    )
    
    # 链接样式
    link_style = ParagraphStyle(
        'LinkStyle',
        parent=styles['Normal'],
        fontName=font_name,
        fontSize=9,
        textColor=blue,
        spaceAfter=3,
        leftIndent=24,
    )
    
    return {
        'title': title_style,
        'heading1': heading1_style,
        'heading2': heading2_style,
        'body': body_style,
        'highlight': highlight_style,
        'link': link_style,
        'numbered': numbered_style
    }

def process_content_for_pdf(content):
    """处理内容，识别并格式化不同类型的文本"""
    if not isinstance(content, str):
        content = str(content)
        
    lines = content.split('\n')
    processed_elements = []
    
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if not line:
            i += 1
            continue
            
        # 识别Markdown表格
        if '|' in line and line.count('|') >= 2:
            table_data, table_end_index = extract_table_from_lines(lines, i)
            if table_data:
                processed_elements.append(('table', table_data))
                i = table_end_index + 1
                continue
        
        # 识别编号段落（一）（二）等
        if re.match(r'^[（(][一二三四五六七八九十\d+][）)]', line):
            processed_elements.append(('numbered', line))
            i += 1
            continue
            
        # 识别标题级别
        if line.startswith('## '):
            processed_elements.append(('heading1', line[3:]))
            i += 1
            continue
        elif line.startswith('### '):
            processed_elements.append(('heading2', line[4:]))
            i += 1
            continue
            
        # 识别加粗重点内容
        if line.startswith('**') and line.endswith('**'):
            processed_elements.append(('highlight', line[2:-2]))
            i += 1
            continue
            
        # 识别列表项
        if line.startswith('- ') or line.startswith('* '):
            processed_elements.append(('body', f"• {line[2:]}"))
            i += 1
            continue
            
        # 识别包含关键词的内容进行高亮
        highlight_keywords = ['重要', '关键', '核心', '主要', '数据', '技术参数', '性能指标', '专利', '创新']
        if any(keyword in line for keyword in highlight_keywords):
            processed_elements.append(('highlight', line))
            i += 1
            continue
            
        # 过滤掉过短或无意义的行
        if len(line) < 3 or line.count('...') > len(line) // 4:
            i += 1
            continue
            
        # 普通正文
        processed_elements.append(('body', line))
        i += 1
    
    return processed_elements

def extract_table_from_lines(lines, start_index):
    """从文本行中提取表格数据"""
    table_data = []
    current_index = start_index
    
    # 查找表格的开始和结束
    while current_index < len(lines):
        line = lines[current_index].strip()
        
        if not line:
            current_index += 1
            continue
            
        if '|' not in line or line.count('|') < 2:
            break
            
        # 跳过分隔线（如 |------|------|）
        if re.match(r'^[\|\-\s]+$', line):
            current_index += 1
            continue
            
        # 解析表格行
        cells = [cell.strip() for cell in line.split('|')]
        # 去除首尾的空单元格
        cells = [cell for cell in cells if cell]
        
        if len(cells) >= 2:  # 至少要有2列才算有效表格行
            table_data.append(cells)
        
        current_index += 1
    
    # 如果找到了有效的表格数据（至少2行）
    if len(table_data) >= 2:
        return table_data, current_index - 1
    else:
        return None, start_index

def create_pdf_table(table_data, styles):
    """创建PDF表格"""
    from reportlab.platypus import Table, TableStyle
    from reportlab.lib.colors import HexColor, black, white
    
    if not table_data or len(table_data) == 0:
        return None
    
    # 确保所有行的列数一致
    max_cols = max(len(row) for row in table_data)
    normalized_data = []
    
    for row in table_data:
        normalized_row = row + [''] * (max_cols - len(row))
        normalized_data.append(normalized_row)
    
    # 创建表格
    table = Table(normalized_data)
    
    # 设置表格样式
    table_style = TableStyle([
        # 表头样式
        ('BACKGROUND', (0, 0), (-1, 0), HexColor('#4A90E2')),
        ('TEXTCOLOR', (0, 0), (-1, 0), white),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'ChineseFont' if register_chinese_font() else 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 11),
        
        # 表格内容样式
        ('BACKGROUND', (0, 1), (-1, -1), HexColor('#F8F9FA')),
        ('TEXTCOLOR', (0, 1), (-1, -1), black),
        ('FONTNAME', (0, 1), (-1, -1), 'ChineseFont' if register_chinese_font() else 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 10),
        
        # 边框样式
        ('GRID', (0, 0), (-1, -1), 1, HexColor('#CCCCCC')),
        ('LINEBELOW', (0, 0), (-1, 0), 2, HexColor('#4A90E2')),
        
        # 行间距
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [HexColor('#F8F9FA'), white]),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ])
    
    table.setStyle(table_style)
    
    return table

def create_single_supplier_pdf(supplier_data, filename):
    """为单个供应商创建增强版PDF报告"""
    doc = SimpleDocTemplate(filename, pagesize=A4, topMargin=1*inch, bottomMargin=1*inch)
    styles = create_enhanced_styles()
    story = []
    
    supplier_name = supplier_data['supplier']
    query = supplier_data['query']
    response = supplier_data['response']
    
    # 清洗内容
    cleaned_response = clean_content(response)
    
    # 提取链接
    references = extract_references(response)
    
    # 添加报告标题
    story.append(Paragraph(f"{supplier_name} 产品信息报告", styles['title']))
    story.append(Paragraph(f"生成时间: {datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')}", styles['body']))
    story.append(Spacer(1, 0.3*inch))
    
    # 处理并添加主要内容
    content_elements = process_content_for_pdf(cleaned_response)
    
    for element_type, content in content_elements:
        if not content:
            continue
            
        try:
            if element_type == 'table':
                # 处理表格
                table = create_pdf_table(content, styles)
                if table:
                    story.append(Spacer(1, 0.1*inch))
                    story.append(table)
                    story.append(Spacer(1, 0.2*inch))
            else:
                # 处理普通文本
                text = str(content)
                if text and text.strip():
                    story.append(Paragraph(text, styles[element_type]))
                    if element_type == 'heading1':
                        story.append(Spacer(1, 0.1*inch))
                    elif element_type == 'numbered':
                        story.append(Spacer(1, 0.08*inch))
                    elif element_type == 'highlight':
                        story.append(Spacer(1, 0.05*inch))
        except Exception as e:
            print(f"  ⚠️ 处理内容时出错: {e}, 类型: {element_type}, 内容: {str(content)[:50]}...")
            # 使用默认样式作为备选
            if element_type != 'table':
                try:
                    story.append(Paragraph(str(content), styles['body']))
                except:
                    # 如果还是失败，跳过这一行
                    continue
    
    # 添加参考资料部分
    if references:
        story.append(Spacer(1, 0.3*inch))
        story.append(Paragraph("参考资料来源", styles['heading1']))
        story.append(Spacer(1, 0.1*inch))
        
        for i, ref in enumerate(references, 1):
            story.append(Paragraph(f"{i}. {ref}", styles['link']))
    
    # 构建PDF
    doc.build(story)
    print(f"  → 单独PDF已生成: {filename}")

def create_pdf_report(suppliers_data, filename="供应商产品信息报告.pdf"):
    """创建增强版合并PDF报告"""
    doc = SimpleDocTemplate(filename, pagesize=A4, topMargin=1*inch, bottomMargin=1*inch)
    styles = create_enhanced_styles()
    story = []
    
    # 添加报告标题
    story.append(Paragraph("供应商产品信息查询报告（合并版）", styles['title']))
    story.append(Paragraph(f"生成时间: {datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')}", styles['body']))
    story.append(Paragraph(f"包含供应商数量: {len(suppliers_data)}", styles['body']))
    story.append(Spacer(1, 0.3*inch))
    
    # 收集所有引用链接
    all_references = []
    
    # 为每个供应商添加内容
    for i, supplier_data in enumerate(suppliers_data):
        if i > 0:  # 除了第一个供应商外，都添加分页符
            story.append(PageBreak())
        
        supplier_name = supplier_data['supplier']
        query = supplier_data['query']
        response = supplier_data['response']
        
        # 清洗内容和提取链接
        cleaned_response = clean_content(response)
        references = extract_references(response)
        all_references.extend(references)
        
        # 供应商标题
        story.append(Paragraph(f"供应商 {i+1}: {supplier_name}", styles['heading1']))
        story.append(Spacer(1, 0.2*inch))
        
        # 处理并添加主要内容
        content_elements = process_content_for_pdf(cleaned_response)
        
        for element_type, content in content_elements:
            if not content:
                continue
                
            try:
                if element_type == 'table':
                    # 处理表格
                    table = create_pdf_table(content, styles)
                    if table:
                        story.append(Spacer(1, 0.1*inch))
                        story.append(table)
                        story.append(Spacer(1, 0.2*inch))
                else:
                    # 处理普通文本
                    text = str(content)
                    if text and text.strip():
                        story.append(Paragraph(text, styles[element_type]))
                        if element_type == 'heading1':
                            story.append(Spacer(1, 0.1*inch))
                        elif element_type == 'numbered':
                            story.append(Spacer(1, 0.08*inch))
                        elif element_type == 'highlight':
                            story.append(Spacer(1, 0.05*inch))
            except Exception as e:
                print(f"  ⚠️ 处理内容时出错: {e}, 类型: {element_type}, 内容: {str(content)[:50]}...")
                # 使用默认样式作为备选
                if element_type != 'table':
                    try:
                        story.append(Paragraph(str(content), styles['body']))
                    except:
                        # 如果还是失败，跳过这一行
                        continue
        
        story.append(Spacer(1, 0.2*inch))
    
    # 添加整体参考资料部分
    if all_references:
        story.append(PageBreak())
        story.append(Paragraph("参考资料来源汇总", styles['heading1']))
        story.append(Spacer(1, 0.2*inch))
        
        # 去重并排序
        unique_references = list(set(all_references))
        sorted_references = extract_references(' '.join(unique_references))
        
        for i, ref in enumerate(sorted_references, 1):
            story.append(Paragraph(f"{i}. {ref}", styles['link']))
    
    # 构建PDF
    doc.build(story)
    print(f"✓ 合并PDF报告已生成: {filename}")

def main():
    set_debug(True)  # 启用langchain调试模式，可以获得如完整提示词等信息
    load_dotenv(verbose=True)  # 加载环境变量配置
    
    # 读取数据表（如果存在的话）
    try:
        suppliers_df = pd.read_excel('企业名称.xlsx')
        suppliers = [c for c in suppliers_df['企业名称']]
        print("✓ 从Excel文件读取供应商列表")
    except:
        # 从配置文件读取供应商列表
        suppliers = DEFAULT_SUPPLIERS
        print("✓ 使用配置文件中的默认供应商列表")
    
    # 也可以通过命令行参数指定供应商
    if len(sys.argv) > 1:
        # 如果有命令行参数，使用参数作为供应商列表
        suppliers = sys.argv[1:]
        print(f"✓ 使用命令行指定的供应商: {suppliers}")
    
    # 创建输出目录
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = f"供应商报告_{timestamp}"
    os.makedirs(output_dir, exist_ok=True)
    print(f"✓ 创建输出目录: {output_dir}")
    
    # 创建状态图以及对话相关的设置
    config = {
        "configurable": {"thread_id": uuid.uuid4().hex},
        "recursion_limit": 100
    }
    graph = create_graph()
    
    all_suppliers_data = []  # 存储所有供应商的数据
    
    print("\n开始自动化查询供应商产品信息...")
    print(f"计划查询 {len(suppliers)} 个供应商")
    print("=" * 50)
    
    # 循环处理每个供应商
    for i, supplier in enumerate(suppliers, 1):
        print(f"\n正在查询第 {i}/{len(suppliers)} 个供应商: {supplier}")
        print("-" * 30)
        
        # 使用配置文件中的查询模板动态生成查询内容
        query = QUERY_TEMPLATE.format(supplier=supplier)
        print(f"查询内容: {query}")
        
        # 创建新的状态（每个供应商使用独立的状态）
        state = plan_state(
            task=query,
            goal='',
            messages=[],
            steps=[],
            steps2results={},
            documents=[]
        )
        
        # 清洗输入，去除非法Unicode字符
        query_clean = query.encode('utf-8', 'ignore').decode('utf-8')
        state["messages"].append(HumanMessage(content=query_clean))
        state["task"] = query_clean
        
        ai_response = ""  # 用于收集AI回复
        
        print("AI回复:")
        # 流式获取AI的回复
        try:
            for answer in stream_graph_updates(graph, state, config):
                print(answer, end="")
                # 确保answer为str类型
                if isinstance(answer, list):
                    answer = "".join(str(x) for x in answer)
                ai_response += str(answer)
        except Exception as e:
            print(f"查询 {supplier} 时出错: {e}")
            ai_response = f"查询失败: {str(e)}"
        
        print()  # 换行
        
        # 保存本轮查询结果
        supplier_data = {
            "supplier": supplier,
            "query": query,
            "response": ai_response
        }
        all_suppliers_data.append(supplier_data)
        
        # 渐进式保存：立即为当前供应商生成单独的PDF
        try:
            single_pdf_filename = os.path.join(output_dir, f"{supplier}产品信息报告_{timestamp}.pdf")
            create_single_supplier_pdf(supplier_data, single_pdf_filename)
        except Exception as e:
            print(f"  ⚠️ 生成 {supplier} 单独PDF时出错: {e}")
            # 备选方案：保存为文本文件
            txt_filename = os.path.join(output_dir, f"{supplier}产品信息报告_{timestamp}.txt")
            with open(txt_filename, "w", encoding="utf-8") as f:
                f.write(f"{supplier} 产品信息报告\n")
                f.write(f"生成时间: {datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')}\n")
                f.write("=" * 50 + "\n\n")
                f.write(f"查询内容: {query}\n\n")
                f.write("详细信息:\n")
                f.write(ai_response)
            print(f"  → 备选文本文件已生成: {txt_filename}")
        
        print(f"✓ {supplier} 查询完成并已保存")
    
    print("\n" + "=" * 50)
    print("所有供应商查询完成!")
    print(f"单独报告文件保存在: {output_dir}")
    
    # 生成合并的PDF报告
    merged_pdf_filename = os.path.join(output_dir, f"合并_供应商产品信息报告_{timestamp}.pdf")
    
    try:
        create_pdf_report(all_suppliers_data, merged_pdf_filename)
    except Exception as e:
        print(f"生成合并PDF报告时出错: {e}")
        print("正在保存为文本格式作为备选...")
        
        # 备选方案：保存为文本文件
        txt_filename = os.path.join(output_dir, f"合并_供应商产品信息报告_{timestamp}.txt")
        with open(txt_filename, "w", encoding="utf-8") as f:
            f.write("供应商产品信息查询报告（合并版）\n")
            f.write(f"生成时间: {datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')}\n")
            f.write(f"包含供应商数量: {len(all_suppliers_data)}\n")
            f.write("=" * 50 + "\n\n")
            
            for i, supplier_data in enumerate(all_suppliers_data, 1):
                f.write(f"供应商 {i}: {supplier_data['supplier']}\n")
                f.write(f"查询内容: {supplier_data['query']}\n")
                f.write("详细信息:\n")
                f.write(supplier_data['response'])
                f.write("\n" + "-" * 50 + "\n\n")
        
        print(f"✓ 合并文本报告已生成: {txt_filename}")
    
    print(f"\n🎉 全部完成！")
    print(f"📁 输出目录: {output_dir}")
    print(f"📄 单独报告: {len(suppliers)} 个")
    print(f"📋 合并报告: 1 个")

if __name__ == "__main__":
    main()
