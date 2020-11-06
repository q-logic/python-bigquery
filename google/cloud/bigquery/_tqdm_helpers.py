# Copyright 2019 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Shared helper functions for tqdm progress bar."""

import concurrent.futures
import time
import warnings

try:
    import tqdm
except ImportError:  # pragma: NO COVER
    tqdm = None

_NO_TQDM_ERROR = (
    "A progress bar was requested, but there was an error loading the tqdm "
    "library. Please install tqdm to use the progress bar functionality."
)

_PROGRESS_BAR_UPDATE_INTERVAL = 0.5


def _get_progress_bar(progress_bar_type, description, total, unit):
    """Construct a tqdm progress bar object, if tqdm is installed."""
    if tqdm is None:
        if progress_bar_type is not None:
            warnings.warn(_NO_TQDM_ERROR, UserWarning, stacklevel=3)
        return None

    try:
        if progress_bar_type == "tqdm":
            return tqdm.tqdm(desc=description, total=total, unit=unit)
        elif progress_bar_type == "tqdm_notebook":
            return tqdm.tqdm_notebook(desc=description, total=total, unit=unit)
        elif progress_bar_type == "tqdm_gui":
            return tqdm.tqdm_gui(desc=description, total=total, unit=unit)
    except (KeyError, TypeError):
        # Protect ourselves from any tqdm errors. In case of
        # unexpected tqdm behavior, just fall back to showing
        # no progress bar.
        warnings.warn(_NO_TQDM_ERROR, UserWarning, stacklevel=3)
    return None


def _query_job_result_helper(query_job, progress_bar_type=None):
    """Return query result and display a progress bar while the query running, if tqdm is installed."""
    if progress_bar_type:
        start_time = time.time()
        progress_bar = _get_progress_bar(
            progress_bar_type, "Query is running", 1, "query"
        )
        if query_job.query_plan:
            i = 0
            while True:
                total = len(query_job.query_plan)
                query_job.reload()  # Refreshes the state via a GET request.
                current_stage = query_job.query_plan[i]
                progress_bar.total = len(query_job.query_plan)
                progress_bar.set_description(
                    "Query executing stage {} and status {} : {:0.2f}s".format(
                        current_stage.name,
                        current_stage.status,
                        time.time() - start_time,
                    ),
                )

                try:
                    query_result = query_job.result(
                        timeout=_PROGRESS_BAR_UPDATE_INTERVAL
                    )
                    progress_bar.update(total)
                    progress_bar.set_description(
                        "Query complete after {:0.2f}s".format(
                            time.time() - start_time
                        ),
                    )
                    break
                except concurrent.futures.TimeoutError:
                    if current_stage.status == "COMPLETE":
                        if i < total - 1:
                            progress_bar.update(i + 1)
                            i += 1
                    continue

        else:
            query_result = query_job.result()
            progress_bar.set_description(
                "Query complete after {:0.2f}s".format(time.time() - start_time),
            )
            progress_bar.update(1)
        progress_bar.close()
    else:
        query_result = query_job.result()

    return query_result
