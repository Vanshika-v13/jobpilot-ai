import os
import logging
from fastapi import APIRouter, HTTPException, status, Request
from schemas.export import ExportRequest, ExportResponse
from agents.export_agent import get_jobs_by_ids, get_export_filename, generate_excel_report, generate_pdf_report

logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/", response_model=ExportResponse)
async def export_jobs(request: Request, body: ExportRequest):
    """
    Export job listings to Excel or PDF.
    """
    # 1. Validate format
    fmt = body.format.lower()
    if fmt not in ["excel", "pdf"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported format: '{body.format}'. Must be 'excel' or 'pdf'."
        )

    # 2. Fetch jobs from DB
    jobs = await get_jobs_by_ids(body.job_ids)
    if not jobs:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No valid jobs found for the provided job IDs."
        )

    # 3. Generate deterministic filename
    filename = get_export_filename(body.job_ids, fmt)
    
    # 4. Determine file path
    # We resolve static path relative to the current working directory (backend/)
    static_dir = os.path.join("static", "exports")
    os.makedirs(static_dir, exist_ok=True)
    filepath = os.path.join(static_dir, filename)

    # 5. Generate file if it doesn't exist
    if not os.path.exists(filepath):
        try:
            if fmt == "excel":
                generate_excel_report(jobs, filepath)
            else:
                generate_pdf_report(jobs, filepath)
            logger.info(f"Successfully generated export file: {filepath}")
        except Exception as e:
            logger.error(f"Failed to generate export file: {e}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to generate export file: {str(e)}"
            )
    else:
        logger.info(f"Serving cached export file: {filepath}")

    # 6. Build the file URL
    base_url = str(request.base_url)
    file_url = f"{base_url.rstrip('/')}/static/exports/{filename}"

    return ExportResponse(
        file_url=file_url,
        format=fmt,
        job_count=len(jobs)
    )
