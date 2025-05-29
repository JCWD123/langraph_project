# Langraph Project

## 项目简介
本项目基于 LangChain、LangGraph 等 AI 框架，结合多智能体与工作流，支持多种任务自动规划、联网搜索、文档处理与对话交互。适用于智能报告生成、自动化任务分解、AI 辅助写作等场景。

## 主要功能
- 智能需求重写与目标拆解
- 子任务自动规划与执行
- 联网搜索与文档检索（Tavily、OpenAI等）
- 多模型支持（如通义千问、DeepSeek等）
- 支持 PDF、Word、Excel、TXT、Markdown 文件上传与处理
- Streamlit 可视化交互界面

## 依赖环境
请先安装 requirements.txt 中的依赖包：
```bash
pip install -r requirements.txt
```

## 建议 Python 版本
建议使用 **Python 3.10** 或 **Python 3.11**。

- Python 3.10/3.11 兼容性最佳，能充分支持 langchain、openai、streamlit 等主流AI生态库。
- 不建议使用 Python 3.12 及以上，部分依赖库可能尚未完全适配。

## 运行方式
1. 配置好 `.env` 文件，填写所需的 API Key（如 OpenAI、Tavily 等）。
2. 启动 Streamlit 前端：
   ```bash
   streamlit run app.py
   ```
3. 或直接运行命令行主程序：
   ```bash
   python main.py
   ```

## 目录结构
- `main.py`：命令行入口
- `app.py`：Streamlit 前端入口
- `model/`：大模型相关接口
- `graph/`：工作流与状态管理
- `*_agent/`：各类智能体与工具模块
- `requirements.txt`：依赖列表

## 备注
- 如需扩展文档解析能力，可根据实际需求补充 `pypdf`、`python-docx`、`openpyxl` 等库。
- `load_vector_store` 相关依赖请根据实际实现补充。 