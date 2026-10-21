"""Supplier directory API backed by TinyDB."""

from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status

from services.api.auth_dependencies import get_current_user
from services.api.supplier_models import (
    SupplierCategory,
    SupplierCountry,
    SupplierCreate,
    SupplierRateUpdate,
    SupplierRecord,
    SupplierStatusUpdate,
)
from services.api.supplier_storage import open_supplier_table

router = APIRouter(
    prefix="/api/suppliers",
    tags=["Suppliers"],
    dependencies=[Depends(get_current_user)],
)


def _to_record(document: Any) -> SupplierRecord:
    record = dict(document)
    record["id"] = document.doc_id
    return SupplierRecord.model_validate(record)


def _get_supplier_or_404(supplier_id: int) -> SupplierRecord:
    try:
        with open_supplier_table() as table:
            document = table.get(doc_id=supplier_id)
    except OSError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error accessing supplier storage",
        ) from None
    if document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Supplier not found",
        )
    return _to_record(document)


@router.post("", response_model=SupplierRecord, status_code=status.HTTP_201_CREATED)
def create_supplier(supplier: SupplierCreate) -> SupplierRecord:
    record = supplier.model_dump(mode="json", exclude_none=True)
    record["updated_at"] = datetime.now(timezone.utc).isoformat()
    try:
        with open_supplier_table() as table:
            supplier_id = table.insert(record)
            created = table.get(doc_id=supplier_id)
    except OSError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error persisting supplier",
        ) from None
    return _to_record(created)


@router.get("", response_model=list[SupplierRecord])
def list_suppliers(
    country: SupplierCountry | None = Query(default=None),
    category: SupplierCategory | None = Query(default=None),
) -> list[SupplierRecord]:
    try:
        with open_supplier_table() as table:
            documents = table.all()
    except OSError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving suppliers from storage",
        ) from None

    suppliers = []
    for document in documents:
        if country is not None and document.get("country") != country:
            continue
        if category is not None and category not in document.get("categories", []):
            continue
        suppliers.append(_to_record(document))
    return suppliers


@router.get("/{supplier_id}", response_model=SupplierRecord)
def get_supplier(supplier_id: int) -> SupplierRecord:
    return _get_supplier_or_404(supplier_id)


@router.patch("/{supplier_id}/rate", response_model=SupplierRecord)
def update_supplier_rate(
    supplier_id: int,
    update: SupplierRateUpdate,
) -> SupplierRecord:
    fields = {
        "monthly_rate": update.monthly_rate,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    try:
        with open_supplier_table() as table:
            updated_ids = table.update(fields, doc_ids=[supplier_id])
            document = table.get(doc_id=supplier_id) if updated_ids else None
    except OSError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error updating supplier rate",
        ) from None
    if document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Supplier not found",
        )
    return _to_record(document)


@router.patch("/{supplier_id}/status", response_model=SupplierRecord)
def update_supplier_status(
    supplier_id: int,
    update: SupplierStatusUpdate,
) -> SupplierRecord:
    try:
        with open_supplier_table() as table:
            updated_ids = table.update(
                {"status": update.status},
                doc_ids=[supplier_id],
            )
            document = table.get(doc_id=supplier_id) if updated_ids else None
    except OSError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error updating supplier status",
        ) from None
    if document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Supplier not found",
        )
    return _to_record(document)


@router.delete("/{supplier_id}", status_code=status.HTTP_200_OK)
def delete_supplier(supplier_id: int) -> dict[str, int | bool]:
    try:
        with open_supplier_table() as table:
            deleted_ids = table.remove(doc_ids=[supplier_id])
    except OSError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error deleting supplier",
        ) from None
    if not deleted_ids:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Supplier not found",
        )
    return {"id": supplier_id, "deleted": True}