from langgraph.graph.state import CompiledStateGraph
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import START, END
from langgraph.graph.state import StateGraph
from langchain_core.messages import HumanMessage, AIMessage

from paper_agent.web_search import web_search
from graph.state import plan_state
from model.llm import get_model
import re
import pandas as pd

def extract_domain(url):
    """从URL中提取域名"""
    if pd.isna(url) or url == '-':
        return '无域名'
    
    try:
        url = str(url).strip()
        if url.startswith('http'):
            # 提取域名部分
            domain = url.split('/')[2]
        else:
            domain = url.split('/')[0]
        
        # 简化域名（移除www等前缀）
        if domain.startswith('www.'):
            domain = domain[4:]
        
        return domain
    except:
        return '解析失败'

def direct_search_agent(state: plan_state):
    """
    两阶段搜索验证代理：
    1. 初步搜索企业信息（优先官网）
    2. 大模型分析生成扩展查询
    3. 验证搜索（重点查官网）
    4. 剔除官网中未出现的信息
    """
    task = state.get("task", "")
    company_website = state.get("company_website", "")
    
    # 从任务中提取企业名称
    company_name = extract_company_name(task)
    if not company_name:
        error_msg = "无法从查询中提取到具体的企业名称"
        state["messages"].append(AIMessage(content=error_msg))
        return state
    
    print(f"🏢 目标企业: {company_name}")
    if company_website:
        print(f"🌐 已知官网: {company_website}")
    
    # 第一阶段：初步搜索（优先官网）
    print(f"\n📍 第一阶段：初步搜索企业信息")
    initial_results = perform_initial_search(company_name, company_website)
    
    if not initial_results:
        error_msg = f"未能找到关于 {company_name} 的初步信息"
        state["messages"].append(AIMessage(content=error_msg))
        return state
    
    # 第二阶段：大模型分析和生成扩展查询
    print(f"\n🤖 第二阶段：大模型分析初步结果")
    analysis_result = analyze_and_generate_queries(company_name, initial_results, company_website)
    
    # 第三阶段：验证搜索（重点查官网）
    print(f"\n🔍 第三阶段：验证搜索（官网优先）")
    verification_results = perform_verification_search(company_name, analysis_result["verification_queries"])
    
    # 第四阶段：信息验证和剔除
    print(f"\n✅ 第四阶段：信息验证和剔除")
    final_report = verify_and_filter_information(
        company_name, 
        analysis_result["extracted_info"], 
        verification_results,
        company_website
    )
    
    # 保存结果
    state["messages"].append(AIMessage(content=final_report))
    state["documents"].extend(initial_results + verification_results)
    
    return state

def perform_initial_search(company_name: str, company_website: str = "") -> list:
    """第一阶段：初步搜索企业基础信息（优先官网）"""
    initial_keywords = []
    
    # 如果有官网，优先搜索官网内容
    if company_website:
        domain = extract_domain(company_website)
        initial_keywords.extend([
            f"{company_name} site:{domain}",
            f"产品 site:{domain}",
            f"关于我们 site:{domain}",
            f"{company_name} 官网"
        ])
    
    # 添加通用搜索关键词
    initial_keywords.extend([
        f"{company_name} 企业信息", 
        f"{company_name} 产品介绍",
        f"{company_name} 公司简介"
    ])
    
    all_results = []
    for i, keyword in enumerate(initial_keywords, 1):
        print(f"   🔍 初步搜索 {i}/{len(initial_keywords)}: {keyword}")
        
        try:
            search_result = web_search.invoke({"key_words": keyword})
            if search_result:
                print(f"      ✅ 找到 {len(search_result)} 条结果")
                all_results.extend(search_result)
            else:
                print(f"      ❌ 未找到结果")
        except Exception as e:
            print(f"      ⚠️ 搜索出错: {e}")
    
    print(f"   📊 初步搜索完成，共收集 {len(all_results)} 条信息")
    return all_results

