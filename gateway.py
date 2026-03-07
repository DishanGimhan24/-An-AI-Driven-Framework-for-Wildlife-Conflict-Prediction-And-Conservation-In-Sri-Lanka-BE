"""
API Gateway - Routes requests to the correct microservice
"""

import os
import httpx
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn

app = FastAPI(title="Wildlife Conflict Prediction Gateway", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

CORRIDOR_SERVICE_URL = os.getenv("CORRIDOR_SERVICE_URL", "http://localhost:8000")
COLLISION_RISK_SERVICE_URL = os.getenv("COLLISION_RISK_SERVICE_URL", "http://localhost:8001")
WILDLIFE_CONFLICT_SERVICE_URL = os.getenv("WILDLIFE_CONFLICT_SERVICE_URL", "http://localhost:5001")


@app.get("/")
async def root():
    return {
        "name": "Wildlife Conflict Prediction Gateway",
        "services": {
            "corridor": {
                "url": CORRIDOR_SERVICE_URL,
                "endpoints": ["/corridors", "/nodes", "/road-crossings", "/predict_risk"]
            },
            "collision_risk": {
                "url": COLLISION_RISK_SERVICE_URL,
                "endpoints": ["/predict"]
            },
            "wildlife_conflict": {
                "url": WILDLIFE_CONFLICT_SERVICE_URL,
                "endpoints": ["/api/predict", "/api/forecast", "/api/historical", "/api/heatmap", "/api/stats", "/api/cities"]
            }
        }
    }


@app.get("/health")
async def health():
    """Check health of all services"""
    statuses = {}
    async with httpx.AsyncClient(timeout=5.0) as client:
        try:
            resp = await client.get(f"{CORRIDOR_SERVICE_URL}/health")
            statuses["corridor_service"] = "healthy" if resp.status_code == 200 else "unhealthy"
        except Exception:
            statuses["corridor_service"] = "unreachable"

        try:
            resp = await client.get(f"{COLLISION_RISK_SERVICE_URL}/")
            statuses["collision_risk_service"] = "healthy" if resp.status_code == 200 else "unhealthy"
        except Exception:
            statuses["collision_risk_service"] = "unreachable"

        try:
            resp = await client.get(f"{WILDLIFE_CONFLICT_SERVICE_URL}/api/health")
            statuses["wildlife_conflict_service"] = "healthy" if resp.status_code == 200 else "unhealthy"
        except Exception:
            statuses["wildlife_conflict_service"] = "unreachable"

    overall = "healthy" if all(v == "healthy" for v in statuses.values()) else "degraded"
    return {"status": overall, "services": statuses}


# ---- Proxy to Corridor Service ----

@app.get("/corridors/{path:path}")
@app.get("/corridors")
async def proxy_corridors(request: Request, path: str = ""):
    return await _proxy(request, CORRIDOR_SERVICE_URL, f"/corridors/{path}" if path else "/corridors")


@app.get("/nodes/{path:path}")
@app.get("/nodes")
async def proxy_nodes(request: Request, path: str = ""):
    return await _proxy(request, CORRIDOR_SERVICE_URL, f"/nodes/{path}" if path else "/nodes")


@app.get("/road-crossings/{path:path}")
@app.get("/road-crossings")
async def proxy_crossings(request: Request, path: str = ""):
    return await _proxy(request, CORRIDOR_SERVICE_URL, f"/road-crossings/{path}" if path else "/road-crossings")


@app.post("/predict_risk")
async def proxy_predict_risk(request: Request):
    return await _proxy(request, CORRIDOR_SERVICE_URL, "/predict_risk")


# ---- Proxy to Collision Risk Service ----

@app.post("/predict")
async def proxy_predict(request: Request):
    return await _proxy(request, COLLISION_RISK_SERVICE_URL, "/predict")


# ---- Proxy to Tharushi's Wildlife Conflict Service ----

@app.api_route("/api/{path:path}", methods=["GET", "POST"])
async def proxy_tharushi_api(request: Request, path: str):
    return await _proxy(request, WILDLIFE_CONFLICT_SERVICE_URL, f"/api/{path}")


# ---- Generic proxy helper ----

async def _proxy(request: Request, service_url: str, path: str):
    """Forward request to the target microservice"""
    url = f"{service_url}{path}"
    params = dict(request.query_params)

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            if request.method == "GET":
                resp = await client.get(url, params=params)
            elif request.method == "POST":
                body = await request.json()
                resp = await client.post(url, json=body, params=params)
            else:
                raise HTTPException(status_code=405, detail="Method not allowed")

            return JSONResponse(content=resp.json(), status_code=resp.status_code)
        except httpx.ConnectError:
            raise HTTPException(status_code=503, detail=f"Service unavailable: {url}")
        except Exception as e:
            raise HTTPException(status_code=502, detail=str(e))


if __name__ == "__main__":
    uvicorn.run("gateway:app", host="0.0.0.0", port=8080, reload=False)
