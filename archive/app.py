import gradio as gr
import subprocess
import sys

def get_system_status():
    """直接调用你那个跑得通的系统检测脚本"""
    try:
        result = subprocess.run(
            [sys.executable, "system_status.py"],
            capture_output=True,
            text=True,
            cwd="C:/MSS-AI-Project",
            encoding='utf-8'  # 强制使用 UTF-8 解码，防止中文乱码
        )
        return result.stdout
    except Exception as e:
        return f"获取状态失败: {str(e)}"

# 创建界面
with gr.Blocks(title="MSS-AI 指挥中心") as demo:
    gr.Markdown("# 🛸 MSS-AI 战术指挥中心")
    gr.Markdown("系统核心引擎运行正常，点击下方按钮刷新状态。")

    output_box = gr.Textbox(label="系统状态报告", lines=20)
    refresh_btn = gr.Button("🔄 刷新系统状态")

    # 点击按钮就运行检测
    refresh_btn.click(get_system_status, outputs=output_box)

    # 页面加载时也自动运行一次
    demo.load(get_system_status, outputs=output_box)

if __name__ == "__main__":
    demo.launch(server_port=7860, share=False)
