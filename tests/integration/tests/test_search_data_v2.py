#  Copyright 2024 ExxonMobil Technology and Engineering Company
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

import pytest

from tests.integration.config import SamplesAnalysisTypes


@pytest.mark.parametrize(
    "analysis_type", [SamplesAnalysisTypes.CCE],
)
@pytest.mark.smoke
@pytest.mark.v2
def test_search_data(
    api, analysis_type,
):
    search = api.sample_analysis.search_data(analysis_type)

    assert isinstance(search, dict)

    assert "columns" in search["result"]
    assert "index" in search["result"]
    assert "data" in search["result"]


@pytest.mark.parametrize(
    "analysis_type", [SamplesAnalysisTypes.CCE],
)
@pytest.mark.smoke
@pytest.mark.v2
def test_search(
    api, analysis_type,
):
    search = api.sample_analysis.search(analysis_type)

    assert isinstance(search, dict)

    assert isinstance(search["result"], list)
    assert len(search["result"]) > 0
