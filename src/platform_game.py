from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Dict, Tuple

from Alympics import PlayGround, Player, LLM

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


@dataclass
class GameConfig:
    """Parameterization of the baseline model in the paper."""

    base_value: float = 100.0  # v
    convenience: float = 10.0  # b
    sigma: float = 5.0  # relative platform advantage
    min_innovation: float = 5.0  # Δ_l
    max_innovation: float = 60.0  # cap for prompts/safety
    innovation_cost_scale: float = 0.08  # controls K(Δ)
    outside_option_scale: float = 120.0  # determines slope of G(·)
    market_size: int = 1000


@dataclass
class RegulationConfig:
    ban_dual_mode: bool = False
    ban_imitation: bool = False
    ban_self_preferencing: bool = False


class PlatformAgent(Player):
    def __init__(self, game_setting: str, name: str, role_desc: str):
        super().__init__(name, False, "")
        self.role_desc = role_desc
        self.balance = 0.0
        self.append_message("system", game_setting + "\n\n" + role_desc)
        self.llm = LLM()

    def decide(self, round_id: int, context: str, decision_prompt: str) -> str:
        prompt = f"Round {round_id}. {context}\n{decision_prompt}"
        self.append_message("user", prompt)
        logger.info("Asking %s: %s", self.name, prompt)
        response = self.llm.call(self.history)
        self.append_message("assistant", response)
        logger.info("%s response: %s", self.name, response)
        return response

    def status(self) -> str:
        return f"{self.name} ({self.role_desc}) profit={self.balance:.2f}"


