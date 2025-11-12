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

from app.core.config import get_app_settings

settings = get_app_settings()

GENERIC_FACILITY_100_KIND = f"{settings.schema_authority}:wks:master-data--GenericFacility:1.0.0"
GENERIC_SITE_100_KIND = f"{settings.schema_authority}:wks:master-data--GenericSite:1.0.0"
SAMPLE_200_KIND = f"{settings.schema_authority}:wks:master-data--Sample:2.0.0"
SAMPLE_210_KIND = f"{settings.schema_authority}:wks:master-data--Sample:2.1.0"
SAMPLE_ACQUISITION_JOB_100_KIND = f"{settings.schema_authority}:wks:master-data--SampleAcquisitionJob:1.0.0"
SAMPLE_CHAIN_OF_CUSTODY_EVENT_100_KIND = f"{settings.schema_authority}:wks:master-data--SampleChainOfCustodyEvent:1.0.0"
SAMPLE_CONTAINER_100_KIND = f"{settings.schema_authority}:wks:master-data--SampleContainer:1.0.0"

MASTER_DATA_KINDS_V2 = (
    GENERIC_FACILITY_100_KIND,
    GENERIC_SITE_100_KIND,
    SAMPLE_200_KIND,
    SAMPLE_210_KIND,
    SAMPLE_ACQUISITION_JOB_100_KIND,
    SAMPLE_CHAIN_OF_CUSTODY_EVENT_100_KIND,
    SAMPLE_CONTAINER_100_KIND,
)

SAMPLESANALYSIS_KIND = f"{settings.schema_authority}:wks:work-product-component--SamplesAnalysis:1.0.0"

SAMPLES_ANALYSES_REPORT_KIND = f"{settings.schema_authority}:wks:work-product-component--SamplesAnalysesReport:1.0.0"

SATURATION_FUNCTION_SET_KIND = f"{settings.schema_authority}:wks:work-product-component--SaturationFunctionSet:1.0.0"
