"""
PulseTrader.01 - Main Orchestrator
Entry point for the autonomous trading system.
"""
from __future__ import annotations

import asyncio
import signal
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict

import yaml
from dotenv import load_dotenv
from loguru import logger

from services.orchestrator.account_manager import AccountManager
from services.orchestrator.state_manager import StateManager
from services.risk_engine.risk_manager import RiskManager
from services.strategies.crypto_momentum import CryptoMomentumStrategy
from services.strategies.leveraged_etf import LeveragedETFStrategy
from services.strategies.stock_swing import StockSwingStrategy
from services.order_router.order_manager import OrderManager
from services.data_feeds.market_data import MarketDataFeed
from services.learning.performance_analyzer import PerformanceAnalyzer
from services.jobs.daily_report import DailyReportJob
from services.jobs.monday_allocation import MondayAllocationJob
from services.jobs.eod_analysis import EODAnalysisJob
from services.connectors.alpaca_client import AlpacaClient
from services.connectors.connection_health_monitor import ConnectionHealthMonitor
from services.connectors.websocket_client import WebSocketClient
from services.utils.config_validator import validate_config, ConfigValidationError


load_dotenv()


class PulseTraderOrchestrator:
    """
    Main orchestrator for PulseTrader.01 autonomous trading system.
    """

    def __init__(self, config_path: str = "config/main.yaml") -> None:
        self.config_path = Path(config_path)
        self.config = self._load_config()
        self.running = False
        self.shutdown_event = asyncio.Event()

        self._setup_logging()

        # Validate configuration before initialization
        try:
            validate_config()
            logger.info("Configuration validation successful")
        except ConfigValidationError as e:
            logger.critical(f"Configuration validation failed: {e}")
            logger.critical("System startup halted due to invalid configuration")
            raise

        # Initialize AlpacaClient for real API integration
        self.alpaca_client = AlpacaClient(self.config)
        logger.info("AlpacaClient initialized")

        # Initialize ConnectionHealthMonitor
        self.health_monitor = ConnectionHealthMonitor(
            alpaca_client=self.alpaca_client,
            check_interval=self.config.get("monitoring", {}).get("health_check_interval", 60),
            error_threshold=self.config.get("monitoring", {}).get("error_threshold", 5),
            slow_response_threshold=self.config.get("monitoring", {}).get("slow_response_threshold", 5.0)
        )
        # Set preservation mode callback
        self.health_monitor.set_preservation_mode_callback(self._enter_preservation_mode)
        logger.info("ConnectionHealthMonitor initialized")

        # Initialize WebSocketClient for real-time streaming
        self.websocket_client = WebSocketClient(self.config)
        logger.info("WebSocketClient initialized")

        self.state_manager = StateManager()
        self.account_manager = AccountManager(self.config, self.alpaca_client)
        self.risk_manager = RiskManager(self.config)
        self.market_data = MarketDataFeed(self.config, self.alpaca_client)
        self.order_manager = OrderManager(
            self.config,
            self.alpaca_client,
            self.account_manager,
            self.market_data,
            self.risk_manager
        )
        self.performance_analyzer = PerformanceAnalyzer(self.config)

        self.strategies = self._initialize_strategies()
        self.jobs = self._initialize_jobs()

        logger.info("PulseTrader.01 Orchestrator initialized")

    def _load_config(self) -> Dict:
        if not self.config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {self.config_path}")

        with self.config_path.open("r", encoding="utf-8") as file_handle:
            config = yaml.safe_load(file_handle)

        return config

    def _setup_logging(self) -> None:
        """
        Configure logging with support for LOG_LEVEL environment variable.
        
        The log level can be set via:
        1. LOG_LEVEL environment variable (highest priority)
        2. Configuration file logging.level setting
        3. Default to INFO if neither is set
        
        Valid log levels: TRACE, DEBUG, INFO, SUCCESS, WARNING, ERROR, CRITICAL
        """
        import os
        
        # Get log level from environment variable or config
        env_log_level = os.getenv("LOG_LEVEL")
        config_log_level = self.config.get("logging", {}).get("level", "INFO")
        
        # Environment variable takes precedence
        if env_log_level:
            log_level = env_log_level.upper()
            logger.info(f"Using log level from LOG_LEVEL environment variable: {log_level}")
        else:
            log_level = config_log_level.upper()
        
        # Validate log level
        valid_levels = ["TRACE", "DEBUG", "INFO", "SUCCESS", "WARNING", "ERROR", "CRITICAL"]
        if log_level not in valid_levels:
            logger.warning(
                f"Invalid log level '{log_level}'. Valid levels: {', '.join(valid_levels)}. "
                f"Defaulting to INFO."
            )
            log_level = "INFO"
        
        log_config = self.config.get("logging", {})
        log_dir = Path(log_config.get("file", {}).get("location", "logs"))

        log_dir.mkdir(parents=True, exist_ok=True)
        (log_dir / "trades").mkdir(exist_ok=True)
        (log_dir / "system").mkdir(exist_ok=True)

        # Remove default logger
        logger.remove()

        # Add console logger with configured level
        logger.add(
            sys.stdout,
            format=(
                "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | "
                "<cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>"
            ),
            level=log_level,
        )

        # Add system log file with configured level
        logger.add(
            log_dir / "system" / "pulsetrader_{time:YYYY-MM-DD}.log",
            rotation="00:00",
            retention="90 days",
            level=log_level,
            format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function} - {message}",
        )

        # Add trade log file (always DEBUG level for detailed trade tracking)
        logger.add(
            log_dir / "trades" / "trades_{time:YYYY-MM-DD}.log",
            rotation="00:00",
            retention="90 days",
            level="DEBUG",
            filter=lambda record: "trade" in record["extra"],
            format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {extra[trade_id]} | {message}",
        )
        
        logger.info(f"Logging configured with level: {log_level}")

    def _initialize_strategies(self) -> Dict[str, object]:
        strategies: Dict[str, object] = {}
        strategy_config = self.config.get("strategies", {})

        if strategy_config.get("crypto_momentum", {}).get("enabled", False):
            strategies["crypto_momentum"] = CryptoMomentumStrategy(
                config=strategy_config["crypto_momentum"],
                risk_manager=self.risk_manager,
                order_manager=self.order_manager,
                market_data=self.market_data,
            )
            logger.info("Crypto Momentum Strategy initialized")

        if strategy_config.get("leveraged_etf_trend", {}).get("enabled", False):
            strategies["leveraged_etf"] = LeveragedETFStrategy(
                config=strategy_config["leveraged_etf_trend"],
                risk_manager=self.risk_manager,
                order_manager=self.order_manager,
                market_data=self.market_data,
            )
            logger.info("Leveraged ETF Strategy initialized")

        if strategy_config.get("stock_swing", {}).get("enabled", False):
            strategies["stock_swing"] = StockSwingStrategy(
                config=strategy_config["stock_swing"],
                risk_manager=self.risk_manager,
                order_manager=self.order_manager,
                market_data=self.market_data,
            )
            logger.info("Stock Swing Strategy initialized (PDT-aware)")

        return strategies

    def _initialize_jobs(self) -> Dict[str, object]:
        jobs: Dict[str, object] = {}

        if self.config.get("reporting", {}).get("daily", {}).get("enabled", False):
            jobs["daily_report"] = DailyReportJob(
                config=self.config,
                account_manager=self.account_manager,
                performance_analyzer=self.performance_analyzer,
            )

        if (
            self.config.get("accounts", {})
            .get("default", {})
            .get("dividend", {})
            .get("monday_allocation", {})
            .get("enabled", False)
        ):
            jobs["monday_allocation"] = MondayAllocationJob(
                config=self.config,
                account_manager=self.account_manager,
                order_manager=self.order_manager,
            )

        if self.config.get("learning", {}).get("eod_analysis", {}).get("enabled", False):
            jobs["eod_analysis"] = EODAnalysisJob(
                config=self.config,
                performance_analyzer=self.performance_analyzer,
                strategies=self.strategies,
            )

        return jobs

    async def start(self) -> None:
        if self.running:
            logger.warning("System is already running")
            return

        logger.info("=" * 60)
        logger.info("PulseTrader.01 Starting...")
        logger.info("=" * 60)

        if self.config.get("emergency", {}).get("kill_switch", {}).get("enabled", False):
            logger.critical("KILL SWITCH IS ENABLED - Trading is DISABLED")
            logger.critical("Set emergency.kill_switch.enabled to false in config to trade")
            return

        try:
            await self.state_manager.load_state()
            await self.account_manager.initialize()

            account = self.account_manager.get_primary_account()
            equity = await account.get_equity()
            logger.info(f"Current Equity: ${equity:,.2f}")

            current_tier = self.risk_manager.get_current_tier(equity)
            logger.info(
                "Current Tier: {name} (${min_equity:,.0f} - ${max_equity:,.0f})".format(
                    name=current_tier["name"],
                    min_equity=current_tier["range"][0],
                    max_equity=current_tier["range"][1],
                )
            )
            logger.info(
                "Risk Parameters: {min_pct:.1f}% - {max_pct:.1f}% per trade".format(
                    min_pct=current_tier["per_trade_min"],
                    max_pct=current_tier["per_trade_max"],
                )
            )
            logger.info(f"Reserve: 20% (${equity * 0.20:,.2f}) - ALWAYS PROTECTED")

            pdt_unlocked = equity >= 25000
            if pdt_unlocked:
                logger.info("✓ PDT UNLOCKED - Full trading capabilities enabled")
            else:
                remaining = 25000 - equity
                logger.info(f"⚠ PDT LOCKED - ${remaining:,.2f} remaining to unlock")
                logger.info("  Trading: Crypto + Leveraged ETFs only")

            milestone_floors = self.risk_manager.get_milestone_floors(equity)
            if milestone_floors:
                logger.info(f"Milestone Floors Active: {milestone_floors}")

            await self.market_data.connect()
            logger.info("Market data feed connected")

            # Connect WebSocket client for real-time streaming
            await self.websocket_client.connect()
            logger.info("WebSocket client connected")

            # Start connection health monitoring
            await self.health_monitor.start()
            logger.info("Connection health monitoring started")

            for name, strategy in self.strategies.items():
                if hasattr(strategy, "min_equity_required"):
                    if equity < strategy.min_equity_required:
                        logger.info(
                            f"Strategy '{name}' suspended until equity >= ${strategy.min_equity_required:,.0f}"
                        )
                        continue

                await strategy.start()
                logger.info(f"Strategy '{name}' started")

            for name, job in self.jobs.items():
                await job.schedule()
                logger.info(f"Job '{name}' scheduled")

            self.running = True
            logger.info("=" * 60)
            logger.info("PulseTrader.01 is LIVE")
            logger.info("=" * 60)
            logger.success("System startup completed successfully")

            await self._run_loop()

        except Exception as exc:
            logger.exception(f"Error starting system: {exc}")
            await self.stop()
            raise

    async def _run_loop(self) -> None:
        try:
            while self.running:
                if self.shutdown_event.is_set():
                    break

                await self.account_manager.update_state()

                for name, strategy in self.strategies.items():
                    if strategy.is_running:
                        try:
                            await strategy.evaluate()
                        except Exception as exc:
                            logger.error(f"Error in strategy '{name}': {exc}")

                if await self.risk_manager.should_enter_preservation_mode(
                    current_equity=await self.account_manager.get_primary_account().get_equity()
                ):
                    logger.warning("Entering Capital Preservation Mode")
                    await self._enter_preservation_mode()

                await self.state_manager.save_state(
                    {
                        "timestamp": datetime.now().isoformat(),
                        "equity": await self.account_manager.get_primary_account().get_equity(),
                        "positions": await self.account_manager.get_primary_account().get_positions(),
                        "daily_pnl": await self.account_manager.get_primary_account().get_daily_pnl(),
                    }
                )

                await asyncio.sleep(1)

        except asyncio.CancelledError:
            logger.info("Event loop cancelled")
        except Exception as exc:
            logger.exception(f"Error in main loop: {exc}")
            raise

    async def _enter_preservation_mode(self) -> None:
        preservation_config = self.config.get("emergency", {}).get("preservation_mode", {})

        if preservation_config.get("behavior", {}).get("disable_new_entries", False):
            for strategy in self.strategies.values():
                strategy.disable_new_entries()
            logger.warning("New entries DISABLED")

        if preservation_config.get("behavior", {}).get("close_losing_positions", False):
            await self.order_manager.close_losing_positions()
            logger.warning("Closing losing positions")

        if preservation_config.get("behavior", {}).get("tighten_stops", False):
            await self.order_manager.tighten_all_stops()
            logger.warning("Tightening all stop losses")

    async def stop(self) -> None:
        if not self.running:
            logger.warning("System is not running")
            return

        logger.info("=" * 60)
        logger.info("PulseTrader.01 Shutting Down...")
        logger.info("=" * 60)

        self.running = False
        self.shutdown_event.set()

        try:
            for name, strategy in self.strategies.items():
                await strategy.stop()
                logger.info(f"Strategy '{name}' stopped")

            # Stop connection health monitoring
            await self.health_monitor.stop()
            logger.info("Connection health monitoring stopped")

            # Disconnect WebSocket client
            await self.websocket_client.disconnect()
            logger.info("WebSocket client disconnected")

            if self.config.get("emergency", {}).get("close_positions_on_shutdown", False):
                await self.order_manager.close_all_positions()
                logger.info("All positions closed")

            await self.market_data.disconnect()
            logger.info("Market data disconnected")

            await self.state_manager.save_state(
                {
                    "timestamp": datetime.now().isoformat(),
                    "shutdown_reason": "manual",
                    "final_equity": await self.account_manager.get_primary_account().get_equity(),
                }
            )

            logger.info("PulseTrader.01 stopped successfully")

        except Exception as exc:
            logger.exception(f"Error during shutdown: {exc}")
            raise

    def handle_signal(self, signum, frame) -> None:
        logger.info(f"Received signal {signum}, initiating shutdown...")
        asyncio.create_task(self.stop())


async def main() -> None:
    orchestrator = PulseTraderOrchestrator()

    signal.signal(signal.SIGINT, orchestrator.handle_signal)
    signal.signal(signal.SIGTERM, orchestrator.handle_signal)

    try:
        await orchestrator.start()
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received")
    finally:
        await orchestrator.stop()


if __name__ == "__main__":
    asyncio.run(main())
