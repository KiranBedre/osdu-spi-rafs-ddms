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
from client.api.core.v2.fluid_model import FluidModel
from client.api.core.v2.master_data import MasterDataV2Core
from client.api.core.v2.sample_analysis import SamplesAnalysis
from client.api.core.v2.samples_analyses_report import SamplesAnalysesReportV2Core
from client.api.core.v2.saturation_function_set import SaturationFunctionSet
from client.api.core.v2.simulation_rock_physics import SimulationRockPhysics
from client.api.legal import APILegal
from client.api.storage import APIStorage


class ApiWorker(object):
    """Class combine all api actions in one place."""

    def __init__(self, host: str, url_prefix: str, data_partition: str, token: str) -> None:
        self.storage = APIStorage(data_partition, token)
        self.legal = APILegal(data_partition, token)
        self.sar = SamplesAnalysesReportV2Core(host, url_prefix, data_partition, token)
        self.masterdata = MasterDataV2Core(host, url_prefix, data_partition, token)
        self.sample_analysis = SamplesAnalysis(host, url_prefix, data_partition, token)
        self.saturation_function_set = SaturationFunctionSet(host, url_prefix, data_partition, token)
        self.simulation_rock_physics = SimulationRockPhysics(host, url_prefix, data_partition, token)
        self.fluid_model = FluidModel(host, url_prefix, data_partition, token)
