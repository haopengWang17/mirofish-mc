"""
Monte Carlo 模拟 API 路由
"""

import os
import json
from flask import request, jsonify
from . import monte_carlo_bp
from ..services.monte_carlo_service import MonteCarloService, MCGroupStatus
from ..utils.logger import get_logger
from ..utils.locale import t

logger = get_logger('mirofish.api.monte_carlo')


@monte_carlo_bp.route('/create', methods=['POST'])
def create_group():
    """
    创建 Monte Carlo 模拟组

    请求 JSON:
        {
            "simulation_id": "sim_xxxx",       // 父模拟ID（必须是 READY 状态）
            "num_runs": 10,                     // 运行次数
            "max_concurrency": 3,               // 最大并发数
            "classification_criteria": ""        // 可选：分类标准
        }
    """
    try:
        data = request.get_json() or {}
        simulation_id = data.get('simulation_id')
        if not simulation_id:
            return jsonify({"success": False, "error": "simulation_id is required"}), 400

        mc_state = MonteCarloService.create_group(
            parent_simulation_id=simulation_id,
            num_runs=data.get('num_runs', 10),
            max_concurrency=data.get('max_concurrency', 3),
            classification_criteria=data.get('classification_criteria', ''),
        )

        return jsonify({
            "success": True,
            "data": mc_state.to_dict(),
        })
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 400
    except Exception as e:
        logger.error(f"Create MC group failed: {e}", exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500


@monte_carlo_bp.route('/start', methods=['POST'])
def start_group():
    """
    启动 Monte Carlo 模拟组

    请求 JSON:
        {
            "group_id": "sim_xxxx",
            "platform": "parallel",
            "max_rounds": null
        }
    """
    try:
        data = request.get_json() or {}
        group_id = data.get('group_id')
        if not group_id:
            return jsonify({"success": False, "error": "group_id is required"}), 400

        mc_state = MonteCarloService.start_group(
            group_id=group_id,
            platform=data.get('platform', 'parallel'),
            max_rounds=data.get('max_rounds'),
            enable_graph_memory_update=data.get('enable_graph_memory_update', False),
        )

        return jsonify({
            "success": True,
            "data": {
                "group_id": mc_state.group_id,
                "status": mc_state.status,
                "child_simulation_ids": mc_state.child_simulation_ids,
                "num_runs": mc_state.num_runs,
                "max_concurrency": mc_state.max_concurrency,
            },
        })
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 400
    except Exception as e:
        logger.error(f"Start MC group failed: {e}", exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500


@monte_carlo_bp.route('/<group_id>', methods=['GET'])
def get_group(group_id):
    """获取 MC 组状态"""
    mc_state = MonteCarloService.get_group_state(group_id)
    if mc_state is None:
        return jsonify({"success": False, "error": "Group not found"}), 404

    return jsonify({"success": True, "data": mc_state.to_dict()})


@monte_carlo_bp.route('/<group_id>/progress', methods=['GET'])
def get_progress(group_id):
    """获取实时进度"""
    progress = MonteCarloService.get_group_progress(group_id)
    if progress is None:
        return jsonify({"success": False, "error": "Group not found"}), 404

    return jsonify({"success": True, "data": progress})


@monte_carlo_bp.route('/<group_id>/analysis', methods=['GET'])
def get_analysis(group_id):
    """获取分析结果"""
    mc_state = MonteCarloService.get_group_state(group_id)
    if mc_state is None:
        return jsonify({"success": False, "error": "Group not found"}), 404

    if mc_state.analysis is None:
        return jsonify({
            "success": False,
            "error": "Analysis not yet available",
            "status": mc_state.status,
        }), 404

    return jsonify({"success": True, "data": mc_state.analysis})


@monte_carlo_bp.route('/<group_id>/analyze', methods=['POST'])
def reanalyze(group_id):
    """
    重新运行分析（可带新分类标准）

    请求 JSON:
        {
            "classification_criteria": "根据支持率分类..."
        }
    """
    try:
        mc_state = MonteCarloService.get_group_state(group_id)
        if mc_state is None:
            return jsonify({"success": False, "error": "Group not found"}), 404

        if mc_state.status not in (MCGroupStatus.COMPLETED, MCGroupStatus.ANALYZING):
            return jsonify({
                "success": False,
                "error": f"Group must be completed, got {mc_state.status}",
            }), 400

        data = request.get_json() or {}
        criteria = data.get('classification_criteria', mc_state.classification_criteria)

        # 获取已完成的子模拟
        completed_children = []
        for child_id in mc_state.child_simulation_ids:
            state_file = os.path.join(
                MonteCarloService._get_sim_dir(child_id), "run_state.json"
            )
            if os.path.exists(state_file):
                with open(state_file, 'r', encoding='utf-8') as f:
                    child_data = json.load(f)
                if child_data.get("runner_status") in ("completed", "stopped"):
                    completed_children.append(child_id)

        if not completed_children:
            return jsonify({
                "success": False,
                "error": "No completed child simulations to analyze",
            }), 400

        from ..services.monte_carlo_analyzer import MonteCarloAnalyzer
        analysis = MonteCarloAnalyzer.analyze(
            group_id=group_id,
            child_ids=completed_children,
            classification_criteria=criteria,
        )

        mc_state.analysis = analysis
        mc_state.classification_criteria = criteria
        MonteCarloService._save_mc_state(mc_state)

        return jsonify({"success": True, "data": analysis})
    except Exception as e:
        logger.error(f"Reanalyze MC group failed: {e}", exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500


@monte_carlo_bp.route('/stop', methods=['POST'])
def stop_group():
    """停止 MC 组"""
    try:
        data = request.get_json() or {}
        group_id = data.get('group_id')
        if not group_id:
            return jsonify({"success": False, "error": "group_id is required"}), 400

        mc_state = MonteCarloService.stop_group(group_id)
        if mc_state is None:
            return jsonify({"success": False, "error": "Group not found"}), 404

        return jsonify({"success": True, "data": mc_state.to_dict()})
    except Exception as e:
        logger.error(f"Stop MC group failed: {e}", exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500


@monte_carlo_bp.route('/<group_id>/children', methods=['GET'])
def list_children(group_id):
    """列出所有子模拟状态"""
    mc_state = MonteCarloService.get_group_state(group_id)
    if mc_state is None:
        return jsonify({"success": False, "error": "Group not found"}), 404

    progress = MonteCarloService.get_group_progress(group_id)
    return jsonify({
        "success": True,
        "data": {
            "children": progress["children"] if progress else [],
        },
    })
