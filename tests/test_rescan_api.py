import pytest

from app.api.rescan import rescan
from app.schemas.rescan import RescanError, RescanRequest, RescanResponse


class _Pipeline:
    async def rescan(self, pages: int) -> RescanResponse:
        return RescanResponse(
            pages_scanned=pages,
            urls_found=2,
            processed=1,
            failed=1,
            errors=[RescanError(url="https://techcrunch.com/x", error="Could not extract article text")],
        )


@pytest.mark.asyncio
async def test_rescan_endpoint_function():
    payload = RescanRequest(pages=2)
    response = await rescan(payload=payload, pipeline=_Pipeline())
    assert response.pages_scanned == 2
    assert response.processed == 1
    assert response.failed == 1
