"""
Lite Research UI组件模块
包含样式定义和静态UI组件
"""

import streamlit as st

# 版本号
VERSION = "1.0.0"


def apply_styles():
    """应用页面样式"""
    st.markdown("""
    <style>
    .stTextInput>div>div>input {
        border-color: #E0E0E0;
    }
    .stProgress > div > div > div > div {
        background-color: #4F8BF9;
    }
    h2, h3, h4 {
        border-bottom: 2px solid !important;
        padding-bottom: 0.5rem !important;
        margin-bottom: 1rem !important;
    }
    h2 {
        color: #1E90FF !important;
        border-bottom-color: #1E90FF !important;
        font-size: 1.8rem !important;
        margin-top: 1.5rem !important;
    }
    h3 {
        color: #16A085 !important;
        border-bottom-color: #16A085 !important;
        font-size: 1.5rem !important;
        margin-top: 1rem !important;
    }
    h4 {
        color: #E67E22 !important;
        border-bottom-color: #E67E22 !important;
        font-size: 1.2rem !important;
        margin-top: 0.5rem !important;
    }
    .workflow-container {
        background-color: rgba(248, 249, 250, 0.8);
        border-radius: 0.5rem;
        padding: 1.5rem;
        margin-bottom: 1.5rem;
        border: 1px solid rgba(0, 0, 0, 0.125);
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
    }
    .workflow-step {
        margin-bottom: 1rem;
        padding: 0.8rem;
        background: white;
        border-radius: 0.3rem;
        border-left: 4px solid #4F8BF9;
    }
    .footer {
        margin-top: 3rem;
        padding: 2rem 0;
        text-align: center;
        color: #666;
        border-top: 1px solid #E0E0E0;
    }
    .footer a {
        color: #4F8BF9;
        text-decoration: none;
    }
    .footer a:hover {
        text-decoration: underline;
    }
    @media (prefers-color-scheme: dark) {
        .workflow-container {
            background-color: rgba(33, 37, 41, 0.8);
            border-color: rgba(255, 255, 255, 0.125);
        }
        .workflow-step {
            background: rgba(255, 255, 255, 0.05);
        }
        h1, h2 {
            color: #3498DB;
            border-bottom-color: #3498DB;
        }
        h3 {
            color: #2ECC71;
            border-bottom-color: #2ECC71;
        }
        h4 {
            color: #F39C12;
            border-bottom-color: #F39C12;
        }
    }
    </style>
    """, unsafe_allow_html=True)


def display_header():
    """显示页面标题"""
    st.title("🔍 Lite Research")
    st.markdown("---")


def display_info_message():
    """显示Lite Research的功能介绍"""
    st.info(
        """
    **Lite Research**是一个基于大语言模型的智能研究工具，旨在协助用户进行深入的主题研究。

    该工具能够根据用户提供的主题自动生成相关子查询，从多个来源收集信息，并进行分析整理。
    系统支持多种报告类型和语气，可根据用户需求生成定制化的研究报告。
    
    ✨ **适用场景**：学术研究、市场调研、技术分析、行业报告等需要快速获取和整理特定主题信息的场景。
    """
    )


def display_workflow():
    """显示Lite Research的工作流程"""
    with st.expander("📝 查看Lite Research工作流程", expanded=False):
        st.markdown(
            """
            <div class="workflow-container">
                <div class="workflow-step">
                    <strong>🎯 1. 智能代理选择</strong><br>
                    根据研究主题，系统自动选择合适的AI代理角色和专业指令。
                </div>
                <div class="workflow-step">
                    <strong>🔍 2. 子查询生成</strong><br>
                    AI代理根据主题生成多个相关的子查询，以全面覆盖研究范围。
                </div>
                <div class="workflow-step">
                    <strong>⚡ 3. 并行信息检索</strong><br>
                    系统同时处理多个子查询，从网络搜索引擎获取相关信息。
                </div>
                <div class="workflow-step">
                    <strong>🧠 4. 上下文压缩</strong><br>
                    使用嵌入技术和相似度匹配，从检索到的大量信息中提取最相关的内容。
                </div>
                <div class="workflow-step">
                    <strong>📄 5. 报告生成</strong><br>
                    根据压缩后的上下文信息，生成结构化的研究报告，并根据指定的语气和格式进行调整。
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def display_footer():
    """显示页脚信息"""
    st.markdown(
        f"""
        <div class="footer">
            <p>© 2024 Lite Research | 
            <a href="https://github.com/i-richardwang/literesearch" target="_blank">GitHub项目</a> | 
            作者：Richard Wang</p>
            <p><small>基于大语言模型技术构建的智能研究工具 | Version {VERSION}</small></p>
        </div>
        """,
        unsafe_allow_html=True
    )


def get_report_type_display_map():
    """获取报告类型的显示映射"""
    return {
        "research_report": "📊 综合研究报告（全面分析和总结）",
        "resource_report": "📚 资源汇总报告（相关资料和参考文献列表）",
        "outline_report": "📝 研究大纲（主要观点和结构框架）",
        "detailed_report": "📋 详细深度报告（全面且深入的分析）",
        "custom_report": "⚙️ 自定义报告（根据特定需求定制）",
        "subtopic_report": "🔬 子主题报告（特定子话题的深入分析）",
    }


def show_success_message():
    """显示研究完成的成功消息"""
    st.success("✅ 研究完成！")
    st.balloons()  # 添加庆祝效果


def show_error_message(message):
    """显示错误消息"""
    st.error(f"⚠️ {message}") 