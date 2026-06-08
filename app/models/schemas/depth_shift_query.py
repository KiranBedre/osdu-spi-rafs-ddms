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

from typing import Optional

from typing_extensions import TypedDict


class DepthShiftQueryParams:
    """Validated depth-shift query parameters passed to the route.

    Exactly one of the two IDs is set; the other is None.
    """

    __slots__ = ("depth_shift_id", "abstract_definitive_depth_shift_id")

    def __init__(
        self,
        depth_shift_id: Optional[str],
        abstract_definitive_depth_shift_id: Optional[str],
    ) -> None:
        self.depth_shift_id = depth_shift_id
        self.abstract_definitive_depth_shift_id = abstract_definitive_depth_shift_id

    @property
    def is_abstract(self) -> bool:
        """True when using the AbstractDefinitiveDepthShift path."""
        return self.abstract_definitive_depth_shift_id is not None


class DepthShiftAugmentedResponse(TypedDict, total=False):
    """Documents the extra columns added to SA bulk data during depth-shift augmentation.

    This typed dict exists for documentation and type-checking purposes only.
    It is NOT used as a FastAPI response_model because the route returns dynamic
    DataFrame content.  Reference it in the augmenter output docstring.

    Extra columns added alongside the original SA DataFrame columns:

    - SampleTop: original measured top depth of the sample (metres, from VerticalMeasurements)
    - SampleBase: original measured base depth of the sample (metres); None for point samples
    - ShiftedSampleTop: depth-shifted SampleTop using the CoreToLog interval table
    - ShiftedSampleBase: depth-shifted SampleBase; None for point samples
    - DepthShiftWarnings: list of warning strings (non-Driller source, wellbore mismatch, etc.)
    """

    SampleTop: Optional[float]
    SampleBase: Optional[float]
    ShiftedSampleTop: Optional[float]
    ShiftedSampleBase: Optional[float]
    DepthShiftWarnings: list
