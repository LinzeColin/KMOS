#!/usr/bin/env python3
"""Validate the local-only independent review of IDS v0.1 STAGE-041..050.

The checker reads only the checked-in taskpack projection and prior review evidence.
It intentionally does not open business sources, raw metadata, runtime services, or
external providers.  A missing artefact or an unexpected contract field fails closed.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path
import sys
from typing import Any, Mapping

import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = PROJECT_ROOT.parent
PURSUE_ROOT = PROJECT_ROOT / "docs" / "pursuing_goal" / "ids_v0_1"
CONTRACT_PATH = (
    PURSUE_ROOT / "batch_review" / "stage041_050_batch_review_contract.json"
)
BATCH_PATH = PURSUE_ROOT / "BATCH041_050_UPLOAD_LOCK.yaml"
ROADMAP_PATH = PROJECT_ROOT / "docs" / "governance" / "roadmap.yaml"
STATUS_PATH = PROJECT_ROOT / "machine" / "facts" / "status.json"
PLAN_PATH = PROJECT_ROOT / "machine" / "facts" / "plan.json"
FACT_ROADMAP_PATH = PROJECT_ROOT / "machine" / "facts" / "roadmap.json"
ACCEPTANCE_PATH = PROJECT_ROOT / "machine" / "facts" / "acceptance.json"

TASK_ID = "IDS-V0_1-BATCH-041-050-REVIEW-GATE"
REVIEW_GATE = TASK_ID
NEXT_GATE = "IDS-STAGE051-P1-GATE"
SUCCESSOR_STAGE = "IDS-STAGE051"
SUCCESSOR_PHASE = "IDS-STAGE051-P1"
SUCCESSOR_TASK = "IDS-V0_1-STAGE051-P1"
SUCCESSOR_NEXT_GATE = "IDS-STAGE051-P2-GATE"
SUCCESSOR_PHASE2 = "IDS-STAGE051-P2"
SUCCESSOR_TASK2 = "IDS-V0_1-STAGE051-P2"
SUCCESSOR_NEXT_GATE2 = "IDS-STAGE051-P3-GATE"
SUCCESSOR_PHASE3 = "IDS-STAGE051-P3"
SUCCESSOR_TASK3 = "IDS-V0_1-STAGE051-P3"
SUCCESSOR_NEXT_GATE3 = "IDS-STAGE051-P4-GATE"
SUCCESSOR_PHASE4 = "IDS-STAGE051-P4"
SUCCESSOR_TASK4 = "IDS-V0_1-STAGE051-P4"
SUCCESSOR_NEXT_GATE4 = "IDS-STAGE051-REVIEW-GATE"
SUCCESSOR_REVIEW = "IDS-STAGE051-REVIEW"
SUCCESSOR_REVIEW_TASK = "IDS-V0_1-STAGE051-REVIEW"
SUCCESSOR_REVIEW_NEXT_GATE = "IDS-STAGE052-P1-GATE"
SUCCESSOR_STAGE052 = "IDS-STAGE052"
SUCCESSOR_PHASE052 = "IDS-STAGE052-P1"
SUCCESSOR_TASK052 = "IDS-V0_1-STAGE052-P1"
SUCCESSOR_NEXT_GATE052 = "IDS-STAGE052-P2-GATE"
SUCCESSOR_PHASE052_P2 = "IDS-STAGE052-P2"
SUCCESSOR_TASK052_P2 = "IDS-V0_1-STAGE052-P2"
SUCCESSOR_NEXT_GATE052_P2 = "IDS-STAGE052-P3-GATE"
SUCCESSOR_PHASE052_P3 = "IDS-STAGE052-P3"
SUCCESSOR_TASK052_P3 = "IDS-V0_1-STAGE052-P3"
SUCCESSOR_NEXT_GATE052_P3 = "IDS-STAGE052-P4-GATE"
SUCCESSOR_PHASE052_P4 = "IDS-STAGE052-P4"
SUCCESSOR_TASK052_P4 = "IDS-V0_1-STAGE052-P4"
SUCCESSOR_NEXT_GATE052_P4 = "IDS-STAGE052-REVIEW-GATE"
SUCCESSOR_PHASE052_REVIEW = "IDS-STAGE052-REVIEW"
SUCCESSOR_TASK052_REVIEW = "IDS-V0_1-STAGE052-REVIEW"
SUCCESSOR_NEXT_GATE052_REVIEW = "IDS-STAGE053-P1-GATE"
SUCCESSOR_STAGE053 = "IDS-STAGE053"
SUCCESSOR_PHASE053 = "IDS-STAGE053-P1"
SUCCESSOR_TASK053 = "IDS-V0_1-STAGE053-P1"
SUCCESSOR_NEXT_GATE053 = "IDS-STAGE053-P2-GATE"
SUCCESSOR_PHASE053_P2 = "IDS-STAGE053-P2"
SUCCESSOR_TASK053_P2 = "IDS-V0_1-STAGE053-P2"
SUCCESSOR_NEXT_GATE053_P2 = "IDS-STAGE053-P3-GATE"
SUCCESSOR_PHASE053_P3 = "IDS-STAGE053-P3"
SUCCESSOR_TASK053_P3 = "IDS-V0_1-STAGE053-P3"
SUCCESSOR_NEXT_GATE053_P3 = "IDS-STAGE053-P4-GATE"
SUCCESSOR_PHASE053_P4 = "IDS-STAGE053-P4"
SUCCESSOR_TASK053_P4 = "IDS-V0_1-STAGE053-P4"
SUCCESSOR_NEXT_GATE053_P4 = "IDS-STAGE053-REVIEW-GATE"
SUCCESSOR_PHASE053_REVIEW = "IDS-STAGE053-REVIEW"
SUCCESSOR_TASK053_REVIEW = "IDS-V0_1-STAGE053-REVIEW"
SUCCESSOR_NEXT_GATE053_REVIEW = "IDS-STAGE054-P1-GATE"
SUCCESSOR_STAGE054 = "IDS-STAGE054"
SUCCESSOR_PHASE054 = "IDS-STAGE054-P1"
SUCCESSOR_TASK054 = "IDS-V0_1-STAGE054-P1"
SUCCESSOR_NEXT_GATE054 = "IDS-STAGE054-P2-GATE"
SUCCESSOR_PHASE054_P2 = "IDS-STAGE054-P2"
SUCCESSOR_TASK054_P2 = "IDS-V0_1-STAGE054-P2"
SUCCESSOR_NEXT_GATE054_P2 = "IDS-STAGE054-P3-GATE"
SUCCESSOR_PHASE054_P3 = "IDS-STAGE054-P3"
SUCCESSOR_TASK054_P3 = "IDS-V0_1-STAGE054-P3"
SUCCESSOR_NEXT_GATE054_P3 = "IDS-STAGE054-P4-GATE"
SUCCESSOR_PHASE054_P4 = "IDS-STAGE054-P4"
SUCCESSOR_TASK054_P4 = "IDS-V0_1-STAGE054-P4"
SUCCESSOR_NEXT_GATE054_P4 = "IDS-STAGE054-REVIEW-GATE"
SUCCESSOR_PHASE054_REVIEW = "IDS-STAGE054-REVIEW"
SUCCESSOR_TASK054_REVIEW = "IDS-V0_1-STAGE054-REVIEW"
SUCCESSOR_NEXT_GATE054_REVIEW = "IDS-STAGE055-P1-GATE"
SUCCESSOR_STAGE055 = "IDS-STAGE055"
SUCCESSOR_PHASE055 = "IDS-STAGE055-P1"
SUCCESSOR_TASK055 = "IDS-V0_1-STAGE055-P1"
SUCCESSOR_NEXT_GATE055 = "IDS-STAGE055-P2-GATE"
SUCCESSOR_PHASE055_P2 = "IDS-STAGE055-P2"
SUCCESSOR_TASK055_P2 = "IDS-V0_1-STAGE055-P2"
SUCCESSOR_NEXT_GATE055_P2 = "IDS-STAGE055-P3-GATE"
SUCCESSOR_PHASE055_P3 = "IDS-STAGE055-P3"
SUCCESSOR_TASK055_P3 = "IDS-V0_1-STAGE055-P3"
SUCCESSOR_NEXT_GATE055_P3 = "IDS-STAGE055-P4-GATE"
SUCCESSOR_PHASE055_P4 = "IDS-STAGE055-P4"
SUCCESSOR_TASK055_P4 = "IDS-V0_1-STAGE055-P4"
SUCCESSOR_NEXT_GATE055_P4 = "IDS-STAGE055-REVIEW-GATE"
SUCCESSOR_PHASE055_REVIEW = "IDS-STAGE055-REVIEW"
SUCCESSOR_TASK055_REVIEW = "IDS-V0_1-STAGE055-REVIEW"
SUCCESSOR_NEXT_GATE055_REVIEW = "IDS-STAGE056-P1-GATE"
SUCCESSOR_STAGE056 = "IDS-STAGE056"
SUCCESSOR_PHASE056 = "IDS-STAGE056-P1"
SUCCESSOR_TASK056 = "IDS-V0_1-STAGE056-P1"
SUCCESSOR_NEXT_GATE056 = "IDS-STAGE056-P2-GATE"
SUCCESSOR_PHASE056_P2 = "IDS-STAGE056-P2"
SUCCESSOR_TASK056_P2 = "IDS-V0_1-STAGE056-P2"
SUCCESSOR_NEXT_GATE056_P2 = "IDS-STAGE056-P3-GATE"
SUCCESSOR_PHASE056_P3 = "IDS-STAGE056-P3"
SUCCESSOR_TASK056_P3 = "IDS-V0_1-STAGE056-P3"
SUCCESSOR_NEXT_GATE056_P3 = "IDS-STAGE056-P4-GATE"
SUCCESSOR_PHASE056_P4 = "IDS-STAGE056-P4"
SUCCESSOR_TASK056_P4 = "IDS-V0_1-STAGE056-P4"
SUCCESSOR_NEXT_GATE056_P4 = "IDS-STAGE056-REVIEW-GATE"
SUCCESSOR_PHASE056_REVIEW = "IDS-STAGE056-REVIEW"
SUCCESSOR_TASK056_REVIEW = "IDS-V0_1-STAGE056-REVIEW"
SUCCESSOR_NEXT_GATE056_REVIEW = "IDS-STAGE057-P1-GATE"
SUCCESSOR_STAGE057 = "IDS-STAGE057"
SUCCESSOR_PHASE057 = "IDS-STAGE057-P1"
SUCCESSOR_TASK057 = "IDS-V0_1-STAGE057-P1"
SUCCESSOR_NEXT_GATE057 = "IDS-STAGE057-P2-GATE"
SUCCESSOR_PHASE057_P2 = "IDS-STAGE057-P2"
SUCCESSOR_TASK057_P2 = "IDS-V0_1-STAGE057-P2"
SUCCESSOR_NEXT_GATE057_P2 = "IDS-STAGE057-P3-GATE"
SUCCESSOR_PHASE057_P3 = "IDS-STAGE057-P3"
SUCCESSOR_TASK057_P3 = "IDS-V0_1-STAGE057-P3"
SUCCESSOR_NEXT_GATE057_P3 = "IDS-STAGE057-P4-GATE"
SUCCESSOR_PHASE057_P4 = "IDS-STAGE057-P4"
SUCCESSOR_TASK057_P4 = "IDS-V0_1-STAGE057-P4"
SUCCESSOR_NEXT_GATE057_P4 = "IDS-STAGE057-REVIEW-GATE"
SUCCESSOR_PHASE057_REVIEW = "IDS-STAGE057-REVIEW"
SUCCESSOR_TASK057_REVIEW = "IDS-V0_1-STAGE057-REVIEW"
SUCCESSOR_NEXT_GATE057_REVIEW = "IDS-STAGE058-P1-GATE"
SUCCESSOR_STAGE058 = "IDS-STAGE058"
SUCCESSOR_PHASE058 = "IDS-STAGE058-P1"
SUCCESSOR_TASK058 = "IDS-V0_1-STAGE058-P1"
SUCCESSOR_NEXT_GATE058 = "IDS-STAGE058-P2-GATE"
SUCCESSOR_PHASE058_P2 = "IDS-STAGE058-P2"
SUCCESSOR_TASK058_P2 = "IDS-V0_1-STAGE058-P2"
SUCCESSOR_NEXT_GATE058_P2 = "IDS-STAGE058-P3-GATE"
SUCCESSOR_PHASE058_P3 = "IDS-STAGE058-P3"
SUCCESSOR_TASK058_P3 = "IDS-V0_1-STAGE058-P3"
SUCCESSOR_NEXT_GATE058_P3 = "IDS-STAGE058-P4-GATE"
SUCCESSOR_PHASE058_P4 = "IDS-STAGE058-P4"
SUCCESSOR_TASK058_P4 = "IDS-V0_1-STAGE058-P4"
SUCCESSOR_NEXT_GATE058_P4 = "IDS-STAGE058-REVIEW-GATE"
SUCCESSOR_PHASE058_REVIEW = "IDS-STAGE058-REVIEW"
SUCCESSOR_TASK058_REVIEW = "IDS-V0_1-STAGE058-REVIEW"
SUCCESSOR_NEXT_GATE058_REVIEW = "IDS-STAGE059-P1-GATE"
SUCCESSOR_STAGE059 = "IDS-STAGE059"
SUCCESSOR_PHASE059 = "IDS-STAGE059-P1"
SUCCESSOR_TASK059 = "IDS-V0_1-STAGE059-P1"
SUCCESSOR_NEXT_GATE059 = "IDS-STAGE059-P2-GATE"
SUCCESSOR_PHASE059_P2 = "IDS-STAGE059-P2"
SUCCESSOR_TASK059_P2 = "IDS-V0_1-STAGE059-P2"
SUCCESSOR_NEXT_GATE059_P2 = "IDS-STAGE059-P3-GATE"
SUCCESSOR_PHASE059_P3 = "IDS-STAGE059-P3"
SUCCESSOR_TASK059_P3 = "IDS-V0_1-STAGE059-P3"
SUCCESSOR_NEXT_GATE059_P3 = "IDS-STAGE059-P4-GATE"
SUCCESSOR_PHASE059_P4 = "IDS-STAGE059-P4"
SUCCESSOR_TASK059_P4 = "IDS-V0_1-STAGE059-P4"
SUCCESSOR_NEXT_GATE059_P4 = "IDS-STAGE059-REVIEW-GATE"
SUCCESSOR_PHASE059_REVIEW = "IDS-STAGE059-REVIEW"
SUCCESSOR_TASK059_REVIEW = "IDS-V0_1-STAGE059-REVIEW"
SUCCESSOR_NEXT_GATE059_REVIEW = "IDS-STAGE060-P1-GATE"
SUCCESSOR_STAGE060 = "IDS-STAGE060"
SUCCESSOR_PHASE060 = "IDS-STAGE060-P1"
SUCCESSOR_TASK060 = "IDS-V0_1-STAGE060-P1"
SUCCESSOR_NEXT_GATE060 = "IDS-STAGE060-P2-GATE"
SUCCESSOR_PHASE060_P2 = "IDS-STAGE060-P2"
SUCCESSOR_TASK060_P2 = "IDS-V0_1-STAGE060-P2"
SUCCESSOR_NEXT_GATE060_P2 = "IDS-STAGE060-P3-GATE"
SUCCESSOR_PHASE060_P3 = "IDS-STAGE060-P3"
SUCCESSOR_TASK060_P3 = "IDS-V0_1-STAGE060-P3"
SUCCESSOR_NEXT_GATE060_P3 = "IDS-STAGE060-P4-GATE"
SUCCESSOR_PHASE060_P4 = "IDS-STAGE060-P4"
SUCCESSOR_TASK060_P4 = "IDS-V0_1-STAGE060-P4"
SUCCESSOR_NEXT_GATE060_P4 = "IDS-STAGE060-REVIEW-GATE"
SUCCESSOR_PHASE060_REVIEW = "IDS-STAGE060-REVIEW"
SUCCESSOR_TASK060_REVIEW = "IDS-V0_1-STAGE060-REVIEW"
SUCCESSOR_NEXT_GATE060_REVIEW = "IDS-V0_1-BATCH-051-060-REVIEW-GATE"
SUCCESSOR_PHASE060_BATCH = "IDS-V0_1-BATCH-051-060-REVIEW-GATE"
SUCCESSOR_TASK060_BATCH = "IDS-V0_1-BATCH-051-060-REVIEW-GATE"
SUCCESSOR_NEXT_GATE060_BATCH = "IDS-STAGE061-P1-GATE"
SUCCESSOR_STAGE061 = "IDS-STAGE061"
SUCCESSOR_PHASE061 = "IDS-STAGE061-P1"
SUCCESSOR_TASK061 = "IDS-V0_1-STAGE061-P1"
SUCCESSOR_NEXT_GATE061 = "IDS-STAGE061-P2-GATE"
SUCCESSOR_PHASE061_P2 = "IDS-STAGE061-P2"
SUCCESSOR_TASK061_P2 = "IDS-V0_1-STAGE061-P2"
SUCCESSOR_NEXT_GATE061_P2 = "IDS-STAGE061-P3-GATE"
SUCCESSOR_PHASE061_P3 = "IDS-STAGE061-P3"
SUCCESSOR_TASK061_P3 = "IDS-V0_1-STAGE061-P3"
SUCCESSOR_NEXT_GATE061_P3 = "IDS-STAGE061-P4-GATE"
SUCCESSOR_PHASE061_P4 = "IDS-STAGE061-P4"
SUCCESSOR_TASK061_P4 = "IDS-V0_1-STAGE061-P4"
SUCCESSOR_NEXT_GATE061_P4 = "IDS-STAGE061-REVIEW-GATE"
SUCCESSOR_PHASE061_REVIEW = "IDS-STAGE061-REVIEW"
SUCCESSOR_TASK061_REVIEW = "IDS-V0_1-STAGE061-REVIEW"
SUCCESSOR_NEXT_GATE061_REVIEW = "IDS-STAGE062-P1-GATE"
SUCCESSOR_STAGE062 = "IDS-STAGE062"
SUCCESSOR_PHASE062 = "IDS-STAGE062-P1"
SUCCESSOR_TASK062 = "IDS-V0_1-STAGE062-P1"
SUCCESSOR_NEXT_GATE062 = "IDS-STAGE062-P2-GATE"
SUCCESSOR_PHASE062_P2 = "IDS-STAGE062-P2"
SUCCESSOR_TASK062_P2 = "IDS-V0_1-STAGE062-P2"
SUCCESSOR_NEXT_GATE062_P2 = "IDS-STAGE062-P3-GATE"
SUCCESSOR_PHASE062_P3 = "IDS-STAGE062-P3"
SUCCESSOR_TASK062_P3 = "IDS-V0_1-STAGE062-P3"
SUCCESSOR_NEXT_GATE062_P3 = "IDS-STAGE062-P4-GATE"
SUCCESSOR_PHASE062_P4 = "IDS-STAGE062-P4"
SUCCESSOR_TASK062_P4 = "IDS-V0_1-STAGE062-P4"
SUCCESSOR_NEXT_GATE062_P4 = "IDS-STAGE062-REVIEW-GATE"
SUCCESSOR_PHASE062_REVIEW = "IDS-STAGE062-REVIEW"
SUCCESSOR_TASK062_REVIEW = "IDS-V0_1-STAGE062-REVIEW"
SUCCESSOR_NEXT_GATE062_REVIEW = "IDS-STAGE063-P1-GATE"
SUCCESSOR_STAGE063 = "IDS-STAGE063"
SUCCESSOR_PHASE063 = "IDS-STAGE063-P1"
SUCCESSOR_TASK063 = "IDS-V0_1-STAGE063-P1"
SUCCESSOR_NEXT_GATE063 = "IDS-STAGE063-P2-GATE"
SUCCESSOR_PHASE063_P2 = "IDS-STAGE063-P2"
SUCCESSOR_TASK063_P2 = "IDS-V0_1-STAGE063-P2"
SUCCESSOR_NEXT_GATE063_P2 = "IDS-STAGE063-P3-GATE"
SUCCESSOR_PHASE063_P3 = "IDS-STAGE063-P3"
SUCCESSOR_TASK063_P3 = "IDS-V0_1-STAGE063-P3"
SUCCESSOR_NEXT_GATE063_P3 = "IDS-STAGE063-P4-GATE"
SUCCESSOR_PHASE063_P4 = "IDS-STAGE063-P4"
SUCCESSOR_TASK063_P4 = "IDS-V0_1-STAGE063-P4"
SUCCESSOR_NEXT_GATE063_P4 = "IDS-STAGE063-REVIEW-GATE"
SUCCESSOR_PHASE063_REVIEW = "IDS-STAGE063-REVIEW"
SUCCESSOR_TASK063_REVIEW = "IDS-V0_1-STAGE063-REVIEW"
SUCCESSOR_NEXT_GATE063_REVIEW = "IDS-STAGE064-P1-GATE"
SUCCESSOR_STAGE064 = "IDS-STAGE064"
SUCCESSOR_PHASE064 = "IDS-STAGE064-P1"
SUCCESSOR_TASK064 = "IDS-V0_1-STAGE064-P1"
SUCCESSOR_NEXT_GATE064 = "IDS-STAGE064-P2-GATE"
SUCCESSOR_PHASE064_P2 = "IDS-STAGE064-P2"
SUCCESSOR_TASK064_P2 = "IDS-V0_1-STAGE064-P2"
SUCCESSOR_NEXT_GATE064_P2 = "IDS-STAGE064-P3-GATE"
SUCCESSOR_PHASE064_P3 = "IDS-STAGE064-P3"
SUCCESSOR_TASK064_P3 = "IDS-V0_1-STAGE064-P3"
SUCCESSOR_NEXT_GATE064_P3 = "IDS-STAGE064-P4-GATE"
SUCCESSOR_PHASE064_P4 = "IDS-STAGE064-P4"
SUCCESSOR_TASK064_P4 = "IDS-V0_1-STAGE064-P4"
SUCCESSOR_NEXT_GATE064_P4 = "IDS-STAGE064-REVIEW-GATE"
SUCCESSOR_PHASE064_REVIEW = "IDS-STAGE064-REVIEW"
SUCCESSOR_TASK064_REVIEW = "IDS-V0_1-STAGE064-REVIEW"
SUCCESSOR_NEXT_GATE064_REVIEW = "IDS-STAGE065-P1-GATE"
SUCCESSOR_STAGE065 = "IDS-STAGE065"
SUCCESSOR_PHASE065 = "IDS-STAGE065-P1"
SUCCESSOR_TASK065 = "IDS-V0_1-STAGE065-P1"
SUCCESSOR_NEXT_GATE065 = "IDS-STAGE065-P2-GATE"
SUCCESSOR_PHASE065_P2 = "IDS-STAGE065-P2"
SUCCESSOR_TASK065_P2 = "IDS-V0_1-STAGE065-P2"
SUCCESSOR_NEXT_GATE065_P2 = "IDS-STAGE065-P3-GATE"
SUCCESSOR_PHASE065_P3 = "IDS-STAGE065-P3"
SUCCESSOR_TASK065_P3 = "IDS-V0_1-STAGE065-P3"
SUCCESSOR_NEXT_GATE065_P3 = "IDS-STAGE065-P4-GATE"
SUCCESSOR_PHASE065_P4 = "IDS-STAGE065-P4"
SUCCESSOR_TASK065_P4 = "IDS-V0_1-STAGE065-P4"
SUCCESSOR_NEXT_GATE065_P4 = "IDS-STAGE065-REVIEW-GATE"
SUCCESSOR_PHASE065_REVIEW = "IDS-STAGE065-REVIEW"
SUCCESSOR_TASK065_REVIEW = "IDS-V0_1-STAGE065-REVIEW"
SUCCESSOR_NEXT_GATE065_REVIEW = "IDS-STAGE066-P1-GATE"
SUCCESSOR_STAGE066 = "IDS-STAGE066"
SUCCESSOR_PHASE066 = "IDS-STAGE066-P1"
SUCCESSOR_TASK066 = "IDS-V0_1-STAGE066-P1"
SUCCESSOR_NEXT_GATE066 = "IDS-STAGE066-P2-GATE"
SUCCESSOR_PHASE066_P2 = "IDS-STAGE066-P2"
SUCCESSOR_TASK066_P2 = "IDS-V0_1-STAGE066-P2"
SUCCESSOR_NEXT_GATE066_P2 = "IDS-STAGE066-P3-GATE"
SUCCESSOR_PHASE066_P3 = "IDS-STAGE066-P3"
SUCCESSOR_TASK066_P3 = "IDS-V0_1-STAGE066-P3"
SUCCESSOR_NEXT_GATE066_P3 = "IDS-STAGE066-P4-GATE"
SUCCESSOR_PHASE066_P4 = "IDS-STAGE066-P4"
SUCCESSOR_TASK066_P4 = "IDS-V0_1-STAGE066-P4"
SUCCESSOR_NEXT_GATE066_P4 = "IDS-STAGE066-REVIEW-GATE"
SUCCESSOR_PHASE066_REVIEW = "IDS-STAGE066-REVIEW"
SUCCESSOR_TASK066_REVIEW = "IDS-V0_1-STAGE066-REVIEW"
SUCCESSOR_NEXT_GATE066_REVIEW = "IDS-STAGE067-P1-GATE"
SUCCESSOR_STAGE067 = "IDS-STAGE067"
SUCCESSOR_PHASE067 = "IDS-STAGE067-P1"
SUCCESSOR_TASK067 = "IDS-V0_1-STAGE067-P1"
SUCCESSOR_NEXT_GATE067 = "IDS-STAGE067-P2-GATE"
SUCCESSOR_PHASE067_P2 = "IDS-STAGE067-P2"
SUCCESSOR_TASK067_P2 = "IDS-V0_1-STAGE067-P2"
SUCCESSOR_NEXT_GATE067_P2 = "IDS-STAGE067-P3-GATE"
SUCCESSOR_PHASE067_P3 = "IDS-STAGE067-P3"
SUCCESSOR_TASK067_P3 = "IDS-V0_1-STAGE067-P3"
SUCCESSOR_NEXT_GATE067_P3 = "IDS-STAGE067-P4-GATE"
SUCCESSOR_PHASE067_P4 = "IDS-STAGE067-P4"
SUCCESSOR_TASK067_P4 = "IDS-V0_1-STAGE067-P4"
SUCCESSOR_NEXT_GATE067_P4 = "IDS-STAGE067-REVIEW-GATE"
SUCCESSOR_PHASE067_REVIEW = "IDS-STAGE067-REVIEW"
SUCCESSOR_TASK067_REVIEW = "IDS-V0_1-STAGE067-REVIEW"
SUCCESSOR_NEXT_GATE067_REVIEW = "IDS-STAGE068-P1-GATE"
SUCCESSOR_STAGE068 = "IDS-STAGE068"
SUCCESSOR_PHASE068 = "IDS-STAGE068-P1"
SUCCESSOR_TASK068 = "IDS-V0_1-STAGE068-P1"
SUCCESSOR_NEXT_GATE068 = "IDS-STAGE068-P2-GATE"
SUCCESSOR_PHASE068_P2 = "IDS-STAGE068-P2"
SUCCESSOR_TASK068_P2 = "IDS-V0_1-STAGE068-P2"
SUCCESSOR_NEXT_GATE068_P2 = "IDS-STAGE068-P3-GATE"
SUCCESSOR_PHASE068_P3 = "IDS-STAGE068-P3"
SUCCESSOR_TASK068_P3 = "IDS-V0_1-STAGE068-P3"
SUCCESSOR_NEXT_GATE068_P3 = "IDS-STAGE068-P4-GATE"
SUCCESSOR_PHASE068_P4 = "IDS-STAGE068-P4"
SUCCESSOR_TASK068_P4 = "IDS-V0_1-STAGE068-P4"
SUCCESSOR_NEXT_GATE068_P4 = "IDS-STAGE068-REVIEW-GATE"
SUCCESSOR_PHASE068_REVIEW = "IDS-STAGE068-REVIEW"
SUCCESSOR_TASK068_REVIEW = "IDS-V0_1-STAGE068-REVIEW"
SUCCESSOR_NEXT_GATE068_REVIEW = "IDS-STAGE069-P1-GATE"
SUCCESSOR_STAGE069 = "IDS-STAGE069"
SUCCESSOR_PHASE069 = "IDS-STAGE069-P1"
SUCCESSOR_TASK069 = "IDS-V0_1-STAGE069-P1"
SUCCESSOR_NEXT_GATE069 = "IDS-STAGE069-P2-GATE"
SUCCESSOR_PHASE069_P2 = "IDS-STAGE069-P2"
SUCCESSOR_TASK069_P2 = "IDS-V0_1-STAGE069-P2"
SUCCESSOR_NEXT_GATE069_P2 = "IDS-STAGE069-P3-GATE"
SUCCESSOR_PHASE069_P3 = "IDS-STAGE069-P3"
SUCCESSOR_TASK069_P3 = "IDS-V0_1-STAGE069-P3"
SUCCESSOR_NEXT_GATE069_P3 = "IDS-STAGE069-P4-GATE"
SUCCESSOR_PHASE069_P4 = "IDS-STAGE069-P4"
SUCCESSOR_TASK069_P4 = "IDS-V0_1-STAGE069-P4"
SUCCESSOR_NEXT_GATE069_P4 = "IDS-STAGE069-REVIEW-GATE"
SUCCESSOR_PHASE069_REVIEW = "IDS-STAGE069-REVIEW"
SUCCESSOR_TASK069_REVIEW = "IDS-V0_1-STAGE069-REVIEW"
SUCCESSOR_NEXT_GATE069_REVIEW = "IDS-STAGE070-P1-GATE"
SUCCESSOR_STAGE070 = "IDS-STAGE070"
SUCCESSOR_PHASE070 = "IDS-STAGE070-P1"
SUCCESSOR_TASK070 = "IDS-V0_1-STAGE070-P1"
SUCCESSOR_NEXT_GATE070 = "IDS-STAGE070-P2-GATE"
SUCCESSOR_PHASE070_P2 = "IDS-STAGE070-P2"
SUCCESSOR_TASK070_P2 = "IDS-V0_1-STAGE070-P2"
SUCCESSOR_NEXT_GATE070_P2 = "IDS-STAGE070-P3-GATE"
SUCCESSOR_PHASE070_P3 = "IDS-STAGE070-P3"
SUCCESSOR_TASK070_P3 = "IDS-V0_1-STAGE070-P3"
SUCCESSOR_NEXT_GATE070_P3 = "IDS-STAGE070-P4-GATE"
SUCCESSOR_PHASE070_P4 = "IDS-STAGE070-P4"
SUCCESSOR_TASK070_P4 = "IDS-V0_1-STAGE070-P4"
SUCCESSOR_NEXT_GATE070_P4 = "IDS-STAGE070-REVIEW-GATE"
SUCCESSOR_PHASE070_REVIEW = "IDS-STAGE070-REVIEW"
SUCCESSOR_TASK070_REVIEW = "IDS-V0_1-STAGE070-REVIEW"
SUCCESSOR_NEXT_GATE070_REVIEW = "IDS-STAGE071-P1-GATE"
SUCCESSOR_STAGE071 = "IDS-STAGE071"
SUCCESSOR_PHASE071 = "IDS-STAGE071-P1"
SUCCESSOR_TASK071 = "IDS-V0_1-STAGE071-P1"
SUCCESSOR_NEXT_GATE071 = "IDS-STAGE071-P2-GATE"
SUCCESSOR_PHASE071_P2 = "IDS-STAGE071-P2"
SUCCESSOR_TASK071_P2 = "IDS-V0_1-STAGE071-P2"
SUCCESSOR_NEXT_GATE071_P2 = "IDS-STAGE071-P3-GATE"
SUCCESSOR_PHASE071_P3 = "IDS-STAGE071-P3"
SUCCESSOR_TASK071_P3 = "IDS-V0_1-STAGE071-P3"
SUCCESSOR_NEXT_GATE071_P3 = "IDS-STAGE071-P4-GATE"
SUCCESSOR_PHASE071_P4 = "IDS-STAGE071-P4"
SUCCESSOR_TASK071_P4 = "IDS-V0_1-STAGE071-P4"
SUCCESSOR_NEXT_GATE071_P4 = "IDS-STAGE071-REVIEW-GATE"
SUCCESSOR_PHASE071_REVIEW = "IDS-STAGE071-REVIEW"
SUCCESSOR_TASK071_REVIEW = "IDS-V0_1-STAGE071-REVIEW"
SUCCESSOR_NEXT_GATE071_REVIEW = "IDS-STAGE072-P1-GATE"
SUCCESSOR_STAGE072 = "IDS-STAGE072"
SUCCESSOR_PHASE072_P1 = "IDS-STAGE072-P1"
SUCCESSOR_TASK072_P1 = "IDS-V0_1-STAGE072-P1"
SUCCESSOR_NEXT_GATE072_P1 = "IDS-STAGE072-P2-GATE"
SUCCESSOR_PHASE072_P2 = "IDS-STAGE072-P2"
SUCCESSOR_TASK072_P2 = "IDS-V0_1-STAGE072-P2"
SUCCESSOR_NEXT_GATE072_P2 = "IDS-STAGE072-P3-GATE"
SUCCESSOR_PHASE072_P3 = "IDS-STAGE072-P3"
SUCCESSOR_TASK072_P3 = "IDS-V0_1-STAGE072-P3"
SUCCESSOR_NEXT_GATE072_P3 = "IDS-STAGE072-P4-GATE"
SUCCESSOR_PHASE072_P4 = "IDS-STAGE072-P4"
SUCCESSOR_TASK072_P4 = "IDS-V0_1-STAGE072-P4"
SUCCESSOR_NEXT_GATE072_P4 = "IDS-STAGE072-REVIEW-GATE"
SUCCESSOR_PHASE072_REVIEW = "IDS-STAGE072-REVIEW"
SUCCESSOR_TASK072_REVIEW = "IDS-V0_1-STAGE072-REVIEW"
SUCCESSOR_NEXT_GATE072_REVIEW = "IDS-STAGE073-P1-GATE"
PASS_RESULT = "PASS_BATCH_REVIEWED_LOCAL_GLOBAL_UPLOAD_LOCKED"
EXPECTED_STAGE_IDS = [f"STAGE-{stage:03d}" for stage in range(41, 51)]
EXPECTED_ACCEPTANCE_IDS = [f"ACC-STAGE-{stage:03d}" for stage in range(41, 51)]
EXPECTED_CONTRACT_KEYS = {
    "schema_version",
    "batch_id",
    "task_id",
    "stage_range",
    "acceptance_range",
    "authority_context",
    "second_authoritative_source_created",
    "stage_reviews",
    "cross_stage_contract",
    "governance_gate",
    "findings",
    "truth_contract",
}
EXPECTED_STAGE_REVIEW_KEYS = {
    "stage_id",
    "acceptance_id",
    "expected_status",
    "review_task_id",
    "taskpack_ref",
    "review_artifact_ref",
    "checker_ref",
    "test_ref",
    "machine_run_ref",
}
EXPECTED_TRUTH = {
    "taskpack_context_read_performed": True,
    "prior_stage_review_evidence_read_performed": True,
    "second_authoritative_source_created": False,
    "ids_business_source_read_performed": False,
    "raw_metadata_content_accessed": False,
    "source_file_open_performed": False,
    "file_detection_performed": False,
    "parser_execution_performed": False,
    "fallback_execution_performed": False,
    "quality_gate_evaluation_performed": False,
    "persistent_state_write_performed": False,
    "agent_execution_performed": False,
    "model_call_performed": False,
    "model_token_consumption_performed": False,
    "ovh_deployment_performed": False,
    "production_runtime_activation_performed": False,
    "stage051_started": False,
    "batch_upload_gate_started": False,
    "github_upload_performed": False,
    "push_performed": False,
    "app_reinstall_performed": False,
}
EXPECTED_INTERFACE_CHAIN = [
    "STAGE-041 lock registration and race control -> STAGE-042 automatic lifecycle",
    "STAGE-042 automatic lifecycle -> STAGE-043 worker crash recovery",
    "STAGE-043 worker crash recovery -> STAGE-044 half-product cleanup",
    "STAGE-044 cleanup boundary -> STAGE-045 file type detection",
    "STAGE-045 file type detection -> STAGE-046 parser routing",
    "STAGE-046 parser routing -> STAGE-047 parser output contract",
    "STAGE-047 parser output contract -> STAGE-048 parser fallback boundary",
    "STAGE-048 parser fallback boundary -> STAGE-049 differential parser evaluation",
    "STAGE-049 differential parser evaluation -> STAGE-050 prompt-injection marker boundary",
]


def load_contract() -> dict[str, Any]:
    """Return the only derived review matrix used by this gate."""

    return json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))


def _load_yaml(path: Path) -> dict[str, Any]:
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    return value if isinstance(value, dict) else {}


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _contract_shape_checks(contract: Mapping[str, Any]) -> dict[str, bool]:
    stages = contract.get("stage_reviews")
    truth = contract.get("truth_contract")
    gate = contract.get("governance_gate")
    chain = contract.get("cross_stage_contract")
    findings = contract.get("findings")
    return {
        "top_level_fields_exact": set(contract) == EXPECTED_CONTRACT_KEYS,
        "identity_exact": (
            contract.get("schema_version") == "ids.v0_1.batch041_050.review_contract.v1"
            and contract.get("batch_id") == "IDS-V0_1-BATCH-041-050"
            and contract.get("task_id") == TASK_ID
            and contract.get("stage_range") == "STAGE-041..STAGE-050"
            and contract.get("acceptance_range") == "ACC-STAGE-041..ACC-STAGE-050"
            and contract.get("authority_context")
            == "FROZEN_IDS_V0_1_TASKPACK_AND_EXISTING_STAGE_REVIEW_EVIDENCE"
            and contract.get("second_authoritative_source_created") is False
        ),
        "stage_review_shapes_exact": (
            isinstance(stages, list)
            and len(stages) == 10
            and all(
                isinstance(stage, dict) and set(stage) == EXPECTED_STAGE_REVIEW_KEYS
                for stage in stages
            )
        ),
        "stage_identity_matrix_exact": (
            isinstance(stages, list)
            and [stage.get("stage_id") for stage in stages] == EXPECTED_STAGE_IDS
            and [stage.get("acceptance_id") for stage in stages]
            == EXPECTED_ACCEPTANCE_IDS
            and all(
                stage.get("review_task_id")
                == f"IDS-V0_1-{stage.get('stage_id', '').replace('-', '')}-REVIEW"
                for stage in stages
                if isinstance(stage, dict)
            )
        ),
        "cross_stage_chain_exact": (
            isinstance(chain, dict)
            and chain.get("interface_chain") == EXPECTED_INTERFACE_CHAIN
            and chain.get("runtime_execution_allowed") is False
            and chain.get("production_runtime_allowed") is False
            and chain.get("stage051_started") is False
            and chain.get("stage051_entry_gate") == NEXT_GATE
        ),
        "governance_gate_exact": (
            isinstance(gate, dict)
            and gate
            == {
                "review_status": "batch041_050_reviewed_local_global_upload_locked",
                "reviewed_stage_count": 10,
                "current_gate": REVIEW_GATE,
                "next_gate": NEXT_GATE,
                "push_allowed": False,
                "github_upload_allowed": False,
                "batch_upload_gate_deferred": "IDS-V0_1-BATCH-041-050-UPLOAD-GATE",
                "global_release_acceptance_required": "ACC-STAGE-168",
                "app_reinstall_allowed": False,
            }
        ),
        "finding_shape_exact": (
            isinstance(findings, list)
            and findings
            == [
                {
                    "finding_id": "BATCH041-050-REVIEW-F1",
                    "severity": "Important",
                    "status": "repaired",
                    "summary": "The prior per-batch upload route did not express the frozen all-taskpack completion condition.",
                    "repair": "Batch review advances only to the Stage051 entry gate while all upload paths remain deferred.",
                }
            ]
        ),
        "truth_contract_exact": isinstance(truth, dict) and truth == EXPECTED_TRUTH,
    }


def _artifact_checks(contract: Mapping[str, Any]) -> dict[str, bool]:
    stages = contract.get("stage_reviews")
    checks: dict[str, bool] = {}
    if not isinstance(stages, list):
        return {stage_id: False for stage_id in EXPECTED_STAGE_IDS}
    for stage in stages:
        stage_id = stage.get("stage_id", "UNKNOWN")
        refs = (
            stage.get("taskpack_ref"),
            stage.get("review_artifact_ref"),
            stage.get("checker_ref"),
            stage.get("test_ref"),
            stage.get("machine_run_ref"),
        )
        try:
            checks[str(stage_id)] = all(
                isinstance(ref, str) and (REPO_ROOT / ref).is_file() for ref in refs
            )
            machine_run = REPO_ROOT / str(stage.get("machine_run_ref", ""))
            if checks[str(stage_id)]:
                checks[str(stage_id)] = isinstance(_load_json(machine_run), dict)
        except (OSError, json.JSONDecodeError):
            checks[str(stage_id)] = False
    return checks


def _stage_checks(
    contract: Mapping[str, Any],
    batch: Mapping[str, Any],
    stage_result_overrides: Mapping[str, bool] | None,
) -> dict[str, bool]:
    progress = batch.get("stage_progress")
    stages = contract.get("stage_reviews")
    checks: dict[str, bool] = {}
    if not isinstance(progress, dict) or not isinstance(stages, list):
        return {stage_id: False for stage_id in EXPECTED_STAGE_IDS}
    for item in stages:
        stage_id = item.get("stage_id")
        node = progress.get(stage_id) if isinstance(stage_id, str) else None
        override = (
            stage_result_overrides.get(stage_id, True)
            if stage_result_overrides is not None and isinstance(stage_id, str)
            else True
        )
        checks[str(stage_id)] = bool(
            override
            and isinstance(node, dict)
            and node.get("status") == item.get("expected_status")
            and node.get("current_task_id") == item.get("review_task_id")
            and node.get("acceptance_id") == item.get("acceptance_id")
            and node.get("review_status") == "passed"
            and node.get("whole_stage_review_performed") is True
            and node.get("batch_review_performed") is True
            and node.get("execution_ready", False) is False
            and node.get("github_upload_allowed") is False
            and node.get("app_reinstall_allowed") is False
            and node.get("push_allowed", False) is False
        )
    return checks


def _governance_checks(
    contract: Mapping[str, Any], batch: Mapping[str, Any], roadmap: Mapping[str, Any]
) -> dict[str, bool]:
    gate = contract.get("governance_gate", {})
    transitions = batch.get("transition_history", {})
    decision = batch.get("decision", {})
    upload_gate = batch.get("upload_gate", {})
    stage050 = next(
        (
            candidate
            for candidate in roadmap.get("stages", [])
            if isinstance(candidate, dict) and candidate.get("stage_id") == "IDS-STAGE050"
        ),
        {},
    )
    phase = next(
        (
            candidate
            for candidate in stage050.get("phases", [])
            if isinstance(candidate, dict) and candidate.get("phase_id") == TASK_ID
        ),
        {},
    )
    task = next(
        (
            candidate
            for candidate in phase.get("tasks", [])
            if isinstance(candidate, dict) and candidate.get("task_id") == TASK_ID
        ),
        {},
    )
    expected_evidence = {
        "KM_IDSystem/docs/pursuing_goal/ids_v0_1/BATCH041_050_REVIEW_GATE.md",
        "KM_IDSystem/docs/pursuing_goal/ids_v0_1/batch_review/stage041_050_batch_review_contract.json",
        "KM_IDSystem/scripts/check_batch041_050_review.py",
        "KM_IDSystem/docs/pursuing_goal/ids_v0_1/tests/test_batch041_050_review_gate.py",
        "KM_IDSystem/machine/runs/2026-08-12-batch041-050-review-local.json",
    }
    return {
        "batch_lock_identity_and_status": (
            batch.get("batch_id") == "IDS-V0_1-BATCH-041-050"
            and batch.get("status") == gate.get("review_status")
            and batch.get("review_task_id") == TASK_ID
            and batch.get("review_evidence_ref")
            == "KM_IDSystem/docs/pursuing_goal/ids_v0_1/BATCH041_050_REVIEW_GATE.md"
            and batch.get("review_contract_ref")
            == "KM_IDSystem/docs/pursuing_goal/ids_v0_1/batch_review/stage041_050_batch_review_contract.json"
        ),
        "transition_history_exact": (
            isinstance(transitions, dict)
            and transitions.get("batch041_050_review_state")
            == {
                "status": "batch041_050_reviewed_local_global_upload_locked",
                "current_task_id": TASK_ID,
                "next_gate": NEXT_GATE,
                "next_allowed_task_id": "IDS-V0_1-STAGE051-P1",
                "github_upload_allowed": False,
            }
        ),
        "decision_keeps_all_upload_paths_closed": (
            isinstance(decision, dict)
            and decision.get("current_task_id") == TASK_ID
            and decision.get("next_allowed_task_id") == "IDS-V0_1-STAGE051-P1"
            and decision.get("github_upload_allowed") is False
            and decision.get("push_allowed") is False
            and decision.get("global_upload_deferred") is True
        ),
        "upload_gate_remains_deferred": (
            isinstance(upload_gate, dict)
            and upload_gate.get("push_allowed") is False
            and upload_gate.get("github_upload_allowed") is False
            and upload_gate.get("batch_upload_gate_deferred") is True
            and upload_gate.get("global_release_acceptance_required") == "ACC-STAGE-168"
        ),
        "roadmap_current_route_exact": (
            (
                roadmap.get("current_stage_id") == "IDS-STAGE050"
                and roadmap.get("current_phase_id") == TASK_ID
                and roadmap.get("current_task_id") == TASK_ID
                and roadmap.get("next_gate_id") == NEXT_GATE
            )
            or (
                roadmap.get("current_stage_id") == SUCCESSOR_STAGE
                and roadmap.get("current_phase_id") == SUCCESSOR_PHASE
                and roadmap.get("current_task_id") == SUCCESSOR_TASK
                and roadmap.get("next_gate_id") == SUCCESSOR_NEXT_GATE
            )
            or (
                roadmap.get("current_stage_id") == SUCCESSOR_STAGE
                and roadmap.get("current_phase_id") == SUCCESSOR_PHASE2
                and roadmap.get("current_task_id") == SUCCESSOR_TASK2
                and roadmap.get("next_gate_id") == SUCCESSOR_NEXT_GATE2
            )
            or (
                roadmap.get("current_stage_id") == SUCCESSOR_STAGE
                and roadmap.get("current_phase_id") == SUCCESSOR_PHASE3
                and roadmap.get("current_task_id") == SUCCESSOR_TASK3
                and roadmap.get("next_gate_id") == SUCCESSOR_NEXT_GATE3
            )
            or (
                roadmap.get("current_stage_id") == SUCCESSOR_STAGE
                and roadmap.get("current_phase_id") == SUCCESSOR_PHASE4
                and roadmap.get("current_task_id") == SUCCESSOR_TASK4
                and roadmap.get("next_gate_id") == SUCCESSOR_NEXT_GATE4
            )
            or (
                roadmap.get("current_stage_id") == SUCCESSOR_STAGE
                and roadmap.get("current_phase_id") == SUCCESSOR_REVIEW
                and roadmap.get("current_task_id") == SUCCESSOR_REVIEW_TASK
                and roadmap.get("next_gate_id") == SUCCESSOR_REVIEW_NEXT_GATE
            )
            or (
                roadmap.get("current_stage_id") == SUCCESSOR_STAGE052
                and roadmap.get("current_phase_id") == SUCCESSOR_PHASE052
                and roadmap.get("current_task_id") == SUCCESSOR_TASK052
                and roadmap.get("next_gate_id") == SUCCESSOR_NEXT_GATE052
            )
            or (
                roadmap.get("current_stage_id") == SUCCESSOR_STAGE052
                and roadmap.get("current_phase_id") == SUCCESSOR_PHASE052_P2
                and roadmap.get("current_task_id") == SUCCESSOR_TASK052_P2
                and roadmap.get("next_gate_id") == SUCCESSOR_NEXT_GATE052_P2
            )
            or (
                roadmap.get("current_stage_id") == SUCCESSOR_STAGE052
                and roadmap.get("current_phase_id") == SUCCESSOR_PHASE052_P3
                and roadmap.get("current_task_id") == SUCCESSOR_TASK052_P3
                and roadmap.get("next_gate_id") == SUCCESSOR_NEXT_GATE052_P3
            )
            or (
                roadmap.get("current_stage_id") == SUCCESSOR_STAGE052
                and roadmap.get("current_phase_id") == SUCCESSOR_PHASE052_P4
                and roadmap.get("current_task_id") == SUCCESSOR_TASK052_P4
                and roadmap.get("next_gate_id") == SUCCESSOR_NEXT_GATE052_P4
            )
            or (
                roadmap.get("current_stage_id") == SUCCESSOR_STAGE052
                and roadmap.get("current_phase_id") == SUCCESSOR_PHASE052_REVIEW
                and roadmap.get("current_task_id") == SUCCESSOR_TASK052_REVIEW
                and roadmap.get("next_gate_id") == SUCCESSOR_NEXT_GATE052_REVIEW
            )
            or (
                roadmap.get("current_stage_id") == SUCCESSOR_STAGE053
                and roadmap.get("current_phase_id") == SUCCESSOR_PHASE053
                and roadmap.get("current_task_id") == SUCCESSOR_TASK053
                and roadmap.get("next_gate_id") == SUCCESSOR_NEXT_GATE053
            )
            or (
                roadmap.get("current_stage_id") == SUCCESSOR_STAGE053
                and roadmap.get("current_phase_id") == SUCCESSOR_PHASE053_P2
                and roadmap.get("current_task_id") == SUCCESSOR_TASK053_P2
                and roadmap.get("next_gate_id") == SUCCESSOR_NEXT_GATE053_P2
            )
            or (
                roadmap.get("current_stage_id") == SUCCESSOR_STAGE053
                and roadmap.get("current_phase_id") == SUCCESSOR_PHASE053_P3
                and roadmap.get("current_task_id") == SUCCESSOR_TASK053_P3
                and roadmap.get("next_gate_id") == SUCCESSOR_NEXT_GATE053_P3
            )
            or (
                roadmap.get("current_stage_id") == SUCCESSOR_STAGE053
                and roadmap.get("current_phase_id") == SUCCESSOR_PHASE053_P4
                and roadmap.get("current_task_id") == SUCCESSOR_TASK053_P4
                and roadmap.get("next_gate_id") == SUCCESSOR_NEXT_GATE053_P4
            )
            or (
                roadmap.get("current_stage_id") == SUCCESSOR_STAGE053
                and roadmap.get("current_phase_id") == SUCCESSOR_PHASE053_REVIEW
                and roadmap.get("current_task_id") == SUCCESSOR_TASK053_REVIEW
                and roadmap.get("next_gate_id") == SUCCESSOR_NEXT_GATE053_REVIEW
            )
            or (
                roadmap.get("current_stage_id") == SUCCESSOR_STAGE054
                and roadmap.get("current_phase_id") == SUCCESSOR_PHASE054
                and roadmap.get("current_task_id") == SUCCESSOR_TASK054
                and roadmap.get("next_gate_id") == SUCCESSOR_NEXT_GATE054
            )
            or (
                roadmap.get("current_stage_id") == SUCCESSOR_STAGE054
                and roadmap.get("current_phase_id") == SUCCESSOR_PHASE054_P2
                and roadmap.get("current_task_id") == SUCCESSOR_TASK054_P2
                and roadmap.get("next_gate_id") == SUCCESSOR_NEXT_GATE054_P2
            )
            or (
                roadmap.get("current_stage_id") == SUCCESSOR_STAGE054
                and roadmap.get("current_phase_id") == SUCCESSOR_PHASE054_P3
                and roadmap.get("current_task_id") == SUCCESSOR_TASK054_P3
                and roadmap.get("next_gate_id") == SUCCESSOR_NEXT_GATE054_P3
            )
            or (
                roadmap.get("current_stage_id") == SUCCESSOR_STAGE054
                and roadmap.get("current_phase_id") == SUCCESSOR_PHASE054_P4
                and roadmap.get("current_task_id") == SUCCESSOR_TASK054_P4
                and roadmap.get("next_gate_id") == SUCCESSOR_NEXT_GATE054_P4
            )
            or (
                roadmap.get("current_stage_id") == SUCCESSOR_STAGE054
                and roadmap.get("current_phase_id") == SUCCESSOR_PHASE054_REVIEW
                and roadmap.get("current_task_id") == SUCCESSOR_TASK054_REVIEW
                and roadmap.get("next_gate_id") == SUCCESSOR_NEXT_GATE054_REVIEW
            )
            or (
                roadmap.get("current_stage_id") == SUCCESSOR_STAGE055
                and roadmap.get("current_phase_id") == SUCCESSOR_PHASE055
                and roadmap.get("current_task_id") == SUCCESSOR_TASK055
                and roadmap.get("next_gate_id") == SUCCESSOR_NEXT_GATE055
            )
            or (
                roadmap.get("current_stage_id") == SUCCESSOR_STAGE055
                and roadmap.get("current_phase_id") == SUCCESSOR_PHASE055_P2
                and roadmap.get("current_task_id") == SUCCESSOR_TASK055_P2
                and roadmap.get("next_gate_id") == SUCCESSOR_NEXT_GATE055_P2
            )
            or (
                roadmap.get("current_stage_id") == SUCCESSOR_STAGE055
                and roadmap.get("current_phase_id") == SUCCESSOR_PHASE055_P3
                and roadmap.get("current_task_id") == SUCCESSOR_TASK055_P3
                and roadmap.get("next_gate_id") == SUCCESSOR_NEXT_GATE055_P3
            )
            or (
                roadmap.get("current_stage_id") == SUCCESSOR_STAGE055
                and roadmap.get("current_phase_id") == SUCCESSOR_PHASE055_P4
                and roadmap.get("current_task_id") == SUCCESSOR_TASK055_P4
                and roadmap.get("next_gate_id") == SUCCESSOR_NEXT_GATE055_P4
            )
            or (
                roadmap.get("current_stage_id") == SUCCESSOR_STAGE055
                and roadmap.get("current_phase_id") == SUCCESSOR_PHASE055_REVIEW
                and roadmap.get("current_task_id") == SUCCESSOR_TASK055_REVIEW
                and roadmap.get("next_gate_id") == SUCCESSOR_NEXT_GATE055_REVIEW
            )
            or (
                roadmap.get("current_stage_id") == SUCCESSOR_STAGE056
                and roadmap.get("current_phase_id") == SUCCESSOR_PHASE056
                and roadmap.get("current_task_id") == SUCCESSOR_TASK056
                and roadmap.get("next_gate_id") == SUCCESSOR_NEXT_GATE056
            )
            or (
                roadmap.get("current_stage_id") == SUCCESSOR_STAGE056
                and roadmap.get("current_phase_id") == SUCCESSOR_PHASE056_P2
                and roadmap.get("current_task_id") == SUCCESSOR_TASK056_P2
                and roadmap.get("next_gate_id") == SUCCESSOR_NEXT_GATE056_P2
            )
            or (
                roadmap.get("current_stage_id") == SUCCESSOR_STAGE056
                and roadmap.get("current_phase_id") == SUCCESSOR_PHASE056_P3
                and roadmap.get("current_task_id") == SUCCESSOR_TASK056_P3
                and roadmap.get("next_gate_id") == SUCCESSOR_NEXT_GATE056_P3
            )
            or (
                roadmap.get("current_stage_id") == SUCCESSOR_STAGE056
                and roadmap.get("current_phase_id") == SUCCESSOR_PHASE056_P4
                and roadmap.get("current_task_id") == SUCCESSOR_TASK056_P4
                and roadmap.get("next_gate_id") == SUCCESSOR_NEXT_GATE056_P4
            )
            or (
                roadmap.get("current_stage_id") == SUCCESSOR_STAGE056
                and roadmap.get("current_phase_id") == SUCCESSOR_PHASE056_REVIEW
                and roadmap.get("current_task_id") == SUCCESSOR_TASK056_REVIEW
                and roadmap.get("next_gate_id") == SUCCESSOR_NEXT_GATE056_REVIEW
            )
            or (
                roadmap.get("current_stage_id") == SUCCESSOR_STAGE057
                and roadmap.get("current_phase_id") == SUCCESSOR_PHASE057
                and roadmap.get("current_task_id") == SUCCESSOR_TASK057
                and roadmap.get("next_gate_id") == SUCCESSOR_NEXT_GATE057
            )
            or (
                roadmap.get("current_stage_id") == SUCCESSOR_STAGE057
                and roadmap.get("current_phase_id") == SUCCESSOR_PHASE057_P2
                and roadmap.get("current_task_id") == SUCCESSOR_TASK057_P2
                and roadmap.get("next_gate_id") == SUCCESSOR_NEXT_GATE057_P2
            )
            or (
                roadmap.get("current_stage_id") == SUCCESSOR_STAGE057
                and roadmap.get("current_phase_id") == SUCCESSOR_PHASE057_P3
                and roadmap.get("current_task_id") == SUCCESSOR_TASK057_P3
                and roadmap.get("next_gate_id") == SUCCESSOR_NEXT_GATE057_P3
            )
            or (
                roadmap.get("current_stage_id") == SUCCESSOR_STAGE057
                and roadmap.get("current_phase_id") == SUCCESSOR_PHASE057_P4
                and roadmap.get("current_task_id") == SUCCESSOR_TASK057_P4
                and roadmap.get("next_gate_id") == SUCCESSOR_NEXT_GATE057_P4
            )
            or (
                roadmap.get("current_stage_id") == SUCCESSOR_STAGE057
                and roadmap.get("current_phase_id") == SUCCESSOR_PHASE057_REVIEW
                and roadmap.get("current_task_id") == SUCCESSOR_TASK057_REVIEW
                and roadmap.get("next_gate_id") == SUCCESSOR_NEXT_GATE057_REVIEW
            )
            or (
                roadmap.get("current_stage_id") == SUCCESSOR_STAGE058
                and roadmap.get("current_phase_id") == SUCCESSOR_PHASE058
                and roadmap.get("current_task_id") == SUCCESSOR_TASK058
                and roadmap.get("next_gate_id") == SUCCESSOR_NEXT_GATE058
            )
            or (
                roadmap.get("current_stage_id") == SUCCESSOR_STAGE058
                and roadmap.get("current_phase_id") == SUCCESSOR_PHASE058_P2
                and roadmap.get("current_task_id") == SUCCESSOR_TASK058_P2
                and roadmap.get("next_gate_id") == SUCCESSOR_NEXT_GATE058_P2
            )
            or (
                roadmap.get("current_stage_id") == SUCCESSOR_STAGE058
                and roadmap.get("current_phase_id") == SUCCESSOR_PHASE058_P3
                and roadmap.get("current_task_id") == SUCCESSOR_TASK058_P3
                and roadmap.get("next_gate_id") == SUCCESSOR_NEXT_GATE058_P3
            )
            or (
                roadmap.get("current_stage_id") == SUCCESSOR_STAGE058
                and roadmap.get("current_phase_id") == SUCCESSOR_PHASE058_P4
                and roadmap.get("current_task_id") == SUCCESSOR_TASK058_P4
                and roadmap.get("next_gate_id") == SUCCESSOR_NEXT_GATE058_P4
            )
            or (
                roadmap.get("current_stage_id") == SUCCESSOR_STAGE058
                and roadmap.get("current_phase_id") == SUCCESSOR_PHASE058_REVIEW
                and roadmap.get("current_task_id") == SUCCESSOR_TASK058_REVIEW
                and roadmap.get("next_gate_id") == SUCCESSOR_NEXT_GATE058_REVIEW
            )
            or (
                roadmap.get("current_stage_id") == SUCCESSOR_STAGE059
                and roadmap.get("current_phase_id") == SUCCESSOR_PHASE059
                and roadmap.get("current_task_id") == SUCCESSOR_TASK059
                and roadmap.get("next_gate_id") == SUCCESSOR_NEXT_GATE059
            )
            or (
                roadmap.get("current_stage_id") == SUCCESSOR_STAGE059
                and roadmap.get("current_phase_id") == SUCCESSOR_PHASE059_P2
                and roadmap.get("current_task_id") == SUCCESSOR_TASK059_P2
                and roadmap.get("next_gate_id") == SUCCESSOR_NEXT_GATE059_P2
            )
            or (
                roadmap.get("current_stage_id") == SUCCESSOR_STAGE059
                and roadmap.get("current_phase_id") == SUCCESSOR_PHASE059_P3
                and roadmap.get("current_task_id") == SUCCESSOR_TASK059_P3
                and roadmap.get("next_gate_id") == SUCCESSOR_NEXT_GATE059_P3
            )
            or (
                roadmap.get("current_stage_id") == SUCCESSOR_STAGE059
                and roadmap.get("current_phase_id") == SUCCESSOR_PHASE059_P4
                and roadmap.get("current_task_id") == SUCCESSOR_TASK059_P4
                and roadmap.get("next_gate_id") == SUCCESSOR_NEXT_GATE059_P4
            )
            or (
                roadmap.get("current_stage_id") == SUCCESSOR_STAGE059
                and roadmap.get("current_phase_id") == SUCCESSOR_PHASE059_REVIEW
                and roadmap.get("current_task_id") == SUCCESSOR_TASK059_REVIEW
                and roadmap.get("next_gate_id") == SUCCESSOR_NEXT_GATE059_REVIEW
            )
            or (
                roadmap.get("current_stage_id") == SUCCESSOR_STAGE060
                and roadmap.get("current_phase_id") == SUCCESSOR_PHASE060
                and roadmap.get("current_task_id") == SUCCESSOR_TASK060
                and roadmap.get("next_gate_id") == SUCCESSOR_NEXT_GATE060
            )
            or (
                roadmap.get("current_stage_id") == SUCCESSOR_STAGE060
                and roadmap.get("current_phase_id") == SUCCESSOR_PHASE060_P2
                and roadmap.get("current_task_id") == SUCCESSOR_TASK060_P2
                and roadmap.get("next_gate_id") == SUCCESSOR_NEXT_GATE060_P2
            )
            or (
                roadmap.get("current_stage_id") == SUCCESSOR_STAGE060
                and roadmap.get("current_phase_id") == SUCCESSOR_PHASE060_P3
                and roadmap.get("current_task_id") == SUCCESSOR_TASK060_P3
                and roadmap.get("next_gate_id") == SUCCESSOR_NEXT_GATE060_P3
            )
            or (
                roadmap.get("current_stage_id") == SUCCESSOR_STAGE060
                and roadmap.get("current_phase_id") == SUCCESSOR_PHASE060_P4
                and roadmap.get("current_task_id") == SUCCESSOR_TASK060_P4
                and roadmap.get("next_gate_id") == SUCCESSOR_NEXT_GATE060_P4
            )
            or (
                roadmap.get("current_stage_id") == SUCCESSOR_STAGE060
                and roadmap.get("current_phase_id") == SUCCESSOR_PHASE060_REVIEW
                and roadmap.get("current_task_id") == SUCCESSOR_TASK060_REVIEW
                and roadmap.get("next_gate_id") == SUCCESSOR_NEXT_GATE060_REVIEW
            )
            or (
                roadmap.get("current_stage_id") == SUCCESSOR_STAGE060
                and roadmap.get("current_phase_id") == SUCCESSOR_PHASE060_BATCH
                and roadmap.get("current_task_id") == SUCCESSOR_TASK060_BATCH
                and roadmap.get("next_gate_id") == SUCCESSOR_NEXT_GATE060_BATCH
            )
            or (
                roadmap.get("current_stage_id") == SUCCESSOR_STAGE061
                and roadmap.get("current_phase_id") == SUCCESSOR_PHASE061
                and roadmap.get("current_task_id") == SUCCESSOR_TASK061
                and roadmap.get("next_gate_id") == SUCCESSOR_NEXT_GATE061
            )
            or (
                roadmap.get("current_stage_id") == SUCCESSOR_STAGE061
                and roadmap.get("current_phase_id") == SUCCESSOR_PHASE061_P2
                and roadmap.get("current_task_id") == SUCCESSOR_TASK061_P2
                and roadmap.get("next_gate_id") == SUCCESSOR_NEXT_GATE061_P2
            )
            or (
                roadmap.get("current_stage_id") == SUCCESSOR_STAGE061
                and roadmap.get("current_phase_id") == SUCCESSOR_PHASE061_P3
                and roadmap.get("current_task_id") == SUCCESSOR_TASK061_P3
                and roadmap.get("next_gate_id") == SUCCESSOR_NEXT_GATE061_P3
            )
            or (
                roadmap.get("current_stage_id") == SUCCESSOR_STAGE061
                and roadmap.get("current_phase_id") == SUCCESSOR_PHASE061_P4
                and roadmap.get("current_task_id") == SUCCESSOR_TASK061_P4
                and roadmap.get("next_gate_id") == SUCCESSOR_NEXT_GATE061_P4
            )
            or (
                roadmap.get("current_stage_id") == SUCCESSOR_STAGE061
                and roadmap.get("current_phase_id") == SUCCESSOR_PHASE061_REVIEW
                and roadmap.get("current_task_id") == SUCCESSOR_TASK061_REVIEW
                and roadmap.get("next_gate_id") == SUCCESSOR_NEXT_GATE061_REVIEW
            )
            or (
                roadmap.get("current_stage_id") == SUCCESSOR_STAGE062
                and roadmap.get("current_phase_id") == SUCCESSOR_PHASE062
                and roadmap.get("current_task_id") == SUCCESSOR_TASK062
                and roadmap.get("next_gate_id") == SUCCESSOR_NEXT_GATE062
            )
            or (
                roadmap.get("current_stage_id") == SUCCESSOR_STAGE062
                and roadmap.get("current_phase_id") == SUCCESSOR_PHASE062_P2
                and roadmap.get("current_task_id") == SUCCESSOR_TASK062_P2
                and roadmap.get("next_gate_id") == SUCCESSOR_NEXT_GATE062_P2
            )
            or (
                roadmap.get("current_stage_id") == SUCCESSOR_STAGE062
                and roadmap.get("current_phase_id") == SUCCESSOR_PHASE062_P3
                and roadmap.get("current_task_id") == SUCCESSOR_TASK062_P3
                and roadmap.get("next_gate_id") == SUCCESSOR_NEXT_GATE062_P3
            )
            or (
                roadmap.get("current_stage_id") == SUCCESSOR_STAGE062
                and roadmap.get("current_phase_id") == SUCCESSOR_PHASE062_P4
                and roadmap.get("current_task_id") == SUCCESSOR_TASK062_P4
                and roadmap.get("next_gate_id") == SUCCESSOR_NEXT_GATE062_P4
            )
            or (
                roadmap.get("current_stage_id") == SUCCESSOR_STAGE062
                and roadmap.get("current_phase_id") == SUCCESSOR_PHASE062_REVIEW
                and roadmap.get("current_task_id") == SUCCESSOR_TASK062_REVIEW
                and roadmap.get("next_gate_id") == SUCCESSOR_NEXT_GATE062_REVIEW
            )
            or (
                roadmap.get("current_stage_id") == SUCCESSOR_STAGE063
                and roadmap.get("current_phase_id") == SUCCESSOR_PHASE063
                and roadmap.get("current_task_id") == SUCCESSOR_TASK063
                and roadmap.get("next_gate_id") == SUCCESSOR_NEXT_GATE063
            )
            or (
                roadmap.get("current_stage_id") == SUCCESSOR_STAGE063
                and roadmap.get("current_phase_id") == SUCCESSOR_PHASE063_P2
                and roadmap.get("current_task_id") == SUCCESSOR_TASK063_P2
                and roadmap.get("next_gate_id") == SUCCESSOR_NEXT_GATE063_P2
            )
            or (
                roadmap.get("current_stage_id") == SUCCESSOR_STAGE063
                and roadmap.get("current_phase_id") == SUCCESSOR_PHASE063_P3
                and roadmap.get("current_task_id") == SUCCESSOR_TASK063_P3
                and roadmap.get("next_gate_id") == SUCCESSOR_NEXT_GATE063_P3
            )
            or (
                roadmap.get("current_stage_id") == SUCCESSOR_STAGE063
                and roadmap.get("current_phase_id") == SUCCESSOR_PHASE063_P4
                and roadmap.get("current_task_id") == SUCCESSOR_TASK063_P4
                and roadmap.get("next_gate_id") == SUCCESSOR_NEXT_GATE063_P4
            )
            or (
                roadmap.get("current_stage_id") == SUCCESSOR_STAGE063
                and roadmap.get("current_phase_id") == SUCCESSOR_PHASE063_REVIEW
                and roadmap.get("current_task_id") == SUCCESSOR_TASK063_REVIEW
                and roadmap.get("next_gate_id") == SUCCESSOR_NEXT_GATE063_REVIEW
            )
            or (
                roadmap.get("current_stage_id") == SUCCESSOR_STAGE064
                and roadmap.get("current_phase_id") == SUCCESSOR_PHASE064
                and roadmap.get("current_task_id") == SUCCESSOR_TASK064
                and roadmap.get("next_gate_id") == SUCCESSOR_NEXT_GATE064
            )
            or (
                roadmap.get("current_stage_id") == SUCCESSOR_STAGE064
                and roadmap.get("current_phase_id") == SUCCESSOR_PHASE064_P2
                and roadmap.get("current_task_id") == SUCCESSOR_TASK064_P2
                and roadmap.get("next_gate_id") == SUCCESSOR_NEXT_GATE064_P2
            )
            or (
                roadmap.get("current_stage_id") == SUCCESSOR_STAGE064
                and roadmap.get("current_phase_id") == SUCCESSOR_PHASE064_P3
                and roadmap.get("current_task_id") == SUCCESSOR_TASK064_P3
                and roadmap.get("next_gate_id") == SUCCESSOR_NEXT_GATE064_P3
            )
            or (
                roadmap.get("current_stage_id") == SUCCESSOR_STAGE064
                and roadmap.get("current_phase_id") == SUCCESSOR_PHASE064_P4
                and roadmap.get("current_task_id") == SUCCESSOR_TASK064_P4
                and roadmap.get("next_gate_id") == SUCCESSOR_NEXT_GATE064_P4
            )
            or (
                roadmap.get("current_stage_id") == SUCCESSOR_STAGE064
                and roadmap.get("current_phase_id") == SUCCESSOR_PHASE064_REVIEW
                and roadmap.get("current_task_id") == SUCCESSOR_TASK064_REVIEW
                and roadmap.get("next_gate_id") == SUCCESSOR_NEXT_GATE064_REVIEW
            )
            or (
                roadmap.get("current_stage_id") == SUCCESSOR_STAGE065
                and roadmap.get("current_phase_id") == SUCCESSOR_PHASE065
                and roadmap.get("current_task_id") == SUCCESSOR_TASK065
                and roadmap.get("next_gate_id") == SUCCESSOR_NEXT_GATE065
            )
            or (
                roadmap.get("current_stage_id") == SUCCESSOR_STAGE065
                and roadmap.get("current_phase_id") == SUCCESSOR_PHASE065_P2
                and roadmap.get("current_task_id") == SUCCESSOR_TASK065_P2
                and roadmap.get("next_gate_id") == SUCCESSOR_NEXT_GATE065_P2
            )
            or (
                roadmap.get("current_stage_id") == SUCCESSOR_STAGE065
                and roadmap.get("current_phase_id") == SUCCESSOR_PHASE065_P3
                and roadmap.get("current_task_id") == SUCCESSOR_TASK065_P3
                and roadmap.get("next_gate_id") == SUCCESSOR_NEXT_GATE065_P3
            )
            or (
                roadmap.get("current_stage_id") == SUCCESSOR_STAGE065
                and roadmap.get("current_phase_id") == SUCCESSOR_PHASE065_P4
                and roadmap.get("current_task_id") == SUCCESSOR_TASK065_P4
                and roadmap.get("next_gate_id") == SUCCESSOR_NEXT_GATE065_P4
            )
            or (
                roadmap.get("current_stage_id") == SUCCESSOR_STAGE065
                and roadmap.get("current_phase_id") == SUCCESSOR_PHASE065_REVIEW
                and roadmap.get("current_task_id") == SUCCESSOR_TASK065_REVIEW
                and roadmap.get("next_gate_id") == SUCCESSOR_NEXT_GATE065_REVIEW
            )
            or (
                roadmap.get("current_stage_id") == SUCCESSOR_STAGE066
                and roadmap.get("current_phase_id") == SUCCESSOR_PHASE066
                and roadmap.get("current_task_id") == SUCCESSOR_TASK066
                and roadmap.get("next_gate_id") == SUCCESSOR_NEXT_GATE066
            )
            or (
                roadmap.get("current_stage_id") == SUCCESSOR_STAGE066
                and roadmap.get("current_phase_id") == SUCCESSOR_PHASE066_P2
                and roadmap.get("current_task_id") == SUCCESSOR_TASK066_P2
                and roadmap.get("next_gate_id") == SUCCESSOR_NEXT_GATE066_P2
            )
            or (
                roadmap.get("current_stage_id") == SUCCESSOR_STAGE066
                and roadmap.get("current_phase_id") == SUCCESSOR_PHASE066_P3
                and roadmap.get("current_task_id") == SUCCESSOR_TASK066_P3
                and roadmap.get("next_gate_id") == SUCCESSOR_NEXT_GATE066_P3
            )
            or (
                roadmap.get("current_stage_id") == SUCCESSOR_STAGE066
                and roadmap.get("current_phase_id") == SUCCESSOR_PHASE066_P4
                and roadmap.get("current_task_id") == SUCCESSOR_TASK066_P4
                and roadmap.get("next_gate_id") == SUCCESSOR_NEXT_GATE066_P4
            )
            or (
                roadmap.get("current_stage_id") == SUCCESSOR_STAGE066
                and roadmap.get("current_phase_id") == SUCCESSOR_PHASE066_REVIEW
                and roadmap.get("current_task_id") == SUCCESSOR_TASK066_REVIEW
                and roadmap.get("next_gate_id") == SUCCESSOR_NEXT_GATE066_REVIEW
            )
            or (
                roadmap.get("current_stage_id") == SUCCESSOR_STAGE067
                and roadmap.get("current_phase_id") == SUCCESSOR_PHASE067
                and roadmap.get("current_task_id") == SUCCESSOR_TASK067
                and roadmap.get("next_gate_id") == SUCCESSOR_NEXT_GATE067
            )
            or (
                roadmap.get("current_stage_id") == SUCCESSOR_STAGE067
                and roadmap.get("current_phase_id") == SUCCESSOR_PHASE067_P2
                and roadmap.get("current_task_id") == SUCCESSOR_TASK067_P2
                and roadmap.get("next_gate_id") == SUCCESSOR_NEXT_GATE067_P2
            )
            or (
                roadmap.get("current_stage_id") == SUCCESSOR_STAGE067
                and roadmap.get("current_phase_id") == SUCCESSOR_PHASE067_P3
                and roadmap.get("current_task_id") == SUCCESSOR_TASK067_P3
                and roadmap.get("next_gate_id") == SUCCESSOR_NEXT_GATE067_P3
            )
            or (
                roadmap.get("current_stage_id") == SUCCESSOR_STAGE067
                and roadmap.get("current_phase_id") == SUCCESSOR_PHASE067_P4
                and roadmap.get("current_task_id") == SUCCESSOR_TASK067_P4
                and roadmap.get("next_gate_id") == SUCCESSOR_NEXT_GATE067_P4
            )
            or (
                roadmap.get("current_stage_id") == SUCCESSOR_STAGE067
                and roadmap.get("current_phase_id") == SUCCESSOR_PHASE067_REVIEW
                and roadmap.get("current_task_id") == SUCCESSOR_TASK067_REVIEW
                and roadmap.get("next_gate_id") == SUCCESSOR_NEXT_GATE067_REVIEW
            )
            or (
                roadmap.get("current_stage_id") == SUCCESSOR_STAGE068
                and roadmap.get("current_phase_id") == SUCCESSOR_PHASE068
                and roadmap.get("current_task_id") == SUCCESSOR_TASK068
                and roadmap.get("next_gate_id") == SUCCESSOR_NEXT_GATE068
            )
            or (
                roadmap.get("current_stage_id") == SUCCESSOR_STAGE068
                and roadmap.get("current_phase_id") == SUCCESSOR_PHASE068_P2
                and roadmap.get("current_task_id") == SUCCESSOR_TASK068_P2
                and roadmap.get("next_gate_id") == SUCCESSOR_NEXT_GATE068_P2
            )
            or (
                roadmap.get("current_stage_id") == SUCCESSOR_STAGE068
                and roadmap.get("current_phase_id") == SUCCESSOR_PHASE068_P3
                and roadmap.get("current_task_id") == SUCCESSOR_TASK068_P3
                and roadmap.get("next_gate_id") == SUCCESSOR_NEXT_GATE068_P3
            )
            or (
                roadmap.get("current_stage_id") == SUCCESSOR_STAGE068
                and roadmap.get("current_phase_id") == SUCCESSOR_PHASE068_P4
                and roadmap.get("current_task_id") == SUCCESSOR_TASK068_P4
                and roadmap.get("next_gate_id") == SUCCESSOR_NEXT_GATE068_P4
            )
            or (
                roadmap.get("current_stage_id") == SUCCESSOR_STAGE068
                and roadmap.get("current_phase_id") == SUCCESSOR_PHASE068_REVIEW
                and roadmap.get("current_task_id") == SUCCESSOR_TASK068_REVIEW
                and roadmap.get("next_gate_id") == SUCCESSOR_NEXT_GATE068_REVIEW
            )
            or (
                roadmap.get("current_stage_id") == SUCCESSOR_STAGE069
                and roadmap.get("current_phase_id") == SUCCESSOR_PHASE069
                and roadmap.get("current_task_id") == SUCCESSOR_TASK069
                and roadmap.get("next_gate_id") == SUCCESSOR_NEXT_GATE069
            )
            or (
                roadmap.get("current_stage_id") == SUCCESSOR_STAGE069
                and roadmap.get("current_phase_id") == SUCCESSOR_PHASE069_P2
                and roadmap.get("current_task_id") == SUCCESSOR_TASK069_P2
                and roadmap.get("next_gate_id") == SUCCESSOR_NEXT_GATE069_P2
            )
            or (
                roadmap.get("current_stage_id") == SUCCESSOR_STAGE069
                and roadmap.get("current_phase_id") == SUCCESSOR_PHASE069_P3
                and roadmap.get("current_task_id") == SUCCESSOR_TASK069_P3
                and roadmap.get("next_gate_id") == SUCCESSOR_NEXT_GATE069_P3
            )
            or (
                roadmap.get("current_stage_id") == SUCCESSOR_STAGE069
                and roadmap.get("current_phase_id") == SUCCESSOR_PHASE069_P4
                and roadmap.get("current_task_id") == SUCCESSOR_TASK069_P4
                and roadmap.get("next_gate_id") == SUCCESSOR_NEXT_GATE069_P4
            )
            or (
                roadmap.get("current_stage_id") == SUCCESSOR_STAGE069
                and roadmap.get("current_phase_id") == SUCCESSOR_PHASE069_REVIEW
                and roadmap.get("current_task_id") == SUCCESSOR_TASK069_REVIEW
                and roadmap.get("next_gate_id") == SUCCESSOR_NEXT_GATE069_REVIEW
            )
            or (
                roadmap.get("current_stage_id") == SUCCESSOR_STAGE070
                and roadmap.get("current_phase_id") == SUCCESSOR_PHASE070
                and roadmap.get("current_task_id") == SUCCESSOR_TASK070
                and roadmap.get("next_gate_id") == SUCCESSOR_NEXT_GATE070
            )
            or (
                roadmap.get("current_stage_id") == SUCCESSOR_STAGE070
                and roadmap.get("current_phase_id") == SUCCESSOR_PHASE070_P2
                and roadmap.get("current_task_id") == SUCCESSOR_TASK070_P2
                and roadmap.get("next_gate_id") == SUCCESSOR_NEXT_GATE070_P2
            )
            or (
                roadmap.get("current_stage_id") == SUCCESSOR_STAGE070
                and roadmap.get("current_phase_id") == SUCCESSOR_PHASE070_P3
                and roadmap.get("current_task_id") == SUCCESSOR_TASK070_P3
                and roadmap.get("next_gate_id") == SUCCESSOR_NEXT_GATE070_P3
            )
            or (
                roadmap.get("current_stage_id") == SUCCESSOR_STAGE070
                and roadmap.get("current_phase_id") == SUCCESSOR_PHASE070_P4
                and roadmap.get("current_task_id") == SUCCESSOR_TASK070_P4
                and roadmap.get("next_gate_id") == SUCCESSOR_NEXT_GATE070_P4
            )
            or (
                roadmap.get("current_stage_id") == SUCCESSOR_STAGE070
                and roadmap.get("current_phase_id") == SUCCESSOR_PHASE070_REVIEW
                and roadmap.get("current_task_id") == SUCCESSOR_TASK070_REVIEW
                and roadmap.get("next_gate_id") == SUCCESSOR_NEXT_GATE070_REVIEW
            )
            or (
                roadmap.get("current_stage_id") == SUCCESSOR_STAGE071
                and roadmap.get("current_phase_id") == SUCCESSOR_PHASE071
                and roadmap.get("current_task_id") == SUCCESSOR_TASK071
                and roadmap.get("next_gate_id") == SUCCESSOR_NEXT_GATE071
            )
            or (
                roadmap.get("current_stage_id") == SUCCESSOR_STAGE071
                and roadmap.get("current_phase_id") == SUCCESSOR_PHASE071_P2
                and roadmap.get("current_task_id") == SUCCESSOR_TASK071_P2
                and roadmap.get("next_gate_id") == SUCCESSOR_NEXT_GATE071_P2
            )
            or (
                roadmap.get("current_stage_id") == SUCCESSOR_STAGE071
                and roadmap.get("current_phase_id") == SUCCESSOR_PHASE071_P3
                and roadmap.get("current_task_id") == SUCCESSOR_TASK071_P3
                and roadmap.get("next_gate_id") == SUCCESSOR_NEXT_GATE071_P3
            )
            or (
                roadmap.get("current_stage_id") == SUCCESSOR_STAGE071
                and roadmap.get("current_phase_id") == SUCCESSOR_PHASE071_P4
                and roadmap.get("current_task_id") == SUCCESSOR_TASK071_P4
                and roadmap.get("next_gate_id") == SUCCESSOR_NEXT_GATE071_P4
            )
            or (
                roadmap.get("current_stage_id") == SUCCESSOR_STAGE071
                and roadmap.get("current_phase_id") == SUCCESSOR_PHASE071_REVIEW
                and roadmap.get("current_task_id") == SUCCESSOR_TASK071_REVIEW
                and roadmap.get("next_gate_id") == SUCCESSOR_NEXT_GATE071_REVIEW
            )
            or (
                roadmap.get("current_stage_id") == SUCCESSOR_STAGE072
                and roadmap.get("current_phase_id") == SUCCESSOR_PHASE072_P1
                and roadmap.get("current_task_id") == SUCCESSOR_TASK072_P1
                and roadmap.get("next_gate_id") == SUCCESSOR_NEXT_GATE072_P1
            )
            or (
                roadmap.get("current_stage_id") == SUCCESSOR_STAGE072
                and roadmap.get("current_phase_id") == SUCCESSOR_PHASE072_P2
                and roadmap.get("current_task_id") == SUCCESSOR_TASK072_P2
                and roadmap.get("next_gate_id") == SUCCESSOR_NEXT_GATE072_P2
            )
            or (
                roadmap.get("current_stage_id") == SUCCESSOR_STAGE072
                and roadmap.get("current_phase_id") == SUCCESSOR_PHASE072_P3
                and roadmap.get("current_task_id") == SUCCESSOR_TASK072_P3
                and roadmap.get("next_gate_id") == SUCCESSOR_NEXT_GATE072_P3
            )
            or (
                roadmap.get("current_stage_id") == SUCCESSOR_STAGE072
                and roadmap.get("current_phase_id") == SUCCESSOR_PHASE072_P4
                and roadmap.get("current_task_id") == SUCCESSOR_TASK072_P4
                and roadmap.get("next_gate_id") == SUCCESSOR_NEXT_GATE072_P4
            )
            or (
                roadmap.get("current_stage_id") == SUCCESSOR_STAGE072
                and roadmap.get("current_phase_id") == SUCCESSOR_PHASE072_REVIEW
                and roadmap.get("current_task_id") == SUCCESSOR_TASK072_REVIEW
                and roadmap.get("next_gate_id") == SUCCESSOR_NEXT_GATE072_REVIEW
            )
            or (
                roadmap.get("current_stage_id") == "IDS-STAGE073"
                and roadmap.get("current_phase_id") == "IDS-STAGE073-P1"
                and roadmap.get("current_task_id") == "IDS-V0_1-STAGE073-P1"
                and roadmap.get("next_gate_id") == "IDS-STAGE073-P2-GATE"
                and isinstance(roadmap.get("current_transition_history"), dict)
                and roadmap["current_transition_history"].get("stage073_phase1_state")
                == {
                    "current_stage_id": "IDS-STAGE073",
                    "current_phase_id": "IDS-STAGE073-P1",
                    "current_task_id": "IDS-V0_1-STAGE073-P1",
                    "next_gate_id": "IDS-STAGE073-P2-GATE",
                }
            )
            or (
                roadmap.get("current_stage_id") == "IDS-STAGE073"
                and roadmap.get("current_phase_id") == "IDS-STAGE073-P2"
                and roadmap.get("current_task_id") == "IDS-V0_1-STAGE073-P2"
                and roadmap.get("next_gate_id") == "IDS-STAGE073-P3-GATE"
                and isinstance(roadmap.get("current_transition_history"), dict)
                and roadmap["current_transition_history"].get("stage073_phase2_state")
                == {
                    "current_stage_id": "IDS-STAGE073",
                    "current_phase_id": "IDS-STAGE073-P2",
                    "current_task_id": "IDS-V0_1-STAGE073-P2",
                    "next_gate_id": "IDS-STAGE073-P3-GATE",
                }
            )
            or (
                roadmap.get("current_stage_id") == "IDS-STAGE073"
                and roadmap.get("current_phase_id") == "IDS-STAGE073-P3"
                and roadmap.get("current_task_id") == "IDS-V0_1-STAGE073-P3"
                and roadmap.get("next_gate_id") == "IDS-STAGE073-P4-GATE"
                and isinstance(roadmap.get("current_transition_history"), dict)
                and roadmap["current_transition_history"].get("stage073_phase3_state")
                == {
                    "current_stage_id": "IDS-STAGE073",
                    "current_phase_id": "IDS-STAGE073-P3",
                    "current_task_id": "IDS-V0_1-STAGE073-P3",
                    "next_gate_id": "IDS-STAGE073-P4-GATE",
                }
            )
            or (
                roadmap.get("current_stage_id") == "IDS-STAGE073"
                and roadmap.get("current_phase_id") == "IDS-STAGE073-P4"
                and roadmap.get("current_task_id") == "IDS-V0_1-STAGE073-P4"
                and roadmap.get("next_gate_id") == "IDS-STAGE073-REVIEW-GATE"
                and isinstance(roadmap.get("current_transition_history"), dict)
                and roadmap["current_transition_history"].get("stage073_phase4_state")
                == {
                    "current_stage_id": "IDS-STAGE073",
                    "current_phase_id": "IDS-STAGE073-P4",
                    "current_task_id": "IDS-V0_1-STAGE073-P4",
                    "next_gate_id": "IDS-STAGE073-REVIEW-GATE",
                }
            )
            or (
                roadmap.get("current_stage_id") == "IDS-STAGE073"
                and roadmap.get("current_phase_id") == "IDS-STAGE073-REVIEW"
                and roadmap.get("current_task_id") == "IDS-V0_1-STAGE073-REVIEW"
                and roadmap.get("next_gate_id") == "IDS-STAGE074-P1-GATE"
                and isinstance(roadmap.get("current_transition_history"), dict)
                and roadmap["current_transition_history"].get("stage073_review_state")
                == {
                    "current_stage_id": "IDS-STAGE073",
                    "current_phase_id": "IDS-STAGE073-REVIEW",
                    "current_task_id": "IDS-V0_1-STAGE073-REVIEW",
                    "next_gate_id": "IDS-STAGE074-P1-GATE",
                }
            )
            or (
                roadmap.get("current_stage_id") == "IDS-STAGE074"
                and roadmap.get("current_phase_id") == "IDS-STAGE074-P1"
                and roadmap.get("current_task_id") == "IDS-V0_1-STAGE074-P1"
                and roadmap.get("next_gate_id") == "IDS-STAGE074-P2-GATE"
                and isinstance(roadmap.get("current_transition_history"), dict)
                and roadmap["current_transition_history"].get("stage074_phase1_state")
                == {
                    "current_stage_id": "IDS-STAGE074",
                    "current_phase_id": "IDS-STAGE074-P1",
                    "current_task_id": "IDS-V0_1-STAGE074-P1",
                    "next_gate_id": "IDS-STAGE074-P2-GATE",
                }
            )
            or (
                roadmap.get("current_stage_id") == "IDS-STAGE074"
                and roadmap.get("current_phase_id") == "IDS-STAGE074-P2"
                and roadmap.get("current_task_id") == "IDS-V0_1-STAGE074-P2"
                and roadmap.get("next_gate_id") == "IDS-STAGE074-P3-GATE"
                and isinstance(roadmap.get("current_transition_history"), dict)
                and roadmap["current_transition_history"].get("stage074_phase2_state")
                == {
                    "current_stage_id": "IDS-STAGE074",
                    "current_phase_id": "IDS-STAGE074-P2",
                    "current_task_id": "IDS-V0_1-STAGE074-P2",
                    "next_gate_id": "IDS-STAGE074-P3-GATE",
                }
            )
            or (
                roadmap.get("current_stage_id") == "IDS-STAGE074"
                and roadmap.get("current_phase_id") == "IDS-STAGE074-P3"
                and roadmap.get("current_task_id") == "IDS-V0_1-STAGE074-P3"
                and roadmap.get("next_gate_id") == "IDS-STAGE074-P4-GATE"
                and isinstance(roadmap.get("current_transition_history"), dict)
                and roadmap["current_transition_history"].get("stage074_phase3_state")
                == {
                    "current_stage_id": "IDS-STAGE074",
                    "current_phase_id": "IDS-STAGE074-P3",
                    "current_task_id": "IDS-V0_1-STAGE074-P3",
                    "next_gate_id": "IDS-STAGE074-P4-GATE",
                }
            )
            or (
                roadmap.get("current_stage_id") == "IDS-STAGE074"
                and roadmap.get("current_phase_id") == "IDS-STAGE074-P4"
                and roadmap.get("current_task_id") == "IDS-V0_1-STAGE074-P4"
                and roadmap.get("next_gate_id") == "IDS-STAGE074-REVIEW-GATE"
                and isinstance(roadmap.get("current_transition_history"), dict)
                and roadmap["current_transition_history"].get("stage074_phase4_state")
                == {
                    "current_stage_id": "IDS-STAGE074",
                    "current_phase_id": "IDS-STAGE074-P4",
                    "current_task_id": "IDS-V0_1-STAGE074-P4",
                    "next_gate_id": "IDS-STAGE074-REVIEW-GATE",
                }
            )
            or (
                roadmap.get("current_stage_id") == "IDS-STAGE074"
                and roadmap.get("current_phase_id") == "IDS-STAGE074-REVIEW"
                and roadmap.get("current_task_id") == "IDS-V0_1-STAGE074-REVIEW"
                and roadmap.get("next_gate_id") == "IDS-STAGE075-P1-GATE"
                and isinstance(roadmap.get("current_transition_history"), dict)
                and roadmap["current_transition_history"].get("stage074_review_state")
                == {
                    "current_stage_id": "IDS-STAGE074",
                    "current_phase_id": "IDS-STAGE074-REVIEW",
                    "current_task_id": "IDS-V0_1-STAGE074-REVIEW",
                    "next_gate_id": "IDS-STAGE075-P1-GATE",
                }
            )
            or (
                roadmap.get("current_stage_id") == "IDS-STAGE075"
                and roadmap.get("current_phase_id") == "IDS-STAGE075-P1"
                and roadmap.get("current_task_id") == "IDS-V0_1-STAGE075-P1"
                and roadmap.get("next_gate_id") == "IDS-STAGE075-P2-GATE"
                and isinstance(roadmap.get("current_transition_history"), dict)
                and roadmap["current_transition_history"].get("stage075_phase1_state")
                == {
                    "current_stage_id": "IDS-STAGE075",
                    "current_phase_id": "IDS-STAGE075-P1",
                    "current_task_id": "IDS-V0_1-STAGE075-P1",
                    "next_gate_id": "IDS-STAGE075-P2-GATE",
                }
            )
            or (
                roadmap.get("current_stage_id") == "IDS-STAGE075"
                and roadmap.get("current_phase_id") == "IDS-STAGE075-P2"
                and roadmap.get("current_task_id") == "IDS-V0_1-STAGE075-P2"
                and roadmap.get("next_gate_id") == "IDS-STAGE075-P3-GATE"
                and isinstance(roadmap.get("current_transition_history"), dict)
                and roadmap["current_transition_history"].get("stage075_phase2_state")
                == {
                    "current_stage_id": "IDS-STAGE075",
                    "current_phase_id": "IDS-STAGE075-P2",
                    "current_task_id": "IDS-V0_1-STAGE075-P2",
                    "next_gate_id": "IDS-STAGE075-P3-GATE",
                }
            )
            or (
                roadmap.get("current_stage_id") == "IDS-STAGE075"
                and roadmap.get("current_phase_id") == "IDS-STAGE075-P3"
                and roadmap.get("current_task_id") == "IDS-V0_1-STAGE075-P3"
                and roadmap.get("next_gate_id") == "IDS-STAGE075-P4-GATE"
                and isinstance(roadmap.get("current_transition_history"), dict)
                and roadmap["current_transition_history"].get("stage075_phase3_state")
                == {
                    "current_stage_id": "IDS-STAGE075",
                    "current_phase_id": "IDS-STAGE075-P3",
                    "current_task_id": "IDS-V0_1-STAGE075-P3",
                    "next_gate_id": "IDS-STAGE075-P4-GATE",
                }
            )
            or (
                roadmap.get("current_stage_id") == "IDS-STAGE075"
                and roadmap.get("current_phase_id") == "IDS-STAGE075-P4"
                and roadmap.get("current_task_id") == "IDS-V0_1-STAGE075-P4"
                and roadmap.get("next_gate_id") == "IDS-STAGE075-REVIEW-GATE"
                and isinstance(roadmap.get("current_transition_history"), dict)
                and roadmap["current_transition_history"].get("stage075_phase4_state")
                == {
                    "current_stage_id": "IDS-STAGE075",
                    "current_phase_id": "IDS-STAGE075-P4",
                    "current_task_id": "IDS-V0_1-STAGE075-P4",
                    "next_gate_id": "IDS-STAGE075-REVIEW-GATE",
                }
            )
            or (
                roadmap.get("current_stage_id") == "IDS-STAGE075"
                and roadmap.get("current_phase_id") == "IDS-STAGE075-REVIEW"
                and roadmap.get("current_task_id") == "IDS-V0_1-STAGE075-REVIEW"
                and roadmap.get("next_gate_id") == "IDS-STAGE076-P1-GATE"
                and isinstance(roadmap.get("current_transition_history"), dict)
                and roadmap["current_transition_history"].get("stage075_review_state")
                == {
                    "current_stage_id": "IDS-STAGE075",
                    "current_phase_id": "IDS-STAGE075-REVIEW",
                    "current_task_id": "IDS-V0_1-STAGE075-REVIEW",
                    "next_gate_id": "IDS-STAGE076-P1-GATE",
                }
            )
            or (
                roadmap.get("current_stage_id") == "IDS-STAGE076"
                and roadmap.get("current_phase_id") == "IDS-STAGE076-P1"
                and roadmap.get("current_task_id") == "IDS-V0_1-STAGE076-P1"
                and roadmap.get("next_gate_id") == "IDS-STAGE076-P2-GATE"
                and isinstance(roadmap.get("current_transition_history"), dict)
                and roadmap["current_transition_history"].get("stage076_phase1_state")
                == {
                    "current_stage_id": "IDS-STAGE076",
                    "current_phase_id": "IDS-STAGE076-P1",
                    "current_task_id": "IDS-V0_1-STAGE076-P1",
                    "next_gate_id": "IDS-STAGE076-P2-GATE",
                }
            )
            or (
                roadmap.get("current_stage_id") == "IDS-STAGE076"
                and roadmap.get("current_phase_id") == "IDS-STAGE076-P2"
                and roadmap.get("current_task_id") == "IDS-V0_1-STAGE076-P2"
                and roadmap.get("next_gate_id") == "IDS-STAGE076-P3-GATE"
                and isinstance(roadmap.get("current_transition_history"), dict)
                and roadmap["current_transition_history"].get("stage076_phase2_state")
                == {
                    "current_stage_id": "IDS-STAGE076",
                    "current_phase_id": "IDS-STAGE076-P2",
                    "current_task_id": "IDS-V0_1-STAGE076-P2",
                    "next_gate_id": "IDS-STAGE076-P3-GATE",
                }
            )
            or (
                roadmap.get("current_stage_id") == "IDS-STAGE076"
                and roadmap.get("current_phase_id") == "IDS-STAGE076-P3"
                and roadmap.get("current_task_id") == "IDS-V0_1-STAGE076-P3"
                and roadmap.get("next_gate_id") == "IDS-STAGE076-P4-GATE"
                and isinstance(roadmap.get("current_transition_history"), dict)
                and roadmap["current_transition_history"].get("stage076_phase3_state")
                == {
                    "current_stage_id": "IDS-STAGE076",
                    "current_phase_id": "IDS-STAGE076-P3",
                    "current_task_id": "IDS-V0_1-STAGE076-P3",
                    "next_gate_id": "IDS-STAGE076-P4-GATE",
                }
            )
            or (
                roadmap.get("current_stage_id") == "IDS-STAGE076"
                and roadmap.get("current_phase_id") == "IDS-STAGE076-P4"
                and roadmap.get("current_task_id") == "IDS-V0_1-STAGE076-P4"
                and roadmap.get("next_gate_id") == "IDS-STAGE076-REVIEW-GATE"
                and isinstance(roadmap.get("current_transition_history"), dict)
                and roadmap["current_transition_history"].get("stage076_phase4_state")
                == {
                    "current_stage_id": "IDS-STAGE076",
                    "current_phase_id": "IDS-STAGE076-P4",
                    "current_task_id": "IDS-V0_1-STAGE076-P4",
                    "next_gate_id": "IDS-STAGE076-REVIEW-GATE",
                }
            )
            or (
                roadmap.get("current_stage_id") == "IDS-STAGE076"
                and roadmap.get("current_phase_id") == "IDS-STAGE076-REVIEW"
                and roadmap.get("current_task_id") == "IDS-V0_1-STAGE076-REVIEW"
                and roadmap.get("next_gate_id") == "IDS-STAGE077-P1-GATE"
                and isinstance(roadmap.get("current_transition_history"), dict)
                and roadmap["current_transition_history"].get("stage076_review_state")
                == {
                    "current_stage_id": "IDS-STAGE076",
                    "current_phase_id": "IDS-STAGE076-REVIEW",
                    "current_task_id": "IDS-V0_1-STAGE076-REVIEW",
                    "next_gate_id": "IDS-STAGE077-P1-GATE",
                }
            )
            or (
                roadmap.get("current_stage_id") == "IDS-STAGE077"
                and roadmap.get("current_phase_id") == "IDS-STAGE077-P1"
                and roadmap.get("current_task_id") == "IDS-V0_1-STAGE077-P1"
                and roadmap.get("next_gate_id") == "IDS-STAGE077-P2-GATE"
                and isinstance(roadmap.get("current_transition_history"), dict)
                and roadmap["current_transition_history"].get("stage077_phase1_state")
                == {
                    "current_stage_id": "IDS-STAGE077",
                    "current_phase_id": "IDS-STAGE077-P1",
                    "current_task_id": "IDS-V0_1-STAGE077-P1",
                    "next_gate_id": "IDS-STAGE077-P2-GATE",
                }
            )
            or (
                roadmap.get("current_stage_id") == "IDS-STAGE077"
                and roadmap.get("current_phase_id") == "IDS-STAGE077-P2"
                and roadmap.get("current_task_id") == "IDS-V0_1-STAGE077-P2"
                and roadmap.get("next_gate_id") == "IDS-STAGE077-P3-GATE"
                and isinstance(roadmap.get("current_transition_history"), dict)
                and roadmap["current_transition_history"].get("stage077_phase2_state")
                == {
                    "current_stage_id": "IDS-STAGE077",
                    "current_phase_id": "IDS-STAGE077-P2",
                    "current_task_id": "IDS-V0_1-STAGE077-P2",
                    "next_gate_id": "IDS-STAGE077-P3-GATE",
                }
            )
            or (
                roadmap.get("current_stage_id") == "IDS-STAGE077"
                and roadmap.get("current_phase_id") == "IDS-STAGE077-P3"
                and roadmap.get("current_task_id") == "IDS-V0_1-STAGE077-P3"
                and roadmap.get("next_gate_id") == "IDS-STAGE077-P4-GATE"
                and isinstance(roadmap.get("current_transition_history"), dict)
                and roadmap["current_transition_history"].get("stage077_phase3_state")
                == {
                    "current_stage_id": "IDS-STAGE077",
                    "current_phase_id": "IDS-STAGE077-P3",
                    "current_task_id": "IDS-V0_1-STAGE077-P3",
                    "next_gate_id": "IDS-STAGE077-P4-GATE",
                }
            )
            or (
                roadmap.get("current_stage_id") == "IDS-STAGE077"
                and roadmap.get("current_phase_id") == "IDS-STAGE077-P4"
                and roadmap.get("current_task_id") == "IDS-V0_1-STAGE077-P4"
                and roadmap.get("next_gate_id") == "IDS-STAGE077-REVIEW-GATE"
                and isinstance(roadmap.get("current_transition_history"), dict)
                and roadmap["current_transition_history"].get("stage077_phase4_state")
                == {
                    "current_stage_id": "IDS-STAGE077",
                    "current_phase_id": "IDS-STAGE077-P4",
                    "current_task_id": "IDS-V0_1-STAGE077-P4",
                    "next_gate_id": "IDS-STAGE077-REVIEW-GATE",
                }
            )
            or (
                roadmap.get("current_stage_id") == "IDS-STAGE077"
                and roadmap.get("current_phase_id") == "IDS-STAGE077-REVIEW"
                and roadmap.get("current_task_id") == "IDS-V0_1-STAGE077-REVIEW"
                and roadmap.get("next_gate_id") == "IDS-STAGE078-P1-GATE"
                and isinstance(roadmap.get("current_transition_history"), dict)
                and roadmap["current_transition_history"].get("stage077_review_state")
                == {
                    "current_stage_id": "IDS-STAGE077",
                    "current_phase_id": "IDS-STAGE077-REVIEW",
                    "current_task_id": "IDS-V0_1-STAGE077-REVIEW",
                    "next_gate_id": "IDS-STAGE078-P1-GATE",
                }
            )
            or (
                roadmap.get("current_stage_id") == "IDS-STAGE078"
                and roadmap.get("current_phase_id") == "IDS-STAGE078-P1"
                and roadmap.get("current_task_id") == "IDS-V0_1-STAGE078-P1"
                and roadmap.get("next_gate_id") == "IDS-STAGE078-P2-GATE"
                and isinstance(roadmap.get("current_transition_history"), dict)
                and roadmap["current_transition_history"].get("stage078_phase1_state")
                == {
                    "current_stage_id": "IDS-STAGE078",
                    "current_phase_id": "IDS-STAGE078-P1",
                    "current_task_id": "IDS-V0_1-STAGE078-P1",
                    "next_gate_id": "IDS-STAGE078-P2-GATE",
                }
            )
            or (
                roadmap.get("current_stage_id") == "IDS-STAGE078"
                and roadmap.get("current_phase_id") == "IDS-STAGE078-P2"
                and roadmap.get("current_task_id") == "IDS-V0_1-STAGE078-P2"
                and roadmap.get("next_gate_id") == "IDS-STAGE078-P3-GATE"
                and isinstance(roadmap.get("current_transition_history"), dict)
                and roadmap["current_transition_history"].get("stage078_phase2_state")
                == {
                    "current_stage_id": "IDS-STAGE078",
                    "current_phase_id": "IDS-STAGE078-P2",
                    "current_task_id": "IDS-V0_1-STAGE078-P2",
                    "next_gate_id": "IDS-STAGE078-P3-GATE",
                }
            )
            or (
                roadmap.get("current_stage_id") == "IDS-STAGE078"
                and roadmap.get("current_phase_id") == "IDS-STAGE078-P3"
                and roadmap.get("current_task_id") == "IDS-V0_1-STAGE078-P3"
                and roadmap.get("next_gate_id") == "IDS-STAGE078-P4-GATE"
                and isinstance(roadmap.get("current_transition_history"), dict)
                and roadmap["current_transition_history"].get("stage078_phase3_state")
                == {
                    "current_stage_id": "IDS-STAGE078",
                    "current_phase_id": "IDS-STAGE078-P3",
                    "current_task_id": "IDS-V0_1-STAGE078-P3",
                    "next_gate_id": "IDS-STAGE078-P4-GATE",
                }
            )
            or (
                roadmap.get("current_stage_id") == "IDS-STAGE078"
                and roadmap.get("current_phase_id") == "IDS-STAGE078-P4"
                and roadmap.get("current_task_id") == "IDS-V0_1-STAGE078-P4"
                and roadmap.get("next_gate_id") == "IDS-STAGE078-REVIEW-GATE"
                and isinstance(roadmap.get("current_transition_history"), dict)
                and roadmap["current_transition_history"].get("stage078_phase4_state")
                == {
                    "current_stage_id": "IDS-STAGE078",
                    "current_phase_id": "IDS-STAGE078-P4",
                    "current_task_id": "IDS-V0_1-STAGE078-P4",
                    "next_gate_id": "IDS-STAGE078-REVIEW-GATE",
                }
            )
            or (
                roadmap.get("current_stage_id") == "IDS-STAGE078"
                and roadmap.get("current_phase_id") == "IDS-STAGE078-REVIEW"
                and roadmap.get("current_task_id") == "IDS-V0_1-STAGE078-REVIEW"
                and roadmap.get("next_gate_id") == "IDS-STAGE079-P1-GATE"
                and isinstance(roadmap.get("current_transition_history"), dict)
                and roadmap["current_transition_history"].get("stage078_review_state")
                == {
                    "current_stage_id": "IDS-STAGE078",
                    "current_phase_id": "IDS-STAGE078-REVIEW",
                    "current_task_id": "IDS-V0_1-STAGE078-REVIEW",
                    "next_gate_id": "IDS-STAGE079-P1-GATE",
                }
            )
            or (
                roadmap.get("current_stage_id") == "IDS-STAGE079"
                and roadmap.get("current_phase_id") == "IDS-STAGE079-P1"
                and roadmap.get("current_task_id") == "IDS-V0_1-STAGE079-P1"
                and roadmap.get("next_gate_id") == "IDS-STAGE079-P2-GATE"
                and isinstance(roadmap.get("current_transition_history"), dict)
                and roadmap["current_transition_history"].get("stage079_phase1_state")
                == {
                    "current_stage_id": "IDS-STAGE079",
                    "current_phase_id": "IDS-STAGE079-P1",
                    "current_task_id": "IDS-V0_1-STAGE079-P1",
                    "next_gate_id": "IDS-STAGE079-P2-GATE",
                }
            )
            or (
                roadmap.get("current_stage_id") == "IDS-STAGE079"
                and roadmap.get("current_phase_id") == "IDS-STAGE079-P2"
                and roadmap.get("current_task_id") == "IDS-V0_1-STAGE079-P2"
                and roadmap.get("next_gate_id") == "IDS-STAGE079-P3-GATE"
                and isinstance(roadmap.get("current_transition_history"), dict)
                and roadmap["current_transition_history"].get("stage079_phase2_state")
                == {
                    "current_stage_id": "IDS-STAGE079",
                    "current_phase_id": "IDS-STAGE079-P2",
                    "current_task_id": "IDS-V0_1-STAGE079-P2",
                    "next_gate_id": "IDS-STAGE079-P3-GATE",
                }
            )
            or (
                roadmap.get("current_stage_id") == "IDS-STAGE079"
                and roadmap.get("current_phase_id") == "IDS-STAGE079-P3"
                and roadmap.get("current_task_id") == "IDS-V0_1-STAGE079-P3"
                and roadmap.get("next_gate_id") == "IDS-STAGE079-P4-GATE"
                and isinstance(roadmap.get("current_transition_history"), dict)
                and roadmap["current_transition_history"].get("stage079_phase3_state")
                == {
                    "current_stage_id": "IDS-STAGE079",
                    "current_phase_id": "IDS-STAGE079-P3",
                    "current_task_id": "IDS-V0_1-STAGE079-P3",
                    "next_gate_id": "IDS-STAGE079-P4-GATE",
                }
            )
            or (
                roadmap.get("current_stage_id") == "IDS-STAGE079"
                and roadmap.get("current_phase_id") == "IDS-STAGE079-P4"
                and roadmap.get("current_task_id") == "IDS-V0_1-STAGE079-P4"
                and roadmap.get("next_gate_id") == "IDS-STAGE079-REVIEW-GATE"
                and isinstance(roadmap.get("current_transition_history"), dict)
                and roadmap["current_transition_history"].get("stage079_phase4_state")
                == {
                    "current_stage_id": "IDS-STAGE079",
                    "current_phase_id": "IDS-STAGE079-P4",
                    "current_task_id": "IDS-V0_1-STAGE079-P4",
                    "next_gate_id": "IDS-STAGE079-REVIEW-GATE",
                }
            )
            or (
                roadmap.get("current_stage_id") == "IDS-STAGE079"
                and roadmap.get("current_phase_id") == "IDS-STAGE079-REVIEW"
                and roadmap.get("current_task_id") == "IDS-V0_1-STAGE079-REVIEW"
                and roadmap.get("next_gate_id") == "IDS-STAGE080-P1-GATE"
                and isinstance(roadmap.get("current_transition_history"), dict)
                and roadmap["current_transition_history"].get("stage079_review_state")
                == {
                    "current_stage_id": "IDS-STAGE079",
                    "current_phase_id": "IDS-STAGE079-REVIEW",
                    "current_task_id": "IDS-V0_1-STAGE079-REVIEW",
                    "next_gate_id": "IDS-STAGE080-P1-GATE",
                }
            )
            or (
                roadmap.get("current_stage_id") == "IDS-STAGE080"
                and roadmap.get("current_phase_id") == "IDS-STAGE080-P1"
                and roadmap.get("current_task_id") == "IDS-V0_1-STAGE080-P1"
                and roadmap.get("next_gate_id") == "IDS-STAGE080-P2-GATE"
                and isinstance(roadmap.get("current_transition_history"), dict)
                and roadmap["current_transition_history"].get("stage080_phase1_state")
                == {
                    "current_stage_id": "IDS-STAGE080",
                    "current_phase_id": "IDS-STAGE080-P1",
                    "current_task_id": "IDS-V0_1-STAGE080-P1",
                    "next_gate_id": "IDS-STAGE080-P2-GATE",
                }
            )
            or (
                roadmap.get("current_stage_id") == "IDS-STAGE080"
                and roadmap.get("current_phase_id") == "IDS-STAGE080-P2"
                and roadmap.get("current_task_id") == "IDS-V0_1-STAGE080-P2"
                and roadmap.get("next_gate_id") == "IDS-STAGE080-P3-GATE"
                and isinstance(roadmap.get("current_transition_history"), dict)
                and roadmap["current_transition_history"].get("stage080_phase2_state")
                == {
                    "current_stage_id": "IDS-STAGE080",
                    "current_phase_id": "IDS-STAGE080-P2",
                    "current_task_id": "IDS-V0_1-STAGE080-P2",
                    "next_gate_id": "IDS-STAGE080-P3-GATE",
                }
            )
            or (
                roadmap.get("current_stage_id") == "IDS-STAGE080"
                and roadmap.get("current_phase_id") == "IDS-STAGE080-P3"
                and roadmap.get("current_task_id") == "IDS-V0_1-STAGE080-P3"
                and roadmap.get("next_gate_id") == "IDS-STAGE080-P4-GATE"
                and isinstance(roadmap.get("current_transition_history"), dict)
                and roadmap["current_transition_history"].get("stage080_phase3_state")
                == {
                    "current_stage_id": "IDS-STAGE080",
                    "current_phase_id": "IDS-STAGE080-P3",
                    "current_task_id": "IDS-V0_1-STAGE080-P3",
                    "next_gate_id": "IDS-STAGE080-P4-GATE",
                }
            )
            or (
                roadmap.get("current_stage_id") == "IDS-STAGE080"
                and roadmap.get("current_phase_id") == "IDS-STAGE080-P4"
                and roadmap.get("current_task_id") == "IDS-V0_1-STAGE080-P4"
                and roadmap.get("next_gate_id") == "IDS-STAGE080-REVIEW-GATE"
                and isinstance(roadmap.get("current_transition_history"), dict)
                and roadmap["current_transition_history"].get("stage080_phase4_state")
                == {
                    "current_stage_id": "IDS-STAGE080",
                    "current_phase_id": "IDS-STAGE080-P4",
                    "current_task_id": "IDS-V0_1-STAGE080-P4",
                    "next_gate_id": "IDS-STAGE080-REVIEW-GATE",
                }
            )
            or (
                roadmap.get("current_stage_id") == "IDS-STAGE080"
                and roadmap.get("current_phase_id") == "IDS-STAGE080-REVIEW"
                and roadmap.get("current_task_id") == "IDS-V0_1-STAGE080-REVIEW"
                and roadmap.get("next_gate_id") == "IDS-STAGE081-P1-GATE"
                and isinstance(roadmap.get("current_transition_history"), dict)
                and roadmap["current_transition_history"].get("stage080_review_state")
                == {
                    "current_stage_id": "IDS-STAGE080",
                    "current_phase_id": "IDS-STAGE080-REVIEW",
                    "current_task_id": "IDS-V0_1-STAGE080-REVIEW",
                    "next_gate_id": "IDS-STAGE081-P1-GATE",
                }
            )
            or (
                roadmap.get("current_stage_id") == "IDS-STAGE081"
                and roadmap.get("current_phase_id") == "IDS-STAGE081-P1"
                and roadmap.get("current_task_id") == "IDS-V0_1-STAGE081-P1"
                and roadmap.get("next_gate_id") == "IDS-STAGE081-P2-GATE"
                and isinstance(roadmap.get("current_transition_history"), dict)
                and roadmap["current_transition_history"].get("stage081_phase1_state")
                == {
                    "current_stage_id": "IDS-STAGE081",
                    "current_phase_id": "IDS-STAGE081-P1",
                    "current_task_id": "IDS-V0_1-STAGE081-P1",
                    "next_gate_id": "IDS-STAGE081-P2-GATE",
                }
            )
            or (
                roadmap.get("current_stage_id") == "IDS-STAGE081"
                and roadmap.get("current_phase_id") == "IDS-STAGE081-P2"
                and roadmap.get("current_task_id") == "IDS-V0_1-STAGE081-P2"
                and roadmap.get("next_gate_id") == "IDS-STAGE081-P3-GATE"
                and isinstance(roadmap.get("current_transition_history"), dict)
                and roadmap["current_transition_history"].get("stage081_phase2_state")
                == {
                    "current_stage_id": "IDS-STAGE081",
                    "current_phase_id": "IDS-STAGE081-P2",
                    "current_task_id": "IDS-V0_1-STAGE081-P2",
                    "next_gate_id": "IDS-STAGE081-P3-GATE",
                }
            )
            or (
                roadmap.get("current_stage_id") == "IDS-STAGE081"
                and roadmap.get("current_phase_id") == "IDS-STAGE081-P3"
                and roadmap.get("current_task_id") == "IDS-V0_1-STAGE081-P3"
                and roadmap.get("next_gate_id") == "IDS-STAGE081-P4-GATE"
                and isinstance(roadmap.get("current_transition_history"), dict)
                and roadmap["current_transition_history"].get("stage081_phase3_state")
                == {
                    "current_stage_id": "IDS-STAGE081",
                    "current_phase_id": "IDS-STAGE081-P3",
                    "current_task_id": "IDS-V0_1-STAGE081-P3",
                    "next_gate_id": "IDS-STAGE081-P4-GATE",
                }
            )
            or (
                roadmap.get("current_stage_id") == "IDS-STAGE081"
                and roadmap.get("current_phase_id") == "IDS-STAGE081-P4"
                and roadmap.get("current_task_id") == "IDS-V0_1-STAGE081-P4"
                and roadmap.get("next_gate_id") == "IDS-STAGE081-REVIEW-GATE"
                and isinstance(roadmap.get("current_transition_history"), dict)
                and roadmap["current_transition_history"].get("stage081_phase4_state")
                == {
                    "current_stage_id": "IDS-STAGE081",
                    "current_phase_id": "IDS-STAGE081-P4",
                    "current_task_id": "IDS-V0_1-STAGE081-P4",
                    "next_gate_id": "IDS-STAGE081-REVIEW-GATE",
                }
            )
            or (
                roadmap.get("current_stage_id") == "IDS-STAGE081"
                and roadmap.get("current_phase_id") == "IDS-STAGE081-REVIEW"
                and roadmap.get("current_task_id") == "IDS-V0_1-STAGE081-REVIEW"
                and roadmap.get("next_gate_id") == "IDS-STAGE082-P1-GATE"
                and isinstance(roadmap.get("current_transition_history"), dict)
                and roadmap["current_transition_history"].get("stage081_review_state")
                == {
                    "current_stage_id": "IDS-STAGE081",
                    "current_phase_id": "IDS-STAGE081-REVIEW",
                    "current_task_id": "IDS-V0_1-STAGE081-REVIEW",
                    "next_gate_id": "IDS-STAGE082-P1-GATE",
                }
            )
            or (
                roadmap.get("current_stage_id") == "IDS-STAGE082"
                and roadmap.get("current_phase_id") == "IDS-STAGE082-P1"
                and roadmap.get("current_task_id") == "IDS-V0_1-STAGE082-P1"
                and roadmap.get("next_gate_id") == "IDS-STAGE082-P2-GATE"
                and isinstance(roadmap.get("current_transition_history"), dict)
                and roadmap["current_transition_history"].get("stage082_phase1_state")
                == {
                    "current_stage_id": "IDS-STAGE082",
                    "current_phase_id": "IDS-STAGE082-P1",
                    "current_task_id": "IDS-V0_1-STAGE082-P1",
                    "next_gate_id": "IDS-STAGE082-P2-GATE",
                }
            )
            or (
                roadmap.get("current_stage_id") == "IDS-STAGE082"
                and roadmap.get("current_phase_id") == "IDS-STAGE082-P2"
                and roadmap.get("current_task_id") == "IDS-V0_1-STAGE082-P2"
                and roadmap.get("next_gate_id") == "IDS-STAGE082-P3-GATE"
                and isinstance(roadmap.get("current_transition_history"), dict)
                and roadmap["current_transition_history"].get("stage082_phase2_state")
                == {
                    "current_stage_id": "IDS-STAGE082",
                    "current_phase_id": "IDS-STAGE082-P2",
                    "current_task_id": "IDS-V0_1-STAGE082-P2",
                    "next_gate_id": "IDS-STAGE082-P3-GATE",
                }
            )
            or (
                roadmap.get("current_stage_id") == "IDS-STAGE082"
                and roadmap.get("current_phase_id") == "IDS-STAGE082-P3"
                and roadmap.get("current_task_id") == "IDS-V0_1-STAGE082-P3"
                and roadmap.get("next_gate_id") == "IDS-STAGE082-P4-GATE"
                and isinstance(roadmap.get("current_transition_history"), dict)
                and roadmap["current_transition_history"].get("stage082_phase3_state")
                == {
                    "current_stage_id": "IDS-STAGE082",
                    "current_phase_id": "IDS-STAGE082-P3",
                    "current_task_id": "IDS-V0_1-STAGE082-P3",
                    "next_gate_id": "IDS-STAGE082-P4-GATE",
                }
            )
            or (
                roadmap.get("current_stage_id") == "IDS-STAGE082"
                and roadmap.get("current_phase_id") == "IDS-STAGE082-P4"
                and roadmap.get("current_task_id") == "IDS-V0_1-STAGE082-P4"
                and roadmap.get("next_gate_id") == "IDS-STAGE082-REVIEW-GATE"
                and isinstance(roadmap.get("current_transition_history"), dict)
                and roadmap["current_transition_history"].get("stage082_phase4_state")
                == {
                    "current_stage_id": "IDS-STAGE082",
                    "current_phase_id": "IDS-STAGE082-P4",
                    "current_task_id": "IDS-V0_1-STAGE082-P4",
                    "next_gate_id": "IDS-STAGE082-REVIEW-GATE",
                }
            )
            or (
                roadmap.get("current_stage_id") == "IDS-STAGE082"
                and roadmap.get("current_phase_id") == "IDS-STAGE082-REVIEW"
                and roadmap.get("current_task_id") == "IDS-V0_1-STAGE082-REVIEW"
                and roadmap.get("next_gate_id") == "IDS-STAGE083-P1-GATE"
                and isinstance(roadmap.get("current_transition_history"), dict)
                and roadmap["current_transition_history"].get("stage082_review_state")
                == {
                    "current_stage_id": "IDS-STAGE082",
                    "current_phase_id": "IDS-STAGE082-REVIEW",
                    "current_task_id": "IDS-V0_1-STAGE082-REVIEW",
                    "next_gate_id": "IDS-STAGE083-P1-GATE",
                }
            )
            or (
                roadmap.get("current_stage_id") == "IDS-STAGE083"
                and roadmap.get("current_phase_id") == "IDS-STAGE083-P1"
                and roadmap.get("current_task_id") == "IDS-V0_1-STAGE083-P1"
                and roadmap.get("next_gate_id") == "IDS-STAGE083-P2-GATE"
                and isinstance(roadmap.get("current_transition_history"), dict)
                and roadmap["current_transition_history"].get("stage083_phase1_state")
                == {
                    "current_stage_id": "IDS-STAGE083",
                    "current_phase_id": "IDS-STAGE083-P1",
                    "current_task_id": "IDS-V0_1-STAGE083-P1",
                    "next_gate_id": "IDS-STAGE083-P2-GATE",
                }
            )
            or (
                roadmap.get("current_stage_id") == "IDS-STAGE083"
                and roadmap.get("current_phase_id") == "IDS-STAGE083-P2"
                and roadmap.get("current_task_id") == "IDS-V0_1-STAGE083-P2"
                and roadmap.get("next_gate_id") == "IDS-STAGE083-P3-GATE"
                and isinstance(roadmap.get("current_transition_history"), dict)
                and roadmap["current_transition_history"].get("stage083_phase2_state")
                == {
                    "current_stage_id": "IDS-STAGE083",
                    "current_phase_id": "IDS-STAGE083-P2",
                    "current_task_id": "IDS-V0_1-STAGE083-P2",
                    "next_gate_id": "IDS-STAGE083-P3-GATE",
                }
            )
            or (
                roadmap.get("current_stage_id") == "IDS-STAGE083"
                and roadmap.get("current_phase_id") == "IDS-STAGE083-P3"
                and roadmap.get("current_task_id") == "IDS-V0_1-STAGE083-P3"
                and roadmap.get("next_gate_id") == "IDS-STAGE083-P4-GATE"
                and isinstance(roadmap.get("current_transition_history"), dict)
                and roadmap["current_transition_history"].get("stage083_phase3_state")
                == {
                    "current_stage_id": "IDS-STAGE083",
                    "current_phase_id": "IDS-STAGE083-P3",
                    "current_task_id": "IDS-V0_1-STAGE083-P3",
                    "next_gate_id": "IDS-STAGE083-P4-GATE",
                }
            )
            or (
                roadmap.get("current_stage_id") == "IDS-STAGE083"
                and roadmap.get("current_phase_id") == "IDS-STAGE083-P4"
                and roadmap.get("current_task_id") == "IDS-V0_1-STAGE083-P4"
                and roadmap.get("next_gate_id") == "IDS-STAGE083-REVIEW-GATE"
                and isinstance(roadmap.get("current_transition_history"), dict)
                and roadmap["current_transition_history"].get("stage083_phase4_state")
                == {
                    "current_stage_id": "IDS-STAGE083",
                    "current_phase_id": "IDS-STAGE083-P4",
                    "current_task_id": "IDS-V0_1-STAGE083-P4",
                    "next_gate_id": "IDS-STAGE083-REVIEW-GATE",
                }
            )
            or (
                roadmap.get("current_stage_id") == "IDS-STAGE083"
                and roadmap.get("current_phase_id") == "IDS-STAGE083-REVIEW"
                and roadmap.get("current_task_id") == "IDS-V0_1-STAGE083-REVIEW"
                and roadmap.get("next_gate_id") == "IDS-STAGE084-P1-GATE"
                and isinstance(roadmap.get("current_transition_history"), dict)
                and roadmap["current_transition_history"].get("stage083_review_state")
                == {
                    "current_stage_id": "IDS-STAGE083",
                    "current_phase_id": "IDS-STAGE083-REVIEW",
                    "current_task_id": "IDS-V0_1-STAGE083-REVIEW",
                    "next_gate_id": "IDS-STAGE084-P1-GATE",
                }
            )
            or (
                roadmap.get("current_stage_id") == "IDS-STAGE084"
                and roadmap.get("current_phase_id") == "IDS-STAGE084-P1"
                and roadmap.get("current_task_id") == "IDS-V0_1-STAGE084-P1"
                and roadmap.get("next_gate_id") == "IDS-STAGE084-P2-GATE"
                and isinstance(roadmap.get("current_transition_history"), dict)
                and roadmap["current_transition_history"].get("stage084_phase1_state")
                == {
                    "current_stage_id": "IDS-STAGE084",
                    "current_phase_id": "IDS-STAGE084-P1",
                    "current_task_id": "IDS-V0_1-STAGE084-P1",
                    "next_gate_id": "IDS-STAGE084-P2-GATE",
                }
            )
            or (
                roadmap.get("current_stage_id") == "IDS-STAGE084"
                and roadmap.get("current_phase_id") == "IDS-STAGE084-P2"
                and roadmap.get("current_task_id") == "IDS-V0_1-STAGE084-P2"
                and roadmap.get("next_gate_id") == "IDS-STAGE084-P3-GATE"
                and isinstance(roadmap.get("current_transition_history"), dict)
                and roadmap["current_transition_history"].get("stage084_phase2_state")
                == {
                    "current_stage_id": "IDS-STAGE084",
                    "current_phase_id": "IDS-STAGE084-P2",
                    "current_task_id": "IDS-V0_1-STAGE084-P2",
                    "next_gate_id": "IDS-STAGE084-P3-GATE",
                }
            )
            or (
                roadmap.get("current_stage_id") == "IDS-STAGE084"
                and roadmap.get("current_phase_id") == "IDS-STAGE084-P3"
                and roadmap.get("current_task_id") == "IDS-V0_1-STAGE084-P3"
                and roadmap.get("next_gate_id") == "IDS-STAGE084-P4-GATE"
                and isinstance(roadmap.get("current_transition_history"), dict)
                and roadmap["current_transition_history"].get("stage084_phase3_state")
                == {
                    "current_stage_id": "IDS-STAGE084",
                    "current_phase_id": "IDS-STAGE084-P3",
                    "current_task_id": "IDS-V0_1-STAGE084-P3",
                    "next_gate_id": "IDS-STAGE084-P4-GATE",
                }
            )
            or (
                roadmap.get("current_stage_id") == "IDS-STAGE084"
                and roadmap.get("current_phase_id") == "IDS-STAGE084-P4"
                and roadmap.get("current_task_id") == "IDS-V0_1-STAGE084-P4"
                and roadmap.get("next_gate_id") == "IDS-STAGE084-REVIEW-GATE"
                and isinstance(roadmap.get("current_transition_history"), dict)
                and roadmap["current_transition_history"].get("stage084_phase4_state")
                == {
                    "current_stage_id": "IDS-STAGE084",
                    "current_phase_id": "IDS-STAGE084-P4",
                    "current_task_id": "IDS-V0_1-STAGE084-P4",
                    "next_gate_id": "IDS-STAGE084-REVIEW-GATE",
                }
            )
            or (
                roadmap.get("current_stage_id") == "IDS-STAGE084"
                and roadmap.get("current_phase_id") == "IDS-STAGE084-REVIEW"
                and roadmap.get("current_task_id") == "IDS-V0_1-STAGE084-REVIEW"
                and roadmap.get("next_gate_id") == "IDS-STAGE085-P1-GATE"
                and isinstance(roadmap.get("current_transition_history"), dict)
                and roadmap["current_transition_history"].get("stage084_review_state")
                == {
                    "current_stage_id": "IDS-STAGE084",
                    "current_phase_id": "IDS-STAGE084-REVIEW",
                    "current_task_id": "IDS-V0_1-STAGE084-REVIEW",
                    "next_gate_id": "IDS-STAGE085-P1-GATE",
                }
            )
            or (
                roadmap.get("current_stage_id") == "IDS-STAGE085"
                and roadmap.get("current_phase_id") == "IDS-STAGE085-P1"
                and roadmap.get("current_task_id") == "IDS-V0_1-STAGE085-P1"
                and roadmap.get("next_gate_id") == "IDS-STAGE085-P2-GATE"
                and isinstance(roadmap.get("current_transition_history"), dict)
                and roadmap["current_transition_history"].get("stage085_phase1_state")
                == {
                    "current_stage_id": "IDS-STAGE085",
                    "current_phase_id": "IDS-STAGE085-P1",
                    "current_task_id": "IDS-V0_1-STAGE085-P1",
                    "next_gate_id": "IDS-STAGE085-P2-GATE",
                }
            )
            or (
                roadmap.get("current_stage_id") == "IDS-STAGE085"
                and roadmap.get("current_phase_id") == "IDS-STAGE085-P2"
                and roadmap.get("current_task_id") == "IDS-V0_1-STAGE085-P2"
                and roadmap.get("next_gate_id") == "IDS-STAGE085-P3-GATE"
                and isinstance(roadmap.get("current_transition_history"), dict)
                and roadmap["current_transition_history"].get("stage085_phase2_state")
                == {
                    "current_stage_id": "IDS-STAGE085",
                    "current_phase_id": "IDS-STAGE085-P2",
                    "current_task_id": "IDS-V0_1-STAGE085-P2",
                    "next_gate_id": "IDS-STAGE085-P3-GATE",
                }
            )
            or (
                roadmap.get("current_stage_id") == "IDS-STAGE085"
                and roadmap.get("current_phase_id") == "IDS-STAGE085-P3"
                and roadmap.get("current_task_id") == "IDS-V0_1-STAGE085-P3"
                and roadmap.get("next_gate_id") == "IDS-STAGE085-P4-GATE"
                and isinstance(roadmap.get("current_transition_history"), dict)
                and roadmap["current_transition_history"].get("stage085_phase3_state")
                == {
                    "current_stage_id": "IDS-STAGE085",
                    "current_phase_id": "IDS-STAGE085-P3",
                    "current_task_id": "IDS-V0_1-STAGE085-P3",
                    "next_gate_id": "IDS-STAGE085-P4-GATE",
                }
            )
            or (
                roadmap.get("current_stage_id") == "IDS-STAGE085"
                and roadmap.get("current_phase_id") == "IDS-STAGE085-P4"
                and roadmap.get("current_task_id") == "IDS-V0_1-STAGE085-P4"
                and roadmap.get("next_gate_id") == "IDS-STAGE085-REVIEW-GATE"
                and isinstance(roadmap.get("current_transition_history"), dict)
                and roadmap["current_transition_history"].get("stage085_phase4_state")
                == {
                    "current_stage_id": "IDS-STAGE085",
                    "current_phase_id": "IDS-STAGE085-P4",
                    "current_task_id": "IDS-V0_1-STAGE085-P4",
                    "next_gate_id": "IDS-STAGE085-REVIEW-GATE",
                }
            )
            or (
                roadmap.get("current_stage_id") == "IDS-STAGE085"
                and roadmap.get("current_phase_id") == "IDS-STAGE085-REVIEW"
                and roadmap.get("current_task_id") == "IDS-V0_1-STAGE085-REVIEW"
                and roadmap.get("next_gate_id") == "IDS-STAGE086-P1-GATE"
                and isinstance(roadmap.get("current_transition_history"), dict)
                and roadmap["current_transition_history"].get("stage085_review_state")
                == {
                    "current_stage_id": "IDS-STAGE085",
                    "current_phase_id": "IDS-STAGE085-REVIEW",
                    "current_task_id": "IDS-V0_1-STAGE085-REVIEW",
                    "next_gate_id": "IDS-STAGE086-P1-GATE",
                }
            )
            or (
                roadmap.get("current_stage_id") == "IDS-STAGE086"
                and roadmap.get("current_phase_id") == "IDS-STAGE086-P1"
                and roadmap.get("current_task_id") == "IDS-V0_1-STAGE086-P1"
                and roadmap.get("next_gate_id") == "IDS-STAGE086-P2-GATE"
                and isinstance(roadmap.get("current_transition_history"), dict)
                and roadmap["current_transition_history"].get("stage086_phase1_state")
                == {
                    "current_stage_id": "IDS-STAGE086",
                    "current_phase_id": "IDS-STAGE086-P1",
                    "current_task_id": "IDS-V0_1-STAGE086-P1",
                    "next_gate_id": "IDS-STAGE086-P2-GATE",
                }
            )
            or (
                roadmap.get("current_stage_id") == "IDS-STAGE086"
                and roadmap.get("current_phase_id") == "IDS-STAGE086-P2"
                and roadmap.get("current_task_id") == "IDS-V0_1-STAGE086-P2"
                and roadmap.get("next_gate_id") == "IDS-STAGE086-P3-GATE"
                and isinstance(roadmap.get("current_transition_history"), dict)
                and roadmap["current_transition_history"].get("stage086_phase2_state")
                == {
                    "current_stage_id": "IDS-STAGE086",
                    "current_phase_id": "IDS-STAGE086-P2",
                    "current_task_id": "IDS-V0_1-STAGE086-P2",
                    "next_gate_id": "IDS-STAGE086-P3-GATE",
                }
            )
            or (
                roadmap.get("current_stage_id") == "IDS-STAGE086"
                and roadmap.get("current_phase_id") == "IDS-STAGE086-P3"
                and roadmap.get("current_task_id") == "IDS-V0_1-STAGE086-P3"
                and roadmap.get("next_gate_id") == "IDS-STAGE086-P4-GATE"
                and isinstance(roadmap.get("current_transition_history"), dict)
                and roadmap["current_transition_history"].get("stage086_phase3_state")
                == {
                    "current_stage_id": "IDS-STAGE086",
                    "current_phase_id": "IDS-STAGE086-P3",
                    "current_task_id": "IDS-V0_1-STAGE086-P3",
                    "next_gate_id": "IDS-STAGE086-P4-GATE",
                }
            )
            or (
                roadmap.get("current_stage_id") == "IDS-STAGE086"
                and roadmap.get("current_phase_id") == "IDS-STAGE086-P4"
                and roadmap.get("current_task_id") == "IDS-V0_1-STAGE086-P4"
                and roadmap.get("next_gate_id") == "IDS-STAGE086-REVIEW-GATE"
                and isinstance(roadmap.get("current_transition_history"), dict)
                and roadmap["current_transition_history"].get("stage086_phase4_state")
                == {
                    "current_stage_id": "IDS-STAGE086",
                    "current_phase_id": "IDS-STAGE086-P4",
                    "current_task_id": "IDS-V0_1-STAGE086-P4",
                    "next_gate_id": "IDS-STAGE086-REVIEW-GATE",
                }
            )
            or (
                roadmap.get("current_stage_id") == "IDS-STAGE086"
                and roadmap.get("current_phase_id") == "IDS-STAGE086-REVIEW"
                and roadmap.get("current_task_id") == "IDS-V0_1-STAGE086-REVIEW"
                and roadmap.get("next_gate_id") == "IDS-STAGE087-P1-GATE"
                and isinstance(roadmap.get("current_transition_history"), dict)
                and roadmap["current_transition_history"].get("stage086_review_state")
                == {
                    "current_stage_id": "IDS-STAGE086",
                    "current_phase_id": "IDS-STAGE086-REVIEW",
                    "current_task_id": "IDS-V0_1-STAGE086-REVIEW",
                    "next_gate_id": "IDS-STAGE087-P1-GATE",
                }
            )
            or (
                roadmap.get("current_stage_id") == "IDS-STAGE087"
                and roadmap.get("current_phase_id") == "IDS-STAGE087-P1"
                and roadmap.get("current_task_id") == "IDS-V0_1-STAGE087-P1"
                and roadmap.get("next_gate_id") == "IDS-STAGE087-P2-GATE"
                and isinstance(roadmap.get("current_transition_history"), dict)
                and roadmap["current_transition_history"].get("stage087_phase1_state")
                == {
                    "current_stage_id": "IDS-STAGE087",
                    "current_phase_id": "IDS-STAGE087-P1",
                    "current_task_id": "IDS-V0_1-STAGE087-P1",
                    "next_gate_id": "IDS-STAGE087-P2-GATE",
                }
            )
            or (
                roadmap.get("current_stage_id") == "IDS-STAGE087"
                and roadmap.get("current_phase_id") == "IDS-STAGE087-P2"
                and roadmap.get("current_task_id") == "IDS-V0_1-STAGE087-P2"
                and roadmap.get("next_gate_id") == "IDS-STAGE087-P3-GATE"
                and isinstance(roadmap.get("current_transition_history"), dict)
                and roadmap["current_transition_history"].get("stage087_phase2_state")
                == {
                    "current_stage_id": "IDS-STAGE087",
                    "current_phase_id": "IDS-STAGE087-P2",
                    "current_task_id": "IDS-V0_1-STAGE087-P2",
                    "next_gate_id": "IDS-STAGE087-P3-GATE",
                }
            )
            or (
                roadmap.get("current_stage_id") == "IDS-STAGE087"
                and roadmap.get("current_phase_id") == "IDS-STAGE087-P3"
                and roadmap.get("current_task_id") == "IDS-V0_1-STAGE087-P3"
                and roadmap.get("next_gate_id") == "IDS-STAGE087-P4-GATE"
                and isinstance(roadmap.get("current_transition_history"), dict)
                and roadmap["current_transition_history"].get("stage087_phase3_state")
                == {
                    "current_stage_id": "IDS-STAGE087",
                    "current_phase_id": "IDS-STAGE087-P3",
                    "current_task_id": "IDS-V0_1-STAGE087-P3",
                    "next_gate_id": "IDS-STAGE087-P4-GATE",
                }
            )
            or (
                roadmap.get("current_stage_id") == "IDS-STAGE087"
                and roadmap.get("current_phase_id") == "IDS-STAGE087-P4"
                and roadmap.get("current_task_id") == "IDS-V0_1-STAGE087-P4"
                and roadmap.get("next_gate_id") == "IDS-STAGE087-REVIEW-GATE"
                and isinstance(roadmap.get("current_transition_history"), dict)
                and roadmap["current_transition_history"].get("stage087_phase4_state")
                == {
                    "current_stage_id": "IDS-STAGE087",
                    "current_phase_id": "IDS-STAGE087-P4",
                    "current_task_id": "IDS-V0_1-STAGE087-P4",
                    "next_gate_id": "IDS-STAGE087-REVIEW-GATE",
                }
            )
            or (
                roadmap.get("current_stage_id") == "IDS-STAGE087"
                and roadmap.get("current_phase_id") == "IDS-STAGE087-REVIEW"
                and roadmap.get("current_task_id") == "IDS-V0_1-STAGE087-REVIEW"
                and roadmap.get("next_gate_id") == "IDS-STAGE088-P1-GATE"
                and isinstance(roadmap.get("current_transition_history"), dict)
                and roadmap["current_transition_history"].get("stage087_review_state")
                == {
                    "current_stage_id": "IDS-STAGE087",
                    "current_phase_id": "IDS-STAGE087-REVIEW",
                    "current_task_id": "IDS-V0_1-STAGE087-REVIEW",
                    "next_gate_id": "IDS-STAGE088-P1-GATE",
                }
            )
            or (
                roadmap.get("current_stage_id") == "IDS-STAGE088"
                and roadmap.get("current_phase_id") == "IDS-STAGE088-P1"
                and roadmap.get("current_task_id") == "IDS-V0_1-STAGE088-P1"
                and roadmap.get("next_gate_id") == "IDS-STAGE088-P2-GATE"
                and isinstance(roadmap.get("current_transition_history"), dict)
                and roadmap["current_transition_history"].get("stage088_phase1_state")
                == {
                    "current_stage_id": "IDS-STAGE088",
                    "current_phase_id": "IDS-STAGE088-P1",
                    "current_task_id": "IDS-V0_1-STAGE088-P1",
                    "next_gate_id": "IDS-STAGE088-P2-GATE",
                }
            )
            or (
                roadmap.get("current_stage_id") == "IDS-STAGE088"
                and roadmap.get("current_phase_id") == "IDS-STAGE088-P2"
                and roadmap.get("current_task_id") == "IDS-V0_1-STAGE088-P2"
                and roadmap.get("next_gate_id") == "IDS-STAGE088-P3-GATE"
                and isinstance(roadmap.get("current_transition_history"), dict)
                and roadmap["current_transition_history"].get("stage088_phase2_state")
                == {
                    "current_stage_id": "IDS-STAGE088",
                    "current_phase_id": "IDS-STAGE088-P2",
                    "current_task_id": "IDS-V0_1-STAGE088-P2",
                    "next_gate_id": "IDS-STAGE088-P3-GATE",
                }
            )
            or (
                roadmap.get("current_stage_id") == "IDS-STAGE088"
                and roadmap.get("current_phase_id") == "IDS-STAGE088-P3"
                and roadmap.get("current_task_id") == "IDS-V0_1-STAGE088-P3"
                and roadmap.get("next_gate_id") == "IDS-STAGE088-P4-GATE"
                and isinstance(roadmap.get("current_transition_history"), dict)
                and roadmap["current_transition_history"].get("stage088_phase3_state")
                == {
                    "current_stage_id": "IDS-STAGE088",
                    "current_phase_id": "IDS-STAGE088-P3",
                    "current_task_id": "IDS-V0_1-STAGE088-P3",
                    "next_gate_id": "IDS-STAGE088-P4-GATE",
                }
            )
            or (
                roadmap.get("current_stage_id") == "IDS-STAGE088"
                and roadmap.get("current_phase_id") == "IDS-STAGE088-P4"
                and roadmap.get("current_task_id") == "IDS-V0_1-STAGE088-P4"
                and roadmap.get("next_gate_id") == "IDS-STAGE088-REVIEW-GATE"
                and isinstance(roadmap.get("current_transition_history"), dict)
                and roadmap["current_transition_history"].get("stage088_phase4_state")
                == {
                    "current_stage_id": "IDS-STAGE088",
                    "current_phase_id": "IDS-STAGE088-P4",
                    "current_task_id": "IDS-V0_1-STAGE088-P4",
                    "next_gate_id": "IDS-STAGE088-REVIEW-GATE",
                }
            )
            or (
                roadmap.get("current_stage_id") == "IDS-STAGE088"
                and roadmap.get("current_phase_id") == "IDS-STAGE088-REVIEW"
                and roadmap.get("current_task_id") == "IDS-V0_1-STAGE088-REVIEW"
                and roadmap.get("next_gate_id") == "IDS-STAGE089-P1-GATE"
                and isinstance(roadmap.get("current_transition_history"), dict)
                and roadmap["current_transition_history"].get("stage088_review_state")
                == {
                    "current_stage_id": "IDS-STAGE088",
                    "current_phase_id": "IDS-STAGE088-REVIEW",
                    "current_task_id": "IDS-V0_1-STAGE088-REVIEW",
                    "next_gate_id": "IDS-STAGE089-P1-GATE",
                }
            )
            or (
                roadmap.get("current_stage_id") == "IDS-STAGE089"
                and roadmap.get("current_phase_id") == "IDS-STAGE089-P1"
                and roadmap.get("current_task_id") == "IDS-V0_1-STAGE089-P1"
                and roadmap.get("next_gate_id") == "IDS-STAGE089-P2-GATE"
                and isinstance(roadmap.get("current_transition_history"), dict)
                and roadmap["current_transition_history"].get("stage089_phase1_state")
                == {
                    "current_stage_id": "IDS-STAGE089",
                    "current_phase_id": "IDS-STAGE089-P1",
                    "current_task_id": "IDS-V0_1-STAGE089-P1",
                    "next_gate_id": "IDS-STAGE089-P2-GATE",
                }
            )
            or (
                roadmap.get("current_stage_id") == "IDS-STAGE089"
                and roadmap.get("current_phase_id") == "IDS-STAGE089-P2"
                and roadmap.get("current_task_id") == "IDS-V0_1-STAGE089-P2"
                and roadmap.get("next_gate_id") == "IDS-STAGE089-P3-GATE"
                and isinstance(roadmap.get("current_transition_history"), dict)
                and roadmap["current_transition_history"].get("stage089_phase2_state")
                == {
                    "current_stage_id": "IDS-STAGE089",
                    "current_phase_id": "IDS-STAGE089-P2",
                    "current_task_id": "IDS-V0_1-STAGE089-P2",
                    "next_gate_id": "IDS-STAGE089-P3-GATE",
                }
            )
            or (
                roadmap.get("current_stage_id") == "IDS-STAGE089"
                and roadmap.get("current_phase_id") == "IDS-STAGE089-P3"
                and roadmap.get("current_task_id") == "IDS-V0_1-STAGE089-P3"
                and roadmap.get("next_gate_id") == "IDS-STAGE089-P4-GATE"
                and isinstance(roadmap.get("current_transition_history"), dict)
                and roadmap["current_transition_history"].get("stage089_phase3_state")
                == {
                    "current_stage_id": "IDS-STAGE089",
                    "current_phase_id": "IDS-STAGE089-P3",
                    "current_task_id": "IDS-V0_1-STAGE089-P3",
                    "next_gate_id": "IDS-STAGE089-P4-GATE",
                }
            )
            or (
                roadmap.get("current_stage_id") == "IDS-STAGE089"
                and roadmap.get("current_phase_id") == "IDS-STAGE089-P4"
                and roadmap.get("current_task_id") == "IDS-V0_1-STAGE089-P4"
                and roadmap.get("next_gate_id") == "IDS-STAGE089-REVIEW-GATE"
                and isinstance(roadmap.get("current_transition_history"), dict)
                and roadmap["current_transition_history"].get("stage089_phase4_state")
                == {
                    "current_stage_id": "IDS-STAGE089",
                    "current_phase_id": "IDS-STAGE089-P4",
                    "current_task_id": "IDS-V0_1-STAGE089-P4",
                    "next_gate_id": "IDS-STAGE089-REVIEW-GATE",
                }
            )
            or (
                roadmap.get("current_stage_id") == "IDS-STAGE089"
                and roadmap.get("current_phase_id") == "IDS-STAGE089-REVIEW"
                and roadmap.get("current_task_id") == "IDS-V0_1-STAGE089-REVIEW"
                and roadmap.get("next_gate_id") == "IDS-STAGE090-P1-GATE"
                and isinstance(roadmap.get("current_transition_history"), dict)
                and roadmap["current_transition_history"].get("stage089_review_state")
                == {
                    "current_stage_id": "IDS-STAGE089",
                    "current_phase_id": "IDS-STAGE089-REVIEW",
                    "current_task_id": "IDS-V0_1-STAGE089-REVIEW",
                    "next_gate_id": "IDS-STAGE090-P1-GATE",
                }
            )
            or (
                roadmap.get("current_stage_id") == "IDS-STAGE090"
                and roadmap.get("current_phase_id") == "IDS-STAGE090-P1"
                and roadmap.get("current_task_id") == "IDS-V0_1-STAGE090-P1"
                and roadmap.get("next_gate_id") == "IDS-STAGE090-P2-GATE"
                and isinstance(roadmap.get("current_transition_history"), dict)
                and roadmap["current_transition_history"].get("stage090_phase1_state")
                == {
                    "current_stage_id": "IDS-STAGE090",
                    "current_phase_id": "IDS-STAGE090-P1",
                    "current_task_id": "IDS-V0_1-STAGE090-P1",
                    "next_gate_id": "IDS-STAGE090-P2-GATE",
                }
            )
            or (
                roadmap.get("current_stage_id") == "IDS-STAGE090"
                and roadmap.get("current_phase_id") == "IDS-STAGE090-P2"
                and roadmap.get("current_task_id") == "IDS-V0_1-STAGE090-P2"
                and roadmap.get("next_gate_id") == "IDS-STAGE090-P3-GATE"
                and isinstance(roadmap.get("current_transition_history"), dict)
                and roadmap["current_transition_history"].get("stage090_phase2_state")
                == {
                    "current_stage_id": "IDS-STAGE090",
                    "current_phase_id": "IDS-STAGE090-P2",
                    "current_task_id": "IDS-V0_1-STAGE090-P2",
                    "next_gate_id": "IDS-STAGE090-P3-GATE",
                }
            )
            or (
                roadmap.get("current_stage_id") == "IDS-STAGE090"
                and roadmap.get("current_phase_id") == "IDS-STAGE090-P3"
                and roadmap.get("current_task_id") == "IDS-V0_1-STAGE090-P3"
                and roadmap.get("next_gate_id") == "IDS-STAGE090-P4-GATE"
                and isinstance(roadmap.get("current_transition_history"), dict)
                and roadmap["current_transition_history"].get("stage090_phase3_state")
                == {
                    "current_stage_id": "IDS-STAGE090",
                    "current_phase_id": "IDS-STAGE090-P3",
                    "current_task_id": "IDS-V0_1-STAGE090-P3",
                    "next_gate_id": "IDS-STAGE090-P4-GATE",
                }
            )
            or (
                roadmap.get("current_stage_id") == "IDS-STAGE090"
                and roadmap.get("current_phase_id") == "IDS-STAGE090-P4"
                and roadmap.get("current_task_id") == "IDS-V0_1-STAGE090-P4"
                and roadmap.get("next_gate_id") == "IDS-STAGE090-REVIEW-GATE"
                and isinstance(roadmap.get("current_transition_history"), dict)
                and roadmap["current_transition_history"].get("stage090_phase4_state")
                == {
                    "current_stage_id": "IDS-STAGE090",
                    "current_phase_id": "IDS-STAGE090-P4",
                    "current_task_id": "IDS-V0_1-STAGE090-P4",
                    "next_gate_id": "IDS-STAGE090-REVIEW-GATE",
                }
            )
            or (
                roadmap.get("current_stage_id") == "IDS-STAGE090"
                and roadmap.get("current_phase_id") == "IDS-STAGE090-REVIEW"
                and roadmap.get("current_task_id") == "IDS-V0_1-STAGE090-REVIEW"
                and roadmap.get("next_gate_id") == "IDS-STAGE091-P1-GATE"
                and isinstance(roadmap.get("current_transition_history"), dict)
                and roadmap["current_transition_history"].get("stage090_review_state")
                == {
                    "current_stage_id": "IDS-STAGE090",
                    "current_phase_id": "IDS-STAGE090-REVIEW",
                    "current_task_id": "IDS-V0_1-STAGE090-REVIEW",
                    "next_gate_id": "IDS-STAGE091-P1-GATE",
                }
            )
            or (
                roadmap.get("current_stage_id") == "IDS-STAGE091"
                and roadmap.get("current_phase_id") == "IDS-STAGE091-P1"
                and roadmap.get("current_task_id") == "IDS-V0_1-STAGE091-P1"
                and roadmap.get("next_gate_id") == "IDS-STAGE091-P2-GATE"
                and isinstance(roadmap.get("current_transition_history"), dict)
                and roadmap["current_transition_history"].get("stage091_phase1_state")
                == {
                    "current_stage_id": "IDS-STAGE091",
                    "current_phase_id": "IDS-STAGE091-P1",
                    "current_task_id": "IDS-V0_1-STAGE091-P1",
                    "next_gate_id": "IDS-STAGE091-P2-GATE",
                }
            )
            or (
                roadmap.get("current_stage_id") == "IDS-STAGE091"
                and roadmap.get("current_phase_id") == "IDS-STAGE091-P2"
                and roadmap.get("current_task_id") == "IDS-V0_1-STAGE091-P2"
                and roadmap.get("next_gate_id") == "IDS-STAGE091-P3-GATE"
                and isinstance(roadmap.get("current_transition_history"), dict)
                and roadmap["current_transition_history"].get("stage091_phase2_state")
                == {
                    "current_stage_id": "IDS-STAGE091",
                    "current_phase_id": "IDS-STAGE091-P2",
                    "current_task_id": "IDS-V0_1-STAGE091-P2",
                    "next_gate_id": "IDS-STAGE091-P3-GATE",
                }
            )
            or (
                roadmap.get("current_stage_id") == "IDS-STAGE091"
                and roadmap.get("current_phase_id") == "IDS-STAGE091-P3"
                and roadmap.get("current_task_id") == "IDS-V0_1-STAGE091-P3"
                and roadmap.get("next_gate_id") == "IDS-STAGE091-P4-GATE"
                and isinstance(roadmap.get("current_transition_history"), dict)
                and roadmap["current_transition_history"].get("stage091_phase3_state")
                == {
                    "current_stage_id": "IDS-STAGE091",
                    "current_phase_id": "IDS-STAGE091-P3",
                    "current_task_id": "IDS-V0_1-STAGE091-P3",
                    "next_gate_id": "IDS-STAGE091-P4-GATE",
                }
            )
            or (
                roadmap.get("current_stage_id") == "IDS-STAGE091"
                and roadmap.get("current_phase_id") == "IDS-STAGE091-P4"
                and roadmap.get("current_task_id") == "IDS-V0_1-STAGE091-P4"
                and roadmap.get("next_gate_id") == "IDS-STAGE091-REVIEW-GATE"
                and isinstance(roadmap.get("current_transition_history"), dict)
                and roadmap["current_transition_history"].get("stage091_phase4_state")
                == {
                    "current_stage_id": "IDS-STAGE091",
                    "current_phase_id": "IDS-STAGE091-P4",
                    "current_task_id": "IDS-V0_1-STAGE091-P4",
                    "next_gate_id": "IDS-STAGE091-REVIEW-GATE",
                }
            )
            or (
                roadmap.get("current_stage_id") == "IDS-STAGE091"
                and roadmap.get("current_phase_id") == "IDS-STAGE091-REVIEW"
                and roadmap.get("current_task_id") == "IDS-V0_1-STAGE091-REVIEW"
                and roadmap.get("next_gate_id") == "IDS-STAGE092-P1-GATE"
                and isinstance(roadmap.get("current_transition_history"), dict)
                and roadmap["current_transition_history"].get("stage091_review_state")
                == {
                    "current_stage_id": "IDS-STAGE091",
                    "current_phase_id": "IDS-STAGE091-REVIEW",
                    "current_task_id": "IDS-V0_1-STAGE091-REVIEW",
                    "next_gate_id": "IDS-STAGE092-P1-GATE",
                }
            )
            or (
                roadmap.get("current_stage_id") == "IDS-STAGE092"
                and roadmap.get("current_phase_id") == "IDS-STAGE092-P1"
                and roadmap.get("current_task_id") == "IDS-V0_1-STAGE092-P1"
                and roadmap.get("next_gate_id") == "IDS-STAGE092-P2-GATE"
                and isinstance(roadmap.get("current_transition_history"), dict)
                and roadmap["current_transition_history"].get("stage092_phase1_state")
                == {
                    "current_stage_id": "IDS-STAGE092",
                    "current_phase_id": "IDS-STAGE092-P1",
                    "current_task_id": "IDS-V0_1-STAGE092-P1",
                    "next_gate_id": "IDS-STAGE092-P2-GATE",
                }
            )
            or (
                roadmap.get("current_stage_id") == "IDS-STAGE092"
                and roadmap.get("current_phase_id") == "IDS-STAGE092-P2"
                and roadmap.get("current_task_id") == "IDS-V0_1-STAGE092-P2"
                and roadmap.get("next_gate_id") == "IDS-STAGE092-P3-GATE"
                and isinstance(roadmap.get("current_transition_history"), dict)
                and roadmap["current_transition_history"].get("stage092_phase2_state")
                == {
                    "current_stage_id": "IDS-STAGE092",
                    "current_phase_id": "IDS-STAGE092-P2",
                    "current_task_id": "IDS-V0_1-STAGE092-P2",
                    "next_gate_id": "IDS-STAGE092-P3-GATE",
                }
            )
            or (
                roadmap.get("current_stage_id") == "IDS-STAGE092"
                and roadmap.get("current_phase_id") == "IDS-STAGE092-P3"
                and roadmap.get("current_task_id") == "IDS-V0_1-STAGE092-P3"
                and roadmap.get("next_gate_id") == "IDS-STAGE092-P4-GATE"
                and isinstance(roadmap.get("current_transition_history"), dict)
                and roadmap["current_transition_history"].get("stage092_phase3_state")
                == {
                    "current_stage_id": "IDS-STAGE092",
                    "current_phase_id": "IDS-STAGE092-P3",
                    "current_task_id": "IDS-V0_1-STAGE092-P3",
                    "next_gate_id": "IDS-STAGE092-P4-GATE",
                }
            )
            or (
                roadmap.get("current_stage_id") == "IDS-STAGE092"
                and roadmap.get("current_phase_id") == "IDS-STAGE092-P4"
                and roadmap.get("current_task_id") == "IDS-V0_1-STAGE092-P4"
                and roadmap.get("next_gate_id") == "IDS-STAGE092-REVIEW-GATE"
                and isinstance(roadmap.get("current_transition_history"), dict)
                and roadmap["current_transition_history"].get("stage092_phase4_state")
                == {
                    "current_stage_id": "IDS-STAGE092",
                    "current_phase_id": "IDS-STAGE092-P4",
                    "current_task_id": "IDS-V0_1-STAGE092-P4",
                    "next_gate_id": "IDS-STAGE092-REVIEW-GATE",
                }
            )
            or (
                roadmap.get("current_stage_id") == "IDS-STAGE092"
                and roadmap.get("current_phase_id") == "IDS-STAGE092-REVIEW"
                and roadmap.get("current_task_id") == "IDS-V0_1-STAGE092-REVIEW"
                and roadmap.get("next_gate_id") == "IDS-STAGE093-P1-GATE"
                and isinstance(roadmap.get("current_transition_history"), dict)
                and roadmap["current_transition_history"].get("stage092_review_state")
                == {
                    "current_stage_id": "IDS-STAGE092",
                    "current_phase_id": "IDS-STAGE092-REVIEW",
                    "current_task_id": "IDS-V0_1-STAGE092-REVIEW",
                    "next_gate_id": "IDS-STAGE093-P1-GATE",
                }
            )
            or (
                roadmap.get("current_stage_id") == "IDS-STAGE093"
                and roadmap.get("current_phase_id") == "IDS-STAGE093-P1"
                and roadmap.get("current_task_id") == "IDS-V0_1-STAGE093-P1"
                and roadmap.get("next_gate_id") == "IDS-STAGE093-P2-GATE"
                and isinstance(roadmap.get("current_transition_history"), dict)
                and roadmap["current_transition_history"].get("stage093_phase1_state")
                == {
                    "current_stage_id": "IDS-STAGE093",
                    "current_phase_id": "IDS-STAGE093-P1",
                    "current_task_id": "IDS-V0_1-STAGE093-P1",
                    "next_gate_id": "IDS-STAGE093-P2-GATE",
                }
            )
            or (
                roadmap.get("current_stage_id") == "IDS-STAGE093"
                and roadmap.get("current_phase_id") == "IDS-STAGE093-P2"
                and roadmap.get("current_task_id") == "IDS-V0_1-STAGE093-P2"
                and roadmap.get("next_gate_id") == "IDS-STAGE093-P3-GATE"
                and isinstance(roadmap.get("current_transition_history"), dict)
                and roadmap["current_transition_history"].get("stage093_phase2_state")
                == {
                    "current_stage_id": "IDS-STAGE093",
                    "current_phase_id": "IDS-STAGE093-P2",
                    "current_task_id": "IDS-V0_1-STAGE093-P2",
                    "next_gate_id": "IDS-STAGE093-P3-GATE",
                }
            )
            or (
                roadmap.get("current_stage_id") == "IDS-STAGE093"
                and roadmap.get("current_phase_id") == "IDS-STAGE093-P3"
                and roadmap.get("current_task_id") == "IDS-V0_1-STAGE093-P3"
                and roadmap.get("next_gate_id") == "IDS-STAGE093-P4-GATE"
                and isinstance(roadmap.get("current_transition_history"), dict)
                and roadmap["current_transition_history"].get("stage093_phase3_state")
                == {
                    "current_stage_id": "IDS-STAGE093",
                    "current_phase_id": "IDS-STAGE093-P3",
                    "current_task_id": "IDS-V0_1-STAGE093-P3",
                    "next_gate_id": "IDS-STAGE093-P4-GATE",
                }
            )
            or (
                roadmap.get("current_stage_id") == "IDS-STAGE093"
                and roadmap.get("current_phase_id") == "IDS-STAGE093-P4"
                and roadmap.get("current_task_id") == "IDS-V0_1-STAGE093-P4"
                and roadmap.get("next_gate_id") == "IDS-STAGE093-REVIEW-GATE"
                and isinstance(roadmap.get("current_transition_history"), dict)
                and roadmap["current_transition_history"].get("stage093_phase4_state")
                == {
                    "current_stage_id": "IDS-STAGE093",
                    "current_phase_id": "IDS-STAGE093-P4",
                    "current_task_id": "IDS-V0_1-STAGE093-P4",
                    "next_gate_id": "IDS-STAGE093-REVIEW-GATE",
                }
            )
            or (
                roadmap.get("current_stage_id") == "IDS-STAGE093"
                and roadmap.get("current_phase_id") == "IDS-STAGE093-REVIEW"
                and roadmap.get("current_task_id") == "IDS-V0_1-STAGE093-REVIEW"
                and roadmap.get("next_gate_id") == "IDS-STAGE094-P1-GATE"
                and isinstance(roadmap.get("current_transition_history"), dict)
                and roadmap["current_transition_history"].get("stage093_review_state")
                == {
                    "current_stage_id": "IDS-STAGE093",
                    "current_phase_id": "IDS-STAGE093-REVIEW",
                    "current_task_id": "IDS-V0_1-STAGE093-REVIEW",
                    "next_gate_id": "IDS-STAGE094-P1-GATE",
                }
            )
            or (
                roadmap.get("current_stage_id") == "IDS-STAGE094"
                and roadmap.get("current_phase_id") == "IDS-STAGE094-P1"
                and roadmap.get("current_task_id") == "IDS-V0_1-STAGE094-P1"
                and roadmap.get("next_gate_id") == "IDS-STAGE094-P2-GATE"
                and isinstance(roadmap.get("current_transition_history"), dict)
                and roadmap["current_transition_history"].get("stage094_phase1_state")
                == {
                    "current_stage_id": "IDS-STAGE094",
                    "current_phase_id": "IDS-STAGE094-P1",
                    "current_task_id": "IDS-V0_1-STAGE094-P1",
                    "next_gate_id": "IDS-STAGE094-P2-GATE",
                }
            )
        ),
        "roadmap_phase_and_task_evidence_exact": (
            isinstance(phase, dict)
            and phase.get("status") == "completed"
            and isinstance(task, dict)
            and task.get("status") == "completed"
            and task.get("acceptance_ids") == EXPECTED_ACCEPTANCE_IDS
            and expected_evidence.issubset(
                {item for item in task.get("evidence_refs", []) if isinstance(item, str)}
            )
        ),
    }


def _projection_checks() -> dict[str, bool]:
    try:
        status = _load_json(STATUS_PATH)
        plan = _load_json(PLAN_PATH)
        fact_roadmap = _load_json(FACT_ROADMAP_PATH)
        acceptance = _load_json(ACCEPTANCE_PATH)
    except (OSError, json.JSONDecodeError):
        return {
            "status_projection_exact": False,
            "plan_projection_exact": False,
            "roadmap_projection_exact": False,
            "acceptance_projection_exact": False,
        }
    acceptance_items = acceptance.get("items", []) if isinstance(acceptance, dict) else []
    acceptance_ids = {
        item.get("id") for item in acceptance_items if isinstance(item, dict)
    }
    fact_stages = (
        fact_roadmap.get("stages", [])
        if isinstance(fact_roadmap, dict)
        else fact_roadmap
    )
    stage050 = next(
        (
            item
            for item in fact_stages
            if isinstance(item, dict) and item.get("id") == "`IDS-STAGE050`"
        ),
        {},
    ) if isinstance(fact_stages, list) else {}
    successor_status = (
        isinstance(status, dict)
        and status.get("stage") == SUCCESSOR_STAGE
        and status.get("phase") == SUCCESSOR_TASK
        and status.get("task") == SUCCESSOR_TASK
        and status.get("next_gate") == SUCCESSOR_NEXT_GATE
        and status.get("runtime_enabled") is False
        and status.get("push_allowed") is False
    )
    successor_phase2_status = (
        isinstance(status, dict)
        and status.get("stage") == SUCCESSOR_STAGE
        and status.get("phase") == SUCCESSOR_TASK2
        and status.get("task") == SUCCESSOR_TASK2
        and status.get("next_gate") == SUCCESSOR_NEXT_GATE2
        and status.get("runtime_enabled") is False
        and status.get("push_allowed") is False
    )
    successor_phase3_status = (
        isinstance(status, dict)
        and status.get("stage") == SUCCESSOR_STAGE
        and status.get("phase") == SUCCESSOR_TASK3
        and status.get("task") == SUCCESSOR_TASK3
        and status.get("next_gate") == SUCCESSOR_NEXT_GATE3
        and status.get("runtime_enabled") is False
        and status.get("push_allowed") is False
    )
    successor_phase4_status = (
        isinstance(status, dict)
        and status.get("stage") == SUCCESSOR_STAGE
        and status.get("phase") == SUCCESSOR_TASK4
        and status.get("task") == SUCCESSOR_TASK4
        and status.get("next_gate") == SUCCESSOR_NEXT_GATE4
        and status.get("runtime_enabled") is False
        and status.get("push_allowed") is False
    )
    successor_review_status = (
        isinstance(status, dict)
        and status.get("stage") == SUCCESSOR_STAGE
        and status.get("phase") == SUCCESSOR_REVIEW_TASK
        and status.get("task") == SUCCESSOR_REVIEW_TASK
        and status.get("next_gate") == SUCCESSOR_REVIEW_NEXT_GATE
        and status.get("runtime_enabled") is False
        and status.get("push_allowed") is False
    )
    successor_stage052_status = (
        isinstance(status, dict)
        and status.get("stage") == SUCCESSOR_STAGE052
        and status.get("phase") == SUCCESSOR_TASK052
        and status.get("task") == SUCCESSOR_TASK052
        and status.get("next_gate") == SUCCESSOR_NEXT_GATE052
        and status.get("runtime_enabled") is False
        and status.get("push_allowed") is False
    )
    successor_stage052_phase2_status = (
        isinstance(status, dict)
        and status.get("stage") == SUCCESSOR_STAGE052
        and status.get("phase") == SUCCESSOR_TASK052_P2
        and status.get("task") == SUCCESSOR_TASK052_P2
        and status.get("next_gate") == SUCCESSOR_NEXT_GATE052_P2
        and status.get("runtime_enabled") is False
        and status.get("push_allowed") is False
    )
    successor_stage052_phase3_status = (
        isinstance(status, dict)
        and status.get("stage") == SUCCESSOR_STAGE052
        and status.get("phase") == SUCCESSOR_TASK052_P3
        and status.get("task") == SUCCESSOR_TASK052_P3
        and status.get("next_gate") == SUCCESSOR_NEXT_GATE052_P3
        and status.get("runtime_enabled") is False
        and status.get("push_allowed") is False
    )
    successor_stage052_phase4_status = (
        isinstance(status, dict)
        and status.get("stage") == SUCCESSOR_STAGE052
        and status.get("phase") == SUCCESSOR_TASK052_P4
        and status.get("task") == SUCCESSOR_TASK052_P4
        and status.get("next_gate") == SUCCESSOR_NEXT_GATE052_P4
        and status.get("runtime_enabled") is False
        and status.get("push_allowed") is False
    )
    successor_stage052_review_status = (
        isinstance(status, dict)
        and status.get("stage") == SUCCESSOR_STAGE052
        and status.get("phase") == SUCCESSOR_TASK052_REVIEW
        and status.get("task") == SUCCESSOR_TASK052_REVIEW
        and status.get("next_gate") == SUCCESSOR_NEXT_GATE052_REVIEW
        and status.get("runtime_enabled") is False
        and status.get("push_allowed") is False
    )
    successor_stage053_status = (
        isinstance(status, dict)
        and status.get("stage") == SUCCESSOR_STAGE053
        and status.get("phase") == SUCCESSOR_TASK053
        and status.get("task") == SUCCESSOR_TASK053
        and status.get("next_gate") == SUCCESSOR_NEXT_GATE053
        and status.get("runtime_enabled") is False
        and status.get("push_allowed") is False
    )
    successor_stage053_phase2_status = (
        isinstance(status, dict)
        and status.get("stage") == SUCCESSOR_STAGE053
        and status.get("phase") == SUCCESSOR_TASK053_P2
        and status.get("task") == SUCCESSOR_TASK053_P2
        and status.get("next_gate") == SUCCESSOR_NEXT_GATE053_P2
        and status.get("runtime_enabled") is False
        and status.get("push_allowed") is False
    )
    successor_stage053_phase3_status = (
        isinstance(status, dict)
        and status.get("stage") == SUCCESSOR_STAGE053
        and status.get("phase") == SUCCESSOR_TASK053_P3
        and status.get("task") == SUCCESSOR_TASK053_P3
        and status.get("next_gate") == SUCCESSOR_NEXT_GATE053_P3
        and status.get("runtime_enabled") is False
        and status.get("push_allowed") is False
    )
    successor_stage053_phase4_status = (
        isinstance(status, dict)
        and status.get("stage") == SUCCESSOR_STAGE053
        and status.get("phase") == SUCCESSOR_TASK053_P4
        and status.get("task") == SUCCESSOR_TASK053_P4
        and status.get("next_gate") == SUCCESSOR_NEXT_GATE053_P4
        and status.get("runtime_enabled") is False
        and status.get("push_allowed") is False
    )
    successor_stage053_review_status = (
        isinstance(status, dict)
        and status.get("stage") == SUCCESSOR_STAGE053
        and status.get("phase") == SUCCESSOR_TASK053_REVIEW
        and status.get("task") == SUCCESSOR_TASK053_REVIEW
        and status.get("next_gate") == SUCCESSOR_NEXT_GATE053_REVIEW
        and status.get("runtime_enabled") is False
        and status.get("push_allowed") is False
    )
    successor_stage054_status = (
        isinstance(status, dict)
        and status.get("stage") == SUCCESSOR_STAGE054
        and status.get("phase") == SUCCESSOR_TASK054
        and status.get("task") == SUCCESSOR_TASK054
        and status.get("next_gate") == SUCCESSOR_NEXT_GATE054
        and status.get("runtime_enabled") is False
        and status.get("push_allowed") is False
    )
    successor_stage054_phase2_status = (
        isinstance(status, dict)
        and status.get("stage") == SUCCESSOR_STAGE054
        and status.get("phase") == SUCCESSOR_TASK054_P2
        and status.get("task") == SUCCESSOR_TASK054_P2
        and status.get("next_gate") == SUCCESSOR_NEXT_GATE054_P2
        and status.get("runtime_enabled") is False
        and status.get("push_allowed") is False
    )
    successor_stage054_phase3_status = (
        isinstance(status, dict)
        and status.get("stage") == SUCCESSOR_STAGE054
        and status.get("phase") == SUCCESSOR_TASK054_P3
        and status.get("task") == SUCCESSOR_TASK054_P3
        and status.get("next_gate") == SUCCESSOR_NEXT_GATE054_P3
        and status.get("runtime_enabled") is False
        and status.get("push_allowed") is False
    )
    successor_stage054_phase4_status = (
        isinstance(status, dict)
        and status.get("stage") == SUCCESSOR_STAGE054
        and status.get("phase") == SUCCESSOR_TASK054_P4
        and status.get("task") == SUCCESSOR_TASK054_P4
        and status.get("next_gate") == SUCCESSOR_NEXT_GATE054_P4
        and status.get("runtime_enabled") is False
        and status.get("push_allowed") is False
    )
    successor_stage054_review_status = (
        isinstance(status, dict)
        and status.get("stage") == SUCCESSOR_STAGE054
        and status.get("phase") == SUCCESSOR_TASK054_REVIEW
        and status.get("task") == SUCCESSOR_TASK054_REVIEW
        and status.get("next_gate") == SUCCESSOR_NEXT_GATE054_REVIEW
        and status.get("runtime_enabled") is False
        and status.get("push_allowed") is False
    )
    successor_stage055_status = (
        isinstance(status, dict)
        and status.get("stage") == SUCCESSOR_STAGE055
        and status.get("phase") == SUCCESSOR_TASK055
        and status.get("task") == SUCCESSOR_TASK055
        and status.get("next_gate") == SUCCESSOR_NEXT_GATE055
        and status.get("runtime_enabled") is False
        and status.get("push_allowed") is False
    )
    successor_stage055_phase2_status = (
        isinstance(status, dict)
        and status.get("stage") == SUCCESSOR_STAGE055
        and status.get("phase") == SUCCESSOR_TASK055_P2
        and status.get("task") == SUCCESSOR_TASK055_P2
        and status.get("next_gate") == SUCCESSOR_NEXT_GATE055_P2
        and status.get("runtime_enabled") is False
        and status.get("push_allowed") is False
    )
    successor_stage055_phase3_status = (
        isinstance(status, dict)
        and status.get("stage") == SUCCESSOR_STAGE055
        and status.get("phase") == SUCCESSOR_TASK055_P3
        and status.get("task") == SUCCESSOR_TASK055_P3
        and status.get("next_gate") == SUCCESSOR_NEXT_GATE055_P3
        and status.get("runtime_enabled") is False
        and status.get("push_allowed") is False
    )
    successor_stage055_phase4_status = (
        isinstance(status, dict)
        and status.get("stage") == SUCCESSOR_STAGE055
        and status.get("phase") == SUCCESSOR_TASK055_P4
        and status.get("task") == SUCCESSOR_TASK055_P4
        and status.get("next_gate") == SUCCESSOR_NEXT_GATE055_P4
        and status.get("runtime_enabled") is False
        and status.get("push_allowed") is False
    )
    successor_stage055_review_status = (
        isinstance(status, dict)
        and status.get("stage") == SUCCESSOR_STAGE055
        and status.get("phase") == SUCCESSOR_TASK055_REVIEW
        and status.get("task") == SUCCESSOR_TASK055_REVIEW
        and status.get("next_gate") == SUCCESSOR_NEXT_GATE055_REVIEW
        and status.get("runtime_enabled") is False
        and status.get("push_allowed") is False
    )
    successor_stage056_status = (
        isinstance(status, dict)
        and status.get("stage") == SUCCESSOR_STAGE056
        and status.get("phase") == SUCCESSOR_TASK056
        and status.get("task") == SUCCESSOR_TASK056
        and status.get("next_gate") == SUCCESSOR_NEXT_GATE056
        and status.get("runtime_enabled") is False
        and status.get("push_allowed") is False
    )
    successor_stage056_phase2_status = (
        isinstance(status, dict)
        and status.get("stage") == SUCCESSOR_STAGE056
        and status.get("phase") == SUCCESSOR_TASK056_P2
        and status.get("task") == SUCCESSOR_TASK056_P2
        and status.get("next_gate") == SUCCESSOR_NEXT_GATE056_P2
        and status.get("runtime_enabled") is False
        and status.get("push_allowed") is False
    )
    successor_stage056_phase3_status = (
        isinstance(status, dict)
        and status.get("stage") == SUCCESSOR_STAGE056
        and status.get("phase") == SUCCESSOR_TASK056_P3
        and status.get("task") == SUCCESSOR_TASK056_P3
        and status.get("next_gate") == SUCCESSOR_NEXT_GATE056_P3
        and status.get("runtime_enabled") is False
        and status.get("push_allowed") is False
    )
    successor_stage056_phase4_status = (
        isinstance(status, dict)
        and status.get("stage") == SUCCESSOR_STAGE056
        and status.get("phase") == SUCCESSOR_TASK056_P4
        and status.get("task") == SUCCESSOR_TASK056_P4
        and status.get("next_gate") == SUCCESSOR_NEXT_GATE056_P4
        and status.get("runtime_enabled") is False
        and status.get("push_allowed") is False
    )
    successor_stage056_review_status = (
        isinstance(status, dict)
        and status.get("stage") == SUCCESSOR_STAGE056
        and status.get("phase") == SUCCESSOR_TASK056_REVIEW
        and status.get("task") == SUCCESSOR_TASK056_REVIEW
        and status.get("next_gate") == SUCCESSOR_NEXT_GATE056_REVIEW
        and status.get("runtime_enabled") is False
        and status.get("push_allowed") is False
    )
    successor_stage057_status = (
        isinstance(status, dict)
        and status.get("stage") == SUCCESSOR_STAGE057
        and (
            (
                status.get("phase") == SUCCESSOR_TASK057
                and status.get("task") == SUCCESSOR_TASK057
                and status.get("next_gate") == SUCCESSOR_NEXT_GATE057
            )
            or (
                status.get("phase") == SUCCESSOR_TASK057_P2
                and status.get("task") == SUCCESSOR_TASK057_P2
                and status.get("next_gate") == SUCCESSOR_NEXT_GATE057_P2
            )
            or (
                status.get("phase") == SUCCESSOR_TASK057_P3
                and status.get("task") == SUCCESSOR_TASK057_P3
                and status.get("next_gate") == SUCCESSOR_NEXT_GATE057_P3
            )
            or (
                status.get("phase") == SUCCESSOR_TASK057_P4
                and status.get("task") == SUCCESSOR_TASK057_P4
                and status.get("next_gate") == SUCCESSOR_NEXT_GATE057_P4
            )
            or (
                status.get("phase") == SUCCESSOR_TASK057_REVIEW
                and status.get("task") == SUCCESSOR_TASK057_REVIEW
                and status.get("next_gate") == SUCCESSOR_NEXT_GATE057_REVIEW
            )
        )
        and status.get("runtime_enabled") is False
        and status.get("push_allowed") is False
    )
    successor_stage058_status = (
        isinstance(status, dict)
        and status.get("stage") == SUCCESSOR_STAGE058
        and status.get("phase") == SUCCESSOR_TASK058
        and status.get("task") == SUCCESSOR_TASK058
        and status.get("next_gate") == SUCCESSOR_NEXT_GATE058
        and status.get("runtime_enabled") is False
        and status.get("push_allowed") is False
    )
    successor_stage058_phase2_status = (
        isinstance(status, dict)
        and status.get("stage") == SUCCESSOR_STAGE058
        and status.get("phase") == SUCCESSOR_TASK058_P2
        and status.get("task") == SUCCESSOR_TASK058_P2
        and status.get("next_gate") == SUCCESSOR_NEXT_GATE058_P2
        and status.get("runtime_enabled") is False
        and status.get("push_allowed") is False
    )
    successor_stage058_phase3_status = (
        isinstance(status, dict)
        and status.get("stage") == SUCCESSOR_STAGE058
        and status.get("phase") == SUCCESSOR_TASK058_P3
        and status.get("task") == SUCCESSOR_TASK058_P3
        and status.get("next_gate") == SUCCESSOR_NEXT_GATE058_P3
        and status.get("runtime_enabled") is False
        and status.get("push_allowed") is False
    )
    successor_stage058_phase4_status = (
        isinstance(status, dict)
        and status.get("stage") == SUCCESSOR_STAGE058
        and status.get("phase") == SUCCESSOR_TASK058_P4
        and status.get("task") == SUCCESSOR_TASK058_P4
        and status.get("next_gate") == SUCCESSOR_NEXT_GATE058_P4
        and status.get("runtime_enabled") is False
        and status.get("push_allowed") is False
    )
    successor_stage058_review_status = (
        isinstance(status, dict)
        and status.get("stage") == SUCCESSOR_STAGE058
        and status.get("phase") == SUCCESSOR_TASK058_REVIEW
        and status.get("task") == SUCCESSOR_TASK058_REVIEW
        and status.get("next_gate") == SUCCESSOR_NEXT_GATE058_REVIEW
        and status.get("runtime_enabled") is False
        and status.get("push_allowed") is False
    )
    successor_stage059_status = (
        isinstance(status, dict)
        and status.get("stage") == SUCCESSOR_STAGE059
        and status.get("phase") == SUCCESSOR_TASK059
        and status.get("task") == SUCCESSOR_TASK059
        and status.get("next_gate") == SUCCESSOR_NEXT_GATE059
        and status.get("runtime_enabled") is False
        and status.get("push_allowed") is False
    )
    successor_stage059_phase2_status = (
        isinstance(status, dict)
        and status.get("stage") == SUCCESSOR_STAGE059
        and status.get("phase") == SUCCESSOR_TASK059_P2
        and status.get("task") == SUCCESSOR_TASK059_P2
        and status.get("next_gate") == SUCCESSOR_NEXT_GATE059_P2
        and status.get("runtime_enabled") is False
        and status.get("push_allowed") is False
    )
    successor_stage059_phase3_status = (
        isinstance(status, dict)
        and status.get("stage") == SUCCESSOR_STAGE059
        and status.get("phase") == SUCCESSOR_TASK059_P3
        and status.get("task") == SUCCESSOR_TASK059_P3
        and status.get("next_gate") == SUCCESSOR_NEXT_GATE059_P3
        and status.get("runtime_enabled") is False
        and status.get("push_allowed") is False
    )
    successor_stage059_phase4_status = (
        isinstance(status, dict)
        and status.get("stage") == SUCCESSOR_STAGE059
        and status.get("phase") == SUCCESSOR_TASK059_P4
        and status.get("task") == SUCCESSOR_TASK059_P4
        and status.get("next_gate") == SUCCESSOR_NEXT_GATE059_P4
        and status.get("runtime_enabled") is False
        and status.get("push_allowed") is False
    )
    successor_stage059_review_status = (
        isinstance(status, dict)
        and status.get("stage") == SUCCESSOR_STAGE059
        and status.get("phase") == SUCCESSOR_TASK059_REVIEW
        and status.get("task") == SUCCESSOR_TASK059_REVIEW
        and status.get("next_gate") == SUCCESSOR_NEXT_GATE059_REVIEW
        and status.get("runtime_enabled") is False
        and status.get("push_allowed") is False
    )
    successor_stage060_status = (
        isinstance(status, dict)
        and status.get("stage") == SUCCESSOR_STAGE060
        and status.get("phase") == SUCCESSOR_TASK060
        and status.get("task") == SUCCESSOR_TASK060
        and status.get("next_gate") == SUCCESSOR_NEXT_GATE060
        and status.get("runtime_enabled") is False
        and status.get("push_allowed") is False
    )
    successor_stage060_phase2_status = (
        isinstance(status, dict)
        and status.get("stage") == SUCCESSOR_STAGE060
        and status.get("phase") == SUCCESSOR_TASK060_P2
        and status.get("task") == SUCCESSOR_TASK060_P2
        and status.get("next_gate") == SUCCESSOR_NEXT_GATE060_P2
        and status.get("runtime_enabled") is False
        and status.get("push_allowed") is False
    )
    successor_stage060_phase3_status = (
        isinstance(status, dict)
        and status.get("stage") == SUCCESSOR_STAGE060
        and status.get("phase") == SUCCESSOR_TASK060_P3
        and status.get("task") == SUCCESSOR_TASK060_P3
        and status.get("next_gate") == SUCCESSOR_NEXT_GATE060_P3
        and status.get("runtime_enabled") is False
        and status.get("push_allowed") is False
    )
    successor_stage060_phase4_status = (
        isinstance(status, dict)
        and status.get("stage") == SUCCESSOR_STAGE060
        and status.get("phase") == SUCCESSOR_TASK060_P4
        and status.get("task") == SUCCESSOR_TASK060_P4
        and status.get("next_gate") == SUCCESSOR_NEXT_GATE060_P4
        and status.get("runtime_enabled") is False
        and status.get("push_allowed") is False
    )
    successor_stage060_review_status = (
        isinstance(status, dict)
        and status.get("stage") == SUCCESSOR_STAGE060
        and status.get("phase") == SUCCESSOR_TASK060_REVIEW
        and status.get("task") == SUCCESSOR_TASK060_REVIEW
        and status.get("next_gate") == SUCCESSOR_NEXT_GATE060_REVIEW
        and status.get("runtime_enabled") is False
        and status.get("push_allowed") is False
    )
    successor_stage060_batch_status = (
        isinstance(status, dict)
        and status.get("stage") == SUCCESSOR_STAGE060
        and status.get("phase") == SUCCESSOR_TASK060_BATCH
        and status.get("task") == SUCCESSOR_TASK060_BATCH
        and status.get("next_gate") == SUCCESSOR_NEXT_GATE060_BATCH
        and status.get("runtime_enabled") is False
        and status.get("push_allowed") is False
    )
    successor_stage061_status = (
        isinstance(status, dict)
        and status.get("stage") == SUCCESSOR_STAGE061
        and status.get("phase") == SUCCESSOR_TASK061
        and status.get("task") == SUCCESSOR_TASK061
        and status.get("next_gate") == SUCCESSOR_NEXT_GATE061
        and status.get("runtime_enabled") is False
        and status.get("push_allowed") is False
    )
    successor_stage061_phase2_status = (
        isinstance(status, dict)
        and status.get("stage") == SUCCESSOR_STAGE061
        and status.get("phase") == SUCCESSOR_TASK061_P2
        and status.get("task") == SUCCESSOR_TASK061_P2
        and status.get("next_gate") == SUCCESSOR_NEXT_GATE061_P2
        and status.get("runtime_enabled") is False
        and status.get("push_allowed") is False
    )
    successor_stage061_phase3_status = (
        isinstance(status, dict)
        and status.get("stage") == SUCCESSOR_STAGE061
        and status.get("phase") == SUCCESSOR_TASK061_P3
        and status.get("task") == SUCCESSOR_TASK061_P3
        and status.get("next_gate") == SUCCESSOR_NEXT_GATE061_P3
        and status.get("runtime_enabled") is False
        and status.get("push_allowed") is False
    )
    successor_stage061_phase4_status = (
        isinstance(status, dict)
        and status.get("stage") == SUCCESSOR_STAGE061
        and status.get("phase") == SUCCESSOR_TASK061_P4
        and status.get("task") == SUCCESSOR_TASK061_P4
        and status.get("next_gate") == SUCCESSOR_NEXT_GATE061_P4
        and status.get("runtime_enabled") is False
        and status.get("push_allowed") is False
    )
    successor_stage061_review_status = (
        isinstance(status, dict)
        and status.get("stage") == SUCCESSOR_STAGE061
        and status.get("phase") == SUCCESSOR_TASK061_REVIEW
        and status.get("task") == SUCCESSOR_TASK061_REVIEW
        and status.get("next_gate") == SUCCESSOR_NEXT_GATE061_REVIEW
        and status.get("runtime_enabled") is False
        and status.get("push_allowed") is False
    )
    successor_stage062_phase1_status = (
        isinstance(status, dict)
        and status.get("stage") == SUCCESSOR_STAGE062
        and status.get("phase") == SUCCESSOR_TASK062
        and status.get("task") == SUCCESSOR_TASK062
        and status.get("next_gate") == SUCCESSOR_NEXT_GATE062
        and status.get("runtime_enabled") is False
        and status.get("push_allowed") is False
    )
    successor_stage062_phase2_status = (
        isinstance(status, dict)
        and status.get("stage") == SUCCESSOR_STAGE062
        and status.get("phase") == SUCCESSOR_TASK062_P2
        and status.get("task") == SUCCESSOR_TASK062_P2
        and status.get("next_gate") == SUCCESSOR_NEXT_GATE062_P2
        and status.get("runtime_enabled") is False
        and status.get("push_allowed") is False
    )
    successor_stage062_phase3_status = (
        isinstance(status, dict)
        and status.get("stage") == SUCCESSOR_STAGE062
        and status.get("phase") == SUCCESSOR_TASK062_P3
        and status.get("task") == SUCCESSOR_TASK062_P3
        and status.get("next_gate") == SUCCESSOR_NEXT_GATE062_P3
        and status.get("runtime_enabled") is False
        and status.get("push_allowed") is False
    )
    successor_stage062_phase4_status = (
        isinstance(status, dict)
        and status.get("stage") == SUCCESSOR_STAGE062
        and status.get("phase") == SUCCESSOR_TASK062_P4
        and status.get("task") == SUCCESSOR_TASK062_P4
        and status.get("next_gate") == SUCCESSOR_NEXT_GATE062_P4
        and status.get("runtime_enabled") is False
        and status.get("push_allowed") is False
    )
    successor_stage062_review_status = (
        isinstance(status, dict)
        and status.get("stage") == SUCCESSOR_STAGE062
        and status.get("phase") == SUCCESSOR_PHASE062_REVIEW
        and status.get("task") == SUCCESSOR_TASK062_REVIEW
        and status.get("next_gate") == SUCCESSOR_NEXT_GATE062_REVIEW
        and status.get("runtime_enabled") is False
        and status.get("push_allowed") is False
    )
    successor_stage063_status = (
        isinstance(status, dict)
        and status.get("stage") == SUCCESSOR_STAGE063
        and status.get("phase") == SUCCESSOR_TASK063
        and status.get("task") == SUCCESSOR_TASK063
        and status.get("next_gate") == SUCCESSOR_NEXT_GATE063
        and status.get("runtime_enabled") is False
        and status.get("push_allowed") is False
    )
    successor_stage063_phase2_status = (
        isinstance(status, dict)
        and status.get("stage") == SUCCESSOR_STAGE063
        and status.get("phase") == SUCCESSOR_TASK063_P2
        and status.get("task") == SUCCESSOR_TASK063_P2
        and status.get("next_gate") == SUCCESSOR_NEXT_GATE063_P2
        and status.get("runtime_enabled") is False
        and status.get("push_allowed") is False
    )
    successor_stage063_phase3_status = (
        isinstance(status, dict)
        and status.get("stage") == SUCCESSOR_STAGE063
        and status.get("phase") == SUCCESSOR_TASK063_P3
        and status.get("task") == SUCCESSOR_TASK063_P3
        and status.get("next_gate") == SUCCESSOR_NEXT_GATE063_P3
        and status.get("runtime_enabled") is False
        and status.get("push_allowed") is False
    )
    successor_stage063_phase4_status = (
        isinstance(status, dict)
        and status.get("stage") == SUCCESSOR_STAGE063
        and status.get("phase") == SUCCESSOR_TASK063_P4
        and status.get("task") == SUCCESSOR_TASK063_P4
        and status.get("next_gate") == SUCCESSOR_NEXT_GATE063_P4
        and status.get("runtime_enabled") is False
        and status.get("push_allowed") is False
    )
    successor_stage063_review_status = (
        isinstance(status, dict)
        and status.get("stage") == SUCCESSOR_STAGE063
        and status.get("phase") == SUCCESSOR_TASK063_REVIEW
        and status.get("task") == SUCCESSOR_TASK063_REVIEW
        and status.get("next_gate") == SUCCESSOR_NEXT_GATE063_REVIEW
        and status.get("runtime_enabled") is False
        and status.get("push_allowed") is False
    )
    successor_stage064_phase1_status = (
        isinstance(status, dict)
        and status.get("stage") == SUCCESSOR_STAGE064
        and status.get("phase") == SUCCESSOR_TASK064
        and status.get("task") == SUCCESSOR_TASK064
        and status.get("next_gate") == SUCCESSOR_NEXT_GATE064
        and status.get("runtime_enabled") is False
        and status.get("push_allowed") is False
    )
    successor_stage064_phase2_status = (
        isinstance(status, dict)
        and status.get("stage") == SUCCESSOR_STAGE064
        and status.get("phase") == SUCCESSOR_TASK064_P2
        and status.get("task") == SUCCESSOR_TASK064_P2
        and status.get("next_gate") == SUCCESSOR_NEXT_GATE064_P2
        and status.get("runtime_enabled") is False
        and status.get("push_allowed") is False
    )
    successor_stage064_phase3_status = (
        isinstance(status, dict)
        and status.get("stage") == SUCCESSOR_STAGE064
        and status.get("phase") == SUCCESSOR_TASK064_P3
        and status.get("task") == SUCCESSOR_TASK064_P3
        and status.get("next_gate") == SUCCESSOR_NEXT_GATE064_P3
        and status.get("runtime_enabled") is False
        and status.get("push_allowed") is False
    )
    successor_stage064_phase4_status = (
        isinstance(status, dict)
        and status.get("stage") == SUCCESSOR_STAGE064
        and status.get("phase") == SUCCESSOR_TASK064_P4
        and status.get("task") == SUCCESSOR_TASK064_P4
        and status.get("next_gate") == SUCCESSOR_NEXT_GATE064_P4
        and status.get("runtime_enabled") is False
        and status.get("push_allowed") is False
    )
    successor_stage064_review_status = (
        isinstance(status, dict)
        and status.get("stage") == SUCCESSOR_STAGE064
        and status.get("phase") == SUCCESSOR_TASK064_REVIEW
        and status.get("task") == SUCCESSOR_TASK064_REVIEW
        and status.get("next_gate") == SUCCESSOR_NEXT_GATE064_REVIEW
        and status.get("runtime_enabled") is False
        and status.get("push_allowed") is False
    )
    successor_stage065_phase1_status = (
        isinstance(status, dict)
        and status.get("stage") == SUCCESSOR_STAGE065
        and status.get("phase") == SUCCESSOR_TASK065
        and status.get("task") == SUCCESSOR_TASK065
        and status.get("next_gate") == SUCCESSOR_NEXT_GATE065
        and status.get("runtime_enabled") is False
        and status.get("push_allowed") is False
    )
    successor_stage065_phase2_status = (
        isinstance(status, dict)
        and status.get("stage") == SUCCESSOR_STAGE065
        and status.get("phase") == SUCCESSOR_TASK065_P2
        and status.get("task") == SUCCESSOR_TASK065_P2
        and status.get("next_gate") == SUCCESSOR_NEXT_GATE065_P2
        and status.get("runtime_enabled") is False
        and status.get("push_allowed") is False
    )
    successor_stage065_phase3_status = (
        isinstance(status, dict)
        and status.get("stage") == SUCCESSOR_STAGE065
        and status.get("phase") == SUCCESSOR_TASK065_P3
        and status.get("task") == SUCCESSOR_TASK065_P3
        and status.get("next_gate") == SUCCESSOR_NEXT_GATE065_P3
        and status.get("runtime_enabled") is False
        and status.get("push_allowed") is False
    )
    successor_stage065_phase4_status = (
        isinstance(status, dict)
        and status.get("stage") == SUCCESSOR_STAGE065
        and status.get("phase") == SUCCESSOR_TASK065_P4
        and status.get("task") == SUCCESSOR_TASK065_P4
        and status.get("next_gate") == SUCCESSOR_NEXT_GATE065_P4
        and status.get("runtime_enabled") is False
        and status.get("push_allowed") is False
    )
    successor_stage065_review_status = (
        isinstance(status, dict)
        and status.get("stage") == SUCCESSOR_STAGE065
        and status.get("phase") == SUCCESSOR_TASK065_REVIEW
        and status.get("task") == SUCCESSOR_TASK065_REVIEW
        and status.get("next_gate") == SUCCESSOR_NEXT_GATE065_REVIEW
        and status.get("runtime_enabled") is False
        and status.get("push_allowed") is False
    )
    successor_stage066_phase1_status = (
        isinstance(status, dict)
        and status.get("stage") == SUCCESSOR_STAGE066
        and status.get("phase") == SUCCESSOR_TASK066
        and status.get("task") == SUCCESSOR_TASK066
        and status.get("next_gate") == SUCCESSOR_NEXT_GATE066
        and status.get("runtime_enabled") is False
        and status.get("push_allowed") is False
    )
    successor_stage066_phase2_status = (
        isinstance(status, dict)
        and status.get("stage") == SUCCESSOR_STAGE066
        and status.get("phase") == SUCCESSOR_TASK066_P2
        and status.get("task") == SUCCESSOR_TASK066_P2
        and status.get("next_gate") == SUCCESSOR_NEXT_GATE066_P2
        and status.get("runtime_enabled") is False
        and status.get("push_allowed") is False
    )
    successor_stage066_phase3_status = (
        isinstance(status, dict)
        and status.get("stage") == SUCCESSOR_STAGE066
        and status.get("phase") == SUCCESSOR_TASK066_P3
        and status.get("task") == SUCCESSOR_TASK066_P3
        and status.get("next_gate") == SUCCESSOR_NEXT_GATE066_P3
        and status.get("runtime_enabled") is False
        and status.get("push_allowed") is False
    )
    successor_stage066_phase4_status = (
        isinstance(status, dict)
        and status.get("stage") == SUCCESSOR_STAGE066
        and status.get("phase") == SUCCESSOR_TASK066_P4
        and status.get("task") == SUCCESSOR_TASK066_P4
        and status.get("next_gate") == SUCCESSOR_NEXT_GATE066_P4
        and status.get("runtime_enabled") is False
        and status.get("push_allowed") is False
    )
    successor_stage066_review_status = (
        isinstance(status, dict)
        and status.get("stage") == SUCCESSOR_STAGE066
        and status.get("phase") == SUCCESSOR_PHASE066_REVIEW
        and status.get("task") == SUCCESSOR_TASK066_REVIEW
        and status.get("next_gate") == SUCCESSOR_NEXT_GATE066_REVIEW
        and status.get("runtime_enabled") is False
        and status.get("push_allowed") is False
    )
    successor_stage067_phase1_status = (
        isinstance(status, dict)
        and status.get("stage") == SUCCESSOR_STAGE067
        and status.get("phase") == SUCCESSOR_TASK067
        and status.get("task") == SUCCESSOR_TASK067
        and status.get("next_gate") == SUCCESSOR_NEXT_GATE067
        and status.get("runtime_enabled") is False
        and status.get("push_allowed") is False
    )
    successor_stage067_phase2_status = (
        isinstance(status, dict)
        and status.get("stage") == SUCCESSOR_STAGE067
        and status.get("phase") == SUCCESSOR_TASK067_P2
        and status.get("task") == SUCCESSOR_TASK067_P2
        and status.get("next_gate") == SUCCESSOR_NEXT_GATE067_P2
        and status.get("runtime_enabled") is False
        and status.get("push_allowed") is False
    )
    successor_stage067_phase3_status = (
        isinstance(status, dict)
        and status.get("stage") == SUCCESSOR_STAGE067
        and status.get("phase") == SUCCESSOR_TASK067_P3
        and status.get("task") == SUCCESSOR_TASK067_P3
        and status.get("next_gate") == SUCCESSOR_NEXT_GATE067_P3
        and status.get("runtime_enabled") is False
        and status.get("push_allowed") is False
    )
    successor_stage067_phase4_status = (
        isinstance(status, dict)
        and status.get("stage") == SUCCESSOR_STAGE067
        and status.get("phase") == SUCCESSOR_TASK067_P4
        and status.get("task") == SUCCESSOR_TASK067_P4
        and status.get("next_gate") == SUCCESSOR_NEXT_GATE067_P4
        and status.get("runtime_enabled") is False
        and status.get("push_allowed") is False
    )
    successor_stage067_review_status = (
        isinstance(status, dict)
        and status.get("stage") == SUCCESSOR_STAGE067
        and status.get("phase") == SUCCESSOR_TASK067_REVIEW
        and status.get("task") == SUCCESSOR_TASK067_REVIEW
        and status.get("next_gate") == SUCCESSOR_NEXT_GATE067_REVIEW
        and status.get("runtime_enabled") is False
        and status.get("push_allowed") is False
    )
    successor_stage068_phase1_status = (
        isinstance(status, dict)
        and status.get("stage") == SUCCESSOR_STAGE068
        and status.get("phase") == SUCCESSOR_TASK068
        and status.get("task") == SUCCESSOR_TASK068
        and status.get("next_gate") == SUCCESSOR_NEXT_GATE068
        and status.get("runtime_enabled") is False
        and status.get("push_allowed") is False
    )
    successor_stage068_phase2_status = (
        isinstance(status, dict)
        and status.get("stage") == SUCCESSOR_STAGE068
        and status.get("phase") == SUCCESSOR_TASK068_P2
        and status.get("task") == SUCCESSOR_TASK068_P2
        and status.get("next_gate") == SUCCESSOR_NEXT_GATE068_P2
        and status.get("runtime_enabled") is False
        and status.get("push_allowed") is False
    )
    successor_stage068_phase3_status = (
        isinstance(status, dict)
        and status.get("stage") == SUCCESSOR_STAGE068
        and status.get("phase") == SUCCESSOR_TASK068_P3
        and status.get("task") == SUCCESSOR_TASK068_P3
        and status.get("next_gate") == SUCCESSOR_NEXT_GATE068_P3
        and status.get("runtime_enabled") is False
        and status.get("push_allowed") is False
    )
    successor_stage068_phase4_status = (
        isinstance(status, dict)
        and status.get("stage") == SUCCESSOR_STAGE068
        and status.get("phase") == SUCCESSOR_TASK068_P4
        and status.get("task") == SUCCESSOR_TASK068_P4
        and status.get("next_gate") == SUCCESSOR_NEXT_GATE068_P4
        and status.get("runtime_enabled") is False
        and status.get("push_allowed") is False
    )
    successor_stage068_review_status = (
        isinstance(status, dict)
        and status.get("stage") == SUCCESSOR_STAGE068
        and status.get("phase") == SUCCESSOR_TASK068_REVIEW
        and status.get("task") == SUCCESSOR_TASK068_REVIEW
        and status.get("next_gate") == SUCCESSOR_NEXT_GATE068_REVIEW
        and status.get("runtime_enabled") is False
        and status.get("push_allowed") is False
    )
    successor_stage069_phase1_status = (
        isinstance(status, dict)
        and status.get("stage") == SUCCESSOR_STAGE069
        and status.get("phase") == SUCCESSOR_TASK069
        and status.get("task") == SUCCESSOR_TASK069
        and status.get("next_gate") == SUCCESSOR_NEXT_GATE069
        and status.get("runtime_enabled") is False
        and status.get("push_allowed") is False
    )
    successor_stage069_phase2_status = (
        isinstance(status, dict)
        and status.get("stage") == SUCCESSOR_STAGE069
        and status.get("phase") == SUCCESSOR_TASK069_P2
        and status.get("task") == SUCCESSOR_TASK069_P2
        and status.get("next_gate") == SUCCESSOR_NEXT_GATE069_P2
        and status.get("runtime_enabled") is False
        and status.get("push_allowed") is False
    )
    successor_stage069_phase3_status = (
        isinstance(status, dict)
        and status.get("stage") == SUCCESSOR_STAGE069
        and status.get("phase") == SUCCESSOR_TASK069_P3
        and status.get("task") == SUCCESSOR_TASK069_P3
        and status.get("next_gate") == SUCCESSOR_NEXT_GATE069_P3
        and status.get("runtime_enabled") is False
        and status.get("push_allowed") is False
    )
    successor_stage069_phase4_status = (
        isinstance(status, dict)
        and status.get("stage") == SUCCESSOR_STAGE069
        and status.get("phase") == SUCCESSOR_TASK069_P4
        and status.get("task") == SUCCESSOR_TASK069_P4
        and status.get("next_gate") == SUCCESSOR_NEXT_GATE069_P4
        and status.get("runtime_enabled") is False
        and status.get("push_allowed") is False
    )
    successor_stage069_review_status = (
        isinstance(status, dict)
        and status.get("stage") == SUCCESSOR_STAGE069
        and status.get("phase") == SUCCESSOR_TASK069_REVIEW
        and status.get("task") == SUCCESSOR_TASK069_REVIEW
        and status.get("next_gate") == SUCCESSOR_NEXT_GATE069_REVIEW
        and status.get("runtime_enabled") is False
        and status.get("push_allowed") is False
    )
    successor_stage070_phase1_status = (
        isinstance(status, dict)
        and status.get("stage") == SUCCESSOR_STAGE070
        and status.get("phase")
        in (
            SUCCESSOR_TASK070,
            SUCCESSOR_TASK070_P2,
            SUCCESSOR_TASK070_P3,
            SUCCESSOR_TASK070_P4,
            SUCCESSOR_TASK070_REVIEW,
        )
        and status.get("task")
        in (
            SUCCESSOR_TASK070,
            SUCCESSOR_TASK070_P2,
            SUCCESSOR_TASK070_P3,
            SUCCESSOR_TASK070_P4,
            SUCCESSOR_TASK070_REVIEW,
        )
        and status.get("next_gate")
        in (
            SUCCESSOR_NEXT_GATE070,
            SUCCESSOR_NEXT_GATE070_P2,
            SUCCESSOR_NEXT_GATE070_P3,
            SUCCESSOR_NEXT_GATE070_P4,
            SUCCESSOR_NEXT_GATE070_REVIEW,
        )
        and status.get("runtime_enabled") is False
        and status.get("push_allowed") is False
    )
    successor_plan = (
        isinstance(plan, dict)
        and plan.get("stage") == SUCCESSOR_STAGE
        and plan.get("phase") == SUCCESSOR_TASK
        and plan.get("task") == SUCCESSOR_TASK
        and SUCCESSOR_NEXT_GATE in str(plan.get("stop_condition"))
    )
    successor_phase2_plan = (
        isinstance(plan, dict)
        and plan.get("stage") == SUCCESSOR_STAGE
        and plan.get("phase") == SUCCESSOR_TASK2
        and plan.get("task") == SUCCESSOR_TASK2
        and SUCCESSOR_NEXT_GATE2 in str(plan.get("stop_condition"))
    )
    successor_phase3_plan = (
        isinstance(plan, dict)
        and plan.get("stage") == SUCCESSOR_STAGE
        and plan.get("phase") == SUCCESSOR_TASK3
        and plan.get("task") == SUCCESSOR_TASK3
        and SUCCESSOR_NEXT_GATE3 in str(plan.get("stop_condition"))
    )
    successor_phase4_plan = (
        isinstance(plan, dict)
        and plan.get("stage") == SUCCESSOR_STAGE
        and plan.get("phase") == SUCCESSOR_TASK4
        and plan.get("task") == SUCCESSOR_TASK4
        and SUCCESSOR_NEXT_GATE4 in str(plan.get("stop_condition"))
    )
    successor_review_plan = (
        isinstance(plan, dict)
        and plan.get("stage") == SUCCESSOR_STAGE
        and plan.get("phase") == SUCCESSOR_REVIEW_TASK
        and plan.get("task") == SUCCESSOR_REVIEW_TASK
        and SUCCESSOR_REVIEW_NEXT_GATE in str(plan.get("stop_condition"))
    )
    successor_stage052_plan = (
        isinstance(plan, dict)
        and plan.get("stage") == SUCCESSOR_STAGE052
        and plan.get("phase") == SUCCESSOR_TASK052
        and plan.get("task") == SUCCESSOR_TASK052
        and SUCCESSOR_NEXT_GATE052 in str(plan.get("stop_condition"))
    )
    successor_stage052_phase2_plan = (
        isinstance(plan, dict)
        and plan.get("stage") == SUCCESSOR_STAGE052
        and plan.get("phase") == SUCCESSOR_TASK052_P2
        and plan.get("task") == SUCCESSOR_TASK052_P2
        and SUCCESSOR_NEXT_GATE052_P2 in str(plan.get("stop_condition"))
    )
    successor_stage052_phase3_plan = (
        isinstance(plan, dict)
        and plan.get("stage") == SUCCESSOR_STAGE052
        and plan.get("phase") == SUCCESSOR_TASK052_P3
        and plan.get("task") == SUCCESSOR_TASK052_P3
        and SUCCESSOR_NEXT_GATE052_P3 in str(plan.get("stop_condition"))
    )
    successor_stage052_phase4_plan = (
        isinstance(plan, dict)
        and plan.get("stage") == SUCCESSOR_STAGE052
        and plan.get("phase") == SUCCESSOR_TASK052_P4
        and plan.get("task") == SUCCESSOR_TASK052_P4
        and SUCCESSOR_NEXT_GATE052_P4 in str(plan.get("stop_condition"))
    )
    successor_stage052_review_plan = (
        isinstance(plan, dict)
        and plan.get("stage") == SUCCESSOR_STAGE052
        and plan.get("phase") == SUCCESSOR_TASK052_REVIEW
        and plan.get("task") == SUCCESSOR_TASK052_REVIEW
        and SUCCESSOR_NEXT_GATE052_REVIEW in str(plan.get("stop_condition"))
    )
    successor_stage053_plan = (
        isinstance(plan, dict)
        and plan.get("stage") == SUCCESSOR_STAGE053
        and plan.get("phase") == SUCCESSOR_TASK053
        and plan.get("task") == SUCCESSOR_TASK053
        and SUCCESSOR_NEXT_GATE053 in str(plan.get("stop_condition"))
    )
    successor_stage053_phase2_plan = (
        isinstance(plan, dict)
        and plan.get("stage") == SUCCESSOR_STAGE053
        and plan.get("phase") == SUCCESSOR_TASK053_P2
        and plan.get("task") == SUCCESSOR_TASK053_P2
        and SUCCESSOR_NEXT_GATE053_P2 in str(plan.get("stop_condition"))
    )
    successor_stage053_phase3_plan = (
        isinstance(plan, dict)
        and plan.get("stage") == SUCCESSOR_STAGE053
        and plan.get("phase") == SUCCESSOR_TASK053_P3
        and plan.get("task") == SUCCESSOR_TASK053_P3
        and SUCCESSOR_NEXT_GATE053_P3 in str(plan.get("stop_condition"))
    )
    successor_stage053_phase4_plan = (
        isinstance(plan, dict)
        and plan.get("stage") == SUCCESSOR_STAGE053
        and plan.get("phase") == SUCCESSOR_TASK053_P4
        and plan.get("task") == SUCCESSOR_TASK053_P4
        and SUCCESSOR_NEXT_GATE053_P4 in str(plan.get("stop_condition"))
    )
    successor_stage053_review_plan = (
        isinstance(plan, dict)
        and plan.get("stage") == SUCCESSOR_STAGE053
        and plan.get("phase") == SUCCESSOR_TASK053_REVIEW
        and plan.get("task") == SUCCESSOR_TASK053_REVIEW
        and SUCCESSOR_NEXT_GATE053_REVIEW in str(plan.get("stop_condition"))
    )
    successor_stage054_plan = (
        isinstance(plan, dict)
        and plan.get("stage") == SUCCESSOR_STAGE054
        and plan.get("phase") == SUCCESSOR_TASK054
        and plan.get("task") == SUCCESSOR_TASK054
        and SUCCESSOR_NEXT_GATE054 in str(plan.get("stop_condition"))
    )
    successor_stage054_phase2_plan = (
        isinstance(plan, dict)
        and plan.get("stage") == SUCCESSOR_STAGE054
        and plan.get("phase") == SUCCESSOR_TASK054_P2
        and plan.get("task") == SUCCESSOR_TASK054_P2
        and SUCCESSOR_NEXT_GATE054_P2 in str(plan.get("stop_condition"))
    )
    successor_stage054_phase3_plan = (
        isinstance(plan, dict)
        and plan.get("stage") == SUCCESSOR_STAGE054
        and plan.get("phase") == SUCCESSOR_TASK054_P3
        and plan.get("task") == SUCCESSOR_TASK054_P3
        and SUCCESSOR_NEXT_GATE054_P3 in str(plan.get("stop_condition"))
    )
    successor_stage054_phase4_plan = (
        isinstance(plan, dict)
        and plan.get("stage") == SUCCESSOR_STAGE054
        and plan.get("phase") == SUCCESSOR_TASK054_P4
        and plan.get("task") == SUCCESSOR_TASK054_P4
        and SUCCESSOR_NEXT_GATE054_P4 in str(plan.get("stop_condition"))
    )
    successor_stage054_review_plan = (
        isinstance(plan, dict)
        and plan.get("stage") == SUCCESSOR_STAGE054
        and plan.get("phase") == SUCCESSOR_TASK054_REVIEW
        and plan.get("task") == SUCCESSOR_TASK054_REVIEW
        and SUCCESSOR_NEXT_GATE054_REVIEW in str(plan.get("stop_condition"))
    )
    successor_stage055_plan = (
        isinstance(plan, dict)
        and plan.get("stage") == SUCCESSOR_STAGE055
        and plan.get("phase") == SUCCESSOR_TASK055
        and plan.get("task") == SUCCESSOR_TASK055
        and SUCCESSOR_NEXT_GATE055 in str(plan.get("stop_condition"))
    )
    successor_stage055_phase2_plan = (
        isinstance(plan, dict)
        and plan.get("stage") == SUCCESSOR_STAGE055
        and plan.get("phase") == SUCCESSOR_TASK055_P2
        and plan.get("task") == SUCCESSOR_TASK055_P2
        and SUCCESSOR_NEXT_GATE055_P2 in str(plan.get("stop_condition"))
    )
    successor_stage055_phase3_plan = (
        isinstance(plan, dict)
        and plan.get("stage") == SUCCESSOR_STAGE055
        and plan.get("phase") == SUCCESSOR_TASK055_P3
        and plan.get("task") == SUCCESSOR_TASK055_P3
        and SUCCESSOR_NEXT_GATE055_P3 in str(plan.get("stop_condition"))
    )
    successor_stage055_phase4_plan = (
        isinstance(plan, dict)
        and plan.get("stage") == SUCCESSOR_STAGE055
        and plan.get("phase") == SUCCESSOR_TASK055_P4
        and plan.get("task") == SUCCESSOR_TASK055_P4
        and SUCCESSOR_NEXT_GATE055_P4 in str(plan.get("stop_condition"))
    )
    successor_stage055_review_plan = (
        isinstance(plan, dict)
        and plan.get("stage") == SUCCESSOR_STAGE055
        and plan.get("phase") == SUCCESSOR_TASK055_REVIEW
        and plan.get("task") == SUCCESSOR_TASK055_REVIEW
        and SUCCESSOR_NEXT_GATE055_REVIEW in str(plan.get("stop_condition"))
    )
    successor_stage056_plan = (
        isinstance(plan, dict)
        and plan.get("stage") == SUCCESSOR_STAGE056
        and plan.get("phase") == SUCCESSOR_TASK056
        and plan.get("task") == SUCCESSOR_TASK056
        and SUCCESSOR_NEXT_GATE056 in str(plan.get("stop_condition"))
    )
    successor_stage056_phase2_plan = (
        isinstance(plan, dict)
        and plan.get("stage") == SUCCESSOR_STAGE056
        and plan.get("phase") == SUCCESSOR_TASK056_P2
        and plan.get("task") == SUCCESSOR_TASK056_P2
        and SUCCESSOR_NEXT_GATE056_P2 in str(plan.get("stop_condition"))
    )
    successor_stage056_phase3_plan = (
        isinstance(plan, dict)
        and plan.get("stage") == SUCCESSOR_STAGE056
        and plan.get("phase") == SUCCESSOR_TASK056_P3
        and plan.get("task") == SUCCESSOR_TASK056_P3
        and SUCCESSOR_NEXT_GATE056_P3 in str(plan.get("stop_condition"))
    )
    successor_stage056_phase4_plan = (
        isinstance(plan, dict)
        and plan.get("stage") == SUCCESSOR_STAGE056
        and plan.get("phase") == SUCCESSOR_TASK056_P4
        and plan.get("task") == SUCCESSOR_TASK056_P4
        and SUCCESSOR_NEXT_GATE056_P4 in str(plan.get("stop_condition"))
    )
    successor_stage056_review_plan = (
        isinstance(plan, dict)
        and plan.get("stage") == SUCCESSOR_STAGE056
        and plan.get("phase") == SUCCESSOR_TASK056_REVIEW
        and plan.get("task") == SUCCESSOR_TASK056_REVIEW
        and SUCCESSOR_NEXT_GATE056_REVIEW in str(plan.get("stop_condition"))
    )
    successor_stage057_plan = (
        isinstance(plan, dict)
        and plan.get("stage") == SUCCESSOR_STAGE057
        and (
            (
                plan.get("phase") == SUCCESSOR_TASK057
                and plan.get("task") == SUCCESSOR_TASK057
                and SUCCESSOR_NEXT_GATE057 in str(plan.get("stop_condition"))
            )
            or (
                plan.get("phase") == SUCCESSOR_TASK057_P2
                and plan.get("task") == SUCCESSOR_TASK057_P2
                and SUCCESSOR_NEXT_GATE057_P2 in str(plan.get("stop_condition"))
            )
            or (
                plan.get("phase") == SUCCESSOR_TASK057_P3
                and plan.get("task") == SUCCESSOR_TASK057_P3
                and SUCCESSOR_NEXT_GATE057_P3 in str(plan.get("stop_condition"))
            )
            or (
                plan.get("phase") == SUCCESSOR_TASK057_P4
                and plan.get("task") == SUCCESSOR_TASK057_P4
                and SUCCESSOR_NEXT_GATE057_P4 in str(plan.get("stop_condition"))
            )
            or (
                plan.get("phase") == SUCCESSOR_TASK057_REVIEW
                and plan.get("task") == SUCCESSOR_TASK057_REVIEW
                and SUCCESSOR_NEXT_GATE057_REVIEW in str(plan.get("stop_condition"))
            )
        )
    )
    successor_stage058_plan = (
        isinstance(plan, dict)
        and plan.get("stage") == SUCCESSOR_STAGE058
        and plan.get("phase") == SUCCESSOR_TASK058
        and plan.get("task") == SUCCESSOR_TASK058
        and SUCCESSOR_NEXT_GATE058 in str(plan.get("stop_condition"))
    )
    successor_stage058_phase2_plan = (
        isinstance(plan, dict)
        and plan.get("stage") == SUCCESSOR_STAGE058
        and plan.get("phase") == SUCCESSOR_TASK058_P2
        and plan.get("task") == SUCCESSOR_TASK058_P2
        and SUCCESSOR_NEXT_GATE058_P2 in str(plan.get("stop_condition"))
    )
    successor_stage058_phase3_plan = (
        isinstance(plan, dict)
        and plan.get("stage") == SUCCESSOR_STAGE058
        and plan.get("phase") == SUCCESSOR_TASK058_P3
        and plan.get("task") == SUCCESSOR_TASK058_P3
        and SUCCESSOR_NEXT_GATE058_P3 in str(plan.get("stop_condition"))
    )
    successor_stage058_phase4_plan = (
        isinstance(plan, dict)
        and plan.get("stage") == SUCCESSOR_STAGE058
        and plan.get("phase") == SUCCESSOR_TASK058_P4
        and plan.get("task") == SUCCESSOR_TASK058_P4
        and SUCCESSOR_NEXT_GATE058_P4 in str(plan.get("stop_condition"))
    )
    successor_stage058_review_plan = (
        isinstance(plan, dict)
        and plan.get("stage") == SUCCESSOR_STAGE058
        and plan.get("phase") == SUCCESSOR_TASK058_REVIEW
        and plan.get("task") == SUCCESSOR_TASK058_REVIEW
        and SUCCESSOR_NEXT_GATE058_REVIEW in str(plan.get("stop_condition"))
    )
    successor_stage059_plan = (
        isinstance(plan, dict)
        and plan.get("stage") == SUCCESSOR_STAGE059
        and plan.get("phase") == SUCCESSOR_TASK059
        and plan.get("task") == SUCCESSOR_TASK059
        and SUCCESSOR_NEXT_GATE059 in str(plan.get("stop_condition"))
    )
    successor_stage059_phase2_plan = (
        isinstance(plan, dict)
        and plan.get("stage") == SUCCESSOR_STAGE059
        and plan.get("phase") == SUCCESSOR_TASK059_P2
        and plan.get("task") == SUCCESSOR_TASK059_P2
        and SUCCESSOR_NEXT_GATE059_P2 in str(plan.get("stop_condition"))
    )
    successor_stage059_phase3_plan = (
        isinstance(plan, dict)
        and plan.get("stage") == SUCCESSOR_STAGE059
        and plan.get("phase") == SUCCESSOR_TASK059_P3
        and plan.get("task") == SUCCESSOR_TASK059_P3
        and SUCCESSOR_NEXT_GATE059_P3 in str(plan.get("stop_condition"))
    )
    successor_stage059_phase4_plan = (
        isinstance(plan, dict)
        and plan.get("stage") == SUCCESSOR_STAGE059
        and plan.get("phase") == SUCCESSOR_TASK059_P4
        and plan.get("task") == SUCCESSOR_TASK059_P4
        and SUCCESSOR_NEXT_GATE059_P4 in str(plan.get("stop_condition"))
    )
    successor_stage059_review_plan = (
        isinstance(plan, dict)
        and plan.get("stage") == SUCCESSOR_STAGE059
        and plan.get("phase") == SUCCESSOR_TASK059_REVIEW
        and plan.get("task") == SUCCESSOR_TASK059_REVIEW
        and SUCCESSOR_NEXT_GATE059_REVIEW in str(plan.get("stop_condition"))
    )
    successor_stage060_plan = (
        isinstance(plan, dict)
        and plan.get("stage") == SUCCESSOR_STAGE060
        and plan.get("phase") == SUCCESSOR_TASK060
        and plan.get("task") == SUCCESSOR_TASK060
        and SUCCESSOR_NEXT_GATE060 in str(plan.get("stop_condition"))
    )
    successor_stage060_phase2_plan = (
        isinstance(plan, dict)
        and plan.get("stage") == SUCCESSOR_STAGE060
        and plan.get("phase") == SUCCESSOR_TASK060_P2
        and plan.get("task") == SUCCESSOR_TASK060_P2
        and SUCCESSOR_NEXT_GATE060_P2 in str(plan.get("stop_condition"))
    )
    successor_stage060_phase3_plan = (
        isinstance(plan, dict)
        and plan.get("stage") == SUCCESSOR_STAGE060
        and plan.get("phase") == SUCCESSOR_TASK060_P3
        and plan.get("task") == SUCCESSOR_TASK060_P3
        and SUCCESSOR_NEXT_GATE060_P3 in str(plan.get("stop_condition"))
    )
    successor_stage060_phase4_plan = (
        isinstance(plan, dict)
        and plan.get("stage") == SUCCESSOR_STAGE060
        and plan.get("phase") == SUCCESSOR_TASK060_P4
        and plan.get("task") == SUCCESSOR_TASK060_P4
        and SUCCESSOR_NEXT_GATE060_P4 in str(plan.get("stop_condition"))
    )
    successor_stage060_review_plan = (
        isinstance(plan, dict)
        and plan.get("stage") == SUCCESSOR_STAGE060
        and plan.get("phase") == SUCCESSOR_TASK060_REVIEW
        and plan.get("task") == SUCCESSOR_TASK060_REVIEW
        and SUCCESSOR_NEXT_GATE060_REVIEW in str(plan.get("stop_condition"))
    )
    successor_stage060_batch_plan = (
        isinstance(plan, dict)
        and plan.get("stage") == SUCCESSOR_STAGE060
        and plan.get("phase") == SUCCESSOR_TASK060_BATCH
        and plan.get("task") == SUCCESSOR_TASK060_BATCH
        and SUCCESSOR_NEXT_GATE060_BATCH in str(plan.get("stop_condition"))
    )
    successor_stage061_plan = (
        isinstance(plan, dict)
        and plan.get("stage") == SUCCESSOR_STAGE061
        and plan.get("phase") == SUCCESSOR_TASK061
        and plan.get("task") == SUCCESSOR_TASK061
        and SUCCESSOR_NEXT_GATE061 in str(plan.get("stop_condition"))
    )
    successor_stage061_phase2_plan = (
        isinstance(plan, dict)
        and plan.get("stage") == SUCCESSOR_STAGE061
        and plan.get("phase") == SUCCESSOR_TASK061_P2
        and plan.get("task") == SUCCESSOR_TASK061_P2
        and SUCCESSOR_NEXT_GATE061_P2 in str(plan.get("stop_condition"))
    )
    successor_stage061_phase3_plan = (
        isinstance(plan, dict)
        and plan.get("stage") == SUCCESSOR_STAGE061
        and plan.get("phase") == SUCCESSOR_TASK061_P3
        and plan.get("task") == SUCCESSOR_TASK061_P3
        and SUCCESSOR_NEXT_GATE061_P3 in str(plan.get("stop_condition"))
    )
    successor_stage061_phase4_plan = (
        isinstance(plan, dict)
        and plan.get("stage") == SUCCESSOR_STAGE061
        and plan.get("phase") == SUCCESSOR_TASK061_P4
        and plan.get("task") == SUCCESSOR_TASK061_P4
        and SUCCESSOR_NEXT_GATE061_P4 in str(plan.get("stop_condition"))
    )
    successor_stage061_review_plan = (
        isinstance(plan, dict)
        and plan.get("stage") == SUCCESSOR_STAGE061
        and plan.get("phase") == SUCCESSOR_TASK061_REVIEW
        and plan.get("task") == SUCCESSOR_TASK061_REVIEW
        and SUCCESSOR_NEXT_GATE061_REVIEW in str(plan.get("stop_condition"))
    )
    successor_stage062_phase1_plan = (
        isinstance(plan, dict)
        and plan.get("stage") == SUCCESSOR_STAGE062
        and plan.get("phase") == SUCCESSOR_TASK062
        and plan.get("task") == SUCCESSOR_TASK062
        and SUCCESSOR_NEXT_GATE062 in str(plan.get("stop_condition"))
    )
    successor_stage062_phase2_plan = (
        isinstance(plan, dict)
        and plan.get("stage") == SUCCESSOR_STAGE062
        and plan.get("phase") == SUCCESSOR_TASK062_P2
        and plan.get("task") == SUCCESSOR_TASK062_P2
        and SUCCESSOR_NEXT_GATE062_P2 in str(plan.get("stop_condition"))
    )
    successor_stage062_phase3_plan = (
        isinstance(plan, dict)
        and plan.get("stage") == SUCCESSOR_STAGE062
        and plan.get("phase") == SUCCESSOR_TASK062_P3
        and plan.get("task") == SUCCESSOR_TASK062_P3
        and SUCCESSOR_NEXT_GATE062_P3 in str(plan.get("stop_condition"))
    )
    successor_stage062_phase4_plan = (
        isinstance(plan, dict)
        and plan.get("stage") == SUCCESSOR_STAGE062
        and plan.get("phase") == SUCCESSOR_TASK062_P4
        and plan.get("task") == SUCCESSOR_TASK062_P4
        and SUCCESSOR_NEXT_GATE062_P4 in str(plan.get("stop_condition"))
    )
    successor_stage062_review_plan = (
        isinstance(plan, dict)
        and plan.get("stage") == SUCCESSOR_STAGE062
        and plan.get("phase") == SUCCESSOR_PHASE062_REVIEW
        and plan.get("task") == SUCCESSOR_TASK062_REVIEW
        and SUCCESSOR_NEXT_GATE062_REVIEW in str(plan.get("stop_condition"))
    )
    successor_stage063_plan = (
        isinstance(plan, dict)
        and plan.get("stage") == SUCCESSOR_STAGE063
        and plan.get("phase") == SUCCESSOR_TASK063
        and plan.get("task") == SUCCESSOR_TASK063
        and SUCCESSOR_NEXT_GATE063 in str(plan.get("stop_condition"))
    )
    successor_stage063_phase2_plan = (
        isinstance(plan, dict)
        and plan.get("stage") == SUCCESSOR_STAGE063
        and plan.get("phase") == SUCCESSOR_TASK063_P2
        and plan.get("task") == SUCCESSOR_TASK063_P2
        and SUCCESSOR_NEXT_GATE063_P2 in str(plan.get("stop_condition"))
    )
    successor_stage063_phase3_plan = (
        isinstance(plan, dict)
        and plan.get("stage") == SUCCESSOR_STAGE063
        and plan.get("phase") == SUCCESSOR_TASK063_P3
        and plan.get("task") == SUCCESSOR_TASK063_P3
        and SUCCESSOR_NEXT_GATE063_P3 in str(plan.get("stop_condition"))
    )
    successor_stage063_phase4_plan = (
        isinstance(plan, dict)
        and plan.get("stage") == SUCCESSOR_STAGE063
        and plan.get("phase") == SUCCESSOR_TASK063_P4
        and plan.get("task") == SUCCESSOR_TASK063_P4
        and SUCCESSOR_NEXT_GATE063_P4 in str(plan.get("stop_condition"))
    )
    successor_stage063_review_plan = (
        isinstance(plan, dict)
        and plan.get("stage") == SUCCESSOR_STAGE063
        and plan.get("phase") == SUCCESSOR_TASK063_REVIEW
        and plan.get("task") == SUCCESSOR_TASK063_REVIEW
        and SUCCESSOR_NEXT_GATE063_REVIEW in str(plan.get("stop_condition"))
    )
    successor_stage064_phase1_plan = (
        isinstance(plan, dict)
        and plan.get("stage") == SUCCESSOR_STAGE064
        and plan.get("phase") == SUCCESSOR_TASK064
        and plan.get("task") == SUCCESSOR_TASK064
        and SUCCESSOR_NEXT_GATE064 in str(plan.get("stop_condition"))
    )
    successor_stage064_phase2_plan = (
        isinstance(plan, dict)
        and plan.get("stage") == SUCCESSOR_STAGE064
        and plan.get("phase") == SUCCESSOR_TASK064_P2
        and plan.get("task") == SUCCESSOR_TASK064_P2
        and SUCCESSOR_NEXT_GATE064_P2 in str(plan.get("stop_condition"))
    )
    successor_stage064_phase3_plan = (
        isinstance(plan, dict)
        and plan.get("stage") == SUCCESSOR_STAGE064
        and plan.get("phase") == SUCCESSOR_TASK064_P3
        and plan.get("task") == SUCCESSOR_TASK064_P3
        and SUCCESSOR_NEXT_GATE064_P3 in str(plan.get("stop_condition"))
    )
    successor_stage064_phase4_plan = (
        isinstance(plan, dict)
        and plan.get("stage") == SUCCESSOR_STAGE064
        and plan.get("phase") == SUCCESSOR_TASK064_P4
        and plan.get("task") == SUCCESSOR_TASK064_P4
        and SUCCESSOR_NEXT_GATE064_P4 in str(plan.get("stop_condition"))
    )
    successor_stage064_review_plan = (
        isinstance(plan, dict)
        and plan.get("stage") == SUCCESSOR_STAGE064
        and plan.get("phase") == SUCCESSOR_TASK064_REVIEW
        and plan.get("task") == SUCCESSOR_TASK064_REVIEW
        and SUCCESSOR_NEXT_GATE064_REVIEW in str(plan.get("stop_condition"))
    )
    successor_stage065_phase1_plan = (
        isinstance(plan, dict)
        and plan.get("stage") == SUCCESSOR_STAGE065
        and plan.get("phase") == SUCCESSOR_TASK065
        and plan.get("task") == SUCCESSOR_TASK065
        and SUCCESSOR_NEXT_GATE065 in str(plan.get("stop_condition"))
    )
    successor_stage065_phase2_plan = (
        isinstance(plan, dict)
        and plan.get("stage") == SUCCESSOR_STAGE065
        and plan.get("phase") == SUCCESSOR_TASK065_P2
        and plan.get("task") == SUCCESSOR_TASK065_P2
        and SUCCESSOR_NEXT_GATE065_P2 in str(plan.get("stop_condition"))
    )
    successor_stage065_phase3_plan = (
        isinstance(plan, dict)
        and plan.get("stage") == SUCCESSOR_STAGE065
        and plan.get("phase") == SUCCESSOR_TASK065_P3
        and plan.get("task") == SUCCESSOR_TASK065_P3
        and SUCCESSOR_NEXT_GATE065_P3 in str(plan.get("stop_condition"))
    )
    successor_stage065_phase4_plan = (
        isinstance(plan, dict)
        and plan.get("stage") == SUCCESSOR_STAGE065
        and plan.get("phase") == SUCCESSOR_TASK065_P4
        and plan.get("task") == SUCCESSOR_TASK065_P4
        and SUCCESSOR_NEXT_GATE065_P4 in str(plan.get("stop_condition"))
    )
    successor_stage065_review_plan = (
        isinstance(plan, dict)
        and plan.get("stage") == SUCCESSOR_STAGE065
        and plan.get("phase") == SUCCESSOR_TASK065_REVIEW
        and plan.get("task") == SUCCESSOR_TASK065_REVIEW
        and SUCCESSOR_NEXT_GATE065_REVIEW in str(plan.get("stop_condition"))
    )
    successor_stage066_phase1_plan = (
        isinstance(plan, dict)
        and plan.get("stage") == SUCCESSOR_STAGE066
        and plan.get("phase") == SUCCESSOR_TASK066
        and plan.get("task") == SUCCESSOR_TASK066
        and SUCCESSOR_NEXT_GATE066 in str(plan.get("stop_condition"))
    )
    successor_stage066_phase2_plan = (
        isinstance(plan, dict)
        and plan.get("stage") == SUCCESSOR_STAGE066
        and plan.get("phase") == SUCCESSOR_TASK066_P2
        and plan.get("task") == SUCCESSOR_TASK066_P2
        and SUCCESSOR_NEXT_GATE066_P2 in str(plan.get("stop_condition"))
    )
    successor_stage066_phase3_plan = (
        isinstance(plan, dict)
        and plan.get("stage") == SUCCESSOR_STAGE066
        and plan.get("phase") == SUCCESSOR_TASK066_P3
        and plan.get("task") == SUCCESSOR_TASK066_P3
        and SUCCESSOR_NEXT_GATE066_P3 in str(plan.get("stop_condition"))
    )
    successor_stage066_phase4_plan = (
        isinstance(plan, dict)
        and plan.get("stage") == SUCCESSOR_STAGE066
        and plan.get("phase") == SUCCESSOR_TASK066_P4
        and plan.get("task") == SUCCESSOR_TASK066_P4
        and SUCCESSOR_NEXT_GATE066_P4 in str(plan.get("stop_condition"))
    )
    successor_stage066_review_plan = (
        isinstance(plan, dict)
        and plan.get("stage") == SUCCESSOR_STAGE066
        and plan.get("phase") == SUCCESSOR_TASK066_REVIEW
        and plan.get("task") == SUCCESSOR_TASK066_REVIEW
        and SUCCESSOR_NEXT_GATE066_REVIEW in str(plan.get("stop_condition"))
    )
    successor_stage067_phase1_plan = (
        isinstance(plan, dict)
        and plan.get("stage") == SUCCESSOR_STAGE067
        and plan.get("phase") == SUCCESSOR_TASK067
        and plan.get("task") == SUCCESSOR_TASK067
        and SUCCESSOR_NEXT_GATE067 in str(plan.get("stop_condition"))
    )
    successor_stage067_phase2_plan = (
        isinstance(plan, dict)
        and plan.get("stage") == SUCCESSOR_STAGE067
        and plan.get("phase") == SUCCESSOR_TASK067_P2
        and plan.get("task") == SUCCESSOR_TASK067_P2
        and SUCCESSOR_NEXT_GATE067_P2 in str(plan.get("stop_condition"))
    )
    successor_stage067_phase3_plan = (
        isinstance(plan, dict)
        and plan.get("stage") == SUCCESSOR_STAGE067
        and plan.get("phase") == SUCCESSOR_TASK067_P3
        and plan.get("task") == SUCCESSOR_TASK067_P3
        and SUCCESSOR_NEXT_GATE067_P3 in str(plan.get("stop_condition"))
    )
    successor_stage067_phase4_plan = (
        isinstance(plan, dict)
        and plan.get("stage") == SUCCESSOR_STAGE067
        and plan.get("phase") == SUCCESSOR_TASK067_P4
        and plan.get("task") == SUCCESSOR_TASK067_P4
        and SUCCESSOR_NEXT_GATE067_P4 in str(plan.get("stop_condition"))
    )
    successor_stage067_review_plan = (
        isinstance(plan, dict)
        and plan.get("stage") == SUCCESSOR_STAGE067
        and plan.get("phase") == SUCCESSOR_TASK067_REVIEW
        and plan.get("task") == SUCCESSOR_TASK067_REVIEW
        and SUCCESSOR_NEXT_GATE067_REVIEW in str(plan.get("stop_condition"))
    )
    successor_stage068_phase1_plan = (
        isinstance(plan, dict)
        and plan.get("stage") == SUCCESSOR_STAGE068
        and plan.get("phase") == SUCCESSOR_TASK068
        and plan.get("task") == SUCCESSOR_TASK068
        and SUCCESSOR_NEXT_GATE068 in str(plan.get("stop_condition"))
    )
    successor_stage068_phase2_plan = (
        isinstance(plan, dict)
        and plan.get("stage") == SUCCESSOR_STAGE068
        and plan.get("phase") == SUCCESSOR_TASK068_P2
        and plan.get("task") == SUCCESSOR_TASK068_P2
        and SUCCESSOR_NEXT_GATE068_P2 in str(plan.get("stop_condition"))
    )
    successor_stage068_phase3_plan = (
        isinstance(plan, dict)
        and plan.get("stage") == SUCCESSOR_STAGE068
        and plan.get("phase") == SUCCESSOR_TASK068_P3
        and plan.get("task") == SUCCESSOR_TASK068_P3
        and SUCCESSOR_NEXT_GATE068_P3 in str(plan.get("stop_condition"))
    )
    successor_stage068_phase4_plan = (
        isinstance(plan, dict)
        and plan.get("stage") == SUCCESSOR_STAGE068
        and plan.get("phase") == SUCCESSOR_TASK068_P4
        and plan.get("task") == SUCCESSOR_TASK068_P4
        and SUCCESSOR_NEXT_GATE068_P4 in str(plan.get("stop_condition"))
    )
    successor_stage068_review_plan = (
        isinstance(plan, dict)
        and plan.get("stage") == SUCCESSOR_STAGE068
        and plan.get("phase") == SUCCESSOR_TASK068_REVIEW
        and plan.get("task") == SUCCESSOR_TASK068_REVIEW
        and SUCCESSOR_NEXT_GATE068_REVIEW in str(plan.get("stop_condition"))
    )
    successor_stage069_phase1_plan = (
        isinstance(plan, dict)
        and plan.get("stage") == SUCCESSOR_STAGE069
        and plan.get("phase") == SUCCESSOR_TASK069
        and plan.get("task") == SUCCESSOR_TASK069
        and SUCCESSOR_NEXT_GATE069 in str(plan.get("stop_condition"))
    )
    successor_stage069_phase2_plan = (
        isinstance(plan, dict)
        and plan.get("stage") == SUCCESSOR_STAGE069
        and plan.get("phase") == SUCCESSOR_TASK069_P2
        and plan.get("task") == SUCCESSOR_TASK069_P2
        and SUCCESSOR_NEXT_GATE069_P2 in str(plan.get("stop_condition"))
    )
    successor_stage069_phase3_plan = (
        isinstance(plan, dict)
        and plan.get("stage") == SUCCESSOR_STAGE069
        and plan.get("phase") == SUCCESSOR_TASK069_P3
        and plan.get("task") == SUCCESSOR_TASK069_P3
        and SUCCESSOR_NEXT_GATE069_P3 in str(plan.get("stop_condition"))
    )
    successor_stage069_phase4_plan = (
        isinstance(plan, dict)
        and plan.get("stage") == SUCCESSOR_STAGE069
        and plan.get("phase") == SUCCESSOR_TASK069_P4
        and plan.get("task") == SUCCESSOR_TASK069_P4
        and SUCCESSOR_NEXT_GATE069_P4 in str(plan.get("stop_condition"))
    )
    successor_stage069_review_plan = (
        isinstance(plan, dict)
        and plan.get("stage") == SUCCESSOR_STAGE069
        and plan.get("phase") == SUCCESSOR_TASK069_REVIEW
        and plan.get("task") == SUCCESSOR_TASK069_REVIEW
        and SUCCESSOR_NEXT_GATE069_REVIEW in str(plan.get("stop_condition"))
    )
    successor_stage070_phase1_plan = (
        isinstance(plan, dict)
        and plan.get("stage") == SUCCESSOR_STAGE070
        and plan.get("phase")
        in (
            SUCCESSOR_TASK070,
            SUCCESSOR_TASK070_P2,
            SUCCESSOR_TASK070_P3,
            SUCCESSOR_TASK070_P4,
            SUCCESSOR_TASK070_REVIEW,
        )
        and plan.get("task")
        in (
            SUCCESSOR_TASK070,
            SUCCESSOR_TASK070_P2,
            SUCCESSOR_TASK070_P3,
            SUCCESSOR_TASK070_P4,
            SUCCESSOR_TASK070_REVIEW,
        )
        and (
            SUCCESSOR_NEXT_GATE070 in str(plan.get("stop_condition"))
            or SUCCESSOR_NEXT_GATE070_P2 in str(plan.get("stop_condition"))
            or SUCCESSOR_NEXT_GATE070_P3 in str(plan.get("stop_condition"))
            or SUCCESSOR_NEXT_GATE070_P4 in str(plan.get("stop_condition"))
            or SUCCESSOR_NEXT_GATE070_REVIEW in str(plan.get("stop_condition"))
        )
    )
    return {
        "status_projection_exact": (
            successor_status
            or successor_phase2_status
            or successor_phase3_status
            or successor_phase4_status
            or successor_review_status
            or successor_stage052_status
            or successor_stage052_phase2_status
            or successor_stage052_phase3_status
            or successor_stage052_phase4_status
            or successor_stage052_review_status
            or successor_stage053_status
            or successor_stage053_phase2_status
            or successor_stage053_phase3_status
            or successor_stage053_phase4_status
            or successor_stage053_review_status
            or successor_stage054_status
            or successor_stage054_phase2_status
            or successor_stage054_phase3_status
            or successor_stage054_phase4_status
            or successor_stage054_review_status
            or successor_stage055_status
            or successor_stage055_phase2_status
            or successor_stage055_phase3_status
            or successor_stage055_phase4_status
            or successor_stage055_review_status
            or successor_stage056_status
            or successor_stage056_phase2_status
            or successor_stage056_phase3_status
            or successor_stage056_phase4_status
            or successor_stage056_review_status
            or successor_stage057_status
            or successor_stage058_status
            or successor_stage058_phase2_status
            or successor_stage058_phase3_status
            or successor_stage058_phase4_status
            or successor_stage058_review_status
            or successor_stage059_status
            or successor_stage059_phase2_status
            or successor_stage059_phase3_status
            or successor_stage059_phase4_status
            or successor_stage059_review_status
            or successor_stage060_status
            or successor_stage060_phase2_status
            or successor_stage060_phase3_status
            or successor_stage060_phase4_status
            or successor_stage060_review_status
            or successor_stage060_batch_status
            or successor_stage061_status
            or successor_stage061_phase2_status
            or successor_stage061_phase3_status
            or successor_stage061_phase4_status
            or successor_stage061_review_status
            or successor_stage062_phase1_status
            or successor_stage062_phase2_status
            or successor_stage062_phase3_status
            or successor_stage062_phase4_status
            or successor_stage062_review_status
            or successor_stage063_status
            or successor_stage063_phase2_status
            or successor_stage063_phase3_status
            or successor_stage063_phase4_status
            or successor_stage063_review_status
            or successor_stage064_phase1_status
            or successor_stage064_phase2_status
            or successor_stage064_phase3_status
            or successor_stage064_phase4_status
            or successor_stage064_review_status
            or successor_stage065_phase1_status
            or successor_stage065_phase2_status
            or successor_stage065_phase3_status
            or successor_stage065_phase4_status
            or successor_stage065_review_status
            or successor_stage066_phase1_status
            or successor_stage066_phase2_status
            or successor_stage066_phase3_status
            or successor_stage066_phase4_status
            or successor_stage066_review_status
            or successor_stage067_phase1_status
            or successor_stage067_phase2_status
            or successor_stage067_phase3_status
            or successor_stage067_phase4_status
            or successor_stage067_review_status
            or successor_stage068_phase1_status
            or successor_stage068_phase2_status
            or successor_stage068_phase3_status
            or successor_stage068_phase4_status
            or successor_stage068_review_status
            or successor_stage069_phase1_status
            or successor_stage069_phase2_status
            or successor_stage069_phase3_status
            or successor_stage069_phase4_status
            or successor_stage069_review_status
            or successor_stage070_phase1_status
            or (
                isinstance(status, dict)
                and status.get("stage") == SUCCESSOR_STAGE071
                and status.get("phase") == SUCCESSOR_TASK071
                and status.get("task") == SUCCESSOR_TASK071
                and status.get("next_gate") == SUCCESSOR_NEXT_GATE071
                and status.get("runtime_enabled") is False
                and status.get("push_allowed") is False
            )
            or (
                isinstance(status, dict)
                and status.get("stage") == "IDS-STAGE075"
                and status.get("phase") == "IDS-V0_1-STAGE075-P1"
                and status.get("task") == "IDS-V0_1-STAGE075-P1"
                and status.get("next_gate") == "IDS-STAGE075-P2-GATE"
                and status.get("runtime_enabled") is False
                and status.get("push_allowed") is False
            )
            or (
                isinstance(status, dict)
                and status.get("stage") == "IDS-STAGE075"
                and status.get("phase") == "IDS-V0_1-STAGE075-REVIEW"
                and status.get("task") == "IDS-V0_1-STAGE075-REVIEW"
                and status.get("next_gate") == "IDS-STAGE076-P1-GATE"
                and status.get("runtime_enabled") is False
                and status.get("push_allowed") is False
            )
            or (
                isinstance(status, dict)
                and status.get("stage") == "IDS-STAGE076"
                and status.get("phase") == "IDS-V0_1-STAGE076-P1"
                and status.get("task") == "IDS-V0_1-STAGE076-P1"
                and status.get("next_gate") == "IDS-STAGE076-P2-GATE"
                and status.get("runtime_enabled") is False
                and status.get("push_allowed") is False
            )
            or (
                isinstance(status, dict)
                and status.get("stage") == "IDS-STAGE077"
                and status.get("phase") == "IDS-V0_1-STAGE077-P1"
                and status.get("task") == "IDS-V0_1-STAGE077-P1"
                and status.get("next_gate") == "IDS-STAGE077-P2-GATE"
                and status.get("runtime_enabled") is False
                and status.get("push_allowed") is False
            )
            or (
                isinstance(status, dict)
                and status.get("stage") == "IDS-STAGE078"
                and status.get("phase") == "IDS-V0_1-STAGE078-P1"
                and status.get("task") == "IDS-V0_1-STAGE078-P1"
                and status.get("next_gate") == "IDS-STAGE078-P2-GATE"
                and status.get("runtime_enabled") is False
                and status.get("push_allowed") is False
            )
            or (
                isinstance(status, dict)
                and status.get("stage") == "IDS-STAGE078"
                and status.get("phase") == "IDS-STAGE078-REVIEW"
                and status.get("task") == "IDS-V0_1-STAGE078-REVIEW"
                and status.get("next_gate") == "IDS-STAGE079-P1-GATE"
                and status.get("runtime_enabled") is False
                and status.get("push_allowed") is False
            )
            or (
                isinstance(status, dict)
                and status.get("stage") == "IDS-STAGE078"
                and status.get("phase") == "IDS-V0_1-STAGE078-P4"
                and status.get("task") == "IDS-V0_1-STAGE078-P4"
                and status.get("next_gate") == "IDS-STAGE078-REVIEW-GATE"
                and status.get("runtime_enabled") is False
                and status.get("push_allowed") is False
            )
            or (
                isinstance(status, dict)
                and status.get("stage") == "IDS-STAGE078"
                and status.get("phase") == "IDS-V0_1-STAGE078-P2"
                and status.get("task") == "IDS-V0_1-STAGE078-P2"
                and status.get("next_gate") == "IDS-STAGE078-P3-GATE"
                and status.get("runtime_enabled") is False
                and status.get("push_allowed") is False
            )
            or (
                isinstance(status, dict)
                and status.get("stage") == "IDS-STAGE078"
                and status.get("phase") == "IDS-V0_1-STAGE078-P3"
                and status.get("task") == "IDS-V0_1-STAGE078-P3"
                and status.get("next_gate") == "IDS-STAGE078-P4-GATE"
                and status.get("runtime_enabled") is False
                and status.get("push_allowed") is False
            )
            or (
                isinstance(status, dict)
                and status.get("stage") == "IDS-STAGE077"
                and status.get("phase") == "IDS-V0_1-STAGE077-P3"
                and status.get("task") == "IDS-V0_1-STAGE077-P3"
                and status.get("next_gate") == "IDS-STAGE077-P4-GATE"
                and status.get("runtime_enabled") is False
                and status.get("push_allowed") is False
            )
            or (
                isinstance(status, dict)
                and status.get("stage") == "IDS-STAGE077"
                and status.get("phase") == "IDS-V0_1-STAGE077-P4"
                and status.get("task") == "IDS-V0_1-STAGE077-P4"
                and status.get("next_gate") == "IDS-STAGE077-REVIEW-GATE"
                and status.get("runtime_enabled") is False
                and status.get("push_allowed") is False
            )
            or (
                isinstance(status, dict)
                and status.get("stage") == "IDS-STAGE077"
                and status.get("phase") == "IDS-V0_1-STAGE077-REVIEW"
                and status.get("task") == "IDS-V0_1-STAGE077-REVIEW"
                and status.get("next_gate") == "IDS-STAGE078-P1-GATE"
                and status.get("runtime_enabled") is False
                and status.get("push_allowed") is False
            )
            or (
                isinstance(status, dict)
                and status.get("stage") == "IDS-STAGE077"
                and status.get("phase") == "IDS-V0_1-STAGE077-P2"
                and status.get("task") == "IDS-V0_1-STAGE077-P2"
                and status.get("next_gate") == "IDS-STAGE077-P3-GATE"
                and status.get("runtime_enabled") is False
                and status.get("push_allowed") is False
            )
            or (
                isinstance(status, dict)
                and status.get("stage") == "IDS-STAGE076"
                and status.get("phase") == "IDS-V0_1-STAGE076-REVIEW"
                and status.get("task") == "IDS-V0_1-STAGE076-REVIEW"
                and status.get("next_gate") == "IDS-STAGE077-P1-GATE"
                and status.get("runtime_enabled") is False
                and status.get("push_allowed") is False
            )
            or (
                isinstance(status, dict)
                and status.get("stage") == "IDS-STAGE076"
                and status.get("phase") == "IDS-V0_1-STAGE076-P3"
                and status.get("task") == "IDS-V0_1-STAGE076-P3"
                and status.get("next_gate") == "IDS-STAGE076-P4-GATE"
                and status.get("runtime_enabled") is False
                and status.get("push_allowed") is False
            )
            or (
                isinstance(status, dict)
                and status.get("stage") == "IDS-STAGE076"
                and status.get("phase") == "IDS-V0_1-STAGE076-P4"
                and status.get("task") == "IDS-V0_1-STAGE076-P4"
                and status.get("next_gate") == "IDS-STAGE076-REVIEW-GATE"
                and status.get("runtime_enabled") is False
                and status.get("push_allowed") is False
            )
            or (
                isinstance(status, dict)
                and status.get("stage") == "IDS-STAGE076"
                and status.get("phase") == "IDS-V0_1-STAGE076-P2"
                and status.get("task") == "IDS-V0_1-STAGE076-P2"
                and status.get("next_gate") == "IDS-STAGE076-P3-GATE"
                and status.get("runtime_enabled") is False
                and status.get("push_allowed") is False
            )
            or (
                isinstance(status, dict)
                and status.get("stage") == "IDS-STAGE075"
                and status.get("phase") == "IDS-V0_1-STAGE075-P4"
                and status.get("task") == "IDS-V0_1-STAGE075-P4"
                and status.get("next_gate") == "IDS-STAGE075-REVIEW-GATE"
                and status.get("runtime_enabled") is False
                and status.get("push_allowed") is False
            )
            or (
                isinstance(status, dict)
                and status.get("stage") == "IDS-STAGE075"
                and status.get("phase") == "IDS-V0_1-STAGE075-P3"
                and status.get("task") == "IDS-V0_1-STAGE075-P3"
                and status.get("next_gate") == "IDS-STAGE075-P4-GATE"
                and status.get("runtime_enabled") is False
                and status.get("push_allowed") is False
            )
            or (
                isinstance(status, dict)
                and status.get("stage") == "IDS-STAGE075"
                and status.get("phase") == "IDS-V0_1-STAGE075-P2"
                and status.get("task") == "IDS-V0_1-STAGE075-P2"
                and status.get("next_gate") == "IDS-STAGE075-P3-GATE"
                and status.get("runtime_enabled") is False
                and status.get("push_allowed") is False
            )
            or (
                isinstance(status, dict)
                and status.get("stage") == SUCCESSOR_STAGE071
                and status.get("phase") == SUCCESSOR_TASK071_P4
                and status.get("task") == SUCCESSOR_TASK071_P4
                and status.get("next_gate") == SUCCESSOR_NEXT_GATE071_P4
                and status.get("runtime_enabled") is False
                and status.get("push_allowed") is False
            )
            or (
                isinstance(status, dict)
                and status.get("stage") == SUCCESSOR_STAGE071
                and status.get("phase") == SUCCESSOR_TASK071_REVIEW
                and status.get("task") == SUCCESSOR_TASK071_REVIEW
                and status.get("next_gate") == SUCCESSOR_NEXT_GATE071_REVIEW
                and status.get("runtime_enabled") is False
                and status.get("push_allowed") is False
            )
            or (
                isinstance(status, dict)
                and status.get("stage") == SUCCESSOR_STAGE072
                and status.get("phase") == SUCCESSOR_TASK072_P1
                and status.get("task") == SUCCESSOR_TASK072_P1
                and status.get("next_gate") == SUCCESSOR_NEXT_GATE072_P1
                and status.get("runtime_enabled") is False
                and status.get("push_allowed") is False
            )
            or (
                isinstance(status, dict)
                and status.get("stage") == SUCCESSOR_STAGE072
                and status.get("phase") == SUCCESSOR_TASK072_P2
                and status.get("task") == SUCCESSOR_TASK072_P2
                and status.get("next_gate") == SUCCESSOR_NEXT_GATE072_P2
                and status.get("runtime_enabled") is False
                and status.get("push_allowed") is False
            )
            or (
                isinstance(status, dict)
                and status.get("stage") == SUCCESSOR_STAGE072
                and status.get("phase") == SUCCESSOR_TASK072_P3
                and status.get("task") == SUCCESSOR_TASK072_P3
                and status.get("next_gate") == SUCCESSOR_NEXT_GATE072_P3
                and status.get("runtime_enabled") is False
                and status.get("push_allowed") is False
            )
            or (
                isinstance(status, dict)
                and status.get("stage") == SUCCESSOR_STAGE072
                and status.get("phase") == SUCCESSOR_TASK072_P4
                and status.get("task") == SUCCESSOR_TASK072_P4
                and status.get("next_gate") == SUCCESSOR_NEXT_GATE072_P4
                and status.get("runtime_enabled") is False
                and status.get("push_allowed") is False
            )
            or (
                isinstance(status, dict)
                and status.get("stage") == SUCCESSOR_STAGE072
                and status.get("phase") == SUCCESSOR_TASK072_REVIEW
                and status.get("task") == SUCCESSOR_TASK072_REVIEW
                and status.get("next_gate") == SUCCESSOR_NEXT_GATE072_REVIEW
                and status.get("runtime_enabled") is False
                and status.get("push_allowed") is False
            )
            or (
                isinstance(status, dict)
                and status.get("stage") == SUCCESSOR_STAGE071
                and status.get("phase") == SUCCESSOR_TASK071_P2
                and status.get("task") == SUCCESSOR_TASK071_P2
                and status.get("next_gate") == SUCCESSOR_NEXT_GATE071_P2
                and status.get("runtime_enabled") is False
                and status.get("push_allowed") is False
            )
            or (
                isinstance(status, dict)
                and status.get("stage") == SUCCESSOR_STAGE071
                and status.get("phase") == SUCCESSOR_TASK071_P3
                and status.get("task") == SUCCESSOR_TASK071_P3
                and status.get("next_gate") == SUCCESSOR_NEXT_GATE071_P3
                and status.get("runtime_enabled") is False
                and status.get("push_allowed") is False
            )
            or (
                isinstance(status, dict)
                and status.get("phase") == TASK_ID
                and status.get("task") == TASK_ID
                and status.get("next_gate") == NEXT_GATE
                and status.get("runtime_enabled") is False
                and status.get("push_allowed") is False
            )
            or (
                isinstance(status, dict)
                and status.get("stage") == "IDS-STAGE073"
                and status.get("phase") == "IDS-V0_1-STAGE073-P1"
                and status.get("task") == "IDS-V0_1-STAGE073-P1"
                and status.get("next_gate") == "IDS-STAGE073-P2-GATE"
                and status.get("runtime_enabled") is False
                and status.get("push_allowed") is False
            )
            or (
                isinstance(status, dict)
                and status.get("stage") == "IDS-STAGE073"
                and status.get("phase") == "IDS-V0_1-STAGE073-P2"
                and status.get("task") == "IDS-V0_1-STAGE073-P2"
                and status.get("next_gate") == "IDS-STAGE073-P3-GATE"
                and status.get("runtime_enabled") is False
                and status.get("push_allowed") is False
            )
            or (
                isinstance(status, dict)
                and status.get("stage") == "IDS-STAGE073"
                and status.get("phase") == "IDS-V0_1-STAGE073-P3"
                and status.get("task") == "IDS-V0_1-STAGE073-P3"
                and status.get("next_gate") == "IDS-STAGE073-P4-GATE"
                and status.get("runtime_enabled") is False
                and status.get("push_allowed") is False
            )
            or (
                isinstance(status, dict)
                and status.get("stage") == "IDS-STAGE073"
                and status.get("phase") == "IDS-V0_1-STAGE073-P4"
                and status.get("task") == "IDS-V0_1-STAGE073-P4"
                and status.get("next_gate") == "IDS-STAGE073-REVIEW-GATE"
                and status.get("runtime_enabled") is False
                and status.get("push_allowed") is False
            )
            or (
                isinstance(status, dict)
                and status.get("stage") == "IDS-STAGE073"
                and status.get("phase") == "IDS-V0_1-STAGE073-REVIEW"
                and status.get("task") == "IDS-V0_1-STAGE073-REVIEW"
                and status.get("next_gate") == "IDS-STAGE074-P1-GATE"
                and status.get("runtime_enabled") is False
                and status.get("push_allowed") is False
            )
            or (
                isinstance(status, dict)
                and status.get("stage") == "IDS-STAGE074"
                and status.get("phase") == "IDS-V0_1-STAGE074-P1"
                and status.get("task") == "IDS-V0_1-STAGE074-P1"
                and status.get("next_gate") == "IDS-STAGE074-P2-GATE"
                and status.get("runtime_enabled") is False
                and status.get("push_allowed") is False
            )
            or (
                isinstance(status, dict)
                and status.get("stage") == "IDS-STAGE074"
                and status.get("phase") == "IDS-V0_1-STAGE074-P2"
                and status.get("task") == "IDS-V0_1-STAGE074-P2"
                and status.get("next_gate") == "IDS-STAGE074-P3-GATE"
                and status.get("runtime_enabled") is False
                and status.get("push_allowed") is False
            )
            or (
                isinstance(status, dict)
                and status.get("stage") == "IDS-STAGE074"
                and status.get("phase") == "IDS-V0_1-STAGE074-P3"
                and status.get("task") == "IDS-V0_1-STAGE074-P3"
                and status.get("next_gate") == "IDS-STAGE074-P4-GATE"
                and status.get("runtime_enabled") is False
                and status.get("push_allowed") is False
            )
            or (
                isinstance(status, dict)
                and status.get("stage") == "IDS-STAGE074"
                and status.get("phase") == "IDS-V0_1-STAGE074-P4"
                and status.get("task") == "IDS-V0_1-STAGE074-P4"
                and status.get("next_gate") == "IDS-STAGE074-REVIEW-GATE"
                and status.get("runtime_enabled") is False
                and status.get("push_allowed") is False
            )
            or (
                isinstance(status, dict)
                and status.get("stage") == "IDS-STAGE074"
                and status.get("phase") == "IDS-V0_1-STAGE074-REVIEW"
                and status.get("task") == "IDS-V0_1-STAGE074-REVIEW"
                and status.get("next_gate") == "IDS-STAGE075-P1-GATE"
                and status.get("runtime_enabled") is False
                and status.get("push_allowed") is False
            )
            or (
                isinstance(status, dict)
                and status.get("stage") == "IDS-STAGE079"
                and status.get("phase") == "IDS-V0_1-STAGE079-P1"
                and status.get("task") == "IDS-V0_1-STAGE079-P1"
                and status.get("next_gate") == "IDS-STAGE079-P2-GATE"
                and status.get("runtime_enabled") is False
                and status.get("push_allowed") is False
            )
            or (
                isinstance(status, dict)
                and status.get("stage") == "IDS-STAGE080"
                and status.get("phase") == "IDS-V0_1-STAGE080-P1"
                and status.get("task") == "IDS-V0_1-STAGE080-P1"
                and status.get("next_gate") == "IDS-STAGE080-P2-GATE"
                and status.get("runtime_enabled") is False
                and status.get("push_allowed") is False
            )
            or (
                isinstance(status, dict)
                and status.get("stage") == "IDS-STAGE080"
                and status.get("phase") == "IDS-V0_1-STAGE080-P4"
                and status.get("task") == "IDS-V0_1-STAGE080-P4"
                and status.get("next_gate") == "IDS-STAGE080-REVIEW-GATE"
                and status.get("runtime_enabled") is False
                and status.get("push_allowed") is False
            )
            or (
                isinstance(status, dict)
                and status.get("stage") == "IDS-STAGE080"
                and status.get("phase") == "IDS-STAGE080-REVIEW"
                and status.get("task") == "IDS-V0_1-STAGE080-REVIEW"
                and status.get("next_gate") == "IDS-STAGE081-P1-GATE"
                and status.get("runtime_enabled") is False
                and status.get("push_allowed") is False
            )
            or (
                isinstance(status, dict)
                and status.get("stage") == "IDS-STAGE081"
                and status.get("phase") == "IDS-STAGE081-P1"
                and status.get("task") == "IDS-V0_1-STAGE081-P1"
                and status.get("next_gate") == "IDS-STAGE081-P2-GATE"
                and status.get("runtime_enabled") is False
                and status.get("push_allowed") is False
            )
            or (
                isinstance(status, dict)
                and status.get("stage") == "IDS-STAGE081"
                and status.get("phase") == "IDS-STAGE081-REVIEW"
                and status.get("task") == "IDS-V0_1-STAGE081-REVIEW"
                and status.get("next_gate") == "IDS-STAGE082-P1-GATE"
                and status.get("runtime_enabled") is False
                and status.get("push_allowed") is False
            )
            or (
                isinstance(status, dict)
                and status.get("stage") == "IDS-STAGE082"
                and status.get("phase") == "IDS-STAGE082-P1"
                and status.get("task") == "IDS-V0_1-STAGE082-P1"
                and status.get("next_gate") == "IDS-STAGE082-P2-GATE"
                and status.get("runtime_enabled") is False
                and status.get("push_allowed") is False
            )
            or (
                isinstance(status, dict)
                and status.get("stage") == "IDS-STAGE082"
                and status.get("phase") == "IDS-STAGE082-P2"
                and status.get("task") == "IDS-V0_1-STAGE082-P2"
                and status.get("next_gate") == "IDS-STAGE082-P3-GATE"
                and status.get("runtime_enabled") is False
                and status.get("push_allowed") is False
            )
            or (
                isinstance(status, dict)
                and status.get("stage") == "IDS-STAGE082"
                and status.get("phase") == "IDS-STAGE082-P3"
                and status.get("task") == "IDS-V0_1-STAGE082-P3"
                and status.get("next_gate") == "IDS-STAGE082-P4-GATE"
                and status.get("runtime_enabled") is False
                and status.get("push_allowed") is False
            )
            or (
                isinstance(status, dict)
                and status.get("stage") == "IDS-STAGE082"
                and status.get("phase") == "IDS-STAGE082-P4"
                and status.get("task") == "IDS-V0_1-STAGE082-P4"
                and status.get("next_gate") == "IDS-STAGE082-REVIEW-GATE"
                and status.get("runtime_enabled") is False
                and status.get("push_allowed") is False
            )
            or (
                isinstance(status, dict)
                and status.get("stage") == "IDS-STAGE082"
                and status.get("phase") == "IDS-STAGE082-REVIEW"
                and status.get("task") == "IDS-V0_1-STAGE082-REVIEW"
                and status.get("next_gate") == "IDS-STAGE083-P1-GATE"
                and status.get("runtime_enabled") is False
                and status.get("push_allowed") is False
            )
            or (
                isinstance(status, dict)
                and status.get("stage") == "IDS-STAGE083"
                and status.get("phase") == "IDS-STAGE083-P1"
                and status.get("task") == "IDS-V0_1-STAGE083-P1"
                and status.get("next_gate") == "IDS-STAGE083-P2-GATE"
                and status.get("runtime_enabled") is False
                and status.get("push_allowed") is False
            )
            or (
                isinstance(status, dict)
                and status.get("stage") == "IDS-STAGE083"
                and status.get("phase") == "IDS-STAGE083-P3"
                and status.get("task") == "IDS-V0_1-STAGE083-P3"
                and status.get("next_gate") == "IDS-STAGE083-P4-GATE"
                and status.get("runtime_enabled") is False
                and status.get("push_allowed") is False
            )
            or (
                isinstance(status, dict)
                and status.get("stage") == "IDS-STAGE083"
                and status.get("phase") == "IDS-STAGE083-P4"
                and status.get("task") == "IDS-V0_1-STAGE083-P4"
                and status.get("next_gate") == "IDS-STAGE083-REVIEW-GATE"
                and status.get("runtime_enabled") is False
                and status.get("push_allowed") is False
            )
            or (
                isinstance(status, dict)
                and status.get("stage") == "IDS-STAGE083"
                and status.get("phase") == "IDS-STAGE083-REVIEW"
                and status.get("task") == "IDS-V0_1-STAGE083-REVIEW"
                and status.get("next_gate") == "IDS-STAGE084-P1-GATE"
                and status.get("runtime_enabled") is False
                and status.get("push_allowed") is False
            )
            or (
                isinstance(status, dict)
                and status.get("stage") == "IDS-STAGE084"
                and status.get("phase") == "IDS-STAGE084-P1"
                and status.get("task") == "IDS-V0_1-STAGE084-P1"
                and status.get("next_gate") == "IDS-STAGE084-P2-GATE"
                and status.get("runtime_enabled") is False
                and status.get("push_allowed") is False
            )
            or (
                isinstance(status, dict)
                and status.get("stage") == "IDS-STAGE085"
                and status.get("phase") == "IDS-STAGE085-P1"
                and status.get("task") == "IDS-V0_1-STAGE085-P1"
                and status.get("next_gate") == "IDS-STAGE085-P2-GATE"
                and status.get("runtime_enabled") is False
                and status.get("push_allowed") is False
            )
            or (
                isinstance(status, dict)
                and status.get("stage") == "IDS-STAGE086"
                and status.get("phase") == "IDS-STAGE086-P1"
                and status.get("task") == "IDS-V0_1-STAGE086-P1"
                and status.get("next_gate") == "IDS-STAGE086-P2-GATE"
                and status.get("runtime_enabled") is False
                and status.get("push_allowed") is False
            )
            or (
                isinstance(status, dict)
                and status.get("stage") == "IDS-STAGE087"
                and status.get("phase") == "IDS-STAGE087-P1"
                and status.get("task") == "IDS-V0_1-STAGE087-P1"
                and status.get("next_gate") == "IDS-STAGE087-P2-GATE"
                and status.get("runtime_enabled") is False
                and status.get("push_allowed") is False
            )
            or (
                isinstance(status, dict)
                and status.get("stage") == "IDS-STAGE087"
                and status.get("phase") == "IDS-STAGE087-REVIEW"
                and status.get("task") == "IDS-V0_1-STAGE087-REVIEW"
                and status.get("next_gate") == "IDS-STAGE088-P1-GATE"
                and status.get("runtime_enabled") is False
                and status.get("push_allowed") is False
            )
            or (
                isinstance(status, dict)
                and status.get("stage") == "IDS-STAGE088"
                and status.get("phase") == "IDS-STAGE088-P1"
                and status.get("task") == "IDS-V0_1-STAGE088-P1"
                and status.get("next_gate") == "IDS-STAGE088-P2-GATE"
                and status.get("runtime_enabled") is False
                and status.get("push_allowed") is False
            )
            or (
                isinstance(status, dict)
                and status.get("stage") == "IDS-STAGE088"
                and status.get("phase") == "IDS-STAGE088-P2"
                and status.get("task") == "IDS-V0_1-STAGE088-P2"
                and status.get("next_gate") == "IDS-STAGE088-P3-GATE"
                and status.get("runtime_enabled") is False
                and status.get("push_allowed") is False
            )
            or (
                isinstance(status, dict)
                and status.get("stage") == "IDS-STAGE088"
                and status.get("phase") == "IDS-STAGE088-P3"
                and status.get("task") == "IDS-V0_1-STAGE088-P3"
                and status.get("next_gate") == "IDS-STAGE088-P4-GATE"
                and status.get("runtime_enabled") is False
                and status.get("push_allowed") is False
            )
            or (
                isinstance(status, dict)
                and status.get("stage") == "IDS-STAGE088"
                and status.get("phase") == "IDS-STAGE088-P4"
                and status.get("task") == "IDS-V0_1-STAGE088-P4"
                and status.get("next_gate") == "IDS-STAGE088-REVIEW-GATE"
                and status.get("runtime_enabled") is False
                and status.get("push_allowed") is False
            )
            or (
                isinstance(status, dict)
                and status.get("stage") == "IDS-STAGE088"
                and status.get("phase") == "IDS-STAGE088-REVIEW"
                and status.get("task") == "IDS-V0_1-STAGE088-REVIEW"
                and status.get("next_gate") == "IDS-STAGE089-P1-GATE"
                and status.get("runtime_enabled") is False
                and status.get("push_allowed") is False
            )
            or (
                isinstance(status, dict)
                and status.get("stage") == "IDS-STAGE089"
                and status.get("phase") == "IDS-STAGE089-P1"
                and status.get("task") == "IDS-V0_1-STAGE089-P1"
                and status.get("next_gate") == "IDS-STAGE089-P2-GATE"
                and status.get("runtime_enabled") is False
                and status.get("push_allowed") is False
            )
            or (
                isinstance(status, dict)
                and status.get("stage") == "IDS-STAGE089"
                and status.get("phase") == "IDS-STAGE089-P3"
                and status.get("task") == "IDS-V0_1-STAGE089-P3"
                and status.get("next_gate") == "IDS-STAGE089-P4-GATE"
                and status.get("runtime_enabled") is False
                and status.get("push_allowed") is False
            )
            or (
                isinstance(status, dict)
                and status.get("stage") == "IDS-STAGE089"
                and status.get("phase") == "IDS-STAGE089-P4"
                and status.get("task") == "IDS-V0_1-STAGE089-P4"
                and status.get("next_gate") == "IDS-STAGE089-REVIEW-GATE"
                and status.get("runtime_enabled") is False
                and status.get("push_allowed") is False
            )
            or (
                isinstance(status, dict)
                and status.get("stage") == "IDS-STAGE089"
                and status.get("phase") == "IDS-STAGE089-REVIEW"
                and status.get("task") == "IDS-V0_1-STAGE089-REVIEW"
                and status.get("next_gate") == "IDS-STAGE090-P1-GATE"
                and status.get("runtime_enabled") is False
                and status.get("push_allowed") is False
            )
            or (
                isinstance(status, dict)
                and status.get("stage") == "IDS-STAGE090"
                and status.get("phase") == "IDS-STAGE090-P1"
                and status.get("task") == "IDS-V0_1-STAGE090-P1"
                and status.get("next_gate") == "IDS-STAGE090-P2-GATE"
                and status.get("runtime_enabled") is False
                and status.get("push_allowed") is False
            )
            or (
                isinstance(status, dict)
                and status.get("stage") == "IDS-STAGE091"
                and status.get("phase") == "IDS-STAGE091-P1"
                and status.get("task") == "IDS-V0_1-STAGE091-P1"
                and status.get("next_gate") == "IDS-STAGE091-P2-GATE"
                and status.get("runtime_enabled") is False
                and status.get("push_allowed") is False
            )
            or (
                isinstance(status, dict)
                and status.get("stage") == "IDS-STAGE092"
                and status.get("phase") == "IDS-STAGE092-P1"
                and status.get("task") == "IDS-V0_1-STAGE092-P1"
                and status.get("next_gate") == "IDS-STAGE092-P2-GATE"
                and status.get("runtime_enabled") is False
                and status.get("push_allowed") is False
            )
            or (
                isinstance(status, dict)
                and status.get("stage") == "IDS-STAGE093"
                and status.get("phase") == "IDS-STAGE093-P1"
                and status.get("task") == "IDS-V0_1-STAGE093-P1"
                and status.get("next_gate") == "IDS-STAGE093-P2-GATE"
                and status.get("runtime_enabled") is False
                and status.get("push_allowed") is False
            )
            or (
                isinstance(status, dict)
                and status.get("stage") == "IDS-STAGE093"
                and status.get("phase") == "IDS-STAGE093-P2"
                and status.get("task") == "IDS-V0_1-STAGE093-P2"
                and status.get("next_gate") == "IDS-STAGE093-P3-GATE"
                and status.get("runtime_enabled") is False
                and status.get("push_allowed") is False
            )
            or (
                isinstance(status, dict)
                and status.get("stage") == "IDS-STAGE093"
                and status.get("phase") == "IDS-STAGE093-P3"
                and status.get("task") == "IDS-V0_1-STAGE093-P3"
                and status.get("next_gate") == "IDS-STAGE093-P4-GATE"
                and status.get("runtime_enabled") is False
                and status.get("push_allowed") is False
            )
            or (
                isinstance(status, dict)
                and status.get("stage") == "IDS-STAGE093"
                and status.get("phase") == "IDS-STAGE093-P4"
                and status.get("task") == "IDS-V0_1-STAGE093-P4"
                and status.get("next_gate") == "IDS-STAGE093-REVIEW-GATE"
                and status.get("runtime_enabled") is False
                and status.get("push_allowed") is False
            )
            or (
                isinstance(status, dict)
                and status.get("stage") == "IDS-STAGE093"
                and status.get("phase") == "IDS-STAGE093-REVIEW"
                and status.get("task") == "IDS-V0_1-STAGE093-REVIEW"
                and status.get("next_gate") == "IDS-STAGE094-P1-GATE"
                and status.get("runtime_enabled") is False
                and status.get("push_allowed") is False
            )
            or (
                isinstance(status, dict)
                and status.get("stage") == "IDS-STAGE094"
                and status.get("phase") == "IDS-STAGE094-P1"
                and status.get("task") == "IDS-V0_1-STAGE094-P1"
                and status.get("next_gate") == "IDS-STAGE094-P2-GATE"
                and status.get("runtime_enabled") is False
                and status.get("push_allowed") is False
            )
            or (
                isinstance(status, dict)
                and status.get("stage") == "IDS-STAGE092"
                and status.get("phase") == "IDS-STAGE092-P4"
                and status.get("task") == "IDS-V0_1-STAGE092-P4"
                and status.get("next_gate") == "IDS-STAGE092-REVIEW-GATE"
                and status.get("runtime_enabled") is False
                and status.get("push_allowed") is False
            )
            or (
                isinstance(status, dict)
                and status.get("stage") == "IDS-STAGE092"
                and status.get("phase") == "IDS-STAGE092-REVIEW"
                and status.get("task") == "IDS-V0_1-STAGE092-REVIEW"
                and status.get("next_gate") == "IDS-STAGE093-P1-GATE"
                and status.get("runtime_enabled") is False
                and status.get("push_allowed") is False
            )
            or (
                isinstance(status, dict)
                and status.get("stage") == "IDS-STAGE092"
                and status.get("phase") == "IDS-STAGE092-P2"
                and status.get("task") == "IDS-V0_1-STAGE092-P2"
                and status.get("next_gate") == "IDS-STAGE092-P3-GATE"
                and status.get("runtime_enabled") is False
                and status.get("push_allowed") is False
            )
            or (
                isinstance(status, dict)
                and status.get("stage") == "IDS-STAGE092"
                and status.get("phase") == "IDS-STAGE092-P3"
                and status.get("task") == "IDS-V0_1-STAGE092-P3"
                and status.get("next_gate") == "IDS-STAGE092-P4-GATE"
                and status.get("runtime_enabled") is False
                and status.get("push_allowed") is False
            )
            or (
                isinstance(status, dict)
                and status.get("stage") == "IDS-STAGE091"
                and status.get("phase") == "IDS-STAGE091-REVIEW"
                and status.get("task") == "IDS-V0_1-STAGE091-REVIEW"
                and status.get("next_gate") == "IDS-STAGE092-P1-GATE"
                and status.get("runtime_enabled") is False
                and status.get("push_allowed") is False
            )
            or (
                isinstance(status, dict)
                and status.get("stage") == "IDS-STAGE091"
                and status.get("phase") == "IDS-STAGE091-P3"
                and status.get("task") == "IDS-V0_1-STAGE091-P3"
                and status.get("next_gate") == "IDS-STAGE091-P4-GATE"
                and status.get("runtime_enabled") is False
                and status.get("push_allowed") is False
            )
            or (
                isinstance(status, dict)
                and status.get("stage") == "IDS-STAGE091"
                and status.get("phase") == "IDS-STAGE091-P4"
                and status.get("task") == "IDS-V0_1-STAGE091-P4"
                and status.get("next_gate") == "IDS-STAGE091-REVIEW-GATE"
                and status.get("runtime_enabled") is False
                and status.get("push_allowed") is False
            )
            or (
                isinstance(status, dict)
                and status.get("stage") == "IDS-STAGE091"
                and status.get("phase") == "IDS-STAGE091-P2"
                and status.get("task") == "IDS-V0_1-STAGE091-P2"
                and status.get("next_gate") == "IDS-STAGE091-P3-GATE"
                and status.get("runtime_enabled") is False
                and status.get("push_allowed") is False
            )
            or (
                isinstance(status, dict)
                and status.get("stage") == "IDS-STAGE090"
                and status.get("phase") == "IDS-STAGE090-REVIEW"
                and status.get("task") == "IDS-V0_1-STAGE090-REVIEW"
                and status.get("next_gate") == "IDS-STAGE091-P1-GATE"
                and status.get("runtime_enabled") is False
                and status.get("push_allowed") is False
            )
            or (
                isinstance(status, dict)
                and status.get("stage") == "IDS-STAGE090"
                and status.get("phase") == "IDS-STAGE090-P4"
                and status.get("task") == "IDS-V0_1-STAGE090-P4"
                and status.get("next_gate") == "IDS-STAGE090-REVIEW-GATE"
                and status.get("runtime_enabled") is False
                and status.get("push_allowed") is False
            )
            or (
                isinstance(status, dict)
                and status.get("stage") == "IDS-STAGE090"
                and status.get("phase") == "IDS-STAGE090-P2"
                and status.get("task") == "IDS-V0_1-STAGE090-P2"
                and status.get("next_gate") == "IDS-STAGE090-P3-GATE"
                and status.get("runtime_enabled") is False
                and status.get("push_allowed") is False
            )
            or (
                isinstance(status, dict)
                and status.get("stage") == "IDS-STAGE090"
                and status.get("phase") == "IDS-STAGE090-P3"
                and status.get("task") == "IDS-V0_1-STAGE090-P3"
                and status.get("next_gate") == "IDS-STAGE090-P4-GATE"
                and status.get("runtime_enabled") is False
                and status.get("push_allowed") is False
            )
            or (
                isinstance(status, dict)
                and status.get("stage") == "IDS-STAGE089"
                and status.get("phase") == "IDS-STAGE089-P2"
                and status.get("task") == "IDS-V0_1-STAGE089-P2"
                and status.get("next_gate") == "IDS-STAGE089-P3-GATE"
                and status.get("runtime_enabled") is False
                and status.get("push_allowed") is False
            )
            or (
                isinstance(status, dict)
                and status.get("stage") == "IDS-STAGE087"
                and status.get("phase") == "IDS-STAGE087-P4"
                and status.get("task") == "IDS-V0_1-STAGE087-P4"
                and status.get("next_gate") == "IDS-STAGE087-REVIEW-GATE"
                and status.get("runtime_enabled") is False
                and status.get("push_allowed") is False
            )
            or (
                isinstance(status, dict)
                and status.get("stage") == "IDS-STAGE087"
                and status.get("phase") == "IDS-STAGE087-P3"
                and status.get("task") == "IDS-V0_1-STAGE087-P3"
                and status.get("next_gate") == "IDS-STAGE087-P4-GATE"
                and status.get("runtime_enabled") is False
                and status.get("push_allowed") is False
            )
            or (
                isinstance(status, dict)
                and status.get("stage") == "IDS-STAGE087"
                and status.get("phase") == "IDS-STAGE087-P2"
                and status.get("task") == "IDS-V0_1-STAGE087-P2"
                and status.get("next_gate") == "IDS-STAGE087-P3-GATE"
                and status.get("runtime_enabled") is False
                and status.get("push_allowed") is False
            )
            or (
                isinstance(status, dict)
                and status.get("stage") == "IDS-STAGE086"
                and status.get("phase") == "IDS-STAGE086-REVIEW"
                and status.get("task") == "IDS-V0_1-STAGE086-REVIEW"
                and status.get("next_gate") == "IDS-STAGE087-P1-GATE"
                and status.get("runtime_enabled") is False
                and status.get("push_allowed") is False
            )
            or (
                isinstance(status, dict)
                and status.get("stage") == "IDS-STAGE086"
                and status.get("phase") == "IDS-STAGE086-P3"
                and status.get("task") == "IDS-V0_1-STAGE086-P3"
                and status.get("next_gate") == "IDS-STAGE086-P4-GATE"
                and status.get("runtime_enabled") is False
                and status.get("push_allowed") is False
            )
            or (
                isinstance(status, dict)
                and status.get("stage") == "IDS-STAGE086"
                and status.get("phase") == "IDS-STAGE086-P4"
                and status.get("task") == "IDS-V0_1-STAGE086-P4"
                and status.get("next_gate") == "IDS-STAGE086-REVIEW-GATE"
                and status.get("runtime_enabled") is False
                and status.get("push_allowed") is False
            )
            or (
                isinstance(status, dict)
                and status.get("stage") == "IDS-STAGE086"
                and status.get("phase") == "IDS-STAGE086-P2"
                and status.get("task") == "IDS-V0_1-STAGE086-P2"
                and status.get("next_gate") == "IDS-STAGE086-P3-GATE"
                and status.get("runtime_enabled") is False
                and status.get("push_allowed") is False
            )
            or (
                isinstance(status, dict)
                and status.get("stage") == "IDS-STAGE085"
                and status.get("phase") == "IDS-STAGE085-REVIEW"
                and status.get("task") == "IDS-V0_1-STAGE085-REVIEW"
                and status.get("next_gate") == "IDS-STAGE086-P1-GATE"
                and status.get("runtime_enabled") is False
                and status.get("push_allowed") is False
            )
            or (
                isinstance(status, dict)
                and status.get("stage") == "IDS-STAGE085"
                and status.get("phase") == "IDS-STAGE085-P3"
                and status.get("task") == "IDS-V0_1-STAGE085-P3"
                and status.get("next_gate") == "IDS-STAGE085-P4-GATE"
                and status.get("runtime_enabled") is False
                and status.get("push_allowed") is False
            )
            or (
                isinstance(status, dict)
                and status.get("stage") == "IDS-STAGE085"
                and status.get("phase") == "IDS-STAGE085-P4"
                and status.get("task") == "IDS-V0_1-STAGE085-P4"
                and status.get("next_gate") == "IDS-STAGE085-REVIEW-GATE"
                and status.get("runtime_enabled") is False
                and status.get("push_allowed") is False
            )
            or (
                isinstance(status, dict)
                and status.get("stage") == "IDS-STAGE085"
                and status.get("phase") == "IDS-STAGE085-P2"
                and status.get("task") == "IDS-V0_1-STAGE085-P2"
                and status.get("next_gate") == "IDS-STAGE085-P3-GATE"
                and status.get("runtime_enabled") is False
                and status.get("push_allowed") is False
            )
            or (
                isinstance(status, dict)
                and status.get("stage") == "IDS-STAGE084"
                and status.get("phase") == "IDS-STAGE084-REVIEW"
                and status.get("task") == "IDS-V0_1-STAGE084-REVIEW"
                and status.get("next_gate") == "IDS-STAGE085-P1-GATE"
                and status.get("runtime_enabled") is False
                and status.get("push_allowed") is False
            )
            or (
                isinstance(status, dict)
                and status.get("stage") == "IDS-STAGE084"
                and status.get("phase") == "IDS-STAGE084-P4"
                and status.get("task") == "IDS-V0_1-STAGE084-P4"
                and status.get("next_gate") == "IDS-STAGE084-REVIEW-GATE"
                and status.get("runtime_enabled") is False
                and status.get("push_allowed") is False
            )
            or (
                isinstance(status, dict)
                and status.get("stage") == "IDS-STAGE084"
                and status.get("phase") == "IDS-STAGE084-P2"
                and status.get("task") == "IDS-V0_1-STAGE084-P2"
                and status.get("next_gate") == "IDS-STAGE084-P3-GATE"
                and status.get("runtime_enabled") is False
                and status.get("push_allowed") is False
            )
            or (
                isinstance(status, dict)
                and status.get("stage") == "IDS-STAGE084"
                and status.get("phase") == "IDS-STAGE084-P3"
                and status.get("task") == "IDS-V0_1-STAGE084-P3"
                and status.get("next_gate") == "IDS-STAGE084-P4-GATE"
                and status.get("runtime_enabled") is False
                and status.get("push_allowed") is False
            )
            or (
                isinstance(status, dict)
                and status.get("stage") == "IDS-STAGE083"
                and status.get("phase") == "IDS-STAGE083-P2"
                and status.get("task") == "IDS-V0_1-STAGE083-P2"
                and status.get("next_gate") == "IDS-STAGE083-P3-GATE"
                and status.get("runtime_enabled") is False
                and status.get("push_allowed") is False
            )
            or (
                isinstance(status, dict)
                and status.get("stage") == "IDS-STAGE081"
                and status.get("phase") == "IDS-STAGE081-P3"
                and status.get("task") == "IDS-V0_1-STAGE081-P3"
                and status.get("next_gate") == "IDS-STAGE081-P4-GATE"
                and status.get("runtime_enabled") is False
                and status.get("push_allowed") is False
            )
            or (
                isinstance(status, dict)
                and status.get("stage") == "IDS-STAGE081"
                and status.get("phase") == "IDS-STAGE081-P4"
                and status.get("task") == "IDS-V0_1-STAGE081-P4"
                and status.get("next_gate") == "IDS-STAGE081-REVIEW-GATE"
                and status.get("runtime_enabled") is False
                and status.get("push_allowed") is False
            )
            or (
                isinstance(status, dict)
                and status.get("stage") == "IDS-STAGE081"
                and status.get("phase") == "IDS-STAGE081-P2"
                and status.get("task") == "IDS-V0_1-STAGE081-P2"
                and status.get("next_gate") == "IDS-STAGE081-P3-GATE"
                and status.get("runtime_enabled") is False
                and status.get("push_allowed") is False
            )
            or (
                isinstance(status, dict)
                and status.get("stage") == "IDS-STAGE080"
                and status.get("phase") == "IDS-V0_1-STAGE080-P2"
                and status.get("task") == "IDS-V0_1-STAGE080-P2"
                and status.get("next_gate") == "IDS-STAGE080-P3-GATE"
                and status.get("runtime_enabled") is False
                and status.get("push_allowed") is False
            )
            or (
                isinstance(status, dict)
                and status.get("stage") == "IDS-STAGE080"
                and status.get("phase") == "IDS-V0_1-STAGE080-P3"
                and status.get("task") == "IDS-V0_1-STAGE080-P3"
                and status.get("next_gate") == "IDS-STAGE080-P4-GATE"
                and status.get("runtime_enabled") is False
                and status.get("push_allowed") is False
            )
            or (
                isinstance(status, dict)
                and status.get("stage") == "IDS-STAGE079"
                and status.get("phase") == "IDS-STAGE079-REVIEW"
                and status.get("task") == "IDS-V0_1-STAGE079-REVIEW"
                and status.get("next_gate") == "IDS-STAGE080-P1-GATE"
                and status.get("runtime_enabled") is False
                and status.get("push_allowed") is False
            )
            or (
                isinstance(status, dict)
                and status.get("stage") == "IDS-STAGE079"
                and status.get("phase") == "IDS-V0_1-STAGE079-P2"
                and status.get("task") == "IDS-V0_1-STAGE079-P2"
                and status.get("next_gate") == "IDS-STAGE079-P3-GATE"
                and status.get("runtime_enabled") is False
                and status.get("push_allowed") is False
            )
            or (
                isinstance(status, dict)
                and status.get("stage") == "IDS-STAGE079"
                and status.get("phase") == "IDS-V0_1-STAGE079-P3"
                and status.get("task") == "IDS-V0_1-STAGE079-P3"
                and status.get("next_gate") == "IDS-STAGE079-P4-GATE"
                and status.get("runtime_enabled") is False
                and status.get("push_allowed") is False
            )
            or (
                isinstance(status, dict)
                and status.get("stage") == "IDS-STAGE079"
                and status.get("phase") == "IDS-V0_1-STAGE079-P4"
                and status.get("task") == "IDS-V0_1-STAGE079-P4"
                and status.get("next_gate") == "IDS-STAGE079-REVIEW-GATE"
                and status.get("runtime_enabled") is False
                and status.get("push_allowed") is False
            )
        ),
        "plan_projection_exact": (
            successor_plan
            or successor_phase2_plan
            or successor_phase3_plan
            or successor_phase4_plan
            or successor_review_plan
            or successor_stage052_plan
            or successor_stage052_phase2_plan
            or successor_stage052_phase3_plan
            or successor_stage052_phase4_plan
            or successor_stage052_review_plan
            or successor_stage053_plan
            or successor_stage053_phase2_plan
            or successor_stage053_phase3_plan
            or successor_stage053_phase4_plan
            or successor_stage053_review_plan
            or successor_stage054_plan
            or successor_stage054_phase2_plan
            or successor_stage054_phase3_plan
            or successor_stage054_phase4_plan
            or successor_stage054_review_plan
            or successor_stage055_plan
            or successor_stage055_phase2_plan
            or successor_stage055_phase3_plan
            or successor_stage055_phase4_plan
            or successor_stage055_review_plan
            or successor_stage056_plan
            or successor_stage056_phase2_plan
            or successor_stage056_phase3_plan
            or successor_stage056_phase4_plan
            or successor_stage056_review_plan
            or successor_stage057_plan
            or successor_stage058_plan
            or successor_stage058_phase2_plan
            or successor_stage058_phase3_plan
            or successor_stage058_phase4_plan
            or successor_stage058_review_plan
            or successor_stage059_plan
            or successor_stage059_phase2_plan
            or successor_stage059_phase3_plan
            or successor_stage059_phase4_plan
            or successor_stage059_review_plan
            or successor_stage060_plan
            or successor_stage060_phase2_plan
            or successor_stage060_phase3_plan
            or successor_stage060_phase4_plan
            or successor_stage060_review_plan
            or successor_stage060_batch_plan
            or successor_stage061_plan
            or successor_stage061_phase2_plan
            or successor_stage061_phase3_plan
            or successor_stage061_phase4_plan
            or successor_stage061_review_plan
            or successor_stage062_phase1_plan
            or successor_stage062_phase2_plan
            or successor_stage062_phase3_plan
            or successor_stage062_phase4_plan
            or successor_stage062_review_plan
            or successor_stage063_plan
            or successor_stage063_phase2_plan
            or successor_stage063_phase3_plan
            or successor_stage063_phase4_plan
            or successor_stage063_review_plan
            or successor_stage064_phase1_plan
            or successor_stage064_phase2_plan
            or successor_stage064_phase3_plan
            or successor_stage064_phase4_plan
            or successor_stage064_review_plan
            or successor_stage065_phase1_plan
            or successor_stage065_phase2_plan
            or successor_stage065_phase3_plan
            or successor_stage065_phase4_plan
            or successor_stage065_review_plan
            or successor_stage066_phase1_plan
            or successor_stage066_phase2_plan
            or successor_stage066_phase3_plan
            or successor_stage066_phase4_plan
            or successor_stage066_review_plan
            or successor_stage067_phase1_plan
            or successor_stage067_phase2_plan
            or successor_stage067_phase3_plan
            or successor_stage067_phase4_plan
            or successor_stage067_review_plan
            or successor_stage068_phase1_plan
            or successor_stage068_phase2_plan
            or successor_stage068_phase3_plan
            or successor_stage068_phase4_plan
            or successor_stage068_review_plan
            or successor_stage069_phase1_plan
            or successor_stage069_phase2_plan
            or successor_stage069_phase3_plan
            or successor_stage069_phase4_plan
            or successor_stage069_review_plan
            or successor_stage070_phase1_plan
            or (
                isinstance(plan, dict)
                and plan.get("stage") == SUCCESSOR_STAGE071
                and plan.get("phase") == SUCCESSOR_TASK071
                and plan.get("task") == SUCCESSOR_TASK071
                and SUCCESSOR_NEXT_GATE071 in str(plan.get("stop_condition"))
            )
            or (
                isinstance(plan, dict)
                and plan.get("stage") == SUCCESSOR_STAGE071
                and plan.get("phase") == SUCCESSOR_TASK071_P2
                and plan.get("task") == SUCCESSOR_TASK071_P2
                and SUCCESSOR_NEXT_GATE071_P2 in str(plan.get("stop_condition"))
            )
            or (
                isinstance(plan, dict)
                and plan.get("stage") == SUCCESSOR_STAGE071
                and plan.get("phase") == SUCCESSOR_TASK071_P3
                and plan.get("task") == SUCCESSOR_TASK071_P3
                and SUCCESSOR_NEXT_GATE071_P3 in str(plan.get("stop_condition"))
            )
            or (
                isinstance(plan, dict)
                and plan.get("stage") == SUCCESSOR_STAGE071
                and plan.get("phase") == SUCCESSOR_TASK071_P4
                and plan.get("task") == SUCCESSOR_TASK071_P4
                and SUCCESSOR_NEXT_GATE071_P4 in str(plan.get("stop_condition"))
            )
            or (
                isinstance(plan, dict)
                and plan.get("stage") == SUCCESSOR_STAGE071
                and plan.get("phase") == SUCCESSOR_TASK071_REVIEW
                and plan.get("task") == SUCCESSOR_TASK071_REVIEW
                and SUCCESSOR_NEXT_GATE071_REVIEW in str(plan.get("stop_condition"))
            )
            or (
                isinstance(plan, dict)
                and plan.get("stage") == SUCCESSOR_STAGE072
                and plan.get("phase") == SUCCESSOR_TASK072_P1
                and plan.get("task") == SUCCESSOR_TASK072_P1
                and SUCCESSOR_NEXT_GATE072_P1 in str(plan.get("stop_condition"))
            )
            or (
                isinstance(plan, dict)
                and plan.get("stage") == SUCCESSOR_STAGE072
                and plan.get("phase") == SUCCESSOR_TASK072_P2
                and plan.get("task") == SUCCESSOR_TASK072_P2
                and SUCCESSOR_NEXT_GATE072_P2 in str(plan.get("stop_condition"))
            )
            or (
                isinstance(plan, dict)
                and plan.get("stage") == SUCCESSOR_STAGE072
                and plan.get("phase") == SUCCESSOR_TASK072_P3
                and plan.get("task") == SUCCESSOR_TASK072_P3
                and SUCCESSOR_NEXT_GATE072_P3 in str(plan.get("stop_condition"))
            )
            or (
                isinstance(plan, dict)
                and plan.get("stage") == SUCCESSOR_STAGE072
                and plan.get("phase") == SUCCESSOR_TASK072_P4
                and plan.get("task") == SUCCESSOR_TASK072_P4
                and SUCCESSOR_NEXT_GATE072_P4 in str(plan.get("stop_condition"))
            )
            or (
                isinstance(plan, dict)
                and plan.get("stage") == SUCCESSOR_STAGE072
                and plan.get("phase") == SUCCESSOR_TASK072_REVIEW
                and plan.get("task") == SUCCESSOR_TASK072_REVIEW
                and SUCCESSOR_NEXT_GATE072_REVIEW in str(plan.get("stop_condition"))
            )
            or (
                isinstance(plan, dict)
                and plan.get("phase") == f"`{TASK_ID}`"
                and plan.get("task") == f"`{TASK_ID}`"
                and NEXT_GATE in str(plan.get("stop_condition"))
            )
            or (
                isinstance(plan, dict)
                and plan.get("stage") == "IDS-STAGE073"
                and plan.get("phase") == "IDS-V0_1-STAGE073-P1"
                and plan.get("task") == "IDS-V0_1-STAGE073-P1"
                and "IDS-STAGE073-P2-GATE" in str(plan.get("stop_condition", ""))
            )
            or (
                isinstance(plan, dict)
                and plan.get("stage") == "IDS-STAGE073"
                and plan.get("phase") == "IDS-V0_1-STAGE073-P2"
                and plan.get("task") == "IDS-V0_1-STAGE073-P2"
                and "IDS-STAGE073-P3-GATE" in str(plan.get("stop_condition", ""))
            )
            or (
                isinstance(plan, dict)
                and plan.get("stage") == "IDS-STAGE073"
                and plan.get("phase") == "IDS-V0_1-STAGE073-P3"
                and plan.get("task") == "IDS-V0_1-STAGE073-P3"
                and "IDS-STAGE073-P4-GATE" in str(plan.get("stop_condition", ""))
            )
            or (
                isinstance(plan, dict)
                and plan.get("stage") == "IDS-STAGE073"
                and plan.get("phase") == "IDS-V0_1-STAGE073-P4"
                and plan.get("task") == "IDS-V0_1-STAGE073-P4"
                and "IDS-STAGE073-REVIEW-GATE" in str(plan.get("stop_condition", ""))
            )
            or (
                isinstance(plan, dict)
                and plan.get("stage") == "IDS-STAGE073"
                and plan.get("phase") == "IDS-V0_1-STAGE073-REVIEW"
                and plan.get("task") == "IDS-V0_1-STAGE073-REVIEW"
                and "IDS-STAGE074-P1-GATE" in str(plan.get("stop_condition", ""))
            )
            or (
                isinstance(plan, dict)
                and plan.get("stage") == "IDS-STAGE074"
                and plan.get("phase") == "IDS-V0_1-STAGE074-P1"
                and plan.get("task") == "IDS-V0_1-STAGE074-P1"
                and "IDS-STAGE074-P2-GATE" in str(plan.get("stop_condition", ""))
            )
            or (
                isinstance(plan, dict)
                and plan.get("stage") == "IDS-STAGE074"
                and plan.get("phase") == "IDS-V0_1-STAGE074-P2"
                and plan.get("task") == "IDS-V0_1-STAGE074-P2"
                and "IDS-STAGE074-P3-GATE" in str(plan.get("stop_condition", ""))
            )
            or (
                isinstance(plan, dict)
                and plan.get("stage") == "IDS-STAGE074"
                and plan.get("phase") == "IDS-V0_1-STAGE074-P3"
                and plan.get("task") == "IDS-V0_1-STAGE074-P3"
                and "IDS-STAGE074-P4-GATE" in str(plan.get("stop_condition", ""))
            )
            or (
                isinstance(plan, dict)
                and plan.get("stage") == "IDS-STAGE074"
                and plan.get("phase") == "IDS-V0_1-STAGE074-P4"
                and plan.get("task") == "IDS-V0_1-STAGE074-P4"
                and "IDS-STAGE074-REVIEW-GATE" in str(plan.get("stop_condition", ""))
            )
            or (
                isinstance(plan, dict)
                and plan.get("stage") == "IDS-STAGE074"
                and plan.get("phase") == "IDS-V0_1-STAGE074-REVIEW"
                and plan.get("task") == "IDS-V0_1-STAGE074-REVIEW"
                and "IDS-STAGE075-P1-GATE" in str(plan.get("stop_condition", ""))
            )
            or (
                isinstance(plan, dict)
                and plan.get("stage") == "IDS-STAGE075"
                and plan.get("phase") == "IDS-V0_1-STAGE075-P1"
                and plan.get("task") == "IDS-V0_1-STAGE075-P1"
                and "IDS-STAGE075-P2-GATE" in str(plan.get("stop_condition", ""))
            )
            or (
                isinstance(plan, dict)
                and plan.get("stage") == "IDS-STAGE075"
                and plan.get("phase") == "IDS-V0_1-STAGE075-P2"
                and plan.get("task") == "IDS-V0_1-STAGE075-P2"
                and "IDS-STAGE075-P3-GATE" in str(plan.get("stop_condition", ""))
            )
            or (
                isinstance(plan, dict)
                and plan.get("stage") == "IDS-STAGE075"
                and plan.get("phase") == "IDS-V0_1-STAGE075-P3"
                and plan.get("task") == "IDS-V0_1-STAGE075-P3"
                and "IDS-STAGE075-P4-GATE" in str(plan.get("stop_condition", ""))
            )
            or (
                isinstance(plan, dict)
                and plan.get("stage") == "IDS-STAGE075"
                and plan.get("phase") == "IDS-V0_1-STAGE075-P4"
                and plan.get("task") == "IDS-V0_1-STAGE075-P4"
                and "IDS-STAGE075-REVIEW-GATE"
                in str(plan.get("stop_condition", ""))
            )
            or (
                isinstance(plan, dict)
                and plan.get("stage") == "IDS-STAGE075"
                and plan.get("phase") == "IDS-V0_1-STAGE075-REVIEW"
                and plan.get("task") == "IDS-V0_1-STAGE075-REVIEW"
                and "IDS-STAGE076-P1-GATE" in str(plan.get("stop_condition", ""))
            )
            or (
                isinstance(plan, dict)
                and plan.get("stage") == "IDS-STAGE076"
                and plan.get("phase") == "IDS-V0_1-STAGE076-P1"
                and plan.get("task") == "IDS-V0_1-STAGE076-P1"
                and "IDS-STAGE076-P2-GATE" in str(plan.get("stop_condition", ""))
            )
            or (
                isinstance(plan, dict)
                and plan.get("stage") == "IDS-STAGE076"
                and plan.get("phase") == "IDS-V0_1-STAGE076-P2"
                and plan.get("task") == "IDS-V0_1-STAGE076-P2"
                and "IDS-STAGE076-P3-GATE" in str(plan.get("stop_condition", ""))
            )
            or (
                isinstance(plan, dict)
                and plan.get("stage") == "IDS-STAGE076"
                and plan.get("phase") == "IDS-V0_1-STAGE076-P3"
                and plan.get("task") == "IDS-V0_1-STAGE076-P3"
                and "IDS-STAGE076-P4-GATE" in str(plan.get("stop_condition", ""))
            )
            or (
                isinstance(plan, dict)
                and plan.get("stage") == "IDS-STAGE076"
                and plan.get("phase") == "IDS-V0_1-STAGE076-P4"
                and plan.get("task") == "IDS-V0_1-STAGE076-P4"
                and "IDS-STAGE076-REVIEW-GATE" in str(plan.get("stop_condition", ""))
            )
            or (
                isinstance(plan, dict)
                and plan.get("stage") == "IDS-STAGE076"
                and plan.get("phase") == "IDS-V0_1-STAGE076-REVIEW"
                and plan.get("task") == "IDS-V0_1-STAGE076-REVIEW"
                and "IDS-STAGE077-P1-GATE" in str(plan.get("stop_condition", ""))
            )
            or (
                isinstance(plan, dict)
                and plan.get("stage") == "IDS-STAGE077"
                and plan.get("phase") == "IDS-V0_1-STAGE077-P1"
                and plan.get("task") == "IDS-V0_1-STAGE077-P1"
                and "IDS-STAGE077-P2-GATE" in str(plan.get("stop_condition", ""))
            )
            or (
                isinstance(plan, dict)
                and plan.get("stage") == "IDS-STAGE077"
                and plan.get("phase") == "IDS-V0_1-STAGE077-P2"
                and plan.get("task") == "IDS-V0_1-STAGE077-P2"
                and "IDS-STAGE077-P3-GATE" in str(plan.get("stop_condition", ""))
            )
            or (
                isinstance(plan, dict)
                and plan.get("stage") == "IDS-STAGE077"
                and plan.get("phase") == "IDS-V0_1-STAGE077-P3"
                and plan.get("task") == "IDS-V0_1-STAGE077-P3"
                and "IDS-STAGE077-P4-GATE" in str(plan.get("stop_condition", ""))
            )
            or (
                isinstance(plan, dict)
                and plan.get("stage") == "IDS-STAGE077"
                and plan.get("phase") == "IDS-V0_1-STAGE077-P4"
                and plan.get("task") == "IDS-V0_1-STAGE077-P4"
                and "IDS-STAGE077-REVIEW-GATE" in str(plan.get("stop_condition", ""))
            )
            or (
                isinstance(plan, dict)
                and plan.get("stage") == "IDS-STAGE077"
                and plan.get("phase") == "IDS-V0_1-STAGE077-REVIEW"
                and plan.get("task") == "IDS-V0_1-STAGE077-REVIEW"
                and "IDS-STAGE078-P1-GATE" in str(plan.get("stop_condition", ""))
            )
            or (
                isinstance(plan, dict)
                and plan.get("stage") == "IDS-STAGE078"
                and plan.get("phase") == "IDS-V0_1-STAGE078-P1"
                and plan.get("task") == "IDS-V0_1-STAGE078-P1"
                and "IDS-STAGE078-P2-GATE" in str(plan.get("stop_condition", ""))
            )
            or (
                isinstance(plan, dict)
                and plan.get("stage") == "IDS-STAGE078"
                and plan.get("phase") == "IDS-V0_1-STAGE078-P2"
                and plan.get("task") == "IDS-V0_1-STAGE078-P2"
                and "IDS-STAGE078-P3-GATE" in str(plan.get("stop_condition", ""))
            )
            or (
                isinstance(plan, dict)
                and plan.get("stage") == "IDS-STAGE078"
                and plan.get("phase") == "IDS-V0_1-STAGE078-P3"
                and plan.get("task") == "IDS-V0_1-STAGE078-P3"
                and "IDS-STAGE078-P4-GATE" in str(plan.get("stop_condition", ""))
            )
            or (
                isinstance(plan, dict)
                and plan.get("stage") == "IDS-STAGE078"
                and plan.get("phase") == "IDS-V0_1-STAGE078-P4"
                and plan.get("task") == "IDS-V0_1-STAGE078-P4"
                and "IDS-STAGE078-REVIEW-GATE" in str(plan.get("stop_condition", ""))
            )
            or (
                isinstance(plan, dict)
                and plan.get("stage") == "IDS-STAGE078"
                and plan.get("phase") == "IDS-STAGE078-REVIEW"
                and plan.get("task") == "IDS-V0_1-STAGE078-REVIEW"
                and "IDS-STAGE079-P1-GATE" in str(plan.get("stop_condition", ""))
            )
            or (
                isinstance(plan, dict)
                and plan.get("stage") == "IDS-STAGE079"
                and plan.get("phase") == "IDS-V0_1-STAGE079-P1"
                and plan.get("task") == "IDS-V0_1-STAGE079-P1"
                and "IDS-STAGE079-P2-GATE" in str(plan.get("stop_condition", ""))
            )
            or (
                isinstance(plan, dict)
                and plan.get("stage") == "IDS-STAGE079"
                and plan.get("phase") == "IDS-V0_1-STAGE079-P2"
                and plan.get("task") == "IDS-V0_1-STAGE079-P2"
                and "IDS-STAGE079-P3-GATE" in str(plan.get("stop_condition", ""))
            )
            or (
                isinstance(plan, dict)
                and plan.get("stage") == "IDS-STAGE079"
                and plan.get("phase") == "IDS-V0_1-STAGE079-P3"
                and plan.get("task") == "IDS-V0_1-STAGE079-P3"
                and "IDS-STAGE079-P4-GATE" in str(plan.get("stop_condition", ""))
            )
            or (
                isinstance(plan, dict)
                and plan.get("stage") == "IDS-STAGE079"
                and plan.get("phase") == "IDS-V0_1-STAGE079-P4"
                and plan.get("task") == "IDS-V0_1-STAGE079-P4"
                and "IDS-STAGE079-REVIEW-GATE" in str(plan.get("stop_condition", ""))
            )
            or (
                isinstance(plan, dict)
                and plan.get("stage") == "IDS-STAGE079"
                and plan.get("phase") == "IDS-STAGE079-REVIEW"
                and plan.get("task") == "IDS-V0_1-STAGE079-REVIEW"
                and "IDS-STAGE080-P1-GATE" in str(plan.get("stop_condition", ""))
            )
            or (
                isinstance(plan, dict)
                and plan.get("stage") == "IDS-STAGE080"
                and plan.get("phase") == "IDS-V0_1-STAGE080-P1"
                and plan.get("task") == "IDS-V0_1-STAGE080-P1"
                and "IDS-STAGE080-P2-GATE" in str(plan.get("stop_condition", ""))
            )
            or (
                isinstance(plan, dict)
                and plan.get("stage") == "IDS-STAGE080"
                and plan.get("phase") == "IDS-V0_1-STAGE080-P2"
                and plan.get("task") == "IDS-V0_1-STAGE080-P2"
                and "IDS-STAGE080-P3-GATE" in str(plan.get("stop_condition", ""))
            )
            or (
                isinstance(plan, dict)
                and plan.get("stage") == "IDS-STAGE080"
                and plan.get("phase") == "IDS-V0_1-STAGE080-P3"
                and plan.get("task") == "IDS-V0_1-STAGE080-P3"
                and "IDS-STAGE080-P4-GATE" in str(plan.get("stop_condition", ""))
            )
            or (
                isinstance(plan, dict)
                and plan.get("stage") == "IDS-STAGE080"
                and plan.get("phase") == "IDS-V0_1-STAGE080-P4"
                and plan.get("task") == "IDS-V0_1-STAGE080-P4"
                and "IDS-STAGE080-REVIEW-GATE" in str(plan.get("stop_condition", ""))
            )
            or (
                isinstance(plan, dict)
                and plan.get("stage") == "IDS-STAGE080"
                and plan.get("phase") == "IDS-STAGE080-REVIEW"
                and plan.get("task") == "IDS-V0_1-STAGE080-REVIEW"
                and "IDS-STAGE081-P1-GATE" in str(plan.get("stop_condition", ""))
            )
            or (
                isinstance(plan, dict)
                and plan.get("stage") == "IDS-STAGE081"
                and plan.get("phase") == "IDS-STAGE081-P1"
                and plan.get("task") == "IDS-V0_1-STAGE081-P1"
                and "IDS-STAGE081-P2-GATE" in str(plan.get("stop_condition", ""))
            )
            or (
                isinstance(plan, dict)
                and plan.get("stage") == "IDS-STAGE081"
                and plan.get("phase") == "IDS-STAGE081-P2"
                and plan.get("task") == "IDS-V0_1-STAGE081-P2"
                and "IDS-STAGE081-P3-GATE" in str(plan.get("stop_condition", ""))
            )
            or (
                isinstance(plan, dict)
                and plan.get("stage") == "IDS-STAGE081"
                and plan.get("phase") == "IDS-STAGE081-P3"
                and plan.get("task") == "IDS-V0_1-STAGE081-P3"
                and "IDS-STAGE081-P4-GATE" in str(plan.get("stop_condition", ""))
            )
            or (
                isinstance(plan, dict)
                and plan.get("stage") == "IDS-STAGE081"
                and plan.get("phase") == "IDS-STAGE081-P4"
                and plan.get("task") == "IDS-V0_1-STAGE081-P4"
                and "IDS-STAGE081-REVIEW-GATE"
                in str(plan.get("stop_condition", ""))
            )
            or (
                isinstance(plan, dict)
                and plan.get("stage") == "IDS-STAGE081"
                and plan.get("phase") == "IDS-STAGE081-REVIEW"
                and plan.get("task") == "IDS-V0_1-STAGE081-REVIEW"
                and "IDS-STAGE082-P1-GATE" in str(plan.get("stop_condition", ""))
            )
            or (
                isinstance(plan, dict)
                and plan.get("stage") == "IDS-STAGE082"
                and plan.get("phase") == "IDS-STAGE082-P1"
                and plan.get("task") == "IDS-V0_1-STAGE082-P1"
                and "IDS-STAGE082-P2-GATE" in str(plan.get("stop_condition", ""))
            )
            or (
                isinstance(plan, dict)
                and plan.get("stage") == "IDS-STAGE082"
                and plan.get("phase") == "IDS-STAGE082-P2"
                and plan.get("task") == "IDS-V0_1-STAGE082-P2"
                and "IDS-STAGE082-P3-GATE" in str(plan.get("stop_condition", ""))
            )
            or (
                isinstance(plan, dict)
                and plan.get("stage") == "IDS-STAGE082"
                and plan.get("phase") == "IDS-STAGE082-P3"
                and plan.get("task") == "IDS-V0_1-STAGE082-P3"
                and "IDS-STAGE082-P4-GATE" in str(plan.get("stop_condition", ""))
            )
            or (
                isinstance(plan, dict)
                and plan.get("stage") == "IDS-STAGE082"
                and plan.get("phase") == "IDS-STAGE082-P4"
                and plan.get("task") == "IDS-V0_1-STAGE082-P4"
                and "IDS-STAGE082-REVIEW-GATE"
                in str(plan.get("stop_condition", ""))
            )
            or (
                isinstance(plan, dict)
                and plan.get("stage") == "IDS-STAGE082"
                and plan.get("phase") == "IDS-STAGE082-REVIEW"
                and plan.get("task") == "IDS-V0_1-STAGE082-REVIEW"
                and "IDS-STAGE083-P1-GATE" in str(plan.get("stop_condition", ""))
            )
            or (
                isinstance(plan, dict)
                and plan.get("stage") == "IDS-STAGE083"
                and plan.get("phase") == "IDS-STAGE083-P1"
                and plan.get("task") == "IDS-V0_1-STAGE083-P1"
                and "IDS-STAGE083-P2-GATE" in str(plan.get("stop_condition", ""))
            )
            or (
                isinstance(plan, dict)
                and plan.get("stage") == "IDS-STAGE083"
                and plan.get("phase") == "IDS-STAGE083-P2"
                and plan.get("task") == "IDS-V0_1-STAGE083-P2"
                and "IDS-STAGE083-P3-GATE" in str(plan.get("stop_condition", ""))
            )
            or (
                isinstance(plan, dict)
                and plan.get("stage") == "IDS-STAGE083"
                and plan.get("phase") == "IDS-STAGE083-P3"
                and plan.get("task") == "IDS-V0_1-STAGE083-P3"
                and "IDS-STAGE083-P4-GATE" in str(plan.get("stop_condition", ""))
            )
            or (
                isinstance(plan, dict)
                and plan.get("stage") == "IDS-STAGE083"
                and plan.get("phase") == "IDS-STAGE083-P4"
                and plan.get("task") == "IDS-V0_1-STAGE083-P4"
                and "IDS-STAGE083-REVIEW-GATE" in str(plan.get("stop_condition", ""))
            )
            or (
                isinstance(plan, dict)
                and plan.get("stage") == "IDS-STAGE083"
                and plan.get("phase") == "IDS-STAGE083-REVIEW"
                and plan.get("task") == "IDS-V0_1-STAGE083-REVIEW"
                and "IDS-STAGE084-P1-GATE" in str(plan.get("stop_condition", ""))
            )
            or (
                isinstance(plan, dict)
                and plan.get("stage") == "IDS-STAGE084"
                and plan.get("phase") == "IDS-STAGE084-P1"
                and plan.get("task") == "IDS-V0_1-STAGE084-P1"
                and "IDS-STAGE084-P2-GATE" in str(plan.get("stop_condition", ""))
            )
            or (
                isinstance(plan, dict)
                and plan.get("stage") == "IDS-STAGE084"
                and plan.get("phase") == "IDS-STAGE084-P2"
                and plan.get("task") == "IDS-V0_1-STAGE084-P2"
                and "IDS-STAGE084-P3-GATE" in str(plan.get("stop_condition", ""))
            )
            or (
                isinstance(plan, dict)
                and plan.get("stage") == "IDS-STAGE084"
                and plan.get("phase") == "IDS-STAGE084-P3"
                and plan.get("task") == "IDS-V0_1-STAGE084-P3"
                and "IDS-STAGE084-P4-GATE" in str(plan.get("stop_condition", ""))
            )
            or (
                isinstance(plan, dict)
                and plan.get("stage") == "IDS-STAGE084"
                and plan.get("phase") == "IDS-STAGE084-P4"
                and plan.get("task") == "IDS-V0_1-STAGE084-P4"
                and "IDS-STAGE084-REVIEW-GATE" in str(plan.get("stop_condition", ""))
            )
            or (
                isinstance(plan, dict)
                and plan.get("stage") == "IDS-STAGE084"
                and plan.get("phase") == "IDS-STAGE084-REVIEW"
                and plan.get("task") == "IDS-V0_1-STAGE084-REVIEW"
                and "IDS-STAGE085-P1-GATE" in str(plan.get("stop_condition", ""))
            )
            or (
                isinstance(plan, dict)
                and plan.get("stage") == "IDS-STAGE085"
                and plan.get("phase") == "IDS-STAGE085-P1"
                and plan.get("task") == "IDS-V0_1-STAGE085-P1"
                and "IDS-STAGE085-P2-GATE" in str(plan.get("stop_condition", ""))
            )
            or (
                isinstance(plan, dict)
                and plan.get("stage") == "IDS-STAGE085"
                and plan.get("phase") == "IDS-STAGE085-P2"
                and plan.get("task") == "IDS-V0_1-STAGE085-P2"
                and "IDS-STAGE085-P3-GATE" in str(plan.get("stop_condition", ""))
            )
            or (
                isinstance(plan, dict)
                and plan.get("stage") == "IDS-STAGE085"
                and plan.get("phase") == "IDS-STAGE085-P3"
                and plan.get("task") == "IDS-V0_1-STAGE085-P3"
                and "IDS-STAGE085-P4-GATE" in str(plan.get("stop_condition", ""))
            )
            or (
                isinstance(plan, dict)
                and plan.get("stage") == "IDS-STAGE085"
                and plan.get("phase") == "IDS-STAGE085-P4"
                and plan.get("task") == "IDS-V0_1-STAGE085-P4"
                and "IDS-STAGE085-REVIEW-GATE" in str(plan.get("stop_condition", ""))
            )
            or (
                isinstance(plan, dict)
                and plan.get("stage") == "IDS-STAGE085"
                and plan.get("phase") == "IDS-STAGE085-REVIEW"
                and plan.get("task") == "IDS-V0_1-STAGE085-REVIEW"
                and "IDS-STAGE086-P1-GATE" in str(plan.get("stop_condition", ""))
            )
            or (
                isinstance(plan, dict)
                and plan.get("stage") == "IDS-STAGE086"
                and plan.get("phase") == "IDS-STAGE086-P1"
                and plan.get("task") == "IDS-V0_1-STAGE086-P1"
                and "IDS-STAGE086-P2-GATE" in str(plan.get("stop_condition", ""))
            )
            or (
                isinstance(plan, dict)
                and plan.get("stage") == "IDS-STAGE086"
                and plan.get("phase") == "IDS-STAGE086-P2"
                and plan.get("task") == "IDS-V0_1-STAGE086-P2"
                and "IDS-STAGE086-P3-GATE" in str(plan.get("stop_condition", ""))
            )
            or (
                isinstance(plan, dict)
                and plan.get("stage") == "IDS-STAGE086"
                and plan.get("phase") == "IDS-STAGE086-P3"
                and plan.get("task") == "IDS-V0_1-STAGE086-P3"
                and "IDS-STAGE086-P4-GATE" in str(plan.get("stop_condition", ""))
            )
            or (
                isinstance(plan, dict)
                and plan.get("stage") == "IDS-STAGE086"
                and plan.get("phase") == "IDS-STAGE086-P4"
                and plan.get("task") == "IDS-V0_1-STAGE086-P4"
                and "IDS-STAGE086-REVIEW-GATE" in str(plan.get("stop_condition", ""))
            )
            or (
                isinstance(plan, dict)
                and plan.get("stage") == "IDS-STAGE086"
                and plan.get("phase") == "IDS-STAGE086-REVIEW"
                and plan.get("task") == "IDS-V0_1-STAGE086-REVIEW"
                and "IDS-STAGE087-P1-GATE" in str(plan.get("stop_condition", ""))
            )
            or (
                isinstance(plan, dict)
                and plan.get("stage") == "IDS-STAGE087"
                and plan.get("phase") == "IDS-STAGE087-P1"
                and plan.get("task") == "IDS-V0_1-STAGE087-P1"
                and "IDS-STAGE087-P2-GATE" in str(plan.get("stop_condition", ""))
            )
            or (
                isinstance(plan, dict)
                and plan.get("stage") == "IDS-STAGE087"
                and plan.get("phase") == "IDS-STAGE087-P2"
                and plan.get("task") == "IDS-V0_1-STAGE087-P2"
                and "IDS-STAGE087-P3-GATE" in str(plan.get("stop_condition", ""))
            )
            or (
                isinstance(plan, dict)
                and plan.get("stage") == "IDS-STAGE087"
                and plan.get("phase") == "IDS-STAGE087-P3"
                and plan.get("task") == "IDS-V0_1-STAGE087-P3"
                and "IDS-STAGE087-P4-GATE" in str(plan.get("stop_condition", ""))
            )
            or (
                isinstance(plan, dict)
                and plan.get("stage") == "IDS-STAGE087"
                and plan.get("phase") == "IDS-STAGE087-P4"
                and plan.get("task") == "IDS-V0_1-STAGE087-P4"
                and "IDS-STAGE087-REVIEW-GATE" in str(plan.get("stop_condition", ""))
            )
            or (
                isinstance(plan, dict)
                and plan.get("stage") == "IDS-STAGE087"
                and plan.get("phase") == "IDS-STAGE087-REVIEW"
                and plan.get("task") == "IDS-V0_1-STAGE087-REVIEW"
                and "IDS-STAGE088-P1-GATE" in str(plan.get("stop_condition", ""))
            )
            or (
                isinstance(plan, dict)
                and plan.get("stage") == "IDS-STAGE088"
                and plan.get("phase") == "IDS-STAGE088-P1"
                and plan.get("task") == "IDS-V0_1-STAGE088-P1"
                and "IDS-STAGE088-P2-GATE" in str(plan.get("stop_condition", ""))
            )
            or (
                isinstance(plan, dict)
                and plan.get("stage") == "IDS-STAGE088"
                and plan.get("phase") == "IDS-STAGE088-P2"
                and plan.get("task") == "IDS-V0_1-STAGE088-P2"
                and "IDS-STAGE088-P3-GATE" in str(plan.get("stop_condition", ""))
            )
            or (
                isinstance(plan, dict)
                and plan.get("stage") == "IDS-STAGE088"
                and plan.get("phase") == "IDS-STAGE088-P3"
                and plan.get("task") == "IDS-V0_1-STAGE088-P3"
                and "IDS-STAGE088-P4-GATE"
                in str(plan.get("stop_condition", ""))
            )
            or (
                isinstance(plan, dict)
                and plan.get("stage") == "IDS-STAGE088"
                and plan.get("phase") == "IDS-STAGE088-P4"
                and plan.get("task") == "IDS-V0_1-STAGE088-P4"
                and "IDS-STAGE088-REVIEW-GATE"
                in str(plan.get("stop_condition", ""))
            )
            or (
                isinstance(plan, dict)
                and plan.get("stage") == "IDS-STAGE088"
                and plan.get("phase") == "IDS-STAGE088-REVIEW"
                and plan.get("task") == "IDS-V0_1-STAGE088-REVIEW"
                and "IDS-STAGE089-P1-GATE"
                in str(plan.get("stop_condition", ""))
            )
            or (
                isinstance(plan, dict)
                and plan.get("stage") == "IDS-STAGE089"
                and plan.get("phase") == "IDS-STAGE089-P1"
                and plan.get("task") == "IDS-V0_1-STAGE089-P1"
                and "IDS-STAGE089-P2-GATE"
                in str(plan.get("stop_condition", ""))
            )
            or (
                isinstance(plan, dict)
                and plan.get("stage") == "IDS-STAGE089"
                and plan.get("phase") == "IDS-STAGE089-P2"
                and plan.get("task") == "IDS-V0_1-STAGE089-P2"
                and "IDS-STAGE089-P3-GATE"
                in str(plan.get("stop_condition", ""))
            )
            or (
                isinstance(plan, dict)
                and plan.get("stage") == "IDS-STAGE089"
                and plan.get("phase") == "IDS-STAGE089-P3"
                and plan.get("task") == "IDS-V0_1-STAGE089-P3"
                and "IDS-STAGE089-P4-GATE"
                in str(plan.get("stop_condition", ""))
            )
            or (
                isinstance(plan, dict)
                and plan.get("stage") == "IDS-STAGE089"
                and plan.get("phase") == "IDS-STAGE089-P4"
                and plan.get("task") == "IDS-V0_1-STAGE089-P4"
                and "IDS-STAGE089-REVIEW-GATE"
                in str(plan.get("stop_condition", ""))
            )
            or (
                isinstance(plan, dict)
                and plan.get("stage") == "IDS-STAGE089"
                and plan.get("phase") == "IDS-STAGE089-REVIEW"
                and plan.get("task") == "IDS-V0_1-STAGE089-REVIEW"
                and "IDS-STAGE090-P1-GATE"
                in str(plan.get("stop_condition", ""))
            )
            or (
                isinstance(plan, dict)
                and plan.get("stage") == "IDS-STAGE090"
                and plan.get("phase") == "IDS-STAGE090-P1"
                and plan.get("task") == "IDS-V0_1-STAGE090-P1"
                and "IDS-STAGE090-P2-GATE"
                in str(plan.get("stop_condition", ""))
            )
            or (
                isinstance(plan, dict)
                and plan.get("stage") == "IDS-STAGE090"
                and plan.get("phase") == "IDS-STAGE090-P2"
                and plan.get("task") == "IDS-V0_1-STAGE090-P2"
                and "IDS-STAGE090-P3-GATE"
                in str(plan.get("stop_condition", ""))
            )
            or (
                isinstance(plan, dict)
                and plan.get("stage") == "IDS-STAGE090"
                and plan.get("phase") == "IDS-STAGE090-P3"
                and plan.get("task") == "IDS-V0_1-STAGE090-P3"
                and "IDS-STAGE090-P4-GATE"
                in str(plan.get("stop_condition", ""))
            )
            or (
                isinstance(plan, dict)
                and plan.get("stage") == "IDS-STAGE090"
                and plan.get("phase") == "IDS-STAGE090-P4"
                and plan.get("task") == "IDS-V0_1-STAGE090-P4"
                and "IDS-STAGE090-REVIEW-GATE"
                in str(plan.get("stop_condition", ""))
            )
            or (
                isinstance(plan, dict)
                and plan.get("stage") == "IDS-STAGE090"
                and plan.get("phase") == "IDS-STAGE090-REVIEW"
                and plan.get("task") == "IDS-V0_1-STAGE090-REVIEW"
                and "IDS-STAGE091-P1-GATE"
                in str(plan.get("stop_condition", ""))
            )
            or (
                isinstance(plan, dict)
                and plan.get("stage") == "IDS-STAGE091"
                and plan.get("phase") == "IDS-STAGE091-P1"
                and plan.get("task") == "IDS-V0_1-STAGE091-P1"
                and "IDS-STAGE091-P2-GATE"
                in str(plan.get("stop_condition", ""))
            )
            or (
                isinstance(plan, dict)
                and plan.get("stage") == "IDS-STAGE091"
                and plan.get("phase") == "IDS-STAGE091-P2"
                and plan.get("task") == "IDS-V0_1-STAGE091-P2"
                and "IDS-STAGE091-P3-GATE"
                in str(plan.get("stop_condition", ""))
            )
            or (
                isinstance(plan, dict)
                and plan.get("stage") == "IDS-STAGE091"
                and plan.get("phase") == "IDS-STAGE091-P3"
                and plan.get("task") == "IDS-V0_1-STAGE091-P3"
                and "IDS-STAGE091-P4-GATE"
                in str(plan.get("stop_condition", ""))
            )
            or (
                isinstance(plan, dict)
                and plan.get("stage") == "IDS-STAGE091"
                and plan.get("phase") == "IDS-STAGE091-P4"
                and plan.get("task") == "IDS-V0_1-STAGE091-P4"
                and "IDS-STAGE091-REVIEW-GATE"
                in str(plan.get("stop_condition", ""))
            )
            or (
                isinstance(plan, dict)
                and plan.get("stage") == "IDS-STAGE091"
                and plan.get("phase") == "IDS-STAGE091-REVIEW"
                and plan.get("task") == "IDS-V0_1-STAGE091-REVIEW"
                and "IDS-STAGE092-P1-GATE"
                in str(plan.get("stop_condition", ""))
            )
            or (
                isinstance(plan, dict)
                and plan.get("stage") == "IDS-STAGE092"
                and plan.get("phase") == "IDS-STAGE092-P1"
                and plan.get("task") == "IDS-V0_1-STAGE092-P1"
                and "IDS-STAGE092-P2-GATE"
                in str(plan.get("stop_condition", ""))
            )
            or (
                isinstance(plan, dict)
                and plan.get("stage") == "IDS-STAGE092"
                and plan.get("phase") == "IDS-STAGE092-P2"
                and plan.get("task") == "IDS-V0_1-STAGE092-P2"
                and "IDS-STAGE092-P3-GATE"
                in str(plan.get("stop_condition", ""))
            )
            or (
                isinstance(plan, dict)
                and plan.get("stage") == "IDS-STAGE092"
                and plan.get("phase") == "IDS-STAGE092-P3"
                and plan.get("task") == "IDS-V0_1-STAGE092-P3"
                and "IDS-STAGE092-P4-GATE"
                in str(plan.get("stop_condition", ""))
            )
            or (
                isinstance(plan, dict)
                and plan.get("stage") == "IDS-STAGE092"
                and plan.get("phase") == "IDS-STAGE092-P4"
                and plan.get("task") == "IDS-V0_1-STAGE092-P4"
                and "IDS-STAGE092-REVIEW-GATE"
                in str(plan.get("stop_condition", ""))
            )
            or (
                isinstance(plan, dict)
                and plan.get("stage") == "IDS-STAGE092"
                and plan.get("phase") == "IDS-STAGE092-REVIEW"
                and plan.get("task") == "IDS-V0_1-STAGE092-REVIEW"
                and "IDS-STAGE093-P1-GATE"
                in str(plan.get("stop_condition", ""))
            )
            or (
                isinstance(plan, dict)
                and plan.get("stage") == "IDS-STAGE093"
                and plan.get("phase") == "IDS-STAGE093-P1"
                and plan.get("task") == "IDS-V0_1-STAGE093-P1"
                and "IDS-STAGE093-P2-GATE"
                in str(plan.get("stop_condition", ""))
            )
            or (
                isinstance(plan, dict)
                and plan.get("stage") == "IDS-STAGE093"
                and plan.get("phase") == "IDS-STAGE093-P2"
                and plan.get("task") == "IDS-V0_1-STAGE093-P2"
                and "IDS-STAGE093-P3-GATE"
                in str(plan.get("stop_condition", ""))
            )
            or (
                isinstance(plan, dict)
                and plan.get("stage") == "IDS-STAGE093"
                and plan.get("phase") == "IDS-STAGE093-P3"
                and plan.get("task") == "IDS-V0_1-STAGE093-P3"
                and "IDS-STAGE093-P4-GATE"
                in str(plan.get("stop_condition", ""))
            )
            or (
                isinstance(plan, dict)
                and plan.get("stage") == "IDS-STAGE093"
                and plan.get("phase") == "IDS-STAGE093-P4"
                and plan.get("task") == "IDS-V0_1-STAGE093-P4"
                and "IDS-STAGE093-REVIEW-GATE"
                in str(plan.get("stop_condition", ""))
            )
            or (
                isinstance(plan, dict)
                and plan.get("stage") == "IDS-STAGE093"
                and plan.get("phase") == "IDS-STAGE093-REVIEW"
                and plan.get("task") == "IDS-V0_1-STAGE093-REVIEW"
                and "IDS-STAGE094-P1-GATE"
                in str(plan.get("stop_condition", ""))
            )
            or (
                isinstance(plan, dict)
                and plan.get("stage") == "IDS-STAGE094"
                and plan.get("phase") == "IDS-STAGE094-P1"
                and plan.get("task") == "IDS-V0_1-STAGE094-P1"
                and "IDS-STAGE094-P2-GATE"
                in str(plan.get("stop_condition", ""))
            )
        ),
        "roadmap_projection_exact": (
            isinstance(stage050, dict)
            and "批次复审" in str(stage050.get("gate"))
            and "上传" in str(stage050.get("status"))
        ),
        "acceptance_projection_exact": {
            "`ACC-BATCH041-050-REVIEW-01`",
            "`ACC-BATCH041-050-REVIEW-02`",
            "`ACC-BATCH041-050-REVIEW-03`",
            "`ACC-BATCH041-050-REVIEW-04`",
        }.issubset(acceptance_ids),
    }


def build_batch041_050_review_report(
    *,
    contract: Mapping[str, Any] | None = None,
    stage_result_overrides: Mapping[str, bool] | None = None,
) -> dict[str, Any]:
    """Return a deterministic, fail-closed batch-review report."""

    active_contract = copy.deepcopy(contract) if contract is not None else load_contract()
    batch = _load_yaml(BATCH_PATH)
    roadmap = _load_yaml(ROADMAP_PATH)
    contract_shape_checks = _contract_shape_checks(active_contract)
    artifact_checks = _artifact_checks(active_contract)
    stage_checks = _stage_checks(active_contract, batch, stage_result_overrides)
    cross_stage_checks = {
        "contract_chain_preserved": contract_shape_checks["cross_stage_chain_exact"],
        "no_runtime_execution_declared": (
            active_contract.get("cross_stage_contract", {}).get("runtime_execution_allowed")
            is False
        ),
        "production_runtime_stays_disabled": (
            active_contract.get("cross_stage_contract", {}).get("production_runtime_allowed")
            is False
        ),
    }
    governance_checks = _governance_checks(active_contract, batch, roadmap)
    projection_checks = _projection_checks()
    truth_checks = {
        key: active_contract.get("truth_contract", {}).get(key) == expected
        for key, expected in EXPECTED_TRUTH.items()
    }
    review_valid = all(
        all(check.values())
        for check in (
            contract_shape_checks,
            artifact_checks,
            stage_checks,
            cross_stage_checks,
            governance_checks,
            projection_checks,
            truth_checks,
        )
    )
    return {
        "schema_version": "ids.v0_1.batch041_050.review_report.v1",
        "batch_id": "IDS-V0_1-BATCH-041-050",
        "task_id": TASK_ID,
        "reviewed_stage_count": sum(stage_checks.values()),
        "contract_shape_checks": contract_shape_checks,
        "artifact_checks": artifact_checks,
        "stage_checks": stage_checks,
        "cross_stage_checks": cross_stage_checks,
        "governance_checks": governance_checks,
        "projection_checks": projection_checks,
        "truth_checks": truth_checks,
        "review_valid": review_valid,
        "result": PASS_RESULT if review_valid else "FAIL_CLOSED",
        "next_gate": NEXT_GATE if review_valid else REVIEW_GATE,
        "github_upload_allowed": False,
        "push_allowed": False,
        "app_reinstall_allowed": False,
    }


def main() -> int:
    report = build_batch041_050_review_report()
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if report["review_valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
