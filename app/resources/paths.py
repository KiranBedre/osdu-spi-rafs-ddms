#  Copyright 2023 ExxonMobil Technology and Engineering Company
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.

from typing import NamedTuple


class CommonRelativePathsV1(NamedTuple):
    ROUTINECOREANALYSIS: str = "/rocksampleanalyses/"
    CCE: str = "/ccereports/"
    DIF_LIB: str = "/difflibreports/"
    TRANSPORT_TEST: str = "/transporttests/"
    COMPOSITIONAL_ANALYSIS: str = "/compositionalanalysisreports/"
    MSS: str = "/multistageseparatortests/"
    SWELLING: str = "/swellingtests/"
    CVD: str = "/constantvolumedepletiontests/"
    WATER_ANALYSIS: str = "/wateranalysisreports/"
    STO_ANALYSIS: str = "/stocktankoilanalysisreports/"
    INTERFACIAL_TENSION: str = "/interfacialtensiontests/"
    VLE: str = "/vaporliquidequilibriumtests/"
    MCM: str = "/multiplecontactmiscibilitytests/"
    SLIMTUBETEST: str = "/slimtubetests/"
    RELATIVE_PERMEABILITY: str = "/relativepermeabilitytests/"
    CAP_PRESSURE: str = "/capillarypressuretests/"
    FRACTIONATION: str = "/fractionationtests/"
    EXTRACTION: str = "/extractiontests/"
    PHYS_CHEM: str = "/physicalchemistrytests/"
    WATER_GAS_RELATIVE_PERMEABILITY: str = "/watergasrelativepermeabilities/"
    ROCK_COMPRESSIBILITY: str = "/rockcompressibilities/"
    ELECTRICAL_PROPERTIES: str = "/electricalproperties/"
    FORMATION_RESISTIVITY_INDEX: str = "/formationresistivityindexes/"


class CommonRelativePathsV2(NamedTuple):
    ROUTINECOREANALYSIS: str = "/data/routinecoreanalysis"
    CCE: str = "/data/constantcompositionexpansion"
    DIFF_LIB: str = "/data/differentialliberation"
    TRANSPORT_TEST: str = "/data/transport"
    COMPOSITIONAL_ANALYSIS: str = "/data/compositionalanalysis"
    MSS: str = "/data/multistageseparator"
    SWELLING: str = "/data/swelling"
    CVD: str = "/data/constantvolumedepletion"
    WATER_ANALYSIS: str = "/data/wateranalysis"
    INTERFACIAL_TENSION: str = "/data/interfacialtension"
    VLE: str = "/data/vaporliquidequilibrium"
    MCM: str = "/data/multiplecontactmiscibility"
    SLIMTUBE: str = "/data/slimtube"
    RELATIVE_PERMEABILITY: str = "/data/relativepermeability"
    FRACTIONATION: str = "/data/fractionation"
    EXTRACTION: str = "/data/extraction"
    WATER_GAS_REL_PERM: str = "/data/watergasrelativepermeability"
    ROCK_COMPRESSIBILITY: str = "/data/rockcompressibility"
    ELECTRICAL_PROPERTIES: str = "/data/electricalproperties"
    NMR: str = "/data/nmr"
    MULTIPLE_SALINITY: str = "/data/multiplesalinitytests"
    GCMS_ALKANES: str = "/data/gcmsalkanes"
    GCMS_AROMATICS: str = "/data/gcmsaromatics"
    GCMS_RATIOS: str = "/data/gcmsratios"
    GAS_CHROMATOGRAPHY: str = "/data/gaschromatographyanalyses"
    GAS_COMPOSITION: str = "/data/gascompositionanalyses"
    ISOTOPE_ANALYSIS: str = "/data/isotopes"
    BULK_PYROLYSIS: str = "/data/bulkpyrolysisanalyses"
    CORE_GAMMA: str = "/data/coregamma"
    UNIAXIAL_TEST: str = "/data/uniaxial"
    GCMSMS_ANALYSIS: str = "/data/gcmsms"
    CEC_CONTENT: str = "/data/cec"
    TRIAXIAL_TEST: str = "/data/triaxial"
    CAP_PRESSURE: str = "/data/capillarypressure"
    WETTABILITY_INDEX: str = "/data/wettabilityindex"
    TEC: str = "/data/tec"
    EDS_MAPPING: str = "/data/edsmapping"
    XRF: str = "/data/xrf"
    TENSILE_STRENGTH: str = "/data/tensilestrength"
    VITRINITE_REFLECTANCE: str = "/data/vitrinitereflectance"
    XRD: str = "/data/xrd"
    PDP: str = "/data/pdp"
    STO: str = "/data/stocktankoilanalysis"


COMMON_RELATIVE_PATHS = {
    "v1": CommonRelativePathsV1,
    "v2": CommonRelativePathsV2,
}
