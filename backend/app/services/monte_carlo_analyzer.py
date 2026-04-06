"""
Monte Carlo 结果分析器
从 N 次模拟中提取叙事结局、LLM 分类结果、计算统计聚合
"""

import os
import json
import math
from typing import Dict, Any, List
from datetime import datetime
from collections import Counter

from ..config import Config
from ..utils.logger import get_logger
from ..utils.llm_client import LLMClient

logger = get_logger('mirofish.monte_carlo.analyzer')


class MonteCarloAnalyzer:
    """Monte Carlo 结果分析器"""

    SIMULATION_DATA_DIR = Config.OASIS_SIMULATION_DATA_DIR

    @classmethod
    def analyze(
        cls,
        group_id: str,
        child_ids: List[str],
        classification_criteria: str = "",
    ) -> Dict[str, Any]:
        logger.info(f"[MC Analyzer] Starting analysis for {group_id} with {len(child_ids)} runs")

        # 1. 提取每次运行的内容和指标
        run_metrics = []
        for child_id in child_ids:
            try:
                metrics = cls._extract_metrics(child_id)
                run_metrics.append(metrics)
            except Exception as e:
                logger.warning(f"Failed to extract metrics for {child_id}: {e}")

        if not run_metrics:
            raise ValueError("No valid metrics extracted from any child simulation")

        # 2. 用 LLM 为每次运行生成结局摘要
        cls._generate_outcome_summaries(run_metrics)

        # 3. 基于结局摘要进行分类
        outcome_categories = cls._classify_outcomes(run_metrics, classification_criteria)

        # 4. 统计聚合
        aggregate = cls._compute_aggregates(run_metrics)

        # 5. 基于结局分类计算收敛指数
        aggregate["convergence_index"] = cls.compute_convergence(
            outcome_categories, len(run_metrics)
        )

        # 6. 生成关键洞察（一句话总结）
        key_insight = cls._generate_key_insight(outcome_categories, aggregate, len(run_metrics))

        analysis = {
            "run_metrics": run_metrics,
            "outcome_categories": outcome_categories,
            "aggregate": aggregate,
            "key_insight": key_insight,
            "classification_criteria": classification_criteria,
            "total_runs_analyzed": len(run_metrics),
            "analyzed_at": datetime.now().isoformat(),
        }

        analysis_path = os.path.join(cls.SIMULATION_DATA_DIR, group_id, "mc_analysis.json")
        with open(analysis_path, 'w', encoding='utf-8') as f:
            json.dump(analysis, f, ensure_ascii=False, indent=2)

        logger.info(f"[MC Analyzer] Analysis complete: {len(outcome_categories)} categories identified")
        return analysis

    @classmethod
    def _extract_metrics(cls, child_id: str) -> Dict[str, Any]:
        """从子模拟的 actions.jsonl 中提取指标和帖子内容。"""
        sim_dir = os.path.join(cls.SIMULATION_DATA_DIR, child_id)
        metrics = {
            "child_id": child_id,
            "total_actions": 0,
            "twitter_actions": 0,
            "reddit_actions": 0,
            "action_type_counts": {},
            "agent_activity": {},
            "total_posts": 0,
            "total_likes": 0,
            "total_comments": 0,
            "total_reposts": 0,
            "total_rounds": 0,
            "all_posts": [],       # 所有帖子内容（用于结局分析）
            "all_comments": [],    # 所有评论内容
            "outcome_summary": "", # 由 LLM 生成的结局摘要
        }

        action_type_counter = Counter()
        agent_counter = Counter()

        for platform in ("twitter", "reddit"):
            actions_file = os.path.join(sim_dir, platform, "actions.jsonl")
            if not os.path.exists(actions_file):
                continue

            platform_count = 0
            with open(actions_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        action = json.loads(line)
                    except json.JSONDecodeError:
                        continue

                    event_type = action.get("event_type")
                    if event_type == "simulation_end":
                        metrics["total_rounds"] = max(
                            metrics["total_rounds"],
                            action.get("total_rounds", 0),
                        )
                        continue
                    if event_type == "round_end":
                        continue

                    platform_count += 1
                    action_type = action.get("action_type", "UNKNOWN")
                    agent_name = action.get("agent_name", "unknown")

                    action_type_counter[action_type] += 1
                    agent_counter[agent_name] += 1

                    if action_type == "CREATE_POST":
                        metrics["total_posts"] += 1
                        content = action.get("action_args", {}).get("content", "")
                        if content:
                            metrics["all_posts"].append({
                                "agent": agent_name,
                                "content": content[:300],
                                "platform": platform,
                                "round": action.get("round", 0),
                            })
                    elif action_type in ("CREATE_COMMENT",):
                        metrics["total_comments"] += 1
                        content = action.get("action_args", {}).get("content", "")
                        if content:
                            metrics["all_comments"].append({
                                "agent": agent_name,
                                "content": content[:200],
                                "platform": platform,
                            })
                    elif action_type in ("LIKE_POST", "LIKE_COMMENT"):
                        metrics["total_likes"] += 1
                    elif action_type in ("REPOST", "QUOTE_POST"):
                        metrics["total_reposts"] += 1

            if platform == "twitter":
                metrics["twitter_actions"] = platform_count
            else:
                metrics["reddit_actions"] = platform_count

        metrics["total_actions"] = metrics["twitter_actions"] + metrics["reddit_actions"]
        metrics["action_type_counts"] = dict(action_type_counter)
        metrics["agent_activity"] = dict(agent_counter.most_common(20))

        return metrics

    @classmethod
    def _generate_outcome_summaries(cls, run_metrics: List[Dict[str, Any]]):
        """用 LLM 为每次运行生成「世界结局」摘要。"""
        llm = LLMClient()

        for m in run_metrics:
            # 取前 15 条帖子 + 后 15 条帖子（看开头和结尾）
            posts = m.get("all_posts", [])
            early_posts = posts[:15]
            late_posts = posts[-15:] if len(posts) > 15 else []
            comments = m.get("all_comments", [])[:10]

            early_text = "\n".join(
                f"[Round {p['round']}] {p['agent']} ({p['platform']}): {p['content']}"
                for p in early_posts
            )
            late_text = "\n".join(
                f"[Round {p['round']}] {p['agent']} ({p['platform']}): {p['content']}"
                for p in late_posts
            )
            comment_text = "\n".join(
                f"{c['agent']}: {c['content']}"
                for c in comments
            )

            prompt = f"""以下是一次社会模拟中 Agent 们发布的帖子和评论。请总结这次模拟最终的世界走向和结局。

初期帖子：
{early_text}

后期帖子：
{late_text}

部分评论：
{comment_text}

请用2-3句话总结这次模拟的最终结局（不要描述数据指标，而是描述事件走向和最终结果，例如"战争升级"、"达成和平协议"、"舆论两极分化"等）："""

            for attempt in range(3):
                try:
                    if attempt > 0:
                        import time
                        time.sleep(2)
                    summary = llm.chat(
                        messages=[{"role": "user", "content": prompt}],
                        temperature=0.3,
                        max_tokens=300,
                    )
                    m["outcome_summary"] = summary.strip()
                    break
                except Exception as e:
                    logger.warning(f"Outcome summary attempt {attempt+1} failed for {m['child_id']}: {e}")
                    if attempt == 2:
                        m["outcome_summary"] = f"共 {m['total_posts']} 条帖子，{m['total_actions']} 次互动"

            # 清理大数据，不存入最终结果（太大）
            m["sample_posts"] = [
                p["content"][:150] for p in (m.get("all_posts", [])[:5])
            ]

        # 清理 all_posts 和 all_comments（太大不存入 JSON）
        for m in run_metrics:
            m.pop("all_posts", None)
            m.pop("all_comments", None)

    @classmethod
    def _classify_outcomes(
        cls,
        run_metrics: List[Dict[str, Any]],
        classification_criteria: str = "",
    ) -> List[Dict[str, Any]]:
        """基于结局摘要对 N 次运行分类。"""
        n = len(run_metrics)

        # 构建每次运行的结局描述
        run_summaries = []
        for i, m in enumerate(run_metrics):
            run_summaries.append(
                f"Run {i+1}: {m.get('outcome_summary', 'No summary available')}"
            )

        criteria_instruction = ""
        if classification_criteria:
            criteria_instruction = (
                f"\n\n用户指定的分类标准：\n"
                f'"{classification_criteria}"\n'
                f"请严格按照此标准分类。\n"
            )
        else:
            criteria_instruction = (
                "\n\n请根据模拟结局的实际走向自动识别 3-6 种不同的结局类型"
                "（例如：战争升级、和平谈判成功、舆论两极分化、国际制裁生效等）。\n"
            )

        prompt = f"""你正在分析 {n} 次独立的蒙特卡洛模拟运行。每次运行有相同的初始设定，但由于随机性产生了不同的结局。

以下是每次运行的结局摘要：

{chr(10).join(run_summaries)}
{criteria_instruction}
请将这些运行分类，返回如下 JSON 格式：
{{
  "categories": [
    {{
      "category_name": "简短的结局类型名称",
      "description": "这种结局的1-2句话描述",
      "run_indices": [0, 2, 5],
      "representative_summary": "这种结局的典型叙事，描述事件最终走向了什么方向"
    }}
  ]
}}

规则：
- 每个 run 必须被分配到恰好一个分类中（run_indices 用 0-based 索引）
- 分类名称应描述世界走向（如"全面战争"、"外交解决"），而非数据指标
- 所有文本用中文"""

        try:
            llm = LLMClient()
            result = llm.chat_json(
                messages=[{"role": "user", "content": prompt}],
                temperature=Config.MC_ANALYSIS_TEMPERATURE,
                max_tokens=4096,
            )

            categories = result.get("categories", [])
            output = []
            for cat in categories:
                indices = cat.get("run_indices", [])
                child_ids = [
                    run_metrics[i]["child_id"]
                    for i in indices
                    if i < len(run_metrics)
                ]
                output.append({
                    "category_name": cat.get("category_name", "Unknown"),
                    "description": cat.get("description", ""),
                    "count": len(child_ids),
                    "percentage": round(len(child_ids) / n * 100, 1) if n > 0 else 0,
                    "child_ids": child_ids,
                    "representative_summary": cat.get("representative_summary", ""),
                })

            # 兜底：把 LLM 漏掉的 run 归入最大的分类
            all_classified = set()
            for cat in output:
                all_classified.update(cat["child_ids"])
            all_ids = set(m["child_id"] for m in run_metrics)
            missing = all_ids - all_classified
            if missing and output:
                largest = max(output, key=lambda c: c["count"])
                largest["child_ids"].extend(missing)
                largest["count"] = len(largest["child_ids"])
                for cat in output:
                    cat["percentage"] = round(cat["count"] / n * 100, 1)
                logger.warning(f"LLM missed {len(missing)} runs, assigned to '{largest['category_name']}'")

            return output

        except Exception as e:
            logger.error(f"LLM classification failed: {e}")
            return cls._fallback_classification(run_metrics)

    @classmethod
    def _fallback_classification(cls, run_metrics: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """LLM 失败时的降级分类。"""
        n = len(run_metrics)
        return [{
            "category_name": "未分类",
            "description": "LLM 分类失败，所有运行归为一类",
            "count": n,
            "percentage": 100.0,
            "child_ids": [m["child_id"] for m in run_metrics],
            "representative_summary": run_metrics[0].get("outcome_summary", "") if run_metrics else "",
        }]

    @classmethod
    def _compute_aggregates(cls, run_metrics: List[Dict[str, Any]]) -> Dict[str, Any]:
        """计算统计聚合。"""
        numeric_keys = [
            "total_actions", "twitter_actions", "reddit_actions",
            "total_posts", "total_likes", "total_comments", "total_reposts",
            "total_rounds",
        ]

        aggregate = {}
        for key in numeric_keys:
            values = [m.get(key, 0) for m in run_metrics]
            if not values:
                continue

            n = len(values)
            mean = sum(values) / n
            variance = sum((v - mean) ** 2 for v in values) / max(n - 1, 1)
            std = math.sqrt(variance)

            aggregate[key] = {
                "mean": round(mean, 2),
                "std": round(std, 2),
                "min": min(values),
                "max": max(values),
                "median": round(sorted(values)[n // 2], 2),
            }

            if n > 1 and std > 0:
                margin = 1.96 * std / math.sqrt(n)
                aggregate[key]["ci_95_lower"] = round(mean - margin, 2)
                aggregate[key]["ci_95_upper"] = round(mean + margin, 2)

        return aggregate

    @classmethod
    def _generate_key_insight(
        cls,
        outcome_categories: List[Dict[str, Any]],
        aggregate: Dict[str, Any],
        total_runs: int,
    ) -> str:
        """生成一句话关键洞察。"""
        cats_desc = "; ".join(
            f"{c['category_name']}({c['percentage']}%)" for c in outcome_categories
        )
        ci = aggregate.get("convergence_index", 0)

        prompt = f"""基于以下蒙特卡洛模拟分析结果，用一句话总结最关键的发现（不超过50个字）：

- 共 {total_runs} 次模拟
- 收敛指数：{ci * 100:.0f}%
- 结局分布：{cats_desc}
- 各结局描述：
{chr(10).join(f'  {c["category_name"]}: {c["representative_summary"]}' for c in outcome_categories)}

要求：直接给出结论性判断，不要说"根据分析"之类的废话。例如"战争升级几乎不可避免（90%概率）"。"""

        try:
            llm = LLMClient()
            return llm.chat(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=100,
            ).strip()
        except Exception as e:
            logger.warning(f"Failed to generate key insight: {e}")
            top = max(outcome_categories, key=lambda c: c["count"])
            return f"{top['category_name']}（{top['percentage']}% 概率）"

    @classmethod
    def compute_convergence(cls, outcome_categories: List[Dict[str, Any]], total_runs: int) -> float:
        """
        基于结局分类计算收敛指数 = 最大分类的占比。
        直观含义：最可能的结局出现的概率。
        - 10/10 同一结局 → 100%
        - 9/10 同一结局 → 90%
        - 5/5 均匀分布 → 50%
        """
        if total_runs <= 0 or not outcome_categories:
            return 1.0

        max_count = max(c["count"] for c in outcome_categories)
        return round(max_count / total_runs, 3)
