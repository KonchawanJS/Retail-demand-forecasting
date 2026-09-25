from contextlib import asynccontextmanager
from pathlib import Path
import json
import logging
import os
import time
from fastapi import FastAPI, HTTPException, Query, Request
from pydantic import BaseModel, Field, ConfigDict, model_validator
from .service import RetailService

logger = logging.getLogger("uvicorn.error")


class OrderRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    sku: str = Field(min_length=1)
    on_hand: float = Field(default=50, ge=0)
    on_order: float = Field(default=0, ge=0)
    backorders: float = Field(default=0, ge=0)
    lead_days: int = Field(default=3, ge=0, le=27)
    review_days: int = Field(default=7, ge=1, le=28)
    safety_days: float = Field(default=2, ge=0, le=28)
    pack_size: int = Field(default=1, ge=1)
    min_order: int = Field(default=0, ge=0)

    @model_validator(mode="after")
    def protection_supported(self):
        if self.lead_days + self.review_days > 28:
            raise ValueError("Lead time + review interval must not exceed 28 days")
        return self


def create_app(root=None):
    root = Path(root or os.getenv("RETAIL_ROOT", "."))

    @asynccontextmanager
    async def lifespan(app):
        # Run the pipeline before startup; fail clearly if required artifacts are absent.
        app.state.retail = RetailService(root)
        yield

    app = FastAPI(title="Retail Forecast & Inventory Planner", version="0.1.0", lifespan=lifespan)

    @app.middleware("http")
    async def request_log(request: Request, call_next):
        start = time.perf_counter()
        response = await call_next(request)
        logger.info(json.dumps({"path": request.url.path, "status": response.status_code,
                                "latency_ms": round((time.perf_counter()-start)*1000, 2)}))
        return response

    @app.get("/health")
    def health():
        return {"status": "ok", "trained_through": app.state.retail.meta["trained_through"]}

    @app.get("/products")
    def products():
        return {"skus": app.state.retail.skus}

    @app.get("/metrics")
    def metrics():
        return app.state.retail.meta

    @app.get("/forecast/{sku}")
    def forecast(sku: str, horizon: int = Query(7, ge=1, le=28)):
        try:
            return app.state.retail.forecast(sku, horizon)
        except KeyError:
            raise HTTPException(404, "Unknown SKU") from None

    @app.post("/inventory/recommend")
    def order(request: OrderRequest):
        try:
            return app.state.retail.order(**request.model_dump())
        except KeyError:
            raise HTTPException(404, "Unknown SKU") from None
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc

    return app


app = create_app()
