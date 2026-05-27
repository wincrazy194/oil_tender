"""
定时调度器 - 每天自动运行招投标采集脚本
使用 schedule 库实现定时任务
"""
import os
import sys
import time
import schedule
import logging
from datetime import datetime

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import SCHEDULE_TIME

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(os.path.dirname(__file__), 'logs', 'scheduler.log'), encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def run_collector():
    """
    执行采集任务
    """
    logger.info("=" * 60)
    logger.info(f"开始执行采集任务 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 60)

    try:
        # 导入并执行采集脚本
        from collector import main as collect_main
        collect_main()
        logger.info("采集任务执行成功")
    except Exception as e:
        logger.error(f"采集任务执行失败：{e}", exc_info=True)

    logger.info("=" * 60)
    logger.info(f"任务结束 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 60)


def main():
    """
    主函数 - 启动定时调度器
    """
    # 获取配置的调度时间（格式：HH:MM）
    schedule_time = SCHEDULE_TIME if SCHEDULE_TIME else "10:00"

    logger.info("=" * 60)
    logger.info("招投标采集定时调度器")
    logger.info("=" * 60)
    logger.info(f"配置的每日运行时间：{schedule_time}")
    logger.info(f"当前时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 60)

    # 注册定时任务
    schedule.every().day.at(schedule_time).do(run_collector)

    logger.info(f"定时任务已注册：每天 {schedule_time} 运行")
    logger.info("调度器正在运行... 按 Ctrl+C 停止")
    logger.info("")

    # 立即执行一次（可选，如果希望启动时就执行一次）
    run_immediately = os.environ.get("SCHEDULER_RUN_IMMEDIATELY", "false").lower() == "true"
    if run_immediately:
        logger.info("检测到 SCHEDULER_RUN_IMMEDIATELY=true，立即执行一次采集任务...")
        run_collector()

    # 主循环
    while True:
        schedule.run_pending()
        time.sleep(60)  # 每分钟检查一次是否有任务需要执行


if __name__ == "__main__":
    main()
