"""
Monte Carlo 模拟服务
管理多次模拟运行、并发控制、结果聚合
"""

import os
import json
import shutil
import threading
import time
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import datetime

from ..config import Config
from ..utils.logger import get_logger
from ..utils.locale import t, get_locale
from .simulation_manager import SimulationManager, SimulationState, SimulationStatus
from .simulation_runner import SimulationRunner

logger = get_logger('mirofish.monte_carlo')


class MCGroupStatus:
    CREATED = "created"
    RUNNING = "running"
    ANALYZING = "analyzing"
    COMPLETED = "completed"
    FAILED = "failed"
    STOPPED = "stopped"


@dataclass
class MonteCarloState:
    """Monte Carlo 组状态"""
    group_id: str
    parent_simulation_id: str
    project_id: str
    graph_id: str

    # MC 配置
    num_runs: int = 10
    max_concurrency: int = 3
    classification_criteria: str = ""

    # 状态
    status: str = MCGroupStatus.CREATED

    # 子模拟
    child_simulation_ids: List[str] = field(default_factory=list)
    completed_count: int = 0
    failed_count: int = 0
    running_count: int = 0

    # 分析结果（完成后填充）
    analysis: Optional[Dict[str, Any]] = None

    # 时间戳
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "group_id": self.group_id,
            "parent_simulation_id": self.parent_simulation_id,
            "project_id": self.project_id,
            "graph_id": self.graph_id,
            "num_runs": self.num_runs,
            "max_concurrency": self.max_concurrency,
            "classification_criteria": self.classification_criteria,
            "status": self.status,
            "child_simulation_ids": self.child_simulation_ids,
            "completed_count": self.completed_count,
            "failed_count": self.failed_count,
            "running_count": self.running_count,
            "analysis": self.analysis,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "error": self.error,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MonteCarloState':
        return cls(
            group_id=data["group_id"],
            parent_simulation_id=data["parent_simulation_id"],
            project_id=data["project_id"],
            graph_id=data["graph_id"],
            num_runs=data.get("num_runs", 10),
            max_concurrency=data.get("max_concurrency", 3),
            classification_criteria=data.get("classification_criteria", ""),
            status=data.get("status", MCGroupStatus.CREATED),
            child_simulation_ids=data.get("child_simulation_ids", []),
            completed_count=data.get("completed_count", 0),
            failed_count=data.get("failed_count", 0),
            running_count=data.get("running_count", 0),
            analysis=data.get("analysis"),
            created_at=data.get("created_at", datetime.now().isoformat()),
            started_at=data.get("started_at"),
            completed_at=data.get("completed_at"),
            error=data.get("error"),
        )


