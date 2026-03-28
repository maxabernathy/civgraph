"""
CivGraph -- Media dynamics model: print, mass, and social media.

Three media ecosystems with distinct dynamics:

  1. **Print media** (newspapers, magazines, books)
     - Declining reach, higher trust, deeper analysis
     - Promotes nuanced opinion formation, slower spread
     - Consumed more by educated, older, upper-class agents

  2. **Mass media** (television, radio)
     - Broad reach, moderate trust, shared narratives
     - Homogenizes opinions (agenda-setting, Overton window)
     - Broad consumption, slight skew toward older demographics

  3. **Social media** (platforms, messaging, algorithmic feeds)
     - Growing reach, lower trust but high engagement
     - Creates echo chambers via algorithmic filtering
     - Polarization amplifier, viral dynamics, influencer effects
     - Consumed more by younger, higher-social-capital agents

References:
  - McCombs & Shaw (1972): agenda-setting theory
  - Sunstein (2001): echo chambers and group polarization
  - Pariser (2011): filter bubbles
  - Zuboff (2019): surveillance capitalism and attention markets
  - Guess et al. (2023): social media and political polarization

Calibrated to Western European media landscape (~2020s).
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field


# ══════════════════════════════════════════════════════════════════════════════
# MEDIA LANDSCAPE
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class MediaLandscape:
    """City-level media ecosystem state."""

    # ── Print media ────────────────────────────────────────────────
    print_reach: float = 0.30           # fraction of population regularly exposed
    print_trust: float = 0.62           # credibility (0-1)
    print_depth: float = 0.80           # analytical depth (0-1)
    print_diversity: float = 0.65       # plurality of viewpoints in print

    # ── Mass media (TV / radio) ───────────────────────────────────
    mass_reach: float = 0.72            # broad but declining
    mass_trust: float = 0.48            # moderate, declining
    mass_homogenization: float = 0.65   # tendency to create shared narrative
    mass_sensationalism: float = 0.45   # entertainment vs information (0-1)

    # ── Social media ──────────────────────────────────────────────
    social_reach: float = 0.68          # growing rapidly
    social_trust: float = 0.28          # low credibility but high engagement
    social_echo_chamber: float = 0.55   # algorithmic bubble strength (0-1)
    social_virality: float = 0.70       # speed and reach of viral content
    social_polarization: float = 0.50   # tendency to amplify extreme positions
    social_influencer_power: float = 0.40  # how much high-social-capital agents amplify

    # ── Cross-media dynamics ──────────────────────────────────────
    media_fragmentation: float = 0.55   # how much audiences are siloed across media
    attention_scarcity: float = 0.60    # total attention is finite; media compete
    misinformation_level: float = 0.25  # prevalence of false/misleading content

    def to_dict(self) -> dict:
        return {k: round(v, 3) for k, v in self.__dict__.items()}


# Baseline for Western European context
MEDIA_BASELINES = {
    "print_reach": 0.30, "print_trust": 0.62, "print_depth": 0.80,
    "print_diversity": 0.65,
    "mass_reach": 0.72, "mass_trust": 0.48, "mass_homogenization": 0.65,
    "mass_sensationalism": 0.45,
    "social_reach": 0.68, "social_trust": 0.28, "social_echo_chamber": 0.55,
    "social_virality": 0.70, "social_polarization": 0.50,
    "social_influencer_power": 0.40,
    "media_fragmentation": 0.55, "attention_scarcity": 0.60,
    "misinformation_level": 0.25,
}


def create_media_landscape(seed: int | None = None) -> MediaLandscape:
    """Initialize with baseline + small random perturbation."""
    rng = random.Random(seed)
    ml = MediaLandscape()
    for attr, base in MEDIA_BASELINES.items():
        noise = rng.gauss(0, 0.02)
        setattr(ml, attr, max(0.0, min(1.0, base + noise)))
    return ml


# ══════════════════════════════════════════════════════════════════════════════
# PER-AGENT MEDIA CONSUMPTION
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class MediaConsumption:
    """Individual media consumption profile."""
    print_exposure: float = 0.25    # 0-1 how much they consume print
    mass_exposure: float = 0.50     # 0-1 how much they consume mass media
    social_exposure: float = 0.50   # 0-1 how much they consume social media
    media_literacy: float = 0.50    # 0-1 ability to critically evaluate
    algorithmic_bubble: float = 0.0 # 0-1 how deep in social media bubble

    def to_dict(self) -> dict:
        return {
            "print_exposure": round(self.print_exposure, 3),
            "mass_exposure": round(self.mass_exposure, 3),
            "social_exposure": round(self.social_exposure, 3),
            "media_literacy": round(self.media_literacy, 3),
            "algorithmic_bubble": round(self.algorithmic_bubble, 3),
        }


def generate_media_consumption(
    age: int,
    education_track_value: str,
    class_rank: int,
    social_capital: float,
    rng: random.Random | None = None,
) -> MediaConsumption:
    """Generate media consumption based on demographics.

    Patterns based on Reuters Digital News Report (2023) and Eurobarometer data:
    - Older + educated → more print
    - Broad demographics → mass media, slight older skew
    - Younger + high social capital → more social media
    - Education → higher media literacy
    """
    r = rng or random

    # ── Print media consumption ────────────────────────────────────
    # Higher for: older, educated, upper-class
    age_print = min(1.0, max(0.0, (age - 20) / 50))  # rises with age
    edu_print = {"vocational": 0.15, "applied": 0.25, "academic": 0.45, "elite": 0.65}.get(
        education_track_value, 0.25
    )
    class_print = class_rank * 0.08
    print_exposure = age_print * 0.35 + edu_print * 0.35 + class_print * 0.15 + r.gauss(0, 0.08)
    print_exposure = max(0.02, min(0.95, print_exposure))

    # ── Mass media consumption ─────────────────────────────────────
    # Broadly consumed, slight older skew
    age_mass = 0.3 + min(0.4, max(0.0, (age - 25) / 50)) * 0.6
    mass_exposure = age_mass * 0.5 + 0.3 + r.gauss(0, 0.10)
    mass_exposure = max(0.10, min(0.95, mass_exposure))

    # ── Social media consumption ───────────────────────────────────
    # Higher for: younger, socially connected
    age_social = max(0.1, 1.0 - (age - 18) / 55)  # declines with age
    social_factor = social_capital * 0.3
    social_exposure = age_social * 0.5 + social_factor + 0.15 + r.gauss(0, 0.10)
    social_exposure = max(0.05, min(0.95, social_exposure))

    # ── Media literacy ─────────────────────────────────────────────
    # Education is primary driver, with some age experience
    edu_lit = {"vocational": 0.25, "applied": 0.40, "academic": 0.60, "elite": 0.80}.get(
        education_track_value, 0.40
    )
    age_lit = min(0.15, max(0.0, (age - 20) / 100))  # slight increase with age
    media_literacy = edu_lit * 0.7 + age_lit + class_rank * 0.04 + r.gauss(0, 0.08)
    media_literacy = max(0.05, min(0.95, media_literacy))

    # ── Attention budget normalization ─────────────────────────────
    # Total attention is limited; normalize so sum ≈ 1.0-1.5
    total = print_exposure + mass_exposure + social_exposure
    if total > 1.5:
        scale = 1.5 / total
        print_exposure *= scale
        mass_exposure *= scale
        social_exposure *= scale

    return MediaConsumption(
        print_exposure=print_exposure,
        mass_exposure=mass_exposure,
        social_exposure=social_exposure,
        media_literacy=media_literacy,
        algorithmic_bubble=0.0,  # starts at zero, builds over time
    )


# ══════════════════════════════════════════════════════════════════════════════
# MEDIA EVOLUTION (per tick)
# ══════════════════════════════════════════════════════════════════════════════

def evolve_media_landscape(ml: MediaLandscape, rng: random.Random):
    """Advance the media landscape by one year.

    Structural trends:
    - Print continues to decline in reach (but trust may rise as it becomes niche)
    - Mass media slowly erodes from competition with social
    - Social media grows in reach and echo-chamber strength
    - Misinformation rises with social media reach
    - Attention scarcity intensifies
    """
    # ── Print: slow decline ────────────────────────────────────────
    ml.print_reach *= (1 - 0.025 + rng.gauss(0, 0.005))   # ~2.5% annual decline
    ml.print_trust += rng.gauss(0.003, 0.005)               # slight trust increase (niche loyalty)
    ml.print_depth += rng.gauss(0, 0.005)                    # stable depth

    # ── Mass: gradual erosion ──────────────────────────────────────
    ml.mass_reach *= (1 - 0.015 + rng.gauss(0, 0.005))     # ~1.5% annual decline
    ml.mass_trust += rng.gauss(-0.005, 0.008)                # slow trust erosion
    ml.mass_sensationalism += rng.gauss(0.005, 0.005)        # increases to compete
    ml.mass_homogenization += rng.gauss(-0.003, 0.005)       # slight fragmentation

    # ── Social: growth with saturation ─────────────────────────────
    social_growth = 0.04 * (1 - ml.social_reach / 0.95)     # logistic toward 0.95
    ml.social_reach += social_growth + rng.gauss(0, 0.005)
    ml.social_echo_chamber += rng.gauss(0.008, 0.005)        # strengthening bubbles
    ml.social_polarization += rng.gauss(0.006, 0.005)         # polarization creep
    ml.social_virality += rng.gauss(0.003, 0.005)
    ml.social_trust += rng.gauss(-0.003, 0.005)               # declining trust
    # Influencer power grows with platform maturity
    ml.social_influencer_power += rng.gauss(0.005, 0.005)

    # ── Cross-media dynamics ───────────────────────────────────────
    # Fragmentation rises with social media
    ml.media_fragmentation += (ml.social_reach - 0.5) * 0.01 + rng.gauss(0, 0.005)
    # Attention scarcity: more media = more scarcity
    ml.attention_scarcity += rng.gauss(0.003, 0.003)
    # Misinformation: correlates with social reach × low literacy
    ml.misinformation_level += ml.social_reach * 0.005 + rng.gauss(0, 0.005)

    # ── Clamp all values to [0, 1] ─────────────────────────────────
    for attr in MEDIA_BASELINES:
        setattr(ml, attr, max(0.0, min(1.0, getattr(ml, attr))))


# ══════════════════════════════════════════════════════════════════════════════
# MEDIA → AGENT EFFECTS
# ══════════════════════════════════════════════════════════════════════════════

def media_affect_agent_opinion(
    agent_opinion: dict[str, float],
    media_consumption: MediaConsumption,
    ml: MediaLandscape,
    agent_politics_numeric: float,
    agent_openness: float,
    neighbors_opinions: dict[str, list[float]] | None = None,
    rng: random.Random | None = None,
) -> dict[str, float]:
    """Apply media effects to an agent's opinion state.

    Returns dict of opinion deltas per topic.
    """
    r = rng or random
    deltas: dict[str, float] = {}

    for topic, opinion in agent_opinion.items():
        delta = 0.0

        # ── Print media effect: nudge toward moderate, nuanced positions ──
        if media_consumption.print_exposure > 0.1:
            # Print promotes depth and moderation (regression to mean)
            print_pull = -opinion * 0.03 * media_consumption.print_exposure * ml.print_trust
            # But print diversity allows for informed extreme positions too
            print_pull *= (1 - ml.print_diversity * 0.3)
            delta += print_pull

        # ── Mass media effect: homogenization toward mainstream narrative ──
        if media_consumption.mass_exposure > 0.1:
            # Mass media pulls toward a "mainstream" position (weak center)
            mainstream = r.gauss(0, 0.1)  # slight noise around center
            mass_pull = (mainstream - opinion) * 0.04 * media_consumption.mass_exposure
            mass_pull *= ml.mass_homogenization * ml.mass_trust
            # Sensationalism amplifies extreme events
            mass_pull += r.gauss(0, 0.01) * ml.mass_sensationalism
            delta += mass_pull

        # ── Social media effect: echo chamber polarization ─────────────
        if media_consumption.social_exposure > 0.15:
            # Algorithmic bubble reinforces existing position
            bubble_strength = (
                media_consumption.algorithmic_bubble *
                ml.social_echo_chamber *
                media_consumption.social_exposure
            )
            # Push toward extremes of current opinion direction
            if abs(opinion) > 0.1:
                direction = 1 if opinion > 0 else -1
                echo_push = direction * 0.05 * bubble_strength
            else:
                echo_push = 0.0
            delta += echo_push

            # Viral content: random strong-sentiment spikes
            if r.random() < ml.social_virality * 0.1:
                viral_opinion = r.gauss(0, 0.4)  # random viral sentiment
                viral_effect = viral_opinion * 0.06 * media_consumption.social_exposure
                viral_effect *= (1 - media_consumption.media_literacy * 0.5)
                delta += viral_effect

            # Social media exposes to neighbor opinions more
            if neighbors_opinions and topic in neighbors_opinions:
                neighbor_ops = neighbors_opinions[topic]
                if neighbor_ops:
                    # Algorithmic selection: show opinions similar to yours more
                    similar = [o for o in neighbor_ops if o * opinion > 0]
                    if similar and bubble_strength > 0.2:
                        avg_similar = sum(similar) / len(similar)
                        social_peer = (avg_similar - opinion) * 0.03 * bubble_strength
                        delta += social_peer

        # ── Media literacy dampens manipulation ────────────────────────
        # High literacy reduces susceptibility to all media effects
        literacy_shield = media_consumption.media_literacy * 0.35
        delta *= (1 - literacy_shield)

        # ── Openness modulates total effect ────────────────────────────
        delta *= (0.5 + agent_openness * 0.5)

        deltas[topic] = delta

    return deltas


def update_algorithmic_bubble(mc: MediaConsumption, opinions: dict[str, float]):
    """Deepen or weaken the algorithmic bubble based on engagement patterns.

    Extreme opinions → more engagement → stronger bubble.
    Low social media use → bubble weakens.
    """
    if not opinions:
        mc.algorithmic_bubble *= 0.95  # decay without engagement
        return

    avg_extremity = sum(abs(v) for v in opinions.values()) / max(1, len(opinions))
    # Higher extremity × higher social exposure → deeper bubble
    bubble_growth = avg_extremity * mc.social_exposure * 0.08
    bubble_decay = 0.03  # natural decay
    mc.algorithmic_bubble += bubble_growth - bubble_decay
    mc.algorithmic_bubble = max(0.0, min(1.0, mc.algorithmic_bubble))


# ══════════════════════════════════════════════════════════════════════════════
# MEDIA → EVENT PROPAGATION AMPLIFICATION
# ══════════════════════════════════════════════════════════════════════════════

def media_event_amplifier(
    ml: MediaLandscape,
    mc: MediaConsumption,
    event_intensity: float,
) -> float:
    """How much media amplifies event reach for a specific agent.

    Returns a multiplier (1.0 = no effect, >1 = amplified, <1 = dampened).
    """
    # Print media: slight dampening (filters, editorial gatekeeping)
    print_effect = mc.print_exposure * ml.print_trust * 0.15  # modest boost
    # Mass media: significant amplification for high-intensity events
    mass_effect = mc.mass_exposure * ml.mass_reach * event_intensity * 0.3
    # Social media: viral amplification, especially for extreme content
    social_effect = mc.social_exposure * ml.social_virality * event_intensity * 0.5
    # Misinformation can amplify or distort
    misinfo_noise = ml.misinformation_level * mc.social_exposure * 0.1

    total = 1.0 + print_effect + mass_effect + social_effect + misinfo_noise
    # Media literacy provides some protection against amplification
    total = 1.0 + (total - 1.0) * (1 - mc.media_literacy * 0.25)

    return max(0.5, min(2.5, total))


# ══════════════════════════════════════════════════════════════════════════════
# MEDIA → ENVIRONMENT COUPLING
# ══════════════════════════════════════════════════════════════════════════════

def media_affect_environment(ml: MediaLandscape, env_indicators: dict):
    """Media landscape affects macro-environment indicators."""
    # Social media polarization erodes social cohesion
    if ml.social_polarization > 0.4:
        env_indicators["social_cohesion"] -= (ml.social_polarization - 0.4) * 0.02

    # Media pluralism is composite of print diversity and media fragmentation
    composite_pluralism = (
        ml.print_diversity * 0.3 +
        (1 - ml.social_echo_chamber) * 0.3 +
        (1 - ml.mass_sensationalism) * 0.2 +
        (1 - ml.misinformation_level) * 0.2
    )
    env_indicators["media_pluralism"] = (
        env_indicators.get("media_pluralism", 0.65) * 0.85 +
        composite_pluralism * 0.15
    )

    # Misinformation erodes institutional trust via democratic quality
    if ml.misinformation_level > 0.3:
        env_indicators["democratic_quality"] -= (ml.misinformation_level - 0.3) * 0.01

    # Clamp
    for key in ("social_cohesion", "media_pluralism", "democratic_quality"):
        if key in env_indicators:
            env_indicators[key] = max(0.0, min(1.0, env_indicators[key]))


def environment_affect_media(ml: MediaLandscape, env_indicators: dict):
    """Environment affects media landscape."""
    # Economic downturns reduce print media (advertising revenue)
    gdp = env_indicators.get("gdp_growth", 0.018)
    if gdp < 0:
        ml.print_reach *= (1 + gdp * 2)  # GDP < 0 shrinks print faster

    # High corruption fuels investigative journalism (paradoxically boosts print depth)
    corruption = env_indicators.get("corruption_index", 0.18)
    if corruption > 0.25:
        ml.print_depth += (corruption - 0.25) * 0.02

    # Democratic quality supports media plurality
    dem_quality = env_indicators.get("democratic_quality", 0.78)
    ml.print_diversity += (dem_quality - 0.7) * 0.01

    # Clamp
    for attr in ("print_reach", "print_depth", "print_diversity"):
        setattr(ml, attr, max(0.0, min(1.0, getattr(ml, attr))))


# ══════════════════════════════════════════════════════════════════════════════
# AGGREGATE MEDIA STATISTICS
# ══════════════════════════════════════════════════════════════════════════════

def compute_media_stats(
    ml: MediaLandscape,
    all_media_consumption: list[MediaConsumption],
) -> dict:
    """Compute city-level media statistics."""
    n = len(all_media_consumption) or 1

    avg_print = sum(mc.print_exposure for mc in all_media_consumption) / n
    avg_mass = sum(mc.mass_exposure for mc in all_media_consumption) / n
    avg_social = sum(mc.social_exposure for mc in all_media_consumption) / n
    avg_literacy = sum(mc.media_literacy for mc in all_media_consumption) / n
    avg_bubble = sum(mc.algorithmic_bubble for mc in all_media_consumption) / n

    # Fraction deeply in echo chambers
    deep_bubble = sum(1 for mc in all_media_consumption if mc.algorithmic_bubble > 0.5) / n
    # Fraction with low media literacy
    low_literacy = sum(1 for mc in all_media_consumption if mc.media_literacy < 0.3) / n

    return {
        "landscape": ml.to_dict(),
        "avg_print_exposure": round(avg_print, 3),
        "avg_mass_exposure": round(avg_mass, 3),
        "avg_social_exposure": round(avg_social, 3),
        "avg_media_literacy": round(avg_literacy, 3),
        "avg_algorithmic_bubble": round(avg_bubble, 3),
        "deep_bubble_fraction": round(deep_bubble, 3),
        "low_literacy_fraction": round(low_literacy, 3),
    }
