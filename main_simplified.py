import uuid
import json
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage
from simplified_graph import create_simplified_graph, stream_simplified_updates
from graph.state import plan_state
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from datetime import datetime
import pandas as pd
import os
import sys
import re
from suppliers_config import DEFAULT_SUPPLIERS
from data_processor import DataProcessor
import glob

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
    """清洗内容"""
    if not isinstance(content, str):
        content = str(content)
    
    # 基础清洗
    content = re.sub(r'\s+', ' ', content)  # 多空格合并
    content = content.strip()
    
    return content

def create_pdf_report(supplier_data, filename):
    """创建PDF报告"""
    doc = SimpleDocTemplate(filename, pagesize=A4, topMargin=1*inch, bottomMargin=1*inch)
    styles = getSampleStyleSheet()
    story = []
    
    supplier_name = supplier_data['supplier']
    response = supplier_data['response']
    
    # 清洗内容
    cleaned_response = clean_content(response)
    
    # 添加报告标题
    title_style = ParagraphStyle(
        'Title',
        parent=styles['Title'],
        fontSize=18,
        spaceAfter=24,
        spaceBefore=12,
        alignment=1,  # 居中
    )
    
    story.append(Paragraph(f"{supplier_name} 产品信息报告", title_style))
    story.append(Paragraph(f"生成时间: {datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')}", styles['Normal']))
    story.append(Spacer(1, 0.3*inch))
    
    # 添加内容
    for line in cleaned_response.split('\n'):
        if line.strip():
            story.append(Paragraph(line, styles['Normal']))
    
    # 构建PDF
    doc.build(story)
    print(f"  → PDF已生成: {filename}")

def save_json_data(data, filename):
    """保存JSON格式数据"""
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return f"✅ JSON文件已保存: {filename}"
    except Exception as e:
        return f"❌ JSON保存失败: {str(e)}"

def print_json_summary(supplier_data):
    """打印企业数据的JSON摘要"""
    summary = {
        "企业名称": supplier_data["supplier"],
        "官网链接": supplier_data.get("structured_data", {}).get("官网链接", "官网未公布"),
        "数据可信度": supplier_data.get("validation", {}).get("整体评级", "未评级"),
        "基础信息完整度": supplier_data.get("validation", {}).get("基础信息完整度", "0/4"),
        "产品信息完整度": supplier_data.get("validation", {}).get("产品信息完整度", "0/4"),
        "主营产品": supplier_data.get("structured_data", {}).get("主营产品类别", "官网未公布"),
        "成立时间": supplier_data.get("structured_data", {}).get("成立时间", "官网未公布")
    }
    
    print("📊 结构化数据摘要:")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return summary

