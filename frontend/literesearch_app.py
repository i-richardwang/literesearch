# Lite Research 主程序

import streamlit as st
import asyncio
import sys
import os

# 导入依赖 - 使用相对路径导入而不是修改sys.path
try:
    from backend.literesearch.literesearcher import LiteResearcher
    from backend.literesearch.research_enums import ReportType, Tone
    from backend.literesearch.constants import (
        MIN_QUERY_LENGTH,
        MAX_ITERATIONS_LIMIT,
        MAX_SUBTOPICS_LIMIT,
        MAX_SEARCH_RESULTS_LIMIT,
        MIN_ITERATIONS,
        MIN_SUBTOPICS,
        MIN_SEARCH_RESULTS
    )
except ImportError:
    # 如果相对导入失败，添加项目根目录到路径
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
    
    from backend.literesearch.literesearcher import LiteResearcher
    from backend.literesearch.research_enums import ReportType, Tone
    from backend.literesearch.constants import (
        MIN_QUERY_LENGTH,
        MAX_ITERATIONS_LIMIT,
        MAX_SUBTOPICS_LIMIT,
        MAX_SEARCH_RESULTS_LIMIT,
        MIN_ITERATIONS,
        MIN_SUBTOPICS,
        MIN_SEARCH_RESULTS
    )

from langchain_core.globals import set_llm_cache
from langchain_community.cache import SQLiteCache

# 设置缓存目录
cache_dir = os.path.join(os.path.dirname(__file__), "..", "data", "llm_cache")
os.makedirs(cache_dir, exist_ok=True)
set_llm_cache(SQLiteCache(database_path=os.path.join(cache_dir, "langchain.db")))

from frontend.ui_components import (
    apply_styles, 
    display_header, 
    display_info_message, 
    display_workflow, 
    display_footer,
    get_report_type_display_map,
    show_success_message,
    show_error_message
)

# 设置页面配置
st.set_page_config(
    page_title="Lite Research",
    page_icon="🔍",
    initial_sidebar_state="collapsed"
)


def main():
    """主程序入口"""
    # 应用样式
    apply_styles()
    
    # 初始化session state
    initialize_session_state()

    # 页面布局
    display_header()
    display_info_message()
    display_workflow()
    display_research_settings()
    display_report()
    display_footer()


def initialize_session_state():
    """初始化session state"""
    if "generated_report" not in st.session_state:
        st.session_state.generated_report = ""
    if "verbose_output" not in st.session_state:
        st.session_state.verbose_output = ""


def display_research_settings():
    """显示研究设置界面"""
    st.markdown("## 研究设置")
    with st.container(border=True):
        # 研究主题输入
        query = st.text_input(
            "请输入您的研究主题：",
            placeholder="例如：人工智能在教育领域的应用现状"
        )

        # 基础设置
        col1, col2 = st.columns(2)
        with col1:
            tone = st.selectbox(
                "请选择报告语气：", 
                options=[tone.value for tone in Tone],
                help="选择报告的写作风格和语气"
            )

        with col2:
            report_type = st.selectbox(
                "请选择报告类型：",
                options=[type.value for type in ReportType],
                format_func=lambda x: get_report_type_display_map().get(x, x),
                help="选择最符合您需求的报告类型"
            )

        # 高级设置
        max_iterations, max_subtopics, max_search_results_per_query = display_advanced_settings()

        # 开始研究按钮
        if st.button("🚀 开始研究", type="primary", use_container_width=True):
            handle_research_request(
                query, 
                tone, 
                report_type, 
                max_iterations, 
                max_subtopics, 
                max_search_results_per_query
            )


