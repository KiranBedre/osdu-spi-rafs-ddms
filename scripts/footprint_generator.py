#  Copyright 2025 ExxonMobil Technology and Engineering Company
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

import inspect
import json
import logging
import os
import re
import sys
from typing import Dict, List, Set

app_dir = os.path.join(os.path.dirname(__file__), "..")  # noqa # isort: skip
sys.path.append(app_dir)  # noqa # isort: skip

from app.models.data_schemas.base import ALL_PATHS_TO_SA_DATA_MODEL
from app.models.domain.osdu.base import (
    MASTER_DATA_KINDS_V2,
    SAMPLES_ANALYSES_REPORT_KIND,
    SAMPLESANALYSIS_KIND,
)

logging.basicConfig(level=logging.DEBUG, stream=sys.stdout)
logger = logging.getLogger(__name__)

RAFS_RELEASE_VERSION = "v0.28"  # make it as an argument
RAFS_DDMS_FOOTPRINT_FILE_PATH = f"{app_dir}/docs/rafs_ddms_footprint_{RAFS_RELEASE_VERSION}.json"
RAFS_REF_DATA_PATH = f"{app_dir}/deployments/shared-schemas/rafsddms/reference-data"

FILENAME_REGEX = re.compile(r"(filename):\s*((\w+\.)+json)")

OSDU_AUTHORITY = "osdu"
WILDCARD_VERSION = "*.*.*"
# List of reference-data kinds that are delivered by forum
FORUM_REFERENCE_KINDS = {
    f"{OSDU_AUTHORITY}:wks:reference-data--AromaticGCMSCompounds",
    f"{OSDU_AUTHORITY}:wks:reference-data--BulkPyrolysisMethod",
    f"{OSDU_AUTHORITY}:wks:reference-data--CompressibilityMeasurementType",
    f"{OSDU_AUTHORITY}:wks:reference-data--ConductivityMeasurementMethod",
    f"{OSDU_AUTHORITY}:wks:reference-data--ConsolidationType",
    f"{OSDU_AUTHORITY}:wks:reference-data--CutFluidType",
    f"{OSDU_AUTHORITY}:wks:reference-data--DesaturationMethod",
    f"{OSDU_AUTHORITY}:wks:reference-data--DisplacedFluidType",
    f"{OSDU_AUTHORITY}:wks:reference-data--DrainageCondition",
    f"{OSDU_AUTHORITY}:wks:reference-data--ElementalAnalysisMethod",
    f"{OSDU_AUTHORITY}:wks:reference-data--Elements",
    f"{OSDU_AUTHORITY}:wks:reference-data--EndFaceEstimationMethod",
    f"{OSDU_AUTHORITY}:wks:reference-data--FluidPhasesPresent",
    f"{OSDU_AUTHORITY}:wks:reference-data--FluidResistivityMeasurementMethod",
    f"{OSDU_AUTHORITY}:wks:reference-data--FluidSystemAnalysisType",
    f"{OSDU_AUTHORITY}:wks:reference-data--FractionationComponent",
    f"{OSDU_AUTHORITY}:wks:reference-data--FractionationMethod",
    f"{OSDU_AUTHORITY}:wks:reference-data--GasIsotopeComponents",
    f"{OSDU_AUTHORITY}:wks:reference-data--NonGasIsotopeComponents",
    f"{OSDU_AUTHORITY}:wks:reference-data--CompoundSpecificIsotopeComponents",
    f"{OSDU_AUTHORITY}:wks:reference-data--GCMSCompoundsRatios",
    f"{OSDU_AUTHORITY}:wks:reference-data--GCMSMSCompounds",
    f"{OSDU_AUTHORITY}:wks:reference-data--GrainDensityMeasurementType",
    f"{OSDU_AUTHORITY}:wks:reference-data--IsotopeRatioElements",
    f"{OSDU_AUTHORITY}:wks:reference-data--SampleStressLoadingMethod",
    f"{OSDU_AUTHORITY}:wks:reference-data--SampleStressLoadingStage",
    f"{OSDU_AUTHORITY}:wks:reference-data--Minerals",
    f"{OSDU_AUTHORITY}:wks:reference-data--NMRTestCondition",
    f"{OSDU_AUTHORITY}:wks:reference-data--PermeabilityMeasurementMethod",
    f"{OSDU_AUTHORITY}:wks:reference-data--PermeabilityMeasurementType",
    f"{OSDU_AUTHORITY}:wks:reference-data--PHMeasurementMethod",
    f"{OSDU_AUTHORITY}:wks:reference-data--PorosityMeasurementType",
    f"{OSDU_AUTHORITY}:wks:reference-data--PressureMeasurementType",
    f"{OSDU_AUTHORITY}:wks:reference-data--SampleAnalysisType",
    f"{OSDU_AUTHORITY}:wks:reference-data--SampleInjectionFluidType",
    f"{OSDU_AUTHORITY}:wks:reference-data--SampleOrganicCompositionComponent",
    f"{OSDU_AUTHORITY}:wks:reference-data--SampleOrientationType",
    f"{OSDU_AUTHORITY}:wks:reference-data--SamplePreparationMethod",
    f"{OSDU_AUTHORITY}:wks:reference-data--SampleTestCondition",
    f"{OSDU_AUTHORITY}:wks:reference-data--SaturateGCMSCompounds",
    f"{OSDU_AUTHORITY}:wks:reference-data--SaturationFluidType",
    f"{OSDU_AUTHORITY}:wks:reference-data--SaturationMethodType",
    f"{OSDU_AUTHORITY}:wks:reference-data--SaturationPressureType",
    f"{OSDU_AUTHORITY}:wks:reference-data--SaturationProcessMethod",
    f"{OSDU_AUTHORITY}:wks:reference-data--SaturationMeasurementLocation",
    f"{OSDU_AUTHORITY}:wks:reference-data--TensileStrengthMethod",
    f"{OSDU_AUTHORITY}:wks:reference-data--UniaxialCycleType",
    f"{OSDU_AUTHORITY}:wks:reference-data--UniaxialTestControlType",
    f"{OSDU_AUTHORITY}:wks:reference-data--ViscosityMethod",
    f"{OSDU_AUTHORITY}:wks:reference-data--VitriniteMountTechnique",
    f"{OSDU_AUTHORITY}:wks:reference-data--VitriniteReflectancePopulationType",
    f"{OSDU_AUTHORITY}:wks:reference-data--WaterSaturationCompositionComponent",
    f"{OSDU_AUTHORITY}:wks:reference-data--WettabilityIndexType",
    f"{OSDU_AUTHORITY}:wks:reference-data--WettabilityPhaseType",
    f"{OSDU_AUTHORITY}:wks:reference-data--WOGnCycleNotation",
    f"{OSDU_AUTHORITY}:wks:reference-data--ElementalMeasurementMethod",
}


