from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from functools import lru_cache
from pathlib import Path
from typing import Any

from django.db.models import Q

from db.models import (
    AssignmentStatus,
    Level,
    ProjectAssignment,
    ProjectRequirement,
    SpecialistProfile,
)


JSON_PATH = Path(__file__).resolve().parent.parent / "data" / "similar_professions.json"


@dataclass
class CandidateRecommendation:
    user_id: int
    full_name: str
    profession: str
    level: str
    experience_years: int
    mode: str  # ideal / fallback
    total_score: float

    required_skill_coverage: float
    required_skill_matches: int
    required_skill_total: int

    desired_skill_score: float
    desired_skill_matches: int
    desired_skill_total: int

    desired_level_score: float
    experience_score: float
    profession_match: float
    level_match: float

    is_exact_profession: bool
    meets_required_level: bool


@lru_cache(maxsize=1)
def load_similar_professions() -> dict[str, set[str]]:
    if not JSON_PATH.exists():
        return {}

    with JSON_PATH.open("r", encoding="utf-8") as f:
        raw = json.load(f)

    return {
        key: set(value)
        for key, value in raw.items()
    }


def level_rank(level: str) -> int:
    order = {
        Level.JUNIOR: 1,
        Level.MIDDLE: 2,
        Level.SENIOR: 3,
    }
    return order.get(level, 0)


def level_meets_required(actual_level: str, required_level: str) -> bool:
    return level_rank(actual_level) >= level_rank(required_level)


def level_match(actual_level: str, required_level: str) -> float:
    actual = level_rank(actual_level)
    required = level_rank(required_level)

    if actual == required:
        return 1.0

    if actual > required:
        return 0.75

    if actual == required - 1:
        return 0.5

    return 0.0


def profession_match(actual_profession: str, required_profession: str) -> float:
    if actual_profession == required_profession:
        return 1.0

    similar_map = load_similar_professions()
    if actual_profession in similar_map.get(required_profession, set()):
        return 0.5

    return 0.0


def required_skill_coverage(user_skills: set[str], required_skills: set[str]) -> tuple[float, int, int]:
    total = len(required_skills)
    if total == 0:
        return 1.0, 0, 0

    matches = len(user_skills & required_skills)
    return matches / total, matches, total


def desired_skill_score(user_skills: set[str], desired_skills: set[str]) -> tuple[float, int, int]:
    total = len(desired_skills)
    if total == 0:
        return 0.0, 0, 0

    matches = len(user_skills & desired_skills)
    score = 15 * (matches / total)
    return score, matches, total


def desired_level_score(actual_level: str, desired_level: str | None) -> float:
    if not desired_level:
        return 0.0
    return 7.0 if actual_level == desired_level else 0.0


def experience_score(experience_years: int) -> float:
    return min(12.0, 3.0 + 1.8 * float(experience_years))


def ideal_score(user_skills: set[str], desired_skills: set[str], actual_level: str, desired_level: str | None, experience_years: int) -> float:
    ds_score, _, _ = desired_skill_score(user_skills, desired_skills)
    dl_score = desired_level_score(actual_level, desired_level)
    exp_score = experience_score(experience_years)
    return ds_score + dl_score + exp_score


def fallback_score(user_skills: set[str], required_skills: set[str], actual_profession: str, required_profession: str, actual_level: str, required_level: str) -> float:
    coverage, _, _ = required_skill_coverage(user_skills, required_skills)
    p_match = profession_match(actual_profession, required_profession)
    l_match = level_match(actual_level, required_level)
    return 1000.0 * coverage + 100.0 * p_match + 10.0 * l_match