def display_advanced_settings():
    """显示高级设置并返回参数值"""
    with st.expander("⚙️ 高级设置"):
        st.markdown("**调整以下参数可以控制研究的深度和广度**")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            max_iterations = st.slider(
                "最大子查询数量",
                min_value=1,
                max_value=10,
                value=3,
                help="控制子查询的最大数量，数量越多覆盖面越广"
            )
        
        with col2:
            max_subtopics = st.slider(
                "最大子主题数",
                min_value=1,
                max_value=10,
                value=3,
                help="控制详细报告中子主题的最大数量"
            )
        
        with col3:
            max_search_results_per_query = st.slider(
                "每个查询的最大搜索结果数",
                min_value=1,
                max_value=20,
                value=5,
                help="控制每个子查询的最大搜索结果数，数量越多信息越丰富"
            )
    
    return max_iterations, max_subtopics, max_search_results_per_query


def handle_research_request(query, tone, report_type, max_iterations, max_subtopics, max_search_results_per_query):
    """处理研究请求"""
    # 输入验证
    if not query or not query.strip():
        show_error_message("请输入研究主题后再开始研究")
        return
    
    if len(query.strip()) < MIN_QUERY_LENGTH:
        show_error_message(f"研究主题至少需要{MIN_QUERY_LENGTH}个字符")
        return
    
    if max_iterations < MIN_ITERATIONS or max_iterations > MAX_ITERATIONS_LIMIT:
        show_error_message(f"最大子查询数量必须在{MIN_ITERATIONS}-{MAX_ITERATIONS_LIMIT}之间")
        return
        
    if max_subtopics < MIN_SUBTOPICS or max_subtopics > MAX_SUBTOPICS_LIMIT:
        show_error_message(f"最大子主题数必须在{MIN_SUBTOPICS}-{MAX_SUBTOPICS_LIMIT}之间")
        return
        
    if max_search_results_per_query < MIN_SEARCH_RESULTS or max_search_results_per_query > MAX_SEARCH_RESULTS_LIMIT:
        show_error_message(f"每个查询的最大搜索结果数必须在{MIN_SEARCH_RESULTS}-{MAX_SEARCH_RESULTS_LIMIT}之间")
        return
    
    # 清空之前的输出
    st.session_state.verbose_output = ""
    
    with st.spinner("🔍 正在进行研究，请稍候..."):
        # 创建研究进度显示区域
        verbose_expander = st.expander("📊 显示研究进度", expanded=True)
        
        with verbose_expander:
            verbose_container = st.empty()

        # 创建回调函数来更新详细信息
        def update_verbose(message):
            st.session_state.verbose_output += message + "\n"
            verbose_container.text(st.session_state.verbose_output)

        # 执行研究
        report = run_research(
            query.strip(), 
            report_type, 
            tone, 
            update_verbose, 
            max_iterations, 
            max_subtopics, 
            max_search_results_per_query
        )
        
        if report:
            st.session_state.generated_report = report
            show_success_message()


def run_research(query, report_type, tone, verbose_callback, max_iterations, max_subtopics, max_search_results_per_query):
    """运行AI研究过程"""
    try:
        # 创建 LiteResearcher 实例
        researcher = LiteResearcher(
            query=query,
            report_type=report_type,
            tone=Tone(tone),
            verbose=True,
            verbose_callback=verbose_callback,
            max_iterations=max_iterations,
            max_subtopics=max_subtopics,
            max_search_results_per_query=max_search_results_per_query,
        )

        # 运行研究过程
        report = asyncio.run(researcher.run())
        return report
        
    except ValueError as e:
        st.error(f"参数错误：{str(e)}")
        return None
    except Exception as e:
        st.error(f"研究过程中发生错误：{str(e)}")
        import traceback
        print(f"详细错误信息：{traceback.format_exc()}")
        return None


def display_report():
    """显示研究报告"""
    if st.session_state.generated_report:
        st.markdown("## 📄 研究报告")
        with st.container(border=True):
            st.markdown(st.session_state.generated_report)

        # 添加下载按钮
        display_download_button()


def display_download_button():
    """显示下载按钮"""
    col1, col2 = st.columns([1, 3])
    with col1:
        st.download_button(
            label="📥 下载报告 (Markdown)",
            data=st.session_state.generated_report,
            file_name="AI研究报告.md",
            mime="text/markdown",
            use_container_width=True,
        )


if __name__ == "__main__":
    main() 