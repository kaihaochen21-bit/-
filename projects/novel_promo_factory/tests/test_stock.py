import json
import httpx
import pytest

from app.stock import PexelsClient, PixabayClient, _select_pexels_file, _select_pixabay_file


def test_pexels_parse():
    async def handler(request: httpx.Request):
        assert request.headers["authorization"] == "pexels-key"
        return httpx.Response(200, json={
            "videos": [{
                "id": 1,
                "url": "https://www.pexels.com/video/1",
                "duration": 8,
                "width": 1080,
                "height": 1920,
                "user": {"name": "Tester"},
                "video_files": [{"link": "https://cdn.test/1.mp4", "width": 1080, "height": 1920}],
            }]
        })

    async def run():
        client = PexelsClient("pexels-key", transport=httpx.MockTransport(handler))
        return await client.search_videos("rain")

    result = __import__("asyncio").run(run())
    assert result[0].provider == "pexels"
    assert result[0].width == 1080
    assert result[0].license == "Pexels License"


def test_pixabay_parse():
    async def handler(request: httpx.Request):
        assert request.url.params["key"] == "pixabay-key"
        return httpx.Response(200, json={
            "hits": [{
                "id": 2,
                "tags": "rain, city",
                "pageURL": "https://pixabay.com/videos/id-2/",
                "user": "Tester",
                "duration": 7,
                "videos": {"medium": {"url": "https://cdn.test/2.mp4", "width": 720, "height": 1280}},
            }]
        })

    async def run():
        client = PixabayClient("pixabay-key", transport=httpx.MockTransport(handler))
        return await client.search_videos("rain")

    result = __import__("asyncio").run(run())
    assert result[0].provider == "pixabay"
    assert result[0].height == 1280
    assert result[0].license == "Pixabay Content License"


def test_file_selection_helpers():
    assert _select_pexels_file({"video_files": [{"link": "a", "width": 640, "height": 360}]})["link"] == "a"
    assert _select_pixabay_file({"videos": {"small": {"url": "b", "width": 640, "height": 360}}})["url"] == "b"

def test_pixabay_image_parse():
    async def handler(request: httpx.Request):
        return httpx.Response(200, json={
            "hits": [{
                "id": 3,
                "tags": "rain, window",
                "pageURL": "https://pixabay.com/photos/id-3/",
                "user": "Tester",
                "imageWidth": 1080,
                "imageHeight": 1920,
                "largeImageURL": "https://cdn.test/3.jpg",
            }]
        })

    async def run():
        client = PixabayClient("pixabay-key", transport=httpx.MockTransport(handler))
        return await client.search_images("rain")

    result = __import__("asyncio").run(run())
    assert result[0].provider == "pixabay"
    assert result[0].width == 1080
    assert result[0].download_url.endswith("3.jpg")


def test_safe_error_masks_key():
    from app.stock import _safe_error
    request = httpx.Request("GET", "https://pixabay.com/api/?key=secret-key&q=rain")
    response = httpx.Response(400, request=request, text="bad request")
    exc = httpx.HTTPStatusError("bad", request=request, response=response)
    message = _safe_error(exc)
    assert "secret-key" not in message
    assert "HTTP 400" in message
