import argparse
import json
import os
from typing import Dict, List

import matplotlib.pyplot as plt

from platform_game import GameConfig, PlatformGame, RegulationConfig
from run import GAME_SETTING


DEFAULT_SCENARIOS: Dict[str, RegulationConfig] = {
    "baseline": RegulationConfig(),
    "ban_self_pref": RegulationConfig(ban_self_preferencing=True),
    "ban_dual_mode": RegulationConfig(ban_dual_mode=True),
}


def run_scenario(label: str, regulation: RegulationConfig, rounds: int, config: GameConfig):
    game = PlatformGame(GAME_SETTING, config=config, regulation=regulation)
    game.run_game(rounds=rounds)
    return [{**record, "scenario": label} for record in game.round_records]


def build_plot(data: List[Dict], output_path: str):
    plt.figure(figsize=(8, 6))
    ax1 = plt.subplot(2, 1, 1)
    ax2 = plt.subplot(2, 1, 2, sharex=ax1)

    scenarios = sorted({entry["scenario"] for entry in data})
    for scenario in scenarios:
        subset = [entry for entry in data if entry["scenario"] == scenario]
        rounds = [entry["round"] for entry in subset]
        profits_M = [entry["profit_M"] for entry in subset]
        profits_S = [entry["profit_S"] for entry in subset]
        ax1.plot(rounds, profits_M, marker="o", label=scenario)
        ax2.plot(rounds, profits_S, marker="o", label=scenario)

    ax1.set_ylabel("Π_M (platform profit)")
    ax2.set_ylabel("π_S (seller profit)")
    ax2.set_xlabel("Round")
    ax1.legend()
    ax2.legend()
    ax1.grid(True, linestyle="--", alpha=0.3)
    ax2.grid(True, linestyle="--", alpha=0.3)

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    plt.tight_layout()
    plt.savefig(output_path)
    plt.close()


def main():
    parser = argparse.ArgumentParser(description="Run multiple platform-game scenarios and plot results.")
    parser.add_argument("--rounds", type=int, default=3, help="Number of rounds per scenario.")
    parser.add_argument(
        "--scenarios",
        type=str,
        default="baseline,ban_self_pref,ban_dual_mode",
        help="Comma-separated scenario keys to run. Available: baseline, ban_self_pref, ban_dual_mode.",
    )
    parser.add_argument("--output-data", type=str, default="exp/platform_game_results.json", help="Path to save raw data.")
    parser.add_argument("--output-plot", type=str, default="exp/platform_game_results.png", help="Path to save the plot.")
    args = parser.parse_args()

    selected = [name.strip() for name in args.scenarios.split(",") if name.strip()]
    config = GameConfig()

    all_records: List[Dict] = []
    for label in selected:
        if label not in DEFAULT_SCENARIOS:
            raise ValueError(f"Unknown scenario '{label}'. Available keys: {', '.join(DEFAULT_SCENARIOS)}")
        scenario_records = run_scenario(label, DEFAULT_SCENARIOS[label], args.rounds, config)
        all_records.extend(scenario_records)

    os.makedirs(os.path.dirname(args.output_data), exist_ok=True)
    with open(args.output_data, "w", encoding="utf-8") as f:
        json.dump(all_records, f, indent=2)

    build_plot(all_records, args.output_plot)
    print(f"Saved raw data to {args.output_data}")
    print(f"Saved plot to {args.output_plot}")


if __name__ == "__main__":
    main()
