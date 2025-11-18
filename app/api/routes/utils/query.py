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

import re
import string
from typing import Any, Iterable, List

from app.api.routes.utils.records import FULLID_ID_INDEX, get_id_version
from app.resources.common_osdu_regex import ALL_OSDU_REGEXES


def divide_chunks(elements: List[Any], chunk_size: int) -> Iterable:
    """Takes a list and returns a generator with given chunk size.

    :param elements: elements to divide into chunks
    :type elements: List[Any]
    :param chunk_size: the size of every chunk
    :type chunk_size: int
    :yield: a chunk of chunk_size
    :rtype: Iterator[Iterable]
    """
    for idx in range(0, len(elements), chunk_size):  # noqa: WPS526 (false positive)
        yield elements[idx:idx + chunk_size]


def find_osdu_ids_from_string(input_string: str) -> set:
    """Takes a string and returns the set of ids that match osdu id regex.

    :param input_string: data string
    :type input_string: str
    :return: the set of osdu ids present in the string
    :rtype: set
    """
    ids_set = set()
    for osdu_regex in ALL_OSDU_REGEXES:
        found_ids = {
            get_id_version(id_.strip(f"{string.whitespace}\"\'"))[FULLID_ID_INDEX]
            for id_ in re.findall(osdu_regex, f" {input_string} ")
        }
        ids_set.update(found_ids)
    return ids_set
