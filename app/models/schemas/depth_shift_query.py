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

from typing import List, Optional

from pydantic import BaseModel


class DepthShiftQueryParams:
    """Validated depth-shift query parameters passed to the route.

    When *depth_shift_policy* is ``"id_provided"``, *depth_shift_id* must be
    set.  When it is ``"definitive"``, the WPC ID is resolved from the already-
    fetched sample records at pipeline time.  When it is ``None``, no depth
    shift is applied.
    """

    __slots__ = ("depth_shift_id", "depth_shift_policy")

    def __init__(
        self,
        depth_shift_id: Optional[str],
        depth_shift_policy: Optional[str],
    ) -> None:
        self.depth_shift_id = depth_shift_id
        self.depth_shift_policy = depth_shift_policy

    @property
    def is_definitive(self) -> bool:
        """True when the resolution strategy is 'definitive'."""
        return self.depth_shift_policy == "definitive"


class DepthShiftMetadata(BaseModel):
    """Top-level metadata block included in every depth-shifted response.

    Fields:

    - appliedDepthShiftId: the DepthShift WPC record ID that was resolved and applied
    - source: ``"definitive"`` when depth_shift_policy=definitive was used;
      ``"user-provided"`` when depth_shift_policy=id_provided was used
    - definitiveDepthShiftAvailable: True if at least one sample in the request
      carries ``data.DefinitiveDepthShift.DefinitiveDepthShiftID``
    - usedDefinitive: True only when depth_shift_policy=definitive was applied
    - warnings: metadata-level warnings (e.g. id_provided conflicts with definitive)
    """

    appliedDepthShiftId: str
    source: str
    definitiveDepthShiftAvailable: bool
    usedDefinitive: bool
    warnings: List[str] = []


class DepthShiftRowData(BaseModel):
    """Per-row depth-shift output included in the DepthShiftData parallel array.

    Fields:

    - SampleTop: original measured top depth (metres, from VerticalMeasurements)
    - SampleBase: original measured base depth; None for point samples
    - ShiftedSampleTop: depth-shifted SampleTop using the CoreToLog interval table
    - ShiftedSampleBase: depth-shifted SampleBase; None for point samples
    - DepthShiftWarnings: per-row warnings (non-Driller source, wellbore mismatch, etc.)
    """

    SampleTop: Optional[float] = None
    SampleBase: Optional[float] = None
    ShiftedSampleTop: Optional[float] = None
    ShiftedSampleBase: Optional[float] = None
    DepthShiftWarnings: List[str] = []
