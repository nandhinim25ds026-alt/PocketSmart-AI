from pydantic import BaseModel
from typing import Optional


# ---------- Auth models ----------
class RegisterUser(BaseModel):
    username: str
    email: str
    password: str


class UserInDB(BaseModel):
    username: str
    email: str
    hashed_password: str


# ---------- Home Planner ----------
class HomeBudgetInput(BaseModel):
    total_budget: float
    num_lights: int = 0
    num_fans: int = 0
    num_furniture: int = 0
    num_dining_tables: int = 0
    has_living_room: bool = False
    has_kitchen: bool = False
    has_bedroom: bool = False
    additional_requirements: Optional[str] = None


# ---------- Party Planner ----------
class PartyBudgetInput(BaseModel):
    total_budget: float
    num_guests: int
    party_type: str
    venue_type: Optional[str] = None
    needs_catering: bool = True
    needs_decoration: bool = True
    needs_entertainment: bool = True
    additional_requirements: Optional[str] = None


# ---------- Jewelry Planner ----------
class JewelryBudgetInput(BaseModel):
    total_budget: float
    occasion: str
    preferences: Optional[str] = None
