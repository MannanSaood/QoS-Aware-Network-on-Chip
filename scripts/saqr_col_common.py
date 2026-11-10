"""Shared settings for the SAQR-C study (docs/SAQR_SPEC_V2.md §22).

Separate binary (.deps/booksim2_saqr_c) and results tree (results/saqr_study/col).
chr_common.py is imported unchanged; its tuning-variable whitelist is extended in
this process only (SAQR-SC, SAQR-H and SAQR-C variables).
"""
import chr_common
import saqr_hot_common  # noqa: F401  (adds the NOC_SAQR_SRC_* and NOC_SAQR_HOT_* variables)
from saqr_hot_common import ROOT, SAQR_STUDY, sha, run  # noqa: F401

COL_BINARY = ROOT / '.deps/booksim2_saqr_c/src/booksim'
COL_STUDY = SAQR_STUDY / 'col'
COL_ENV = ('NOC_SAQR_COL_ON', 'NOC_SAQR_COL_OFF', 'NOC_SAQR_COL_FLOOR', 'NOC_SAQR_COL_INIT', 'NOC_SAQR_COL_SHIFT', 'NOC_SAQR_COL_MODE')
chr_common.TUNING_ENV = tuple(chr_common.TUNING_ENV) + COL_ENV
