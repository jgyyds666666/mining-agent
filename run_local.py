"""本地一键启动：同时启动 3 个 MCP Server + 运行 Agent"""

import asyncio
import json
import logging
import os
import sys
import time
import subprocess
import webbrowser

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("launcher")

# 项目根目录
ROOT = os.path.dirname(os.path.abspath(__file__))

MCP_SERVERS = {
    "mining-news-mcp": {
        "path": os.path.join(ROOT, "servers", "mining-news-mcp", "server.py"),
        "port": 8001,
    },
    "mineral-pdf-mcp": {
        "path": os.path.join(ROOT, "servers", "mineral-pdf-mcp", "server.py"),
        "port": 8002,
    },
    "lme-price-mcp": {
        "path": os.path.join(ROOT, "servers", "lme-price-mcp", "server.py"),
        "port": 8003,
    },
}

processes = []


def check_port(port: int) -> bool:
    """Check if a port is in use (quick check)."""
    import socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(("127.0.0.1", port)) == 0


def start_servers():
    """Start all 3 MCP servers as subprocesses."""
    for name, info in MCP_SERVERS.items():
        if check_port(info["port"]):
            logger.warning("%s 端口 %d 已被占用，跳过", name, info["port"])
            continue

        logger.info("启动 %s (端口 %d)...", name, info["port"])
        proc = subprocess.Popen(
            [sys.executable, info["path"]],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            cwd=os.path.dirname(info["path"]),
        )
        processes.append((name, proc))

    # 等待所有服务就绪
    logger.info("等待服务启动...")
    for _ in range(30):  # 最多等 30 秒
        all_ready = all(
            check_port(info["port"])
            for name, info in MCP_SERVERS.items()
            if name in [p[0] for p in processes]
        )
        if all_ready:
            logger.info("所有 MCP Server 已就绪 ✅")
            return True
        time.sleep(1)

    logger.error("服务启动超时")
    return False


def stop_servers():
    """Stop all running server processes."""
    for name, proc in processes:
        logger.info("停止 %s...", name)
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
    processes.clear()
    logger.info("所有服务已停止")


async def run_agent(query: str):
    """Run the agent with the given query."""
    agent_main = os.path.join(ROOT, "agent", "main.py")
    subprocess.run([sys.executable, agent_main, query], cwd=ROOT)


def main():
    # 设置 DeepSeek Key
    if not os.environ.get("DEEPSEEK_API_KEY"):
        key = input("请输入你的 DeepSeek API Key（直接回车跳过，使用模板模式）: ").strip()
        if key:
            os.environ["DEEPSEEK_API_KEY"] = key
            # 也写入当前进程的环境变量
            os.environ["DEEPSEEK_API_KEY"] = key

    # 获取查询
    if len(sys.argv) > 1:
        query = " ".join(sys.argv[1:])
    else:
        query = input("请输入查询（例如: 给我生成一份关于 Pilbara 锂矿的今日简报）: ").strip()
        if not query:
            query = "给我生成一份关于 Pilbara 锂矿的今日简报"
            print(f"使用默认查询: {query}")

    try:
        # 启动 MCP 服务
        logger.info("=" * 50)
        logger.info("启动 MCP Server...")
        logger.info("=" * 50)

        if not start_servers():
            logger.error("启动失败，退出")
            return

        # 运行 Agent
        logger.info("=" * 50)
        logger.info("运行矿权日报 Agent...")
        logger.info("=" * 50)
        asyncio.run(run_agent(query))

    finally:
        stop_servers()


if __name__ == "__main__":
    main()