def analyze_and_generate_queries(company_name: str, search_results: list, company_website: str = "") -> dict:
    """第二阶段：大模型分析结果并生成扩展验证查询"""
    
    # 合并搜索结果内容
    combined_content = ""
    official_urls = []
    
    for doc in search_results:
        if hasattr(doc, 'page_content'):
            combined_content += doc.page_content + "\n\n"
        if hasattr(doc, 'metadata') and doc.metadata.get('source'):
            url = doc.metadata['source']
            # 识别可能的官网链接
            if any(domain in url.lower() for domain in ['.com', '.com.cn', '.cn']) and \
               not any(third_party in url.lower() for third_party in ['baidu', 'zhihu', 'csdn', 'sohu']):
                official_urls.append(url)
    
    # 使用大模型分析
    model = get_model()
    
    # 构建已知官网信息
    known_website_info = ""
    if company_website:
        known_website_info = f"\n# 已知官网：\n{company_website}\n"
    
    analysis_prompt = f"""
基于以下关于 {company_name} 的搜索结果，请进行分析并生成验证查询：

# 搜索结果内容：
{combined_content[:2000]}...
{known_website_info}
# 可能的官网链接：
{chr(10).join(official_urls[:3])}

请完成以下任务：

## 1. 提取关键信息
从搜索结果中提取以下信息（如果有的话）：
- 主营产品/服务
- 核心技术
- 企业规模
- 成立时间
- 总部地址
- 认证资质

## 2. 生成验证查询
为每个提取的信息生成官网验证查询关键词，格式：
- "{company_name} [具体产品/技术] site:官网域名"
- "{company_name} [具体信息] 官网"

## 3. 官网域名识别
{f"已知官网域名: {extract_domain(company_website)}" if company_website else "如果能识别出官网域名，请列出。"}

请用以下JSON格式回复：
{{
    "extracted_info": {{
        "主营产品": "具体产品名称",
        "核心技术": "具体技术",
        "企业规模": "规模信息",
        "成立时间": "时间",
        "总部地址": "地址",
        "认证资质": "认证信息"
    }},
    "official_domains": ["域名1", "域名2"],
    "verification_queries": [
        "{company_name} 具体产品 官网",
        "{company_name} 技术 site:域名"
    ]
}}
"""
    
    try:
        print(f"   🤖 大模型分析中...")
        response = model.invoke([HumanMessage(content=analysis_prompt)])
        
        # 尝试解析JSON响应
        import json
        try:
            # 提取JSON部分
            content = response.content
            json_start = content.find('{')
            json_end = content.rfind('}') + 1
            if json_start != -1 and json_end != -1:
                json_str = content[json_start:json_end]
                result = json.loads(json_str)
                print(f"   ✅ 分析完成，提取了 {len(result.get('extracted_info', {}))} 项信息")
                print(f"   📋 生成了 {len(result.get('verification_queries', []))} 个验证查询")
                return result
        except json.JSONDecodeError:
            print(f"   ⚠️ JSON解析失败，使用备选方案")
            
        # 备选方案：简单的关键词生成
        return generate_fallback_queries(company_name, combined_content)
        
    except Exception as e:
        print(f"   ⚠️ 大模型分析出错: {e}")
        return generate_fallback_queries(company_name, combined_content)

def generate_fallback_queries(company_name: str, content: str) -> dict:
    """备选方案：简单生成验证查询"""
    return {
        "extracted_info": {
            "主营产品": "待验证",
            "核心技术": "待验证", 
            "企业规模": "待验证"
        },
        "official_domains": [],
        "verification_queries": [
            f"{company_name} 主营产品 官网",
            f"{company_name} 核心技术 官网",
            f"{company_name} 企业介绍 官网",
            f"{company_name} 产品中心 官网"
        ]
    }

def perform_verification_search(company_name: str, verification_queries: list) -> list:
    """第三阶段：执行验证搜索"""
    all_results = []
    
    for i, query in enumerate(verification_queries, 1):
        print(f"   🔍 验证搜索 {i}/{len(verification_queries)}: {query}")
        
        try:
            search_result = web_search.invoke({"key_words": query})
            if search_result:
                print(f"      ✅ 找到 {len(search_result)} 条验证结果")
                all_results.extend(search_result)
            else:
                print(f"      ❌ 验证未找到结果")
        except Exception as e:
            print(f"      ⚠️ 验证搜索出错: {e}")
    
    print(f"   📊 验证搜索完成，共收集 {len(all_results)} 条验证信息")
    return all_results

