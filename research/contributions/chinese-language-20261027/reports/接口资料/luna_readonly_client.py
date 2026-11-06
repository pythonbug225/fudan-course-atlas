"""Conservative read-only clients for FDU TreeHole and DanXi Danke APIs.

Tokens are read from caller-provided environment variables only when a request is made.
This module never reads browser cookies, databases, or local credential stores.
"""
from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Callable, Mapping, Optional

TREEHOLE_BASE_URL = "https://forum.fduhole.com/api"
DANKE_BASE_URL = "https://danke.fduhole.com/api"
DEFAULT_PAGE_SIZE = 30
DEFAULT_MAX_PAGES = 10
CLIENT_MAX_PAGE_SIZE = 100
CLIENT_MAX_PAGES = 100


class ApiError(Exception):
    """A transport, HTTP, or response parsing error without request credentials."""

    def __init__(self, message: str, *, kind: str, status: Optional[int] = None):
        super().__init__(message)
        self.kind = kind
        self.status = status


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    """Do not forward an Authorization header to a redirect target."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def _default_transport(url: str, headers: Mapping[str, str], timeout: float) -> Any:
    request = urllib.request.Request(url, headers=dict(headers), method="GET")
    opener = urllib.request.build_opener(_NoRedirect())
    try:
        with opener.open(request, timeout=timeout) as response:
            body = response.read()
    except urllib.error.HTTPError as exc:
        raise ApiError(f"HTTP {exc.code}", kind="http", status=exc.code) from None
    except urllib.error.URLError as exc:
        reason = type(exc.reason).__name__
        raise ApiError(f"network error ({reason})", kind="network") from None
    except TimeoutError:
        raise ApiError("request timed out", kind="timeout") from None
    except OSError as exc:
        raise ApiError(f"network error ({type(exc).__name__})", kind="network") from None

    try:
        return json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise ApiError("response was not valid UTF-8 JSON", kind="json") from None


class ReadOnlyApiClient:
    """Sequential GET-only client with bounded pagination and a safe failure ledger."""

    def __init__(
        self,
        base_url: str,
        *,
        service: str,
        token_env: str,
        timeout_s: float = 12.0,
        min_interval_s: float = 0.5,
        transport: Optional[Callable[[str, Mapping[str, str], float], Any]] = None,
        token_provider: Optional[Callable[[str], Optional[str]]] = None,
        monotonic: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], None] = time.sleep,
    ):
        self.base_url = base_url.rstrip("/")
        self.service = service
        self.token_env = token_env
        self.timeout_s = timeout_s
        self.min_interval_s = min_interval_s
        self.transport = transport or _default_transport
        self.token_provider = token_provider or (lambda name: os.environ.get(name))
        self.monotonic = monotonic
        self.sleep = sleep
        self._last_request_at: Optional[float] = None
        self.failures: list[dict[str, Any]] = []

    def _record_failure(
        self,
        path: str,
        error: ApiError,
        context: Optional[Mapping[str, Any]] = None,
    ) -> None:
        self.failures.append(
            {
                "service": self.service,
                "path": path,
                "context": dict(context or {}),
                "kind": error.kind,
                "status": error.status,
                "message": str(error),
            }
        )

    def _get_json(
        self,
        path: str,
        params: Optional[Mapping[str, Any]] = None,
        *,
        context: Optional[Mapping[str, Any]] = None,
    ) -> Any:
        clean_params = {key: value for key, value in (params or {}).items() if value is not None}
        query = urllib.parse.urlencode(clean_params)
        url = self.base_url + "/" + path.lstrip("/")
        if query:
            url += "?" + query

        headers = {
            "Accept": "application/json",
            "User-Agent": "fdu-course-research-readonly/1.0",
        }
        token = self.token_provider(self.token_env)
        if token:
            token = token.strip()
            if token:
                headers["Authorization"] = token if token.startswith("Bearer ") else "Bearer " + token

        now = self.monotonic()
        if self._last_request_at is not None and self.min_interval_s > 0:
            delay = self.min_interval_s - (now - self._last_request_at)
            if delay > 0:
                self.sleep(delay)
        self._last_request_at = self.monotonic()

        try:
            return self.transport(url, headers, self.timeout_s)
        except ApiError as exc:
            self._record_failure(path, exc, context)
            raise
        except Exception as exc:
            wrapped = ApiError(f"request failed ({type(exc).__name__})", kind="client")
            self._record_failure(path, wrapped, context)
            raise wrapped from None

    @staticmethod
    def _validate_paging(page_size: int, max_pages: int, *, max_page_size: int = CLIENT_MAX_PAGE_SIZE) -> None:
        if not 1 <= page_size <= max_page_size:
            raise ValueError(f"page_size must be between 1 and {max_page_size}")
        if not 1 <= max_pages <= CLIENT_MAX_PAGES:
            raise ValueError(f"max_pages must be between 1 and {CLIENT_MAX_PAGES}")

    def _record_schema_failure(self, path: str, context: Mapping[str, Any], message: str) -> None:
        self._record_failure(path, ApiError(message, kind="schema"), context)


class TreeholeClient(ReadOnlyApiClient):
    def __init__(self, **kwargs: Any):
        kwargs.setdefault("base_url", TREEHOLE_BASE_URL)
        kwargs.setdefault("service", "treehole")
        kwargs.setdefault("token_env", "TREEHOLE_ACCESS_TOKEN")
        super().__init__(**kwargs)

    def search_floors(
        self,
        search: str,
        *,
        page_size: int = DEFAULT_PAGE_SIZE,
        max_pages: int = DEFAULT_MAX_PAGES,
        offset: int = 0,
        accurate: bool = False,
        start_time: Optional[int] = None,
        end_time: Optional[int] = None,
    ) -> dict[str, Any]:
        if not search.strip():
            raise ValueError("search must be a non-empty string")
        self._validate_paging(page_size, max_pages)
        if offset < 0:
            raise ValueError("offset must be >= 0")
        path = "/floors/search"
        failures_before = len(self.failures)
        items: list[Any] = []
        seen_ids: set[Any] = set()
        pages_fetched = 0

        for page_index in range(max_pages):
            current_offset = offset + page_index * page_size
            context = {"page": page_index + 1, "offset": current_offset}
            try:
                batch = self._get_json(
                    path,
                    {
                        "search": search,
                        "size": page_size,
                        "offset": current_offset,
                        "accurate": "true" if accurate else "false",
                        "start_time": start_time,
                        "end_time": end_time,
                    },
                    context=context,
                )
            except ApiError:
                break
            pages_fetched += 1
            if not isinstance(batch, list):
                self._record_schema_failure(path, context, "expected an array response")
                break
            if not batch:
                break
            for row in batch:
                row_id = row.get("id") if isinstance(row, dict) else None
                if row_id is None:
                    items.append(row)
                elif row_id not in seen_ids:
                    seen_ids.add(row_id)
                    items.append(row)
            if len(batch) < page_size:
                break

        return {
            "items": items,
            "pages_fetched": pages_fetched,
            "failures": self.failures[failures_before:],
        }

    def get_hole(self, hole_id: int) -> Any:
        self._validate_id(hole_id, "hole_id")
        return self._get_json(f"/holes/{hole_id}")

    def list_hole_floors(
        self,
        hole_id: int,
        *,
        page_size: int = DEFAULT_PAGE_SIZE,
        max_pages: int = DEFAULT_MAX_PAGES,
        offset: int = 0,
        sort: str = "asc",
        order_by: str = "id",
    ) -> dict[str, Any]:
        self._validate_id(hole_id, "hole_id")
        self._validate_paging(page_size, max_pages)
        if offset < 0:
            raise ValueError("offset must be >= 0")
        if sort not in {"asc", "desc"}:
            raise ValueError("sort must be asc or desc")
        if order_by not in {"id", "like"}:
            raise ValueError("order_by must be id or like")
        path = f"/holes/{hole_id}/floors"
        failures_before = len(self.failures)
        items: list[Any] = []
        seen_ids: set[Any] = set()
        pages_fetched = 0

        for page_index in range(max_pages):
            current_offset = offset + page_index * page_size
            context = {"page": page_index + 1, "offset": current_offset, "hole_id": hole_id}
            try:
                batch = self._get_json(
                    path,
                    {"size": page_size, "offset": current_offset, "sort": sort, "order_by": order_by},
                    context=context,
                )
            except ApiError:
                break
            pages_fetched += 1
            if not isinstance(batch, list):
                self._record_schema_failure(path, context, "expected an array response")
                break
            if not batch:
                break
            for row in batch:
                row_id = row.get("id") if isinstance(row, dict) else None
                if row_id is None:
                    items.append(row)
                elif row_id not in seen_ids:
                    seen_ids.add(row_id)
                    items.append(row)
            if len(batch) < page_size:
                break

        return {
            "items": items,
            "pages_fetched": pages_fetched,
            "failures": self.failures[failures_before:],
        }

    def get_floor(self, floor_id: int) -> Any:
        self._validate_id(floor_id, "floor_id")
        return self._get_json(f"/floors/{floor_id}")

    @staticmethod
    def _validate_id(value: int, name: str) -> None:
        if not isinstance(value, int) or value <= 0:
            raise ValueError(f"{name} must be a positive integer")


class DankeClient(ReadOnlyApiClient):
    def __init__(self, **kwargs: Any):
        kwargs.setdefault("base_url", DANKE_BASE_URL)
        kwargs.setdefault("service", "danke")
        kwargs.setdefault("token_env", "DANKE_ACCESS_TOKEN")
        super().__init__(**kwargs)

    def search_course_groups(
        self,
        query: str,
        *,
        page_size: int = 25,
        max_pages: int = DEFAULT_MAX_PAGES,
        page: int = 1,
    ) -> dict[str, Any]:
        if not query.strip():
            raise ValueError("query must be a non-empty string")
        self._validate_paging(page_size, max_pages)
        if page < 1:
            raise ValueError("page must be >= 1")
        path = "/v3/course_groups/search"
        failures_before = len(self.failures)
        items: list[Any] = []
        seen_ids: set[Any] = set()
        pages_fetched = 0

        for page_index in range(max_pages):
            current_page = page + page_index
            context = {"page": current_page, "page_size": page_size}
            try:
                response = self._get_json(
                    path,
                    {"query": query, "page": current_page, "page_size": page_size},
                    context=context,
                )
            except ApiError:
                break
            pages_fetched += 1
            if not isinstance(response, dict) or not isinstance(response.get("items"), list):
                self._record_schema_failure(path, context, "expected an object containing an items array")
                break
            batch = response["items"]
            if not batch:
                break
            for row in batch:
                row_id = row.get("id") if isinstance(row, dict) else None
                if row_id is None:
                    items.append(row)
                elif row_id not in seen_ids:
                    seen_ids.add(row_id)
                    items.append(row)
            if len(batch) < page_size:
                break

        return {
            "items": items,
            "pages_fetched": pages_fetched,
            "failures": self.failures[failures_before:],
        }

    def get_course_group(self, group_id: int) -> Any:
        self._validate_id(group_id, "group_id")
        return self._get_json(f"/v3/course_groups/{group_id}")

    def list_course_reviews(self, course_id: int) -> Any:
        self._validate_id(course_id, "course_id")
        path = f"/courses/{course_id}/reviews"
        response = self._get_json(path)
        if not isinstance(response, list):
            self._record_schema_failure(path, {}, "expected an array response")
            raise ApiError("expected an array response", kind="schema")
        return response

    def get_review(self, review_id: int) -> Any:
        self._validate_id(review_id, "review_id")
        return self._get_json(f"/reviews/{review_id}")

    @staticmethod
    def _validate_id(value: int, name: str) -> None:
        if not isinstance(value, int) or value <= 0:
            raise ValueError(f"{name} must be a positive integer")