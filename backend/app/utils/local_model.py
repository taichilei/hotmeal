import logging
import os

from llama_cpp import Llama

# 全局变量，用于缓存本地模型实例，确保只加载一次
_local_model_instance = None


def get_local_model() -> Llama:
    """
    加载并返回本地 Llama 模型实例。
    如果模型尚未加载，则根据模型文件路径加载，并缓存实例。

    Returns:
        Llama: 已加载的本地模型实例。

    Raises:
        Exception: 如果模型加载失败，则抛出异常。
    """
    global _local_model_instance
    if _local_model_instance is None:
        try:
            # 获取当前文件所在目录
            base_dir = os.path.dirname(os.path.abspath(__file__))
            # 假设模型文件放在 backend/llm 目录下，调整路径以适应项目结构
            # 如果 local_model.py 位于 backend 文件夹下，则模型路径为 backend/llm
            model_path = os.path.join(base_dir, "llm", "tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf")

            # 初始化本地模型，参数可以根据实际情况调整
            _local_model_instance = Llama(model_path=model_path, n_ctx=512, n_gpu_layers=0)
            logging.info(f"成功加载本地模型: {model_path}")
        except Exception as ex:
            logging.error("加载本地模型失败", exc_info=True)
            raise Exception("加载本地模型失败") from ex
    return _local_model_instance


if __name__ == "__main__":
    # 测试本地模型加载与调用
    model = get_local_model()
    prompt = "你好，欢迎使用本地模型！"
    output = model(prompt)
    # 根据返回值结构提取回复
    if isinstance(output, dict) and "choices" in output and len(output["choices"]) > 0:
        reply = output["choices"][0].get("text", "").strip()
    elif isinstance(output, str):
        reply = output.strip()
    else:
        reply = "未知回复格式"
    print("模型回复:", reply)
