"""Shared settings for the SAQR-SC study (docs/SAQR_SPEC_V2.md §19).

Separate binary (.deps/booksim2_saqr_src) and results tree (results/saqr_study/src)
so the frozen G4 build, sources and receipts are never touched. chr_common.py is
imported unchanged; its tuning-variable whitelist is extended in this process only.
"""
import chr_common
from chr_common import ROOT, SAQR_STUDY, SAQR_BINARY, sha, run, trace  # noqa: F401

SRC_BINARY=ROOT/'.deps/booksim2_saqr_src/src/booksim'
SRC_STUDY=SAQR_STUDY/'src'
SRC_ENV=('NOC_SAQR_SRC_ON','NOC_SAQR_SRC_OFF','NOC_SAQR_SRC_HIST','NOC_SAQR_SRC_SHIFT')
chr_common.TUNING_ENV=tuple(chr_common.TUNING_ENV)+SRC_ENV
