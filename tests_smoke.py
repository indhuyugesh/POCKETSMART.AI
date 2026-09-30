from app.ai import fallback_home
from app.schemas import HomeBudgetInput

def test_fallback_home_stays_in_budget():
    r=fallback_home(HomeBudgetInput(total_budget=50000,num_lights=5,num_fans=4,num_furniture=2,num_dining_tables=1))
    assert r['total_budget']==50000
    assert r['remaining_budget']>=0
