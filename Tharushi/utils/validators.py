from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class PredictRequest(BaseModel):
    """Validation for predict endpoint"""
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    date: str = Field(..., pattern=r'^\d{4}-\d{2}-\d{2}$')

    @field_validator('date')
    def validate_date(cls, v):
        try:
            datetime.strptime(v, '%Y-%m-%d')
            return v
        except ValueError:
            raise ValueError('Date must be in YYYY-MM-DD format')


class ForecastRequest(BaseModel):
    """Validation for forecast endpoint"""
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    forecast_days: int = Field(default=7, ge=1, le=30)
    start_date: Optional[str] = Field(None, pattern=r'^\d{4}-\d{2}-\d{2}$')

    @field_validator('start_date')
    def validate_start_date(cls, v):
        if v is None:
            return v
        try:
            datetime.strptime(v, '%Y-%m-%d')
            return v
        except ValueError:
            raise ValueError('Date must be in YYYY-MM-DD format')

class HotspotsRequest(BaseModel):
    """Request model for hotspot retrieval"""
    date: Optional[str] = None
    risk_threshold: float = Field(default=0.7, ge=0, le=1)

    @field_validator('date')
    def validate_date(cls, v):
        """Validate date format if provided"""
        if v:
            try:
                datetime.strptime(v, '%Y-%m-%d')
                return v
            except ValueError:
                raise ValueError('Date must be in YYYY-MM-DD format')
        return v