class MonteCarloService:
    """
    Monte Carlo 模拟组管理器

    管理 N 次子模拟的创建、并发执行和结果聚合。
    每个子模拟是一个独立的 SimulationRunner 实例，
    共享父模拟的 config 和 profiles。
    """

    SIMULATION_DATA_DIR = Config.OASIS_SIMULATION_DATA_DIR

    # 运行中的组监控线程
    _monitor_threads: Dict[str, threading.Thread] = {}
    _stop_flags: Dict[str, threading.Event] = {}
    _lock = threading.Lock()
    _state_lock = threading.Lock()  # 保护 mc_state.json 的读写

    @classmethod
    def _get_sim_dir(cls, simulation_id: str) -> str:
        return os.path.join(cls.SIMULATION_DATA_DIR, simulation_id)

    @classmethod
    def _mc_state_path(cls, parent_sim_id: str) -> str:
        return os.path.join(cls._get_sim_dir(parent_sim_id), "mc_state.json")

    @classmethod
    def _save_mc_state(cls, state: MonteCarloState):
        path = cls._mc_state_path(state.parent_simulation_id)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(state.to_dict(), f, ensure_ascii=False, indent=2)

    @classmethod
    def _load_mc_state(cls, group_id: str) -> Optional[MonteCarloState]:
        path = cls._mc_state_path(group_id)
        if not os.path.exists(path):
            return None
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return MonteCarloState.from_dict(data)

    @classmethod
    def create_group(
        cls,
        parent_simulation_id: str,
        num_runs: int = Config.MC_DEFAULT_NUM_RUNS,
        max_concurrency: int = Config.MC_DEFAULT_MAX_CONCURRENCY,
        classification_criteria: str = "",
    ) -> MonteCarloState:
        """
        从已准备好的父模拟创建 Monte Carlo 组。

        Args:
            parent_simulation_id: 父模拟ID（必须是 READY 状态）
            num_runs: 运行次数
            max_concurrency: 最大并发数
            classification_criteria: 用户提供的分类标准（可选）

        Returns:
            MonteCarloState
        """
        # 验证父模拟状态
        manager = SimulationManager()
        parent_state = manager._load_simulation_state(parent_simulation_id)
        if parent_state is None:
            raise ValueError(f"Simulation {parent_simulation_id} not found")
        if parent_state.status != SimulationStatus.READY:
            raise ValueError(
                f"Parent simulation must be READY, got {parent_state.status.value}"
            )

        # 验证必需文件存在
        parent_dir = cls._get_sim_dir(parent_simulation_id)
        config_path = os.path.join(parent_dir, "simulation_config.json")
        if not os.path.exists(config_path):
            raise ValueError("Parent simulation missing simulation_config.json")

        # 验证参数
        num_runs = max(1, min(num_runs, 1000))
        max_concurrency = max(1, min(max_concurrency, 20))

        state = MonteCarloState(
            group_id=parent_simulation_id,
            parent_simulation_id=parent_simulation_id,
            project_id=parent_state.project_id,
            graph_id=parent_state.graph_id,
            num_runs=num_runs,
            max_concurrency=max_concurrency,
            classification_criteria=classification_criteria,
        )

        cls._save_mc_state(state)
        logger.info(
            f"Monte Carlo group created: {state.group_id}, "
            f"num_runs={num_runs}, max_concurrency={max_concurrency}"
        )
        return state

    @classmethod
    def _create_child_simulation(
        cls,
        parent_sim_id: str,
        child_index: int,
        parent_state: SimulationState,
    ) -> str:
        """
        创建单个子模拟目录，复制配置和 profiles。

        Returns:
            child_simulation_id
        """
        child_id = f"{parent_sim_id}_mc{child_index:03d}"
        child_dir = cls._get_sim_dir(child_id)
        os.makedirs(child_dir, exist_ok=True)

        parent_dir = cls._get_sim_dir(parent_sim_id)

        # 复制配置文件
        files_to_copy = [
            "simulation_config.json",
            "reddit_profiles.json",
            "twitter_profiles.csv",
        ]
        for filename in files_to_copy:
            src = os.path.join(parent_dir, filename)
            if os.path.exists(src):
                shutil.copy2(src, os.path.join(child_dir, filename))

        # 创建子模拟的 state.json
        child_state = SimulationState(
            simulation_id=child_id,
            project_id=parent_state.project_id,
            graph_id=parent_state.graph_id,
            enable_twitter=parent_state.enable_twitter,
            enable_reddit=parent_state.enable_reddit,
            status=SimulationStatus.READY,
            entities_count=parent_state.entities_count,
            profiles_count=parent_state.profiles_count,
            entity_types=parent_state.entity_types,
            config_generated=True,
            config_reasoning=parent_state.config_reasoning,
            mc_parent=parent_sim_id,
        )

        # 直接写 state.json
        state_file = os.path.join(child_dir, "state.json")
        with open(state_file, 'w', encoding='utf-8') as f:
            json.dump(child_state.to_dict(), f, ensure_ascii=False, indent=2)

        return child_id

    @classmethod
    def start_group(
        cls,
        group_id: str,
        platform: str = "parallel",
        max_rounds: Optional[int] = None,
        enable_graph_memory_update: bool = False,
    ) -> MonteCarloState:
        """
        启动 Monte Carlo 组运行。

        1. 创建 N 个子模拟目录
        2. 启动后台线程管理并发执行
        """
        mc_state = cls._load_mc_state(group_id)
        if mc_state is None:
            raise ValueError(f"Monte Carlo group {group_id} not found")
        if mc_state.status not in (MCGroupStatus.CREATED, MCGroupStatus.STOPPED, MCGroupStatus.FAILED):
            raise ValueError(f"Group is already {mc_state.status}")

        # 加载父模拟状态
        manager = SimulationManager()
        parent_state = manager._load_simulation_state(mc_state.parent_simulation_id)
        if parent_state is None:
            raise ValueError("Parent simulation not found")

        # 创建子模拟
        child_ids = []
        for i in range(mc_state.num_runs):
            child_id = cls._create_child_simulation(
                mc_state.parent_simulation_id, i, parent_state
            )
            child_ids.append(child_id)

        mc_state.child_simulation_ids = child_ids
        mc_state.status = MCGroupStatus.RUNNING
        mc_state.started_at = datetime.now().isoformat()
        mc_state.completed_count = 0
        mc_state.failed_count = 0
        mc_state.running_count = 0
        mc_state.error = None
        cls._save_mc_state(mc_state)

        # 启动后台监控线程
        stop_event = threading.Event()
        locale = get_locale()
        thread = threading.Thread(
            target=cls._run_children,
            args=(
                group_id,
                child_ids,
                mc_state.max_concurrency,
                platform,
                max_rounds,
                enable_graph_memory_update,
                mc_state.graph_id,
                mc_state.classification_criteria,
                locale,
                stop_event,
            ),
            daemon=True,
            name=f"mc-{group_id}",
        )

        with cls._lock:
            cls._monitor_threads[group_id] = thread
            cls._stop_flags[group_id] = stop_event

        thread.start()
        logger.info(
            f"Monte Carlo group started: {group_id}, "
            f"{len(child_ids)} children, max_concurrency={mc_state.max_concurrency}"
        )
        return mc_state

    @classmethod
    def _run_children(
        cls,
        group_id: str,
        child_ids: List[str],
        max_concurrency: int,
        platform: str,
        max_rounds: Optional[int],
        enable_graph_memory_update: bool,
        graph_id: str,
        classification_criteria: str,
        locale: str,
        stop_event: threading.Event,
    ):
        """
        后台线程：使用信号量控制并发，运行所有子模拟。
        """
        from ..utils.locale import set_locale
        set_locale(locale)

        semaphore = threading.Semaphore(max_concurrency)
        child_threads = []
        child_results: Dict[str, str] = {}  # child_id -> "completed"|"failed"
        results_lock = threading.Lock()

        max_retries = 3

        def run_single_child(child_id: str):
            semaphore.acquire()
            if stop_event.is_set():
                semaphore.release()
                with results_lock:
                    child_results[child_id] = "stopped"
                return

            try:
                cls._update_running_count(group_id, delta=1)

                result = "failed"
                for attempt in range(1, max_retries + 1):
                    if stop_event.is_set():
                        result = "stopped"
                        break

                    try:
                        logger.info(f"[MC {group_id}] Starting child: {child_id} (attempt {attempt}/{max_retries})")

                        # 重试前清理旧的运行状态
                        if attempt > 1:
                            SimulationRunner.cleanup_simulation_logs(child_id)
                            time.sleep(2)  # 等待 API 限流窗口恢复

                        SimulationRunner.start_simulation(
                            simulation_id=child_id,
                            platform=platform,
                            max_rounds=max_rounds,
                            enable_graph_memory_update=enable_graph_memory_update,
                            graph_id=graph_id,
                        )

                        result = cls._poll_child_completion(
                            child_id, stop_event, Config.MC_CHILD_TIMEOUT
                        )

                        if result == "completed":
                            break

                        logger.warning(
                            f"[MC {group_id}] Child {child_id} attempt {attempt} failed, "
                            f"{'retrying...' if attempt < max_retries else 'no more retries'}"
                        )

                    except Exception as e:
                        logger.error(f"[MC {group_id}] Child {child_id} attempt {attempt} error: {e}")
                        if attempt == max_retries:
                            result = "failed"

                with results_lock:
                    child_results[child_id] = result

                logger.info(f"[MC {group_id}] Child {child_id} finished: {result}")

            except Exception as e:
                logger.error(f"[MC {group_id}] Child {child_id} error: {e}")
                with results_lock:
                    child_results[child_id] = "failed"
            finally:
                cls._update_running_count(group_id, delta=-1)
                semaphore.release()

        # 启动所有子线程
        for child_id in child_ids:
            if stop_event.is_set():
                break
            t = threading.Thread(
                target=run_single_child,
                args=(child_id,),
                daemon=True,
                name=f"mc-child-{child_id}",
            )
            t.start()
            child_threads.append(t)

        # 等待所有子线程完成
        for t in child_threads:
            t.join()

        # 统计结果
        completed = sum(1 for v in child_results.values() if v == "completed")
        failed = sum(1 for v in child_results.values() if v != "completed")

        mc_state = cls._load_mc_state(group_id)
        if mc_state is None:
            return

        mc_state.completed_count = completed
        mc_state.failed_count = failed
        mc_state.running_count = 0

        if stop_event.is_set():
            mc_state.status = MCGroupStatus.STOPPED
            cls._save_mc_state(mc_state)
            logger.info(f"[MC {group_id}] Stopped by user")
            return

        # 运行分析
        if completed > 0:
            try:
                mc_state.status = MCGroupStatus.ANALYZING
                cls._save_mc_state(mc_state)

                from .monte_carlo_analyzer import MonteCarloAnalyzer
                analysis = MonteCarloAnalyzer.analyze(
                    group_id=group_id,
                    child_ids=[
                        cid for cid, r in child_results.items() if r == "completed"
                    ],
                    classification_criteria=classification_criteria,
                )
                mc_state.analysis = analysis
                mc_state.status = MCGroupStatus.COMPLETED
                mc_state.completed_at = datetime.now().isoformat()
                logger.info(f"[MC {group_id}] Analysis complete")
            except Exception as e:
                logger.error(f"[MC {group_id}] Analysis failed: {e}")
                mc_state.status = MCGroupStatus.COMPLETED
                mc_state.completed_at = datetime.now().isoformat()
                mc_state.error = f"Analysis failed: {str(e)}"
        else:
            mc_state.status = MCGroupStatus.FAILED
            mc_state.error = "All child simulations failed"

        cls._save_mc_state(mc_state)

        # 清理
        with cls._lock:
            cls._monitor_threads.pop(group_id, None)
            cls._stop_flags.pop(group_id, None)

    @classmethod
    def _update_running_count(cls, group_id: str, delta: int):
        with cls._state_lock:
            mc_state = cls._load_mc_state(group_id)
            if mc_state:
                mc_state.running_count = max(0, mc_state.running_count + delta)
                cls._save_mc_state(mc_state)

    @classmethod
    def _poll_child_completion(
        cls, child_id: str, stop_event: threading.Event, timeout: int
    ) -> str:
        """轮询子模拟直到完成或超时。返回 'completed'|'failed'|'stopped'。"""
        start = time.time()
        poll_interval = Config.MC_CHILD_POLL_INTERVAL

        while not stop_event.is_set():
            elapsed = time.time() - start
            if elapsed > timeout:
                logger.warning(f"Child {child_id} timed out after {timeout}s")
                try:
                    SimulationRunner.stop_simulation(child_id)
                except Exception:
                    pass
                return "failed"

            # 尝试从 SimulationRunner 内存获取
            run_state = SimulationRunner.get_run_state(child_id)
            if run_state is not None:
                status = run_state.to_dict().get("runner_status", "")
                if status in ("completed", "stopped"):
                    return "completed"
                elif status == "failed":
                    return "failed"
            else:
                # 尝试从文件读取
                state_file = os.path.join(
                    cls._get_sim_dir(child_id), "run_state.json"
                )
                if os.path.exists(state_file):
                    try:
                        with open(state_file, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                        status = data.get("runner_status", "")
                        if status in ("completed", "stopped"):
                            return "completed"
                        elif status == "failed":
                            return "failed"
                    except (json.JSONDecodeError, IOError):
                        pass

            time.sleep(poll_interval)

        return "stopped"

    @classmethod
    def get_group_state(cls, group_id: str) -> Optional[MonteCarloState]:
        return cls._load_mc_state(group_id)

    @classmethod
    def get_group_progress(cls, group_id: str) -> Optional[Dict[str, Any]]:
        """获取实时进度，包括每个子模拟的状态。"""
        mc_state = cls._load_mc_state(group_id)
        if mc_state is None:
            return None

        children = []
        for child_id in mc_state.child_simulation_ids:
            child_info = {"child_id": child_id, "status": "pending"}

            # 尝试读取 run_state.json
            state_file = os.path.join(cls._get_sim_dir(child_id), "run_state.json")
            if os.path.exists(state_file):
                try:
                    with open(state_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    child_info["status"] = data.get("runner_status", "pending")
                    child_info["progress_percent"] = data.get("progress_percent", 0)
                    child_info["current_round"] = data.get("current_round", 0)
                    child_info["total_rounds"] = data.get("total_rounds", 0)
                    child_info["twitter_actions_count"] = data.get("twitter_actions_count", 0)
                    child_info["reddit_actions_count"] = data.get("reddit_actions_count", 0)
                except (json.JSONDecodeError, IOError):
                    pass

            children.append(child_info)

        # 实时统计
        completed = sum(1 for c in children if c["status"] in ("completed", "stopped"))
        failed = sum(1 for c in children if c["status"] == "failed")
        running = sum(1 for c in children if c["status"] in ("running", "starting"))
        pending = len(children) - completed - failed - running

        return {
            "group_id": group_id,
            "status": mc_state.status,
            "total": mc_state.num_runs,
            "completed": completed,
            "failed": failed,
            "running": running,
            "pending": pending,
            "progress_percent": round(completed / max(mc_state.num_runs, 1) * 100, 1),
            "children": children,
        }

    @classmethod
    def stop_group(cls, group_id: str) -> Optional[MonteCarloState]:
        """停止所有运行中的子模拟。"""
        mc_state = cls._load_mc_state(group_id)
        if mc_state is None:
            return None

        # 触发停止标志
        with cls._lock:
            stop_event = cls._stop_flags.get(group_id)
            if stop_event:
                stop_event.set()

        # 停止所有运行中的子模拟
        for child_id in mc_state.child_simulation_ids:
            try:
                SimulationRunner.stop_simulation(child_id)
            except Exception as e:
                logger.warning(f"Failed to stop child {child_id}: {e}")

        mc_state.status = MCGroupStatus.STOPPED
        cls._save_mc_state(mc_state)
        logger.info(f"Monte Carlo group stopped: {group_id}")
        return mc_state

    @classmethod
    def delete_group(cls, group_id: str) -> bool:
        """删除 MC 组及所有子模拟目录。"""
        mc_state = cls._load_mc_state(group_id)
        if mc_state is None:
            return False

        # 先停止
        if mc_state.status == MCGroupStatus.RUNNING:
            cls.stop_group(group_id)
            time.sleep(2)

        # 删除子模拟目录
        for child_id in mc_state.child_simulation_ids:
            child_dir = cls._get_sim_dir(child_id)
            if os.path.exists(child_dir):
                shutil.rmtree(child_dir, ignore_errors=True)

        # 删除 mc_state.json（保留父模拟）
        mc_path = cls._mc_state_path(group_id)
        if os.path.exists(mc_path):
            os.remove(mc_path)

        # 删除 mc_analysis.json
        analysis_path = os.path.join(cls._get_sim_dir(group_id), "mc_analysis.json")
        if os.path.exists(analysis_path):
            os.remove(analysis_path)

        logger.info(f"Monte Carlo group deleted: {group_id}")
        return True
