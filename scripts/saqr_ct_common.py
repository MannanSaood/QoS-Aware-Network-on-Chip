"""Shared settings for the SAQR-CT study (docs/SAQR_SPEC_V2.md §23).

Separate binary (.deps/booksim2_saqr_ct) and results tree (results/saqr_study/ct).
chr_common.py is imported unchanged; its tuning-variable whitelist is extended in this
process only (SAQR-SC, SAQR-H, SAQR-C and SAQR-CT variables).
"""
import chr_common
import saqr_col_common  # noqa: F401
from saqr_col_common import ROOT, SAQR_STUDY, COL_BINARY, sha, run  # noqa: F401

CT_BINARY = ROOT / '.deps/booksim2_saqr_ct/src/booksim'
CT_STUDY = SAQR_STUDY / 'ct'
chr_common.TUNING_ENV = tuple(chr_common.TUNING_ENV) + ('NOC_SAQR_CT_THR',)