class PlatformGame(PlayGround):
    def __init__(
        self,
        game_setting: str,
        config: GameConfig | None = None,
        regulation: RegulationConfig | None = None,
    ) -> None:
        super().__init__()
        self.game_setting = game_setting
        self.config = config or GameConfig()
        self.regulation = regulation or RegulationConfig()
        self.round_records: list[Dict[str, float | str | bool]] = []

        self.player_M = PlatformAgent(
            game_setting,
            "Amazonia",
            "You are the Platform M. You choose the business mode, set commissions, and may self-preference or imitate as in the RAND paper.",
        )
        self.player_S = PlatformAgent(
            game_setting,
            "StartUpInc",
            "You are the Innovative Seller S. You invest in innovation and set on/off platform prices following the paper's timing.",
        )

        self.add_player(self.player_M)
        self.add_player(self.player_S)

    # ---------------- Parsing helpers ---------------- #
    def _extract_number(self, text: str, key: str, default: float) -> float:
        match = re.search(rf"{key}\s*[:=]\s*(-?\d+(\.\d+)?)", text, re.IGNORECASE)
        if match:
            return float(match.group(1))
        logger.warning("Could not extract %s from response '%s', fallback=%s", key, text, default)
        return default

    def _extract_mode(self, text: str, allowed: Tuple[str, ...], default: str) -> str:
        lower = text.lower()
        for option in allowed:
            if option in lower:
                return option
        # also allow shorthand answers
        if "dual" in lower:
            return "dual"
        if "market" in lower:
            return "marketplace"
        if "seller" in lower:
            return "seller"
        logger.warning("Mode not found in '%s', fallback=%s", text, default)
        return default

    def _extract_choice(self, text: str, key: str, default: bool) -> bool:
        match = re.search(rf"{key}\s*[:=]?\s*(yes|no|true|false)", text, re.IGNORECASE)
        if match:
            value = match.group(1).lower()
            return value in {"yes", "true"}
        lowered = text.lower()
        if "yes" in lowered or "imitate" in lowered:
            return True
        if "no" in lowered:
            return False
        logger.warning("Could not parse boolean %s from '%s', fallback=%s", key, text, default)
        return default

    # ---------------- Economic primitives ---------------- #
    def _cdf(self, net_utility: float) -> float:
        return max(0.0, min(1.0, net_utility / self.config.outside_option_scale))

    def _innovation_cost(self, innovation: float) -> float:
        delta = max(0.0, innovation - self.config.min_innovation)
        return self.config.innovation_cost_scale * (delta ** 2)

    def _clip(self, value: float, lower: float, upper: float) -> float:
        return max(lower, min(upper, value))

    def _available_modes(self) -> Tuple[str, ...]:
        if self.regulation.ban_dual_mode:
            return ("marketplace", "seller")
        return ("dual", "marketplace", "seller")

    def _allocate_sales(self, options: Dict[str, float], share: float) -> Dict[str, float]:
        if share <= 0.0 or not options:
            return {label: 0.0 for label in options}
        best_label = max(options, key=options.get)
        best_net = options[best_label]
        if best_net <= 0:
            return {label: 0.0 for label in options}
        demand_share = self._cdf(best_net) * share
        quantity = demand_share * self.config.market_size
        result = {label: 0.0 for label in options}
        result[best_label] = quantity
        return result

    # ---------------- Game loop ---------------- #
    def run_game(self, rounds: int = 5):
        for round_id in range(1, rounds + 1):
            logger.info("--- Round %s ---", round_id)
            self._play_round(round_id)

    def _play_round(self, round_id: int):
        allowed_modes = self._available_modes()
        status_msg = f"M: {self.player_M.status()} | S: {self.player_S.status()}"
        mode_resp = self.player_M.decide(
            round_id,
            f"Available modes: {', '.join(allowed_modes)}. {status_msg}",
            "Select your business mode for this product category following the paper's stage-0 problem. Reply with 'Mode: dual/marketplace/seller' and justify.",
        )
        mode = self._extract_mode(mode_resp, allowed_modes, allowed_modes[0])

        commission = 0.0
        if mode in {"dual", "marketplace"}:
            fee_prompt = (
                "Stage 1 (fee). Choose a commission τ between 0 and the convenience benefit b= "
                f"{self.config.convenience}. Remember τ>b induces showrooming and zero platform revenue."
            )
            response = self.player_M.decide(round_id, f"Mode={mode}", fee_prompt + " Output 'Commission: value'.")
            commission = self._clip(
                self._extract_number(response, "Commission", self.config.convenience),
                0.0,
                self.config.convenience,
            )
        innovation_prompt = (
            f"Stage 2. Set your innovation Δ (≥ {self.config.min_innovation}, ≤ {self.config.max_innovation}). "
            "Innovation raises the value v+Δ on/off platform but costs K(Δ)=c*(Δ-Δ_l)^2. "
            f"Current commission τ={commission:.2f}."
        )
        response = self.player_S.decide(round_id, status_msg, innovation_prompt + " Reply 'Innovation: value'.")
        innovation = self._clip(
            self._extract_number(response, "Innovation", self.config.min_innovation),
            self.config.min_innovation,
            self.config.max_innovation,
        )
        imitation = False
        if mode == "dual" and not self.regulation.ban_imitation and innovation > self.config.sigma:
            imitate_prompt = (
                "Stage 2b. You may copy S's product when Δ>σ. "
                "State 'Imitate: yes/no' and explain how this affects your later pricing."
            )
            resp_imt = self.player_M.decide(round_id, f"Seller innovation={innovation:.1f}", imitate_prompt)
            imitation = self._extract_choice(resp_imt, "Imitate", False)

        price_M = 0.0
        if mode in {"dual", "seller"}:
            limit = self.config.convenience + (innovation if imitation else self.config.sigma)
            price_prompt = (
                f"Stage 3 pricing. Set your product price P_M (≤ {limit:.2f}) "
                "given fringe competition and any imitation decision."
            )
            resp_price_m = self.player_M.decide(round_id, f"Mode={mode}, τ={commission:.2f}", price_prompt + " Output 'Price: value'.")
            price_M = self._clip(self._extract_number(resp_price_m, "Price", limit), 0.0, limit)

        price_S_platform = 0.0
        price_S_direct = 0.0
        if mode in {"dual", "marketplace"}:
            s_prompt = (
                "Stage 3 pricing. Provide both the on-platform price and direct (off-platform) price. "
                "Respect the Bertrand upper bound pi ≤ τ + Δ and po ≤ pi - b. "
                "Format: 'PlatformPrice: x, DirectPrice: y'."
            )
            resp_price_s = self.player_S.decide(round_id, f"τ={commission:.2f}, Δ={innovation:.1f}", s_prompt)
            price_S_platform = self._clip(
                self._extract_number(resp_price_s, "PlatformPrice", commission + innovation),
                0.0,
                commission + innovation,
            )
            inferred_direct = max(price_S_platform - self.config.convenience, 0.0)
            price_S_direct = self._clip(
                self._extract_number(resp_price_s, "DirectPrice", inferred_direct),
                0.0,
                max(price_S_platform - self.config.convenience, price_S_platform),
            )

        display_bias = 1.0
        if mode == "dual" and not self.regulation.ban_self_preferencing:
            bias_prompt = (
                "Stage 4. Decide the share of consumers that you let observe S (0=hide completely, 1=show always). "
                "This captures self-preferencing/steering. Format 'DisplayShare: value between 0 and 1'."
            )
            resp_bias = self.player_M.decide(round_id, "", bias_prompt)
            display_bias = self._clip(self._extract_number(resp_bias, "DisplayShare", 1.0), 0.0, 1.0)
        elif mode != "dual":
            display_bias = 1.0 if mode == "marketplace" else 0.0

        outcome = self._settle_round(
            round_id,
            mode,
            commission,
            innovation,
            imitation,
            price_M,
            price_S_platform,
            price_S_direct,
            display_bias,
        )

        self.player_M.balance += outcome["profit_M"]
        self.player_S.balance += outcome["profit_S"]
        summary = (
            f"Round {round_id} result:\n"
            f"Mode={mode}, τ={commission:.2f}, Δ={innovation:.1f}, imitation={'yes' if imitation else 'no'}, show={display_bias:.2f}\n"
            f"P_M={price_M:.2f}, P_S^in={price_S_platform:.2f}, P_S^out={price_S_direct:.2f}\n"
            f"Sales -> M={outcome['sales_M']:.0f}, S_on={outcome['sales_S_platform']:.0f}, S_off={outcome['sales_S_direct']:.0f}\n"
            f"Profits -> Π_M={outcome['profit_M']:.2f}, π_S={outcome['profit_S']:.2f}"
        )
        logger.info(summary)
        self.player_M.append_message("user", summary)
        self.player_S.append_message("user", summary)
        self.round_records.append(
            {
                "round": round_id,
                "mode": mode,
                "commission": commission,
                "innovation": innovation,
                "imitation": imitation,
                "display_share": display_bias,
                "price_M": price_M,
                "price_S_platform": price_S_platform,
                "price_S_direct": price_S_direct,
                "profit_M": outcome["profit_M"],
                "profit_S": outcome["profit_S"],
                "sales_M": outcome["sales_M"],
                "sales_S_platform": outcome["sales_S_platform"],
                "sales_S_direct": outcome["sales_S_direct"],
            }
        )

    def _settle_round(
        self,
        round_id: int,
        mode: str,
        commission: float,
        innovation: float,
        imitation: bool,
        price_M: float,
        price_S_platform: float,
        price_S_direct: float,
        display_bias: float,
    ) -> Dict[str, float]:
        value_M = self.config.base_value + (innovation if imitation else self.config.sigma) + self.config.convenience
        value_S_platform = self.config.base_value + innovation + self.config.convenience
        value_S_direct = self.config.base_value + innovation
        net_M = value_M - price_M if mode in {"dual", "seller"} else float("-inf")
        net_S_platform = value_S_platform - price_S_platform if mode in {"dual", "marketplace"} else float("-inf")
        net_S_direct = value_S_direct - price_S_direct if mode in {"dual", "marketplace"} else float("-inf")

        if mode == "marketplace":
            aware_share = 1.0
            unaware_share = 0.0
        elif mode == "seller":
            aware_share = 0.0
            unaware_share = 1.0
        else:
            aware_share = display_bias
            unaware_share = 1.0 - display_bias

        aware_sales = self._allocate_sales(
            {
                "platform": net_M,
                "seller_platform": net_S_platform,
                "seller_direct": net_S_direct,
                "fringe": 0.0,
            },
            aware_share,
        )
        unaware_sales = self._allocate_sales(
            {
                "platform": net_M,
                "fringe": 0.0,
            },
            unaware_share,
        )

        sales_M = aware_sales.get("platform", 0.0) + unaware_sales.get("platform", 0.0)
        sales_S_platform = aware_sales.get("seller_platform", 0.0)
        sales_S_direct = aware_sales.get("seller_direct", 0.0)
        innovation_cost = self._innovation_cost(innovation)

        profit_M = price_M * sales_M + commission * price_S_platform * sales_S_platform
        profit_S = (
            price_S_platform * (1 - commission) * sales_S_platform + price_S_direct * sales_S_direct - innovation_cost
        )

        return {
            "sales_M": sales_M,
            "sales_S_platform": sales_S_platform,
            "sales_S_direct": sales_S_direct,
            "profit_M": profit_M,
            "profit_S": profit_S,
            "innovation_cost": innovation_cost,
            "round": round_id,
        }
