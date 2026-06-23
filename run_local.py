"""本地一键启动：同时启动 3 个 MCP Server + 运行 Agent"""

import asyncio
import logging
import os
import sys
import time
import subprocess
import threading

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("launcher")

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
    import socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(1)
        return s.connect_ex(("127.0.0.1", port)) == 0


def _print_output(proc: subprocess.Popen, name: str):
    """Print subprocess output in real-time, line by line."""
    try:
        for line in iter(proc.stdout.readline, b""):
            text = line.decode("utf-8", errors="replace").rstrip()
            if text:
                print(f"  [{name}] {text}")
    except Exception:
        pass


def start_servers():
    """启动 3 个 MCP Server，实时显示日志。"""
    logger.info("=" * 50)
    logger.info("正在启动 3 个 MCP Server...")
    logger.info("=" * 50)

    for name, info in MCP_SERVERS.items():
        if check_port(info["port"]):
            logger.warning("⚠️   %s 端口 %d 已被占用，跳过", name, info["port"])
            continue

        logger.info("▶️  启动 %s (端口 %d)", name, info["port"])
        proc = subprocess.Popen(
            [sys.executable, info["path"]],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            cwd=os.path.dirname(info["path"]),
        )
        processes.append((name, proc))

        # 启动后台线程打印输出
        t = threading.Thread(target=_print_output, args=(proc, name), daemon=True)
        t.start()

    # 等待服务就绪，每 2 秒显示状态
    logger.info("")
    logger.info("⏳ 等待服务启动（最多 60 秒）...")
    for i in range(60):
        ready = []
        not_ready = []
        for name, info in MCP_SERVERS.items():
            if name in [p[0] for p in processes]:
                if check_port(info["port"]):
                    ready.append(name)
                else:
                    not_ready.append(name)

        if not_ready:
            status = f"[{', '.join(ready)}] ✅  /  [{', '.join(not_ready)}] ⏳"
            if i % 5 == 0 or i < 3:  # 每 5 秒或前 3 次显示
                print(f"  第 {i+1} 秒: {status}")
            time.sleep(1)
        else:
            print(f"\n✅ 所有 MCP Server 已就绪！")
            return True

    logger.error("❌ 服务启动超时")
    return False


def stop_servers():
    for name, proc in processes:
        logger.info("停止 %s...", name)
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
    processes.clear()
    logger.info("已停止所有服务")


async def run_agent(query: str):
    agent_main = os.path.join(ROOT, "agent", "main.py")
    logger.info("")
    logger.info("=" * 50)
    logger.info("📋 正在生成矿权日报...")
    logger.info("=" * 50)
    result = subprocess.run(
        [sys.executable, agent_main, query],
        cwd=ROOT,
    )
    if result.returncode != 0:
        logger.error("Agent 运行失败 (exit code %d)", result.returncode)


def main():
    # API Key
    if not os.environ.get("DEEPSEEK_API_KEY"):
        key = input("🔑 请输入 DeepSeek API Key（直接回车跳过，使用模板模式）: ").strip()
        if key:
            os.environ["DEEPSEEK_API_KEY"] = key

    # Query
    if len(sys.argv) > 1:
        query = " ".join(sys.argv[1:])
    else:
        query = input("📝 请输入查询: ").strip()
        if not query:
            query = "给我生成一份关于 Pilbara 锂矿的今日简报"
            print(f"  使用默认查询: {query}")

    try:
        if not start_servers():
            sys.exit(1)
        asyncio.run(run_agent(query))
    except KeyboardInterrupt:
        print("\n\n⚠️  用户中断")
    finally:
        stop_servers()


if __name__ == "__main__":
    main()
