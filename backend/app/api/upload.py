import os
import uuid
from pathlib import Path
from typing import List

from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse

from app.config import settings
from app.models import UploadResponse, DocumentInfo
from app.rag_engine import get_rag_engine


router = APIRouter()


@router.post("/upload", response_model=UploadResponse)
async def upload_document(file: UploadFile = File(...)):
    """
    Upload and ingest a document into the RAG system.

    Args:
        file: The document file to upload

    Returns:
        Upload response with document info
    """
    try:
        # Validate file extension
        file_ext = Path(file.filename).suffix.lower()
        if file_ext not in settings.ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail=f"File type {file_ext} not supported. Allowed types: {settings.ALLOWED_EXTENSIONS}"
            )

        # Validate file size
        contents = await file.read()
        if len(contents) > settings.MAX_UPLOAD_SIZE:
            raise HTTPException(
                status_code=400,
                detail=f"File size exceeds maximum allowed size of {settings.MAX_UPLOAD_SIZE} bytes"
            )

        # Generate unique document ID
        document_id = str(uuid.uuid4())

        # Save file temporarily
        upload_dir = Path(settings.UPLOAD_DIR)
        upload_dir.mkdir(parents=True, exist_ok=True)

        temp_file_path = upload_dir / f"{document_id}_{file.filename}"

        with open(temp_file_path, "wb") as f:
            f.write(contents)

        # Prepare metadata
        metadata = {
            "document_id": document_id,
            "filename": file.filename,
            "file_type": file_ext
        }

        # Ingest into RAG system
        rag_engine = get_rag_engine()
        chunks_created = rag_engine.ingest_document(str(temp_file_path), metadata)

        # Clean up temporary file
        os.remove(temp_file_path)

        return UploadResponse(
            document_id=document_id,
            filename=file.filename,
            status="success",
            chunks_created=chunks_created,
            message=f"Document uploaded and ingested successfully with {chunks_created} chunks"
        )

    except HTTPException:
        raise
    except Exception as e:
        # Clean up on error
        if 'temp_file_path' in locals() and os.path.exists(temp_file_path):
            os.remove(temp_file_path)

        raise HTTPException(
            status_code=500,
            detail=f"Error uploading document: {str(e)}"
        )


@router.get("/documents", response_model=List[DocumentInfo])
async def list_documents():
    """
    List all uploaded documents.

    Returns:
        List of document information
    """
    try:
        # Note: This is a simplified implementation
        # In production, you'd query the vector store for unique documents
        # For now, return an empty list as a placeholder
        return []

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error listing documents: {str(e)}"
        )
