import pandas as pd
import re
import json
from datetime import datetime
from typing import Dict, List, Any, Optional
from suppliers_config import CSV_FIELDS, CSV_OUTPUT_CONFIG, OFFICIAL_WEBSITE_KEYWORDS, CREDIBILITY_LEVELS, DATA_CLEANING_RULES

class DataProcessor:
    """数据处理器 - 专注于官网数据验证和CSV结构化输出"""
    
    def __init__(self):
        self.csv_fields = CSV_FIELDS
        self.output_config = CSV_OUTPUT_CONFIG
        self.official_keywords = OFFICIAL_WEBSITE_KEYWORDS
        self.credibility_levels = CREDIBILITY_LEVELS
        self.cleaning_rules = DATA_CLEANING_RULES
        
    def extract_structured_data(self, supplier_name: str, raw_response: str) -> Dict[str, Any]:
        """从原始回复中提取结构化数据"""
        
        # 初始化数据字典
        structured_data = {field: "官网未公布" for field in self.csv_fields}
        structured_data["企业全称"] = supplier_name
        structured_data["信息更新时间"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # 提取官网链接
        official_urls = self.extract_official_urls(raw_response)
        if official_urls:
            structured_data["官网链接"] = official_urls[0]
            structured_data["数据来源页面"] = "; ".join(official_urls[:3])
        
        # 使用正则表达式和关键词匹配提取各字段信息
        field_patterns = self.create_field_patterns()
        
        for field, patterns in field_patterns.items():
            if field in structured_data:
                extracted_value = self.extract_field_value(raw_response, patterns)
                if extracted_value and extracted_value != "官网未公布":
                    # 验证数据来源可信度（放宽条件）
                    credibility = self.assess_credibility(extracted_value, raw_response)
                    # 现在接受官网和部分第三方数据，只排除明显不可信的
                    if credibility != "无法验证":  
                        structured_data[field] = self.clean_data(extracted_value)
                        
        # 尝试通用文本提取作为补充
        self.extract_general_patterns(raw_response, structured_data)
                        
        # 评估整体数据可信度
        structured_data["数据可信度"] = self.calculate_overall_credibility(structured_data, raw_response)
        
        return structured_data
    
    def create_field_patterns(self) -> Dict[str, List[str]]:
        """创建字段提取模式（增强版，更灵活的匹配）"""
        return {
            # 企业基础信息
            "成立时间": [
                r"成立时间[：:]\s*(\d{4}[年\-]\d{1,2}[月\-]\d{1,2}[日]?)",
                r"成立于[：:]?\s*(\d{4}年?)",
                r"创立于[：:]?\s*(\d{4}年?)",
                r"创建时间[：:]\s*(\d{4}年?)",
                r"注册时间[：:]\s*(\d{4}[年\-]\d{1,2}[月\-]\d{1,2}[日]?)",
                r"始建于[：:]?\s*(\d{4}年?)",
                r"(\d{4})年成立",
                r"(\d{4})年创立"
            ],
            "注册资本": [
                r"注册资本[：:]\s*([\d,.]+(万元|亿元|万美元|万港币|元))",
                r"注册资金[：:]\s*([\d,.]+(万元|亿元|万美元|万港币|元))",
                r"资本金[：:]\s*([\d,.]+(万元|亿元|万美元|万港币|元))",
                r"注册资本.*?([\d,.]+(万元|亿元|万美元|万港币))"
            ],
            "员工规模": [
                r"员工[总数|规模|人数][：:]\s*([\d,]+[万]?[余]?人?)",
                r"职工[总数|规模|人数][：:]\s*([\d,]+[万]?[余]?人?)",
                r"团队规模[：:]\s*([\d,]+[万]?[余]?人?)",
                r"现有员工[：:]?\s*([\d,]+[万]?[余]?人?)",
                r"员工约[：:]?\s*([\d,]+[万]?[余]?人?)",
                r"(\d+[万]?[余]?人)",
                r"员工.*?(\d+[万]?余?人)",
                r"人员规模.*?(\d+[万]?余?人)"
            ],
            "总部地址": [
                r"总部地址[：:]\s*([^。\n\r]+)",
                r"公司地址[：:]\s*([^。\n\r]+)",
                r"注册地址[：:]\s*([^。\n\r]+)",
                r"办公地址[：:]\s*([^。\n\r]+)",
                r"地址[：:]\s*([^。\n\r]+)",
                r"位于([^。\n\r]+)",
                r"坐落在([^。\n\r]+)"
            ],
            "联系电话": [
                r"联系电话[：:]\s*([\d\-\+\(\)\s]+)",
                r"客服电话[：:]\s*([\d\-\+\(\)\s]+)",
                r"服务热线[：:]\s*([\d\-\+\(\)\s]+)",
                r"电话[：:]\s*([\d\-\+\(\)\s]+)",
                r"热线[：:]\s*([\d\-\+\(\)\s]+)"
            ],
            "联系邮箱": [
                r"联系邮箱[：:]\s*([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})",
                r"官方邮箱[：:]\s*([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})",
                r"客服邮箱[：:]\s*([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})",
                r"邮箱[：:]\s*([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})",
                r"([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})"
            ],
            
            # 产品信息
            "主营产品类别": [
                r"主营产品[：:]\s*([^。\n\r]+)",
                r"产品类别[：:]\s*([^。\n\r]+)",
                r"主要产品[：:]\s*([^。\n\r]+)",
                r"核心产品[：:]\s*([^。\n\r]+)",
                r"产品范围[：:]\s*([^。\n\r]+)",
                r"主营[：:]?\s*([^。\n\r]*产品[^。\n\r]*)",
                r"专业生产[：:]?\s*([^。\n\r]+)",
                r"主要从事[：:]?\s*([^。\n\r]*产品[^。\n\r]*)"
            ],
            "核心产品型号": [
                r"产品型号[：:]\s*([^。\n\r]+)",
                r"主要型号[：:]\s*([^。\n\r]+)",
                r"核心型号[：:]\s*([^。\n\r]+)",
                r"型号[：:]\s*([^。\n\r]+)",
                r"系列产品[：:]\s*([^。\n\r]+)"
            ],
            "产品应用领域": [
                r"应用领域[：:]\s*([^。\n\r]+)",
                r"应用范围[：:]\s*([^。\n\r]+)",
                r"适用于[：:]?\s*([^。\n\r]+)",
                r"广泛应用于[：:]?\s*([^。\n\r]+)",
                r"主要应用[：:]?\s*([^。\n\r]+)"
            ],
            "技术特点": [
                r"技术特点[：:]\s*([^。\n\r]+)",
                r"技术优势[：:]\s*([^。\n\r]+)",
                r"核心技术[：:]\s*([^。\n\r]+)",
                r"技术亮点[：:]\s*([^。\n\r]+)"
            ],
            "产品优势": [
                r"产品优势[：:]\s*([^。\n\r]+)",
                r"优势[：:]\s*([^。\n\r]+)",
                r"产品特色[：:]\s*([^。\n\r]+)",
                r"竞争优势[：:]\s*([^。\n\r]+)"
            ],
            
            # 技术实力
            "研发团队规模": [
                r"研发[人员|团队][：:]\s*([\d,]+[万]?[余]?人?)",
                r"技术团队[：:]\s*([\d,]+[万]?[余]?人?)",
                r"工程师[：:]\s*([\d,]+[万]?[余]?人?)",
                r"研发人员.*?(\d+[万]?[余]?人)",
                r"技术人员.*?(\d+[万]?[余]?人)"
            ],
            "专利数量": [
                r"专利[数量|总数][：:]\s*([\d,]+[项|件]?)",
                r"发明专利[：:]\s*([\d,]+[项|件]?)",
                r"知识产权[：:]\s*([\d,]+[项|件]?)",
                r"拥有专利.*?(\d+[项|件])",
                r"专利.*?(\d+[项|件])",
                r"(\d+项?专利)"
            ],
            
            # 企业资质
            "ISO认证": [
                r"ISO\s*[\d]+[：:]?\s*([^。\n\r]+)",
                r"质量认证[：:]\s*([^。\n\r]*ISO[^。\n\r]*)",
                r"国际认证[：:]\s*([^。\n\r]*ISO[^。\n\r]*)",
                r"ISO认证[：:]\s*([^。\n\r]+)",
                r"通过.*?ISO.*?认证[：:]?\s*([^。\n\r]*)"
            ]
        }
    
    def extract_general_patterns(self, text: str, structured_data: Dict[str, Any]):
        """通用模式提取作为补充"""
        
        # 提取官网地址的更灵活模式
        if structured_data.get("官网链接", "官网未公布") == "官网未公布":
            website_patterns = [
                r"官网[：:]?\s*(https?://[^\s\n\r]+)",
                r"网站[：:]?\s*(https?://[^\s\n\r]+)",
                r"官方网站[：:]?\s*(https?://[^\s\n\r]+)",
                r"(https?://[^\s\n\r]*\.(?:com|cn|net|org)[^\s\n\r]*)"
            ]
            for pattern in website_patterns:
                matches = re.findall(pattern, text, re.IGNORECASE)
                if matches:
                    structured_data["官网链接"] = matches[0]
                    break
        
        # 提取公司全称的更灵活模式
        name_patterns = [
            r"([^，。\n\r]*有限公司)",
            r"([^，。\n\r]*股份有限公司)", 
            r"([^，。\n\r]*集团[^，。\n\r]*)",
            r"([^，。\n\r]*科技[^，。\n\r]*公司)",
            r"([^，。\n\r]*实业[^，。\n\r]*公司)"
        ]
        
        for pattern in name_patterns:
            matches = re.findall(pattern, text)
            if matches:
                full_name = matches[0].strip()
                if len(full_name) > 3 and structured_data["企业全称"] in full_name:
                    structured_data["企业全称"] = full_name
                    break
    
    def extract_field_value(self, text: str, patterns: List[str]) -> str:
        """使用模式匹配提取字段值（改进版）"""
        for pattern in patterns:
            try:
                matches = re.findall(pattern, text, re.IGNORECASE | re.MULTILINE | re.DOTALL)
                if matches:
                    result = matches[0]
                    if isinstance(result, tuple):
                        result = result[0] if result[0] else (result[1] if len(result) > 1 else "")
                    if result and len(result.strip()) > 0:
                        return result.strip()
            except Exception as e:
                print(f"   ⚠️ 正则表达式错误: {pattern}, 错误: {e}")
                continue
        return "官网未公布"
    
    def extract_official_urls(self, text: str) -> List[str]:
        """提取官方网站URL（改进版）"""
        url_patterns = [
            r'https?://[^\s<>"{}|\\^`[\]]+\.[a-zA-Z]{2,}',
            r'www\.[^\s<>"{}|\\^`[\]]+\.[a-zA-Z]{2,}',
            r'[a-zA-Z0-9.-]+\.(?:com|com\.cn|cn|net|org)(?:/[^\s]*)?'
        ]
        
        all_urls = []
        for pattern in url_patterns:
            urls = re.findall(pattern, text, re.IGNORECASE)
            all_urls.extend(urls)
        
        # 过滤出可能的官方网站
        official_urls = []
        for url in all_urls:
            # 添加协议头
            if not url.startswith('http'):
                url = 'https://' + url
            
            # 检查是否包含官网关键特征
            url_lower = url.lower()
            if any(keyword in url_lower for keyword in ['.com', '.com.cn', '.cn', '.net', '.org']):
                # 排除明显的第三方网站
                excluded_domains = ['baidu.com', 'google.com', 'bing.com', 'zhihu.com', 'csdn.net', 
                                   'weibo.com', 'qq.com', 'sina.com', 'sohu.com', '163.com']
                if not any(excluded in url_lower for excluded in excluded_domains):
                    official_urls.append(url)
        
        return list(set(official_urls))  # 去重
    
    def assess_credibility(self, value: str, context: str) -> str:
        """评估数据来源可信度（放宽条件）"""
        
        # 检查是否包含官网验证关键词
        official_indicators = self.cleaning_rules["官网验证关键词"]
        for indicator in official_indicators:
            if indicator in context:
                return "官网"
        
        # 检查是否有URL链接作为来源
        if "http" in context:
            return "官网"
        
        # 检查是否包含明显不可信关键词
        unreliable_indicators = self.cleaning_rules["移除关键词"]
        for indicator in unreliable_indicators:
            if indicator in value:  # 改为检查值本身，而不是整个上下文
                return "无法验证"
        
        # 默认返回第三方（而不是无法验证）
        return "第三方"
    
    def clean_data(self, value: str) -> str:
        """清洗数据（改进版）"""
        if not value or value == "官网未公布":
            return "官网未公布"
            
        # 移除不可信关键词
        for keyword in self.cleaning_rules["移除关键词"]:
            value = value.replace(keyword, "")
        
        # 基础清洗
        value = re.sub(r'\s+', ' ', value)  # 多空格合并
        value = re.sub(r'^[：:\-\s]+', '', value)  # 移除开头的标点
        value = re.sub(r'[：:\-\s]+$', '', value)  # 移除结尾的标点
        value = value.strip()
        
        # 移除过短的值
        if len(value) < 2:
            return "官网未公布"
        
        return value if value else "官网未公布"
    
    def calculate_overall_credibility(self, data: Dict[str, Any], raw_response: str) -> str:
        """计算整体数据可信度（调整评分标准）"""
        
        # 统计有效数据字段数
        valid_fields = sum(1 for v in data.values() if v != "官网未公布" and v != "")
        total_fields = len([f for f in self.csv_fields if f not in ["信息更新时间", "数据可信度"]])
        
        # 检查是否有官网链接
        has_official_url = data.get("官网链接", "官网未公布") != "官网未公布"
        
        # 检查官网验证关键词出现频率
        official_keywords_count = sum(1 for keyword in self.cleaning_rules["官网验证关键词"] if keyword in raw_response)
        
        # 调整评分标准（更宽松）
        if has_official_url and valid_fields >= total_fields * 0.4:
            return "A级 - 官方数据"
        elif has_official_url or valid_fields >= total_fields * 0.3:
            return "B级 - 部分官方数据"
        elif valid_fields >= total_fields * 0.1:
            return "C级 - 基础数据"
        else:
            return "D级 - 数据不足"
    
    def export_to_csv(self, data_list: List[Dict[str, Any]], filename: str) -> str:
        """导出数据到CSV文件"""
        
        if not data_list:
            return "没有数据可导出"
        
        try:
            # 创建DataFrame
            df = pd.DataFrame(data_list)
            
            # 确保所有CSV字段都存在
            for field in self.csv_fields:
                if field not in df.columns:
                    df[field] = "官网未公布"
            
            # 按照字段顺序重新排列列
            df = df[self.csv_fields]
            
            # 导出CSV
            df.to_csv(
                filename,
                encoding=self.output_config["encoding"],
                index=self.output_config["index"],
                na_rep=self.output_config["na_rep"]
            )
            
            return f"✅ CSV文件已导出: {filename}"
            
        except Exception as e:
            return f"❌ CSV导出失败: {str(e)}"
    
    def export_to_excel(self, data_list: List[Dict[str, Any]], filename: str) -> str:
        """导出数据到Excel文件"""
        
        if not data_list:
            return "没有数据可导出"
        
        try:
            # 创建DataFrame
            df = pd.DataFrame(data_list)
            
            # 确保所有CSV字段都存在
            for field in self.csv_fields:
                if field not in df.columns:
                    df[field] = "官网未公布"
            
            # 按照字段顺序重新排列列
            df = df[self.csv_fields]
            
            # 创建Excel写入器
            with pd.ExcelWriter(filename, engine='openpyxl') as writer:
                # 写入主数据表
                df.to_excel(writer, sheet_name='企业数据', index=False)
                
                # 创建数据质量统计表
                quality_stats = self.generate_quality_statistics(data_list)
                quality_df = pd.DataFrame(quality_stats)
                quality_df.to_excel(writer, sheet_name='数据质量统计', index=False)
            
            return f"✅ Excel文件已导出: {filename}"
            
        except Exception as e:
            return f"❌ Excel导出失败: {str(e)}"
    
    def generate_quality_statistics(self, data_list: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """生成数据质量统计"""
        
        if not data_list:
            return []
        
        stats = []
        total_companies = len(data_list)
        
        # 统计各字段的完整度
        for field in self.csv_fields:
            if field in ["信息更新时间", "数据可信度"]:
                continue
                
            valid_count = sum(1 for data in data_list if data.get(field, "官网未公布") != "官网未公布")
            completion_rate = (valid_count / total_companies) * 100
            
            stats.append({
                "字段名称": field,
                "有效数据数量": valid_count,
                "总企业数量": total_companies,
                "完整度百分比": f"{completion_rate:.1f}%"
            })
        
        # 按完整度排序
        stats.sort(key=lambda x: float(x["完整度百分比"].replace('%', '')), reverse=True)
        
        return stats
    
    def validate_official_data(self, data: Dict[str, Any]) -> Dict[str, str]:
        """验证官网数据的有效性"""
        
        validation_result = {}
        
        # 检查是否有官网链接
        if data.get("官网链接", "官网未公布") == "官网未公布":
            validation_result["官网链接"] = "❌ 缺少官网链接"
        else:
            validation_result["官网链接"] = "✅ 有官网链接"
        
        # 检查基础信息完整度
        basic_fields = ["企业全称", "成立时间", "总部地址", "主营产品类别"]
        basic_completion = sum(1 for field in basic_fields if data.get(field, "官网未公布") != "官网未公布")
        validation_result["基础信息完整度"] = f"{basic_completion}/{len(basic_fields)}"
        
        # 检查产品信息完整度
        product_fields = ["主营产品类别", "核心产品型号", "产品应用领域", "技术特点"]
        product_completion = sum(1 for field in product_fields if data.get(field, "官网未公布") != "官网未公布")
        validation_result["产品信息完整度"] = f"{product_completion}/{len(product_fields)}"
        
        # 整体评级
        total_valid = sum(1 for v in data.values() if v != "官网未公布")
        total_fields = len(self.csv_fields) - 2  # 排除时间和可信度字段
        
        if total_valid >= total_fields * 0.8:
            validation_result["整体评级"] = "A级 - 信息完整"
        elif total_valid >= total_fields * 0.6:
            validation_result["整体评级"] = "B级 - 信息较完整"
        else:
            validation_result["整体评级"] = "C级 - 信息不完整"
        
        return validation_result 