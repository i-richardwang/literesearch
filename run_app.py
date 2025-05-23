#!/usr/bin/env python3
"""
Lite Research 启动脚本
"""

import subprocess
import sys
import os

def main():
    """启动 Lite Research 应用"""
    
    # 确保在项目根目录
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)
    
    # 应用文件路径
    app_file = os.path.join("frontend", "literesearch_app.py")
    
    if not os.path.exists(app_file):
        print(f"❌ 错误：找不到应用文件 {app_file}")
        return 1
    
    print("🚀 正在启动 Lite Research...")
    print(f"📂 工作目录：{script_dir}")
    print(f"📄 应用文件：{app_file}")
    print("-" * 50)
    
    try:
        # 启动streamlit应用
        cmd = [sys.executable, "-m", "streamlit", "run", app_file]
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        print(f"❌ 启动失败：{e}")
        return 1
    except KeyboardInterrupt:
        print("\n👋 应用已关闭")
        return 0

if __name__ == "__main__":
    sys.exit(main()) 