def verify_and_filter_information(company_name: str, extracted_info: dict, verification_results: list, company_website: str) -> str:
    """第四阶段：验证信息并剔除非官网内容"""
    
    # 分离官网和非官网内容
    official_content = []
    non_official_content = []
    official_urls = []
    
    # 如果有已知官网，优先匹配已知官网的内容
    known_domain = extract_domain(company_website) if company_website else ""
    
    for doc in verification_results:
        if hasattr(doc, 'metadata') and doc.metadata.get('source'):
            url = doc.metadata['source']
            # 判断是否为官网（优先已知官网）
            if is_official_website(url, known_domain):
                official_content.append(doc.page_content if hasattr(doc, 'page_content') else str(doc))
                official_urls.append(url)
            else:
                non_official_content.append(doc.page_content if hasattr(doc, 'page_content') else str(doc))
    
    print(f"   📊 官网内容: {len(official_content)} 条")
    print(f"   📊 非官网内容: {len(non_official_content)} 条")
    if known_domain:
        print(f"   🎯 已知官网域名: {known_domain}")
    
    # 验证提取的信息
    verified_info = {}
    removed_info = {}
    
    combined_official_content = "\n".join(official_content)
    
    for key, value in extracted_info.items():
        if value and value != "待验证":
            # 检查官网内容中是否包含该信息
            if verify_info_in_official_content(value, combined_official_content):
                verified_info[key] = value
                print(f"   ✅ {key}: {value} - 官网验证通过")
            else:
                removed_info[key] = value
                print(f"   ❌ {key}: {value} - 官网未找到，已剔除")
        else:
            # 尝试从官网内容中提取
            extracted_value = extract_info_from_official_content(key, combined_official_content)
            if extracted_value:
                verified_info[key] = extracted_value
                print(f"   ✅ {key}: {extracted_value} - 从官网新提取")
    
    # 生成最终报告
    report = generate_verified_report(company_name, verified_info, removed_info, official_urls, company_website)
    
    return report

def is_official_website(url: str, known_domain: str = "") -> bool:
    """判断是否为官网（优先已知域名）"""
    url_lower = url.lower()
    
    # 如果有已知域名，优先匹配
    if known_domain and known_domain.lower() in url_lower:
        return True
    
    # 排除明显的第三方网站
    third_party_sites = [
        'baidu.com', 'google.com', 'bing.com', 'zhihu.com', 'csdn.net',
        'weibo.com', 'qq.com', 'sina.com', 'sohu.com', '163.com',
        'chinaz.com', 'tianyancha.com', 'qichacha.com', 'aiqicha.com'
    ]
    
    if any(site in url_lower for site in third_party_sites):
        return False
    
    # 包含企业域名特征
    official_indicators = ['.com', '.com.cn', '.cn', '.net', '.org']
    return any(indicator in url_lower for indicator in official_indicators)

def verify_info_in_official_content(info: str, official_content: str) -> bool:
    """验证信息是否在官网内容中出现"""
    if not info or not official_content:
        return False
    
    # 提取关键词进行匹配
    keywords = re.findall(r'[\u4e00-\u9fff]+|[a-zA-Z]+', info)
    official_content_lower = official_content.lower()
    
    # 至少有50%的关键词在官网内容中出现
    matched_keywords = 0
    for keyword in keywords:
        if len(keyword) > 1 and keyword.lower() in official_content_lower:
            matched_keywords += 1
    
    return len(keywords) > 0 and (matched_keywords / len(keywords)) >= 0.5

