from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from modules.summerization.service import SummerizationService
from core.middleware import is_authenticated


router = APIRouter(prefix="/summarization", tags=["Summarization"])

summerizerization_service = SummerizationService()


@router.get("/debates/{debate_id}/summarize")
async def summarize_debate(debate_id: int, user: dict = Depends(is_authenticated)):
    return summerizerization_service.generate_summary(debate_id)


@router.get("/debates/{debate_id}/summarize/report")
async def download_summarize_debate(debate_id: int, user: dict = Depends(is_authenticated)):
    file_path = summerizerization_service.get_report_path(debate_id)
    if not file_path:
        raise HTTPException(status_code=404, detail="Report not found")

    return FileResponse(
        path=file_path,
        media_type="application/pdf",
        filename=f"debate_summary_{debate_id}.pdf",
    )