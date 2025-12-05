import argparse

from platform_game import GameConfig, PlatformGame, RegulationConfig

# 基于论文内容的 Game Setting Prompt
# 这里将论文 Section 2 的核心规则提取为自然语言
GAME_SETTING = """
Welcome to the "Platform Dual Mode Game". 

The Scenario:
1. **Roles**: 
   - Player M is a digital Platform (like Amazon/Apple). It runs a marketplace and also sells its own product (Dual Mode).
   - Player S is a Third-party Seller. It sells an innovative product on M's marketplace.

2. **Products & Value**:
   - Fringe sellers sell a basic product with value V=100.
   - Platform M sells a product with value V_M = 100 + 5 (Platform advantage) + 10 (Convenience).
   - Seller S sells a product with value V_S = 100 + Delta (Innovation) + 10 (Convenience).
   - S determines 'Delta' by investing money. Cost of innovation is exponential.

3. **Decisions**:
   - **Stage 1 (M)**: Set the Commission Rate (percentage of S's revenue taken by M).
   - **Stage 2 (S)**: Decide Innovation Level (how much to improve the product).
   - **Stage 3 (Both)**: Set Prices (P_M and P_S).

4. **Goal**: Maximize your own accumulated profit over the rounds. 
   - M's Profit = (P_M * Sales_M) + (Commission * P_S * Sales_S).
   - S's Profit = (P_S * (1 - Commission) * Sales_S) - Innovation_Cost.

5. **Competition**: Consumers strictly prefer the product that offers higher Utility (Value - Price).
"""

def main():
    parser = argparse.ArgumentParser(description='Platform Dual Mode Game')
    parser.add_argument('--round', type=int, default=5, help='Number of rounds')
    parser.add_argument('--base-value', type=float, default=100.0, dest='base_value', help='Baseline product value v.')
    parser.add_argument('--sigma', type=float, default=5.0, help='Platform product advantage σ.')
    parser.add_argument('--convenience', type=float, default=10.0, help='Convenience value b offered by the platform.')
    parser.add_argument('--min-innovation', type=float, default=5.0, dest='min_innovation', help='Lower bound Δ_l.')
    parser.add_argument('--max-innovation', type=float, default=60.0, dest='max_innovation', help='Upper bound on Δ used in prompts.')
    parser.add_argument('--innovation-cost-scale', type=float, default=0.08, dest='innovation_cost_scale', help='Scale of the quadratic innovation cost K(Δ).')
    parser.add_argument('--outside-scale', type=float, default=120.0, dest='outside_scale', help='Upper support of outside option distribution G.')
    parser.add_argument('--market-size', type=int, default=1000, dest='market_size', help='Number of consumers in the simulation mass.')
    parser.add_argument('--ban-dual', action='store_true', help='Ban M from entering the dual mode (forces seller/marketplace choice).')
    parser.add_argument('--ban-imitation', action='store_true', help='Forbid product imitation in dual mode.')
    parser.add_argument('--ban-self-preferencing', action='store_true', help='Force the platform to show S whenever it lists on the marketplace.')
    args = parser.parse_args()

    config = GameConfig(
        base_value=args.base_value,
        convenience=args.convenience,
        sigma=args.sigma,
        min_innovation=args.min_innovation,
        max_innovation=args.max_innovation,
        innovation_cost_scale=args.innovation_cost_scale,
        outside_option_scale=args.outside_scale,
        market_size=args.market_size,
    )
    regulation = RegulationConfig(
        ban_dual_mode=args.ban_dual,
        ban_imitation=args.ban_imitation,
        ban_self_preferencing=args.ban_self_preferencing,
    )

    game = PlatformGame(GAME_SETTING, config=config, regulation=regulation)
    game.run_game(rounds=args.round)

if __name__ == '__main__':
    main()