class DDMSFootprintGen:
    GITLAB_URL = "https://community.opengroup.org/osdu/platform/domain-data-mgmt-services/rock-and-fluid-sample/rafs-ddms-services/-/blob/main/app/models/data_schemas/jsonschema/api_v2"  # noqa

    @classmethod
    def run(cls):
        logger.info("RAFS DDMS Footprint Generator is running...")

        logger.info(f"Reading the {RAFS_DDMS_FOOTPRINT_FILE_PATH} file data")
        footprint_data = cls.get_footprint_file_content()

        logger.info("Populating the DDMS version {RAFS_RELEASE_VERSION}")
        footprint_data["DdmsVersion"] = RAFS_RELEASE_VERSION

        logger.info("Retrieving all supported kinds")
        types_map = cls._get_supported_types()
        logger.info(f"Types found: {types_map.keys()}.")

        logger.info("Populating the CoveredItems section...")
        footprint_with_covered_items = cls.populate_covered_items(footprint_data, sorted(types_map.keys()))
        logger.info("CoveredItems sections has been populated.")

        logger.info("Populating the AuthorityToContentTypes section")
        footprint_data_with_ctypes = cls.populate_authority_content_types(
            footprint_with_covered_items,
            types_map,
        )
        logger.info("AuthorityToContentTypes section has been populated.")

        logger.info(f"Save the footprint data into {RAFS_DDMS_FOOTPRINT_FILE_PATH}")
        cls.update_footprint_file(footprint_data_with_ctypes)

    @classmethod
    def _get_supported_types(cls) -> Dict:
        analysis_types_versions_map = {
            path.strip("/").split("/")[-1]: cls.get_type_versions_files_map(versions.items())
            for path, versions in ALL_PATHS_TO_SA_DATA_MODEL.items()
        }
        return analysis_types_versions_map

    @classmethod
    def get_type_versions_files_map(cls, versions: Dict) -> Dict:
        _map = {}
        for version, model_cls in versions:
            _map[version] = cls.get_model_source_filename(model_cls)

        return _map

    @staticmethod
    def get_model_source_filename(model_cls) -> str:
        source_file = inspect.getsourcefile(model_cls)

        with open(source_file, "r") as f:
            f_content = f.read()
            source_file_groups = FILENAME_REGEX.findall(f_content)
            source_file_name = source_file_groups[0][1]

            logger.info(f"Source file name found: {source_file_name}")
            return source_file_name

    @staticmethod
    def get_footprint_file_content() -> Dict:
        with open(RAFS_DDMS_FOOTPRINT_FILE_PATH, "r") as f:
            footprint_data = json.load(f)
        return footprint_data

    @staticmethod
    def get_master_data_kinds() -> List[str]:
        return list(MASTER_DATA_KINDS_V2)

    @classmethod
    def get_reference_data_kinds(cls) -> List[str]:
        # traverse the reference-data folder and get all the reference-data kinds
        ref_kinds = cls.get_reference_files_kinds()
        ref_kinds.union(FORUM_REFERENCE_KINDS)

        return sorted([f"{k}:{WILDCARD_VERSION}" for k in ref_kinds])

    @staticmethod
    def get_reference_files_kinds() -> Set[str]:
        ref_kinds_found = set()

        for root, dirs, files in os.walk(RAFS_REF_DATA_PATH):
            for file in files:
                if file.endswith(".json"):
                    with open(os.path.join(root, file), "r") as f:
                        ref_data = json.load(f)

                        source = ref_data["schemaInfo"]["schemaIdentity"]["source"]
                        entity_type = ref_data["schemaInfo"]["schemaIdentity"]["entityType"]

                        ref_kinds_found.add(f"{OSDU_AUTHORITY}:{source}:{entity_type}")
        return ref_kinds_found

    @classmethod
    def populate_content_types(cls, types_map: Dict) -> List[Dict]:
        content_types_populated = []

        for ct, versions in types_map.items():
            for version, schema_filename in versions.items():
                content_types_populated.append(
                    {
                        "ContentType": ct,
                        "URL": f"{cls.GITLAB_URL}/{schema_filename}",
                    },
                )
        return content_types_populated

    @classmethod
    def populate_covered_items(cls, footprint_content: Dict, supported_types: List) -> Dict:
        # @TODO add PVT kinds as soon as they are graduated

        logger.info("Preparing reference-data items")
        reference_data_items = cls.get_reference_data_kinds()

        logger.info("Preparing master-data items")
        master_data_items = cls.get_master_data_kinds()

        covered_items = reference_data_items + master_data_items + [SAMPLES_ANALYSES_REPORT_KIND]
        footprint_content["CoveredItems"] = [{"WKS": t} for t in covered_items]

        logger.info("Populating the ContentTypes for work-product-component--SamplesAnalysis")
        footprint_content["CoveredItems"].append(
            {
                "WKS": SAMPLESANALYSIS_KIND,
                "ContentTypes": list(supported_types),
            }
        )

        return footprint_content

    @classmethod
    def populate_authority_content_types(cls, footprint_content: Dict, types_map: Dict) -> Dict:
        footprint_content["AuthorityToContentTypes"][0]["ContentTypeURLs"] = cls.populate_content_types(types_map)

        return footprint_content

    @staticmethod
    def update_footprint_file(footprint_content):
        with open(RAFS_DDMS_FOOTPRINT_FILE_PATH, "w") as f:
            json.dump(footprint_content, f, indent=4)


if __name__ == "__main__":
    logger.info("Run RAFS DDMS Footprint Generator")
    DDMSFootprintGen.run()
    logger.info("Finishing RAFS DDMS Footprint generation")