def extract_info_from_official_content(info_type: str, official_content: str) -> str:
    """从官网内容中提取特定类型的信息"""
    if not official_content:
        return ""
    
    # 定义提取模式
    patterns = {
        "主营产品": [
            r"主营产品[：:]\s*([^。\n]+)",
            r"主要产品[：:]\s*([^。\n]+)",
            r"产品[：:]\s*([^。\n]+)",
            r"专业生产\s*([^。\n]+)"
        ],
        "核心技术": [
            r"核心技术[：:]\s*([^。\n]+)",
            r"技术优势[：:]\s*([^。\n]+)",
            r"技术特点[：:]\s*([^。\n]+)"
        ],
        "企业规模": [
            r"员工[：:]\s*([^。\n]*人)",
            r"规模[：:]\s*([^。\n]+)"
        ]
    }
    
    if info_type in patterns:
        for pattern in patterns[info_type]:
            matches = re.findall(pattern, official_content)
            if matches:
                return matches[0].strip()
    
    return ""

def generate_verified_report(company_name: str, verified_info: dict, removed_info: dict, official_urls: list, company_website: str) -> str:
    """生成验证后的报告"""
    
    website_note = f"\n🏢 已知官网：{company_website}" if company_website else ""
    
    report = f"""# {company_name} 企业信息报告（官网验证版）

## 数据验证说明
✅ 本报告信息均经过官网验证
❌ 已剔除无法在官网中确认的信息
🔍 数据来源：优先采用官方网站信息{website_note}

## 企业基础信息（官网验证）

"""
    
    # 添加验证通过的信息
    if verified_info:
        for key, value in verified_info.items():
            report += f"**{key}**: {value}\n\n"
    else:
        report += "暂无完整的官网验证信息\n\n"
    
    # 添加被剔除的信息说明
    if removed_info:
        report += "## 已剔除信息（官网未确认）\n\n"
        for key, value in removed_info.items():
            report += f"- {key}: {value} （在官网中未找到相关信息）\n"
        report += "\n"
    
    # 添加官网来源
    if official_urls or company_website:
        report += "## 官方信息来源\n\n"
        idx = 1
        
        # 如果有已知官网，优先显示
        if company_website:
            report += f"{idx}. {company_website} (已知官网)\n"
            idx += 1
            
        # 添加搜索到的官网
        for url in set(official_urls):
            if url != company_website:  # 避免重复显示
                report += f"{idx}. {url}\n"
                idx += 1
    
    report += f"\n## 报告特点\n\n"
    report += f"- ✅ 信息真实性：仅包含官网确认的信息\n"
    report += f"- ❌ 信息剔除：移除了 {len(removed_info)} 项无法验证的信息\n"
    report += f"- 🔍 验证来源：{len(set(official_urls))} 个官方网站\n"
    if company_website:
        known_domain = extract_domain(company_website)
        report += f"- 🎯 已知官网优先：优先从已知官网 {known_domain} 获取信息\n"
    
    return report

def extract_company_name(task: str) -> str:
    """
    从任务描述中提取企业名称
    """
    # 尝试多种模式来提取企业名称
    patterns = [
        r'请为我收集\s*([^的]*?)\s*的详细产品信息',
        r'收集\s*([^的]*?)\s*的.*?信息',
        r'查询\s*([^的]*?)\s*的.*?信息',
        r'([^，。\n]*(?:有限公司|股份有限公司|集团|科技|实业))',
        r'([^，。\n]*公司)',
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, task)
        if matches:
            company_name = matches[0].strip()
            if len(company_name) > 2:  # 过滤过短的名称
                return company_name
    
    return ""

def create_simplified_graph() -> CompiledStateGraph:
    """
    创建简化的工作流 - 移除solve_agent，直接进行搜索
    """
    workflow = StateGraph(plan_state)
    
    # 只添加必要的节点
    workflow.add_node("direct_search", direct_search_agent)
    
    # 简单的线性流程
    workflow.add_edge(START, "direct_search")
    workflow.add_edge("direct_search", END)
    
    return workflow.compile(checkpointer=MemorySaver())

def stream_simplified_updates(graph: CompiledStateGraph, state: plan_state, config: dict):
    """
    流式处理简化工作流的更新
    """
    for chunk, _ in graph.stream(state, config, stream_mode="messages"):
        if hasattr(chunk, 'content') and chunk.content:
            yield chunk.content 