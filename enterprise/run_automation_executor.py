"""Entry point for the automation executor.

Usage: python -m run_automation_executor

This runs as a Kubernetes Deployment (long-running). It polls the automation_events
inbox, matches events to automations, claims and executes runs, and monitors
conversation completion.

Environment variables:
    OPENHANDS_API_URL        Base URL for the V1 API (default: http://openhands-service:3000)
    MAX_CONCURRENT_RUNS      Max concurrent runs per executor (default: 5)
    RUN_TIMEOUT_SECONDS      Max time for a single run (default: 7200)
    POLL_INTERVAL_SECONDS    Fallback poll interval (default: 30)
    HEARTBEAT_INTERVAL_SECONDS  Heartbeat update interval (default: 60)
"""

import asyncio
import logging
import signal
import sys

logger = logging.getLogger('saas.automation.executor')


def _setup_logging() -> None:
    """Configure logging, deferring to enterprise logger if available."""
    try:
        from server.logger import setup_all_loggers

        setup_all_loggers()
    except ImportError:
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s %(name)s %(levelname)s %(message)s',
            stream=sys.stdout,
        )


def _install_signal_handlers(loop: asyncio.AbstractEventLoop) -> None:
    """Install signal handlers for graceful shutdown."""
    from services.automation_executor import request_shutdown

    def _handle_signal(signum: int, _frame: object) -> None:
        sig_name = signal.Signals(signum).name
        logger.info('Received %s, initiating graceful shutdown...', sig_name)
        request_shutdown()

    for sig in (signal.SIGTERM, signal.SIGINT):
        signal.signal(sig, _handle_signal)


async def main() -> None:
    from services.automation_executor import executor_main

    await executor_main()


if __name__ == '__main__':
    _setup_logging()

    loop = asyncio.new_event_loop()
    _install_signal_handlers(loop)

    logger.info('Starting automation executor')
    try:
        loop.run_until_complete(main())
    except KeyboardInterrupt:
        logger.info('Interrupted by user')
    finally:
        loop.close()
        logger.info('Automation executor process exiting')
