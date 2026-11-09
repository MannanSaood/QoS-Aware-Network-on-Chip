"""Shared settings for the SAQR-H study (docs/SAQR_SPEC_V2.md §20).

Separate binary (.deps/booksim2_saqr_hot) and results tree (results/saqr_study/hot),
so the frozen G4 and SAQR-SC builds, sources and receipts are never touched.
chr_common.py is imported unchanged; its tuning-variable whitelist is extended in
this process only (SAQR-SC variables via saqr_src_common, plus the tracker's).
"""
import chr_common
import saqr_src_common  # noqa: F401  (adds the NOC_SAQR_SRC_* variables)
from chr_common import ROOT, SAQR_STUDY, SAQR_BINARY, sha, run, trace  # noqa: F401
from saqr_src_common import SRC_BINARY  # noqa: F401

HOT_BINARY=ROOT/'.deps/booksim2_saqr_hot/src/booksim'
HOT_STUDY=SAQR_STUDY/'hot'
HOT_ENV=('NOC_SAQR_HOT_ON','NOC_SAQR_HOT_OFF','NOC_SAQR_HOT_FLOOR','NOC_SAQR_HOT_INIT','NOC_SAQR_HOT_SHIFT')
chr_common.TUNING_ENV=tuple(chr_common.TUNING_ENV)+HOT_ENV
