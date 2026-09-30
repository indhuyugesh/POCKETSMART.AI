import json
from urllib.parse import quote_plus
from .config import GOOGLE_API_KEY, GEMINI_MODEL
from .schemas import HomeBudgetInput, PartyBudgetInput, JewelryBudgetInput
try:
    from google import genai
    from google.genai import types
except Exception:
    genai = None; types = None

def _links(q):
    q = quote_plus(q)
    return {"amazon":f"https://www.amazon.in/s?k={q}","flipkart":f"https://www.flipkart.com/search?q={q}","myntra":f"https://www.myntra.com/{q}","meesho":f"https://www.meesho.com/search?q={q}"}
def _extract_json(text):
    text = (text or "").strip().replace("```json","").replace("```","")
    a,b=text.find("{"),text.rfind("}")
    if a<0 or b<0: raise ValueError("No JSON returned")
    return json.loads(text[a:b+1])
def _generate(prompt, image_bytes=None, mime_type=None):
    if not GOOGLE_API_KEY or genai is None: raise RuntimeError("AI not configured")
    client=genai.Client(api_key=GOOGLE_API_KEY); contents=[prompt]
    if image_bytes: contents.append(types.Part.from_bytes(data=image_bytes,mime_type=mime_type or "image/jpeg"))
    r=client.models.generate_content(model=GEMINI_MODEL,contents=contents,config=types.GenerateContentConfig(temperature=0.2,response_mime_type="application/json"))
    return _extract_json(r.text)
def _normalize(result,budget,kind):
    result["total_budget"]=float(budget); spent=0.0
    items=result.get("jewelry_recommendations",[]) if kind=="jewelry" else [i for c in result.get("budget_breakdown",[]) for i in c.get("items",[])]
    for item in items:
        p=float(item.get("estimated_price",0) or 0); q=float(item.get("quantity",1) or 1); spent += p*q
        if item.get("search_terms") and not item.get("shopping_links"): item["shopping_links"]=_links(item["search_terms"])
    result["remaining_budget"]=round(max(0,budget-spent),2); return result

def home_recommendations(d:HomeBudgetInput):
    prompt=f'''You are PocketSmart, an India-focused budget planner. Create a practical home interior shopping plan in INR for total budget {d.total_budget:.2f}. Rooms: {", ".join(d.rooms) or "Not specified"}. Lights: {d.num_lights}; fans: {d.num_fans}; furniture: {d.num_furniture}; dining tables: {d.num_dining_tables}. Requirements: {d.requirements or "None"}. Keep total <= budget. Return JSON with total_budget, budget_breakdown [{ {"category":"...","allocation":0,"items":[{"name":"...","description":"...","estimated_price":0,"quantity":1,"search_terms":"..."}]} }], remaining_budget, additional_suggestions, calculation_table_inr.'''
    try:return _normalize(_generate(prompt),d.total_budget,"home")
    except Exception:return fallback_home(d)
def party_recommendations(d:PartyBudgetInput):
    prompt=f'''You are PocketSmart, an India-focused party planner. Create a detailed event budget in INR for {d.total_budget:.2f}. Party: {d.party_type}; venue: {d.venue_type or "Not specified"}; guests: {d.num_guests}; catering: {d.needs_catering}; decoration: {d.needs_decoration}; entertainment: {d.needs_entertainment}; requirements: {d.additional_requirements or "None"}. Keep total <= budget. Return JSON with total_budget, budget_breakdown, venue_suggestions, remaining_budget, additional_suggestions, calculation_table_inr. Each item needs name, description, estimated_price, quantity, search_terms.'''
    try:return _normalize(_generate(prompt),d.total_budget,"party")
    except Exception:return fallback_party(d)
def jewelry_recommendations(d:JewelryBudgetInput,image_bytes=None,mime_type=None):
    prompt=f'''You are PocketSmart, an India-focused jewelry stylist and budget planner. Recommend jewelry within INR {d.total_budget:.2f}. Occasion: {d.occasion}. Preferences: {d.preferences or "Not specified"}. If an outfit image is provided, analyze only visible colors/style/formality and do not identify the person. Return JSON with outfit_analysis, total_budget, jewelry_recommendations, remaining_budget, styling_tips. Each recommendation needs name, description, estimated_price, quantity, search_terms. Never exceed budget.'''
    try:return _normalize(_generate(prompt,image_bytes,mime_type),d.total_budget,"jewelry")
    except Exception:return fallback_jewelry(d,image_bytes is not None)
def _item(name,desc,price,qty,query): return {"name":name,"description":desc,"estimated_price":round(price,2),"quantity":qty,"search_terms":query,"shopping_links":_links(query)}
def fallback_home(d):
    specs=[("Lighting",.20,max(1,d.num_lights)),("Ceiling Fans",.15,max(1,d.num_fans)),("Furniture",.45,max(1,d.num_furniture)),("Dining",.20,max(1,d.num_dining_tables))]; bs=[]; spent=0
    for cat,ratio,qty in specs:
        alloc=d.total_budget*ratio; price=alloc/qty; bs.append({"category":cat,"allocation":round(alloc,2),"items":[_item(cat,f"Budget-friendly {cat.lower()} for Indian homes.",price,qty,f"{cat} budget India")]}); spent+=price*qty
    return {"total_budget":d.total_budget,"budget_breakdown":bs,"remaining_budget":round(max(0,d.total_budget-spent),2),"additional_suggestions":["Compare multiple sellers.","Prioritize essentials first.","Reserve money for delivery and installation."],"calculation_table_inr":[]}
def fallback_party(d):
    specs=[("Venue",.30),("Catering",.35 if d.needs_catering else .20),("Decoration",.20 if d.needs_decoration else .10),("Entertainment",.15 if d.needs_entertainment else .05)]; s=sum(x[1] for x in specs); bs=[]; spent=0
    for cat,r in specs:
        alloc=d.total_budget*r/s; bs.append({"category":cat,"allocation":round(alloc,2),"items":[_item(cat,f"Practical {cat.lower()} allocation for an India-based event.",alloc,1,f"{cat} {d.party_type} India")]}); spent+=alloc
    return {"total_budget":d.total_budget,"budget_breakdown":bs,"venue_suggestions":[{"name":"Local banquet/community hall","type":d.venue_type or "Event venue","capacity":d.num_guests,"estimated_cost":round(d.total_budget*.30,2),"search_terms":f"{d.party_type} venue near me"}],"remaining_budget":round(max(0,d.total_budget-spent),2),"additional_suggestions":["Get written vendor quotes.","Bundle services when possible.","Keep an emergency reserve."],"calculation_table_inr":[]}
def fallback_jewelry(d,has_image=False):
    recs=[]
    for name,r in [("Necklace",.40),("Earrings",.25),("Bracelet",.20),("Ring",.15)]: recs.append(_item(name,f"Versatile {name.lower()} suitable for the occasion.",d.total_budget*r,1,f"{name} {d.occasion} Indian jewelry"))
    return {"outfit_analysis":{"colors":["Image provided" if has_image else "Not analyzed"],"style":"Occasion-focused","formality":"Based on selected occasion"},"total_budget":d.total_budget,"jewelry_recommendations":recs,"remaining_budget":0,"styling_tips":["Match metal tone with outfit accents.","Balance one statement piece with simpler pieces.","Check return/exchange policies before buying."]}