def get_busy_user_ids(requirement: ProjectRequirement) -> set[int]:
    project = requirement.project
    project_start = project.start_date
    project_end = project.end_date

    busy_statuses = [
        AssignmentStatus.ACCEPTED,
        AssignmentStatus.WORKING,
    ]

    qs = ProjectAssignment.objects.filter(status__in=busy_statuses)

    if project_end is not None:
        qs = qs.filter(
            start_date__lte=project_end
        ).filter(
            Q(end_date__isnull=True) | Q(end_date__gte=project_start)
        )
    else:
        qs = qs.filter(
            Q(end_date__isnull=True) | Q(end_date__gte=project_start)
        )

    return set(qs.values_list("user_id", flat=True))


def recommend_specialists_for_requirement(requirement: ProjectRequirement, limit: int = 10) -> list[dict[str, Any]]:
    required_skills = set(
        requirement.required_skills.values_list("skill", flat=True)
    )
    desired_skills = set(
        requirement.desired_skills.values_list("skill", flat=True)
    )

    busy_user_ids = get_busy_user_ids(requirement)

    profiles = (
        SpecialistProfile.objects
        .select_related("user")
        .prefetch_related("user__user_skills")
        .exclude(user_id__in=busy_user_ids)
    )

    ideal_candidates: list[CandidateRecommendation] = []
    reserve_candidates: list[CandidateRecommendation] = []

    for profile in profiles:
        user_skills = set(profile.user.user_skills.values_list("skill", flat=True))

        coverage, req_matches, req_total = required_skill_coverage(user_skills, required_skills)
        ds_score, ds_matches, ds_total = desired_skill_score(user_skills, desired_skills)
        dl_score = desired_level_score(profile.level, requirement.desired_level)
        exp_score = experience_score(profile.experience_years)
        p_match = profession_match(profile.profession, requirement.profession)
        l_match = level_match(profile.level, requirement.required_level)

        is_exact_profession = profile.profession == requirement.profession
        meets_level = level_meets_required(profile.level, requirement.required_level)
        has_all_required_skills = required_skills.issubset(user_skills)

        candidate = CandidateRecommendation(
            user_id=profile.user_id,
            full_name=f"{profile.user.last_name} {profile.user.first_name} {profile.user.middle_name or ''}".strip(),
            profession=profile.profession,
            level=profile.level,
            experience_years=profile.experience_years,
            mode="fallback",
            total_score=0.0,
            required_skill_coverage=coverage,
            required_skill_matches=req_matches,
            required_skill_total=req_total,
            desired_skill_score=ds_score,
            desired_skill_matches=ds_matches,
            desired_skill_total=ds_total,
            desired_level_score=dl_score,
            experience_score=exp_score,
            profession_match=p_match,
            level_match=l_match,
            is_exact_profession=is_exact_profession,
            meets_required_level=meets_level,
        )

        if is_exact_profession and meets_level and has_all_required_skills:
            candidate.mode = "ideal"
            candidate.total_score = ideal_score(
                user_skills=user_skills,
                desired_skills=desired_skills,
                actual_level=profile.level,
                desired_level=requirement.desired_level,
                experience_years=profile.experience_years,
            )
            ideal_candidates.append(candidate)
        else:
            if coverage > 0 or p_match > 0 or l_match > 0:
                candidate.total_score = fallback_score(
                    user_skills=user_skills,
                    required_skills=required_skills,
                    actual_profession=profile.profession,
                    required_profession=requirement.profession,
                    actual_level=profile.level,
                    required_level=requirement.required_level,
                )
                reserve_candidates.append(candidate)

    if ideal_candidates:
        ideal_candidates.sort(
            key=lambda c: (
                c.total_score,
                c.desired_skill_matches,
                c.experience_years,
                level_rank(c.level),
                -c.user_id,
            ),
            reverse=True,
        )
        return [asdict(item) for item in ideal_candidates[:limit]]

    reserve_candidates.sort(
        key=lambda c: (
            c.total_score,
            c.desired_skill_matches,
            c.experience_years,
            level_rank(c.level),
            -c.user_id,
        ),
        reverse=True,
    )
    return [asdict(item) for item in reserve_candidates[:limit]]