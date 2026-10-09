from datetime import date, datetime, timedelta, timezone
import re
from typing import Literal
from pydantic import BaseModel, Field, field_validator, model_validator

PropertyType = Literal['any', 'flat', 'pg', 'hostel', 'hotel', 'house']

class SelectedLocation(BaseModel):
    name: str = Field(min_length=1, max_length=180)
    address: str = Field(default='', max_length=240)
    lat: float = Field(ge=-90, le=90, allow_inf_nan=False)
    lng: float = Field(ge=-180, le=180, allow_inf_nan=False)

class SearchRequest(BaseModel):
    area: str = Field(min_length=2, max_length=160)
    city: str = Field(default='Ahmedabad', min_length=2, max_length=80)
    location: SelectedLocation | None = None
    property_types: list[Literal['flat','pg','hostel','hotel','house']] | None = Field(default=None,min_length=1,max_length=5)
    destination: str = Field(default='', max_length=240)
    mode: Literal['live', 'demo'] = 'live'
    property_type: PropertyType = 'any'
    budget: int | None = Field(default=None, ge=1000, le=1000000)
    strict_budget: bool = True
    household: Literal['solo', 'couple', 'family', 'friends'] = 'solo'
    occupants: int = Field(default=1, ge=1, le=20)
    gender_requirement: Literal['any', 'women', 'men','both','unknown'] = 'any'
    hotel_budget: int | None = Field(default=None, ge=100, le=1000000)
    radius_km: float | None = Field(default=None,gt=0,le=50)
    photos_only: bool = False
    known_only: bool = False
    bedrooms: int | None = Field(default=None, ge=0, le=10)
    amenities: list[Literal['kitchen','parking','furnished','lift','security','food','accessible','pets']] = Field(default_factory=list, max_length=8)
    priority: Literal['balanced','commute','cost','security','space'] = 'balanced'
    travel_mode: Literal['transit','driving','two_wheeler','walking','cycling'] = 'transit'
    departure_time: str = '09:00'
    return_time: str = '18:00'
    office_days: int = Field(default=22, ge=0, le=31)
    max_commute: int | None = Field(default=None, ge=5, le=180)
    check_in: date | None = None
    check_out: date | None = None
    sort: Literal['match','price','commute','rating','distance','safety'] = 'match'

    @field_validator('area','city','destination')
    @classmethod
    def clean_text(cls, v):
        return ' '.join(v.strip().split())

    @field_validator('departure_time','return_time')
    @classmethod
    def clock(cls, v):
        if not re.fullmatch(r'(?:[01]\d|2[0-3]):[0-5]\d', v):
            raise ValueError('Use a valid time in HH:MM format.')
        return v

    @model_validator(mode='after')
    def dates(self):
        if bool(self.check_in) != bool(self.check_out):
            raise ValueError('Provide both check-in and check-out dates.')
        if self.check_in:
            today = datetime.now(timezone(timedelta(hours=5, minutes=30))).date()
            if self.check_in < today or self.check_out <= self.check_in:
                raise ValueError('Choose future stay dates with check-out after check-in.')
        return self

class RecommendationRequest(BaseModel):
    property_ids: list[str] = Field(max_length=60)
    preferences: SearchRequest

class DetailRequest(BaseModel):
    preferences: SearchRequest
    section: Literal['overview','nearby','area','photos','reviews','commute','place'] = 'overview'

class PropertyInputs(BaseModel):
    price: int = Field(ge=1000, le=1000000)
    deposit: int | None = Field(default=None, ge=0, le=10000000)
    maintenance: int | None = Field(default=None, ge=0, le=100000)
    bedrooms: int | None = Field(default=None, ge=0, le=10)
    occupancy: int | None = Field(default=None, ge=1, le=20)

class ObservationInput(BaseModel):
    area: str = Field(min_length=2,max_length=160)
    city: str = Field(min_length=2,max_length=80)
    category: Literal['lighting','transport','security','water','noise','maintenance','other']
    sentiment: Literal['good','bad','serious']
    text: str = Field(min_length=15,max_length=800)
    occurred_on: date | None = None

    @field_validator('text')
    @classmethod
    def safe_observation(cls, v):
        if '<' in v or '>' in v or re.search(r'[\w.+-]+@[\w.-]+\.\w+|(?:\+?91[\s-]?)?[6-9]\d{9}', v):
            raise ValueError('Describe the area without HTML, email addresses or phone numbers.')
        return v.strip()

    @model_validator(mode='after')
    def observed_date(self):
        if self.occurred_on and self.occurred_on > datetime.now(timezone(timedelta(hours=5,minutes=30))).date():
            raise ValueError('The observation date cannot be in the future.')
        return self
