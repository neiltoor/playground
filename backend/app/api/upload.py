import os
import uuid
import json
from pathlib import Path
from typing import List
from datetime import datetime

from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from fastapi.responses import JSONResponse

from app.config import settings
from app.models import UploadResponse, DocumentInfo
from app.rag_engine import get_rag_engine
from app.auth import get_current_user


router = APIRouter()


@router.post("/upload", response_model=UploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    user: dict = Depends(get_current_user)
):
    """
    Upload and ingest a document into the RAG system.

    Protected endpoint - requires authentication.
    Document will be associated with the current user.

    Args:
        file: The document file to upload
        user: Current authenticated user dict

    Returns:
        Upload response with document info
    """
    username = user["username"]
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

        # Prepare metadata with user ownership
        metadata = {
            "document_id": document_id,
            "filename": file.filename,
            "file_type": file_ext,
            "user_id": username
        }

        # Ingest into RAG system
        rag_engine = get_rag_engine()
        chunks_created = rag_engine.ingest_document(str(temp_file_path), metadata)

        # Save metadata file for document listing
        meta_file = upload_dir / f".{document_id}.meta.json"
        with open(meta_file, 'w') as f:
            json.dump({
                "user_id": username,
                "document_id": document_id,
                "filename": file.filename,
                "chunks": chunks_created,
                "upload_date": datetime.utcnow().isoformat()
            }, f)

        # Keep the file for persistent storage (don't delete)
        # File is now stored in /app/uploads which is mounted to /data/customer_docs

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
async def list_documents(user: dict = Depends(get_current_user)):
    """
    List user's documents + shared documents.

    Protected endpoint - requires authentication.
    Returns documents uploaded by current user plus shared docs (like neiltoor.pdf).

    Args:
        user: Current authenticated user dict

    Returns:
        List of document information
    """
    username = user["username"]
    try:
        upload_dir = Path(settings.UPLOAD_DIR)

        if not upload_dir.exists():
            return []

        documents = []

        # Always include neiltoor.pdf (shared document)
        neiltoor_path = upload_dir / "neiltoor.pdf"
        if neiltoor_path.is_file():
            stat = neiltoor_path.stat()
            documents.append(DocumentInfo(
                id="default-neiltoor",
                filename="neiltoor.pdf",
                upload_date=datetime.fromtimestamp(stat.st_mtime),
                chunk_count=0,
                is_shared=True
            ))

        # List user-specific documents
        for file_path in upload_dir.glob("*"):
            if file_path.is_file() and not file_path.name.startswith("."):
                # Skip neiltoor.pdf (already added)
                if file_path.name == "neiltoor.pdf":
                    continue

                # Parse filename: {document_id}_{original_filename}
                parts = file_path.name.split("_", 1)
                if len(parts) == 2:
                    document_id = parts[0]
                    original_filename = parts[1]

                    # Check if this document belongs to current user
                    # Read metadata from companion .meta.json file
                    meta_file = upload_dir / f".{document_id}.meta.json"
                    if meta_file.exists():
                        try:
                            with open(meta_file, 'r') as f:
                                meta = json.load(f)

                            # Only include user's own documents
                            if meta.get("user_id") == username:
                                stat = file_path.stat()
                                documents.append(DocumentInfo(
                                    id=document_id,
                                    filename=original_filename,
                                    upload_date=datetime.fromtimestamp(stat.st_mtime),
                                    chunk_count=meta.get("chunks", 0),
                                    is_shared=False
                                ))
                        except json.JSONDecodeError:
                            # Skip documents with invalid metadata
                            continue

        # Sort by upload date, most recent first
        documents.sort(key=lambda x: x.upload_date, reverse=True)

        return documents

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error listing documents: {str(e)}"
        )
