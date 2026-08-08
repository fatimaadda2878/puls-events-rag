import io

import app.openagenda as oa


class JsonResponse:
    def __init__(self, payload, status_code=200):
        self.payload = payload
        self.status_code = status_code
        self.response = self

    def raise_for_status(self):
        if self.status_code >= 400:
            import requests
            err = requests.HTTPError(f"{self.status_code}")
            err.response = self
            raise err

    def json(self):
        return self.payload


class CsvResponse:
    def __init__(self, text):
        self.status_code = 200
        self.raw = io.BytesIO(text.encode("utf-8"))
        self.raw.decode_content = False

    def raise_for_status(self):
        return None


class PaginationSession:
    def __init__(self):
        self.calls = []

    def get(self, url, params=None, timeout=None, stream=False):
        self.calls.append((url, dict(params or {}), stream))
        offset = int((params or {}).get("offset", 0))
        rows = [
            {
                "uid": str(i),
                "title_fr": f"E{i}",
                "location_city": "Paris",
                "firstdate_begin": "2099-01-01T00:00:00+00:00",
            }
            for i in range(offset, min(offset + 2, 3))
        ]
        return JsonResponse({"total_count": 3, "results": rows})


def test_records_pagination(monkeypatch):
    monkeypatch.setattr(oa, "OPENAGENDA_PAGE_SIZE", 2)
    session = PaginationSession()
    events = oa.fetch_all_events(session=session)
    assert len(events) == 3
    offsets = [
        params["offset"]
        for _, params, stream in session.calls
        if not stream and "offset" in params
    ]
    assert offsets == [0, 2]


class ExportSession:
    def __init__(self):
        self.calls = []

    def get(self, url, params=None, timeout=None, stream=False):
        self.calls.append((url, dict(params or {}), stream))
        if url.endswith("/records"):
            return JsonResponse(
                {
                    "total_count": 10001,
                    "results": [
                        {
                            "uid": "first",
                            "title_fr": "First",
                            "location_city": "Paris",
                            "firstdate_begin": "2099-01-01T00:00:00+00:00",
                        }
                    ],
                }
            )

        csv_text = (
            "uid;title_fr;location_city;firstdate_begin\n"
            "1;Event 1;Paris;2099-01-01T00:00:00+00:00\n"
            "2;Event 2;Paris;2099-01-02T00:00:00+00:00\n"
        )
        return CsvResponse(csv_text)


def test_switches_to_streaming_export():
    session = ExportSession()
    events = oa.fetch_all_events(session=session)
    assert [event["title"] for event in events] == ["Event 1", "Event 2"]
    assert any(stream for _, _, stream in session.calls)