def main():
    """主函数 - 使用简化工作流，输出JSON和CSV数据"""
    load_dotenv()
    
    print("🚀 企业信息收集系统（简化版 - JSON/CSV输出）")
    print("="*60)
    print("📋 输出格式：")
    print("   • JSON格式：每个企业的结构化数据")
    print("   • CSV格式：所有企业的汇总表格") 
    print("   • 控制台：实时数据摘要")
    print("   • PDF报告：可选生成")
    print("="*60)
    
    # 初始化数据处理器
    data_processor = DataProcessor()
    
    # 读取企业列表
    try:
        # 查找最新的有官网企业文件
        pattern = "企业名称_有官网_*.xlsx"
        files = glob.glob(pattern)
        
        if files:
            # 使用最新的清洗文件
            latest_file = max(files, key=os.path.getctime)
            suppliers_df = pd.read_excel(latest_file)
            suppliers = [c for c in suppliers_df['企业名称']]
            print(f"✓ 从清洗后文件读取供应商列表: {latest_file}")
            print(f"✓ 已加载 {len(suppliers)} 个有官网的企业")
            
            # 创建企业-官网映射
            company_website_map = dict(zip(suppliers_df['企业名称'], suppliers_df['网址']))
            print(f"✓ 创建企业官网映射，包含 {len(company_website_map)} 个官网")
        else:
            # 备选方案：使用原始文件
            suppliers_df = pd.read_excel('企业名称.xlsx')
            suppliers = [c for c in suppliers_df['企业名称']]
            company_website_map = {}
            print("✓ 从原始Excel文件读取供应商列表")
    except:
        suppliers = DEFAULT_SUPPLIERS
        company_website_map = {}
        print("✓ 使用配置文件中的默认供应商列表")
    
    # 命令行参数支持
    if len(sys.argv) > 1:
        suppliers = sys.argv[1:]
        print(f"✓ 使用命令行指定的供应商: {suppliers}")
    
    # 创建输出目录
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = f"企业数据_{timestamp}"
    os.makedirs(output_dir, exist_ok=True)
    print(f"✓ 创建输出目录: {output_dir}")
    
    # 创建简化的状态图
    config = {
        "configurable": {"thread_id": uuid.uuid4().hex},
        "recursion_limit": 50
    }
    graph = create_simplified_graph()
    
    all_suppliers_data = []
    structured_data_list = []
    json_summary_list = []
    
    print("\n开始企业信息收集...")
    print(f"计划查询 {len(suppliers)} 个企业")
    print("=" * 50)
    
    # 处理每个企业
    for i, supplier in enumerate(suppliers, 1):
        print(f"\n📋 第 {i}/{len(suppliers)} 个企业: {supplier}")
        print("-" * 40)
        
        # 使用简化的查询
        simple_query = f"请收集 {supplier} 的详细产品信息和企业信息"
        print(f"📝 查询: {simple_query}")
        
        # 创建状态
        state = plan_state(
            task=simple_query,
            goal=f'收集{supplier}的企业信息',
            messages=[HumanMessage(content=simple_query)],
            steps=[],
            steps2results={},
            documents=[],
            current_step=0,
            company_website=company_website_map.get(supplier, "")
        )
        
        ai_response = ""
        
        print("🔍 开始搜索...")
        try:
            for answer in stream_simplified_updates(graph, state, config):
                print(answer, end="")
                ai_response += str(answer)
        except Exception as e:
            print(f"❌ 查询 {supplier} 时出错: {e}")
            ai_response = f"查询失败: {str(e)}"
        
        print()  # 换行
        
        # 提取结构化数据
        print("📊 提取结构化数据...")
        structured_data = data_processor.extract_structured_data(supplier, ai_response)
        structured_data_list.append(structured_data)
        
        # 验证数据质量
        validation_result = data_processor.validate_official_data(structured_data)
        print(f"   📈 数据质量: {validation_result.get('整体评级', 'C级')}")
        print(f"   🔗 官网链接: {validation_result.get('官网链接', '❌')}")
        
        # 保存数据
        supplier_data = {
            "supplier": supplier,
            "query": simple_query,
            "response": ai_response,
            "structured_data": structured_data,
            "validation": validation_result,
            "timestamp": datetime.now().isoformat(),
            "known_website": company_website_map.get(supplier, "")
        }
        all_suppliers_data.append(supplier_data)
        
        # 打印JSON摘要并保存
        json_summary = print_json_summary(supplier_data)
        json_summary_list.append(json_summary)
        
        # 保存单个企业的JSON文件
        individual_json_file = os.path.join(output_dir, f"{supplier}_{timestamp}.json")
        json_result = save_json_data(supplier_data, individual_json_file)
        print(f"   {json_result}")
        
        print(f"✅ {supplier} 处理完成")
    
    print("\n" + "=" * 50)
    print("🎉 所有企业处理完成!")
    
    # 导出汇总数据
    print("\n📊 导出汇总数据...")
    
    # 1. 保存所有企业的JSON汇总
    all_data_json_file = os.path.join(output_dir, f"所有企业数据_{timestamp}.json")
    json_result = save_json_data(all_suppliers_data, all_data_json_file)
    print(f"   {json_result}")
    
    # 2. 保存JSON摘要（便于快速查看）
    summary_json_file = os.path.join(output_dir, f"企业数据摘要_{timestamp}.json")
    summary_result = save_json_data(json_summary_list, summary_json_file)
    print(f"   {summary_result}")
    
    # 3. CSV导出
    if structured_data_list:
        csv_filename = os.path.join(output_dir, f"企业数据_{timestamp}.csv")
        csv_result = data_processor.export_to_csv(structured_data_list, csv_filename)
        print(f"   {csv_result}")
        
        # 4. Excel导出（包含数据质量统计）
        excel_filename = os.path.join(output_dir, f"企业数据_{timestamp}.xlsx")
        excel_result = data_processor.export_to_excel(structured_data_list, excel_filename)
        print(f"   {excel_result}")
        
        # 5. 数据质量统计
        print("\n📈 数据质量统计:")
        quality_stats = data_processor.generate_quality_statistics(structured_data_list)
        
        print("   前5个字段完整度:")
        for i, stat in enumerate(quality_stats[:5], 1):
            print(f"   {i}. {stat['字段名称']:15s} - {stat['完整度百分比']:>6s}")
        
        # 6. 可信度分布
        credibility_distribution = {}
        for data in structured_data_list:
            credibility = data.get("数据可信度", "D级 - 数据不足")
            credibility_distribution[credibility] = credibility_distribution.get(credibility, 0) + 1
        
        print(f"\n   数据可信度分布:")
        for credibility, count in credibility_distribution.items():
            percentage = (count / len(structured_data_list)) * 100
            print(f"      {credibility}: {count}家 ({percentage:.1f}%)")
    
    # 生成数据访问指南
    print(f"\n📁 数据输出总结:")
    print(f"   输出目录: {output_dir}")
    print(f"   📊 数据格式:")
    print(f"      • JSON汇总: 所有企业数据_{timestamp}.json")
    print(f"      • JSON摘要: 企业数据摘要_{timestamp}.json")
    print(f"      • CSV表格: 企业数据_{timestamp}.csv")
    print(f"      • Excel报告: 企业数据_{timestamp}.xlsx")
    print(f"      • 单企业JSON: [企业名称]_{timestamp}.json")
    
    # 返回结构化数据（用于API调用等）
    return {
        "summary": {
            "total_companies": len(suppliers),
            "successful_queries": len([d for d in all_suppliers_data if "查询失败" not in d["response"]]),
            "output_directory": output_dir,
            "timestamp": timestamp
        },
        "data": all_suppliers_data,
        "json_summaries": json_summary_list,
        "structured_data": structured_data_list
    }

if __name__ == "__main__":
    result = main()
    
    # 如果作为模块调用，可以返回数据
    print(f"\n💡 程序完成，返回了包含 {len(result['data'])} 个企业的结构化数据")
    print(f"📋 数据可通过以下方式访问:")
    print(f"   - result['data']: 完整企业数据")
    print(f"   - result['json_summaries']: 企业摘要数据")
    print(f"   - result['structured_data']: CSV结构化数据") 