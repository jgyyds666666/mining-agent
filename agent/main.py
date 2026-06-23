"""矿权日报 Agent — 入口"""

import asyncio
import logging
import os
import sys

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("agent")

# 抑制 noisy 日志
logging.getLogger("mcp").setLevel(logging.WARNING)
logging.getLogger("openai").setLevel(logging.WARNING)


async def main():
    # 获取用户查询
    if len(sys.argv) > 1:
        query = " ".join(sys.argv[1:])
    else:
        print("=" * 50)
        print("  矿权日报 Agent v1.0")
        print("  输入查询内容，例如：")
        print('    "给我生成一份关于 Pilbara 锂矿的今日简报"')
        print("    "生成一份关于赣锋锂业的报告"")
        print("  输入 q 或 exit 退出")
        print("=" * 50)
        query = input("\n📝 请输入查询: ").strip()
        if query.lower() in ("q", "exit", "quit", ""):
            print("👋 再见")
            return

    # 检查 DeepSeek API Key
    if not os.environ.get("DEEPSEEK_API_KEY"):
        logger.warning("DEEPSEEK_API_KEY 未设置，将使用模板模式生成报告（不含智能分析）")

    logger.info("🔄 开始处理查询: %s", query)

    try:
        from graph import run_agent

        report = await run_agent(query)

        print("\n" + "=" * 55)
        print(report)
        print("=" * 55)
        print("\n✅ 报告生成完毕")

    except Exception as exc:
        logger.exception("Agent 运行失败")
        print(f"\n❌ 生成报告时出错: {exc}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
