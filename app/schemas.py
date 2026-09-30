from pydantic import BaseModel, EmailStr, Field
class RegisterUser(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    email: EmailStr
    full_name: str | None = Field(default=None, max_length=120)
    password: str = Field(min_length=6, max_length=128)
class HomeBudgetInput(BaseModel):
    total_budget: float = Field(gt=0)
    num_lights: int = Field(default=1, ge=0, le=100)
    num_fans: int = Field(default=1, ge=0, le=100)
    num_furniture: int = Field(default=1, ge=0, le=100)
    num_dining_tables: int = Field(default=0, ge=0, le=20)
    rooms: list[str] = Field(default_factory=list)
    requirements: str | None = None
class PartyBudgetInput(BaseModel):
    total_budget: float = Field(gt=0)
    party_type: str
    venue_type: str | None = None
    num_guests: int = Field(default=10, ge=1, le=5000)
    needs_catering: bool = False
    needs_decoration: bool = False
    needs_entertainment: bool = False
    additional_requirements: str | None = None
class JewelryBudgetInput(BaseModel):
    total_budget: float = Field(gt=0)
    occasion: str
    preferences: str | None = None
