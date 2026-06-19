# =============================================================
# ECO-TRAVEL ADVISOR CHATBOT — actions.py
# Custom Actions — API Calls, Carbon Scoring, Ranking
# =============================================================

import os
import requests
from dotenv import load_dotenv
from typing import Any, Text, Dict, List, Optional

from rasa_sdk import Action, Tracker, FormValidationAction
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.events import SlotSet, AllSlotsReset, ConversationPaused
from rasa_sdk.types import DomainDict

# Load environment variables from .env file
load_dotenv()

# =============================================================
# CONSTANTS & CONFIGURATION
# =============================================================

CLIMATIQ_API_KEY   = os.getenv("PD33CRRJ357PHFS5JHZ64KC75C", "")
AMADEUS_API_KEY    = os.getenv("AMADEUS_API_KEY", "")
AMADEUS_API_SECRET = os.getenv("AMADEUS_API_SECRET", "")

# Carbon emission factors (kg CO2 per km per person)
# Source: MDPI Sustainability — Safaa et al. 2023 (Paper 14)
CARBON_FACTORS = {
    "flight": 0.255,
    "car":    0.171,
    "bus":    0.089,
    "train":  0.041,
}

# Approximate distances from Hyderabad (km)
DISTANCES = {
    "goa":        640,
    "kerala":     900,
    "bangalore":  570,
    "mumbai":     710,
    "delhi":      1500,
    "manali":     2000,
    "ooty":       650,
    "rishikesh":  1700,
    "coorg":      680,
    "shimla":     1800,
    "darjeeling": 2100,
    "jaipur":     1200,
    "chennai":    625,
    "kolkata":    1500,
    "paris":      7200,
    "amsterdam":  7400,
    "berlin":     7000,
    "london":     7600,
    "barcelona":  7300,
    "rome":       6800,
    "prague":     6900,
    "default":    800,
}

# Eco hotel database (demo data)
ECO_HOTELS_DB = {
    "goa": [
        {
            "name": "Wildernest Nature Resort",
            "rating": 4.5,
            "price_per_night": 4500,
            "eco_score": 9.2,
            "features": "Solar powered, rainwater harvesting, organic farm",
            "carbon_label": "🟢 Low Carbon"
        },
        {
            "name": "Alila Diwa Goa",
            "rating": 4.3,
            "price_per_night": 6000,
            "eco_score": 8.1,
            "features": "Green certified, waste management, local sourcing",
            "carbon_label": "🟢 Low Carbon"
        },
        {
            "name": "Standard Beach Resort",
            "rating": 4.0,
            "price_per_night": 3500,
            "eco_score": 5.5,
            "features": "Basic recycling programme",
            "carbon_label": "🟡 Medium Carbon"
        }
    ],
    "kerala": [
        {
            "name": "Spice Village CGH Earth",
            "rating": 4.8,
            "price_per_night": 8000,
            "eco_score": 9.8,
            "features": "100% solar, zero plastic, tribal community support",
            "carbon_label": "🟢 Low Carbon"
        },
        {
            "name": "Coconut Lagoon CGH Earth",
            "rating": 4.6,
            "price_per_night": 7000,
            "eco_score": 9.5,
            "features": "Heritage eco resort, boat transport only",
            "carbon_label": "🟢 Low Carbon"
        },
        {
            "name": "Kumarakom Lake Resort",
            "rating": 4.4,
            "price_per_night": 9000,
            "eco_score": 7.8,
            "features": "Green certification, responsible tourism",
            "carbon_label": "🟡 Medium Carbon"
        }
    ],
    "manali": [
        {
            "name": "Solang Valley Resort",
            "rating": 4.2,
            "price_per_night": 3500,
            "eco_score": 8.0,
            "features": "Solar heating, local materials construction",
            "carbon_label": "🟢 Low Carbon"
        },
        {
            "name": "Johnson's Hotel",
            "rating": 4.0,
            "price_per_night": 2500,
            "eco_score": 6.5,
            "features": "Eco-friendly practices, local food",
            "carbon_label": "🟡 Medium Carbon"
        }
    ],
    "default": [
        {
            "name": "EcoStay Premium",
            "rating": 4.3,
            "price_per_night": 5000,
            "eco_score": 8.5,
            "features": "Solar powered, water recycling, local produce",
            "carbon_label": "🟢 Low Carbon"
        },
        {
            "name": "Green Lodge",
            "rating": 4.1,
            "price_per_night": 3500,
            "eco_score": 7.2,
            "features": "Certified eco-friendly, waste reduction",
            "carbon_label": "🟢 Low Carbon"
        },
        {
            "name": "City Hotel Standard",
            "rating": 3.8,
            "price_per_night": 2500,
            "eco_score": 4.5,
            "features": "Basic sustainability measures",
            "carbon_label": "🔴 High Carbon"
        }
    ]
}

# Carbon offset programs
# Source: Nature Scientific Data — Karnik et al. 2025 (Paper 25)
OFFSET_PROGRAMS = [
    {
        "name": "Reforest India — Western Ghats",
        "type": "Reforestation",
        "cost_per_tonne": 15,
        "description": "Plant native trees in Western Ghats biodiversity hotspot",
        "verified": "Gold Standard Certified"
    },
    {
        "name": "Solar Urja — Rural India",
        "type": "Renewable Energy",
        "cost_per_tonne": 12,
        "description": "Fund solar panels for rural Indian communities",
        "verified": "VCS Certified"
    },
    {
        "name": "Himalayan Clean Cookstoves",
        "type": "Clean Energy",
        "cost_per_tonne": 10,
        "description": "Replace wood-burning stoves in Himalayan villages",
        "verified": "CDM Certified"
    },
    {
        "name": "Mangrove Restoration — Sundarbans",
        "type": "Blue Carbon",
        "cost_per_tonne": 18,
        "description": "Restore mangrove ecosystems in Sundarbans delta",
        "verified": "Plan Vivo Certified"
    }
]


# =============================================================
# HELPER FUNCTIONS
# =============================================================

def get_amadeus_token() -> Optional[str]:
    """Get Amadeus API access token."""
    try:
        url  = "https://test.api.amadeus.com/v1/security/oauth2/token"
        data = {
            "grant_type":    "client_credentials",
            "client_id":     AMADEUS_API_KEY,
            "client_secret": AMADEUS_API_SECRET
        }
        response = requests.post(url, data=data, timeout=10)
        if response.status_code == 200:
            return response.json().get("access_token")
        return None
    except Exception:
        return None


def calculate_carbon_kg(transport_mode: str, destination: str) -> float:
    """
    Calculate carbon footprint in kg CO2.
    Uses emission factors from MDPI Sustainability
    Safaa et al. 2023 (Paper 14).
    """
    dest_key = destination.lower() if destination else "default"
    distance = DISTANCES.get(dest_key, DISTANCES["default"])
    factor   = CARBON_FACTORS.get(
        transport_mode.lower() if transport_mode else "flight",
        CARBON_FACTORS["flight"]
    )
    return round(distance * factor, 2)


def get_carbon_label(carbon_kg: float) -> str:
    """Return colour-coded carbon label."""
    if carbon_kg < 50:
        return "🟢 Low Carbon"
    elif carbon_kg < 150:
        return "🟡 Medium Carbon"
    else:
        return "🔴 High Carbon"


def normalise(value: float, min_val: float, max_val: float) -> float:
    """Normalise a value between 0 and 1."""
    if max_val == min_val:
        return 0.5
    return (value - min_val) / (max_val - min_val)


def rank_options(options: List[Dict], sustainability_level: str) -> List[Dict]:
    """
    Rank options using weighted scoring model.
    Score = w_carbon * carbon_normalised
          + w_price  * price_normalised
          + w_eco    * eco_score_normalised
    Weights adjusted based on user sustainability preference.
    """
    if not options:
        return options

    # Adjust weights based on sustainability preference
    if sustainability_level == "high":
        w_carbon = 0.6
        w_price  = 0.1
        w_eco    = 0.3
    elif sustainability_level == "low":
        w_carbon = 0.2
        w_price  = 0.6
        w_eco    = 0.2
    else:
        w_carbon = 0.5
        w_price  = 0.3
        w_eco    = 0.2

    carbons    = [o.get("carbon_kg", 0) for o in options]
    prices     = [o.get("price", 0) for o in options]
    eco_scores = [o.get("eco_score", 5) for o in options]

    min_c, max_c = min(carbons), max(carbons)
    min_p, max_p = min(prices), max(prices)
    min_e, max_e = min(eco_scores), max(eco_scores)

    for option in options:
        carbon_norm = 1 - normalise(option.get("carbon_kg", 0), min_c, max_c)
        price_norm  = 1 - normalise(option.get("price", 0), min_p, max_p)
        eco_norm    = normalise(option.get("eco_score", 5), min_e, max_e)

        option["score"] = round(
            (w_carbon * carbon_norm) +
            (w_price  * price_norm)  +
            (w_eco    * eco_norm),
            3
        )

    return sorted(options, key=lambda x: x["score"], reverse=True)


# =============================================================
# ACTION 1: Get Eco Hotels
# =============================================================

class ActionGetEcoHotels(Action):

    def name(self) -> Text:
        return "action_get_eco_hotels"

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: DomainDict
    ) -> List[Dict[Text, Any]]:

        destination = tracker.get_slot("destination") or "default"
        budget      = tracker.get_slot("budget") or 10000
        dest_key    = destination.lower()

        hotels     = ECO_HOTELS_DB.get(dest_key, ECO_HOTELS_DB["default"])
        affordable = [
            h for h in hotels
            if h["price_per_night"] <= float(budget)
        ]

        if not affordable:
            affordable = sorted(
                hotels, key=lambda x: x["price_per_night"]
            )[:1]
            dispatcher.utter_message(
                text=f"⚠️ No hotels found within ₹{budget}. "
                     f"Showing most affordable option:"
            )

        if affordable:
            dispatcher.utter_message(
                text=f"🏨 Eco-friendly hotels in "
                     f"**{destination.title()}**:\n"
            )
            for i, hotel in enumerate(affordable[:3], 1):
                dispatcher.utter_message(
                    text=(
                        f"**Option {i}: {hotel['name']}** "
                        f"{hotel['carbon_label']}\n"
                        f"⭐ Rating: {hotel['rating']}/5\n"
                        f"💰 Price: ₹{hotel['price_per_night']}/night\n"
                        f"🌿 Eco Score: {hotel['eco_score']}/10\n"
                        f"✅ Features: {hotel['features']}\n"
                    )
                )
        else:
            dispatcher.utter_message(
                text=f"Sorry, could not find eco hotels in "
                     f"{destination} right now."
            )

        return []


# =============================================================
# ACTION 2: Get Transport Options
# =============================================================

class ActionGetTransportOptions(Action):

    def name(self) -> Text:
        return "action_get_transport_options"

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: DomainDict
    ) -> List[Dict[Text, Any]]:

        destination = tracker.get_slot("destination") or "default"
        dest_key    = destination.lower()
        distance    = DISTANCES.get(dest_key, DISTANCES["default"])

        dispatcher.utter_message(
            text=f"🚆 Transport options to "
                 f"**{destination.title()}** "
                 f"(approx. {distance} km):\n"
        )

        options_text = ""
        emoji_map    = {
            "flight": "✈️",
            "train":  "🚂",
            "bus":    "🚌",
            "car":    "🚗"
        }

        for mode, factor in CARBON_FACTORS.items():
            carbon        = round(distance * factor, 2)
            label         = get_carbon_label(carbon)
            options_text += (
                f"{emoji_map.get(mode, '🚗')} **{mode.title()}**: "
                f"{carbon} kg CO₂ {label}\n"
            )

        dispatcher.utter_message(text=options_text)

        train_carbon  = round(distance * CARBON_FACTORS["train"], 2)
        flight_carbon = round(distance * CARBON_FACTORS["flight"], 2)
        saving        = round(flight_carbon - train_carbon, 1)

        dispatcher.utter_message(
            text=f"💡 **Tip:** Choosing train over flight "
                 f"saves **{saving} kg CO₂** on this trip!"
        )

        return []


# =============================================================
# ACTION 3: Calculate Carbon Footprint
# =============================================================

class ActionCalculateCarbon(Action):

    def name(self) -> Text:
                return "action_calculate_carbon"

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: DomainDict
    ) -> List[Dict[Text, Any]]:

        destination    = tracker.get_slot("destination") or "default"
        transport_mode = tracker.get_slot("transport_mode") or "flight"
        num_travellers = tracker.get_slot("num_travellers") or 1

        carbon_per_person = calculate_carbon_kg(transport_mode, destination)
        total_carbon      = round(carbon_per_person * float(num_travellers), 2)
        label             = get_carbon_label(carbon_per_person)

        # Try Climatiq API if key available
        if CLIMATIQ_API_KEY and CLIMATIQ_API_KEY != "your_climatiq_key_here":
            try:
                dest_key = destination.lower()
                distance = DISTANCES.get(dest_key, DISTANCES["default"])
                headers  = {"Authorization": f"Bearer {CLIMATIQ_API_KEY}"}
                payload  = {
                    "emission_factor": {
                        "activity_id": f"passenger_transport-mode_{transport_mode.lower()}-fuel_source_na-distance_na-vehicle_age_na-vehicle_weight_na"
                    },
                    "parameters": {
                        "distance":      distance,
                        "distance_unit": "km",
                        "passengers":    int(num_travellers)
                    }
                }
                response = requests.post(
                    "https://beta3.api.climatiq.io/estimate",
                    json=payload,
                    headers=headers,
                    timeout=10
                )
                if response.status_code == 200:
                    data              = response.json()
                    carbon_per_person = round(
                        data.get("co2e", carbon_per_person), 2
                    )
                    total_carbon = round(
                        carbon_per_person * float(num_travellers), 2
                    )
            except Exception:
                pass  # Fall back to local calculation

        dispatcher.utter_message(
            text=(
                f"🌍 **Carbon Footprint Estimate:**\n"
                f"🚗 Transport: {transport_mode.title()}\n"
                f"📍 Destination: {destination.title()}\n"
                f"👤 Per person: {carbon_per_person} kg CO₂ {label}\n"
                f"👥 Total ({int(float(num_travellers))} travellers): "
                f"{total_carbon} kg CO₂\n\n"
                f"🌳 Equals planting "
                f"{round(total_carbon / 21, 1)} trees to offset."
            )
        )

        return [SlotSet("carbon_score", carbon_per_person)]


# =============================================================
# ACTION 4: Rank Options
# =============================================================

class ActionRankOptions(Action):

    def name(self) -> Text:
        return "action_rank_options"

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: DomainDict
    ) -> List[Dict[Text, Any]]:

        destination          = tracker.get_slot("destination") or "default"
        sustainability_level = tracker.get_slot("sustainability_level") or "medium"
        transport_mode       = tracker.get_slot("transport_mode") or "flight"
        dest_key             = destination.lower()

        hotels  = ECO_HOTELS_DB.get(dest_key, ECO_HOTELS_DB["default"])
        options = []

        for hotel in hotels:
            carbon = calculate_carbon_kg(transport_mode, destination)
            options.append({
                "name":      hotel["name"],
                "carbon_kg": carbon,
                "price":     hotel["price_per_night"],
                "eco_score": hotel["eco_score"],
                "label":     hotel["carbon_label"]
            })

        ranked = rank_options(options, sustainability_level)

        dispatcher.utter_message(
            text=(
                f"🏆 **Top Recommendations for "
                f"{destination.title()}**\n"
                f"Based on **{sustainability_level}** "
                f"sustainability preference:\n"
            )
        )

        medals = ["🥇", "🥈", "🥉"]
        for i, option in enumerate(ranked[:3], 1):
            dispatcher.utter_message(
                text=(
                    f"{medals[i-1]} **{option['name']}**\n"
                    f"   {option['label']}\n"
                    f"   💰 ₹{option['price']}/night\n"
                    f"   🌿 Eco Score: {option['eco_score']}/10\n"
                    f"   📊 Overall Score: {option['score']}/1.0\n"
                )
            )

        dispatcher.utter_message(
            text=(
                "📊 *Score = 50% carbon + "
                "30% price + 20% eco certification*"
            )
        )

        return []


# =============================================================
# ACTION 5: Recommend Carbon Offset
# =============================================================

class ActionRecommendOffset(Action):

    def name(self) -> Text:
        return "action_recommend_offset"

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: DomainDict
    ) -> List[Dict[Text, Any]]:

        carbon_score   = tracker.get_slot("carbon_score") or 100
        num_travellers = tracker.get_slot("num_travellers") or 1
        total_carbon   = float(carbon_score) * float(num_travellers)
        total_tonnes   = round(total_carbon / 1000, 3)

        dispatcher.utter_message(
            text=(
                f"🌳 **Carbon Offset Options**\n"
                f"Your trip produces **{total_carbon} kg CO₂** "
                f"({total_tonnes} tonnes).\n"
                f"Verified programs to neutralise it:\n"
            )
        )

        for i, program in enumerate(OFFSET_PROGRAMS[:3], 1):
            cost = round(total_tonnes * program["cost_per_tonne"], 2)
            dispatcher.utter_message(
                text=(
                    f"**{i}. {program['name']}**\n"
                    f"   🌿 Type: {program['type']}\n"
                    f"   ✅ Verified: {program['verified']}\n"
                    f"   💰 Cost to offset: €{cost}\n"
                    f"   📖 {program['description']}\n"
                )
            )

        dispatcher.utter_message(
            text=(
                "💡 Offsetting makes your trip **carbon neutral**. "
                "Choosing train over flight reduces emissions "
                "by up to 80% before offsetting!"
            )
        )

        return []


# =============================================================
# ACTION 6: Human Handover
# =============================================================

class ActionHumanHandover(Action):

    def name(self) -> Text:
        return "action_human_handover"

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: DomainDict
    ) -> List[Dict[Text, Any]]:

        destination          = tracker.get_slot("destination") or "Not provided"
        travel_dates         = tracker.get_slot("travel_dates") or "Not provided"
        budget               = tracker.get_slot("budget") or "Not provided"
        sustainability_level = tracker.get_slot("sustainability_level") or "Not provided"
        transport_mode       = tracker.get_slot("transport_mode") or "Not provided"
        carbon_score         = tracker.get_slot("carbon_score") or "Not calculated"
        num_travellers       = tracker.get_slot("num_travellers") or 1

        context_summary = (
            f"\n{'='*50}\n"
            f"ECO-TRAVEL ADVISOR — HANDOVER REQUEST\n"
            f"{'='*50}\n"
            f"Destination:          {destination}\n"
            f"Travel Dates:         {travel_dates}\n"
            f"Budget:               {budget}\n"
            f"Sustainability Level: {sustainability_level}\n"
            f"Transport Mode:       {transport_mode}\n"
            f"Travellers:           {num_travellers}\n"
            f"Carbon Score:         {carbon_score} kg CO₂\n"
            f"{'='*50}\n"
        )

        # In production: send via email/ticketing API
        print(context_summary)

        dispatcher.utter_message(
            text=(
                f"✅ **Details sent to eco-travel advisor:**\n"
                f"📍 Destination: {destination}\n"
                f"📅 Dates: {travel_dates}\n"
                f"💰 Budget: {budget}\n"
                f"🌿 Sustainability: {sustainability_level}\n"
                f"🚗 Transport: {transport_mode}\n\n"
                f"A human expert will contact you "
                f"within 24 hours. 🧑‍💼"
            )
        )

        return [
            SlotSet("handover_flag", True),
            ConversationPaused()
        ]


# =============================================================
# ACTION 7: Fallback Handler
# =============================================================

class ActionFallbackHandler(Action):

    def name(self) -> Text:
        return "action_fallback_handler"

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: DomainDict
    ) -> List[Dict[Text, Any]]:

        fallback_count = 0
        for event in reversed(tracker.events):
            if event.get("event") == "action" and \
               event.get("name") == "action_fallback_handler":
                fallback_count += 1
            else:
                break

        if fallback_count >= 2:
            dispatcher.utter_message(
                text=(
                    "I have had trouble understanding your last "
                    "few messages. Would you like me to connect "
                    "you with a human eco-travel advisor? "
                    "Say **yes** to be connected. 🧑‍💼"
                )
            )
        else:
            dispatcher.utter_message(
                text=(
                    "I am sorry, I did not understand that. 🤔\n"
                    "Could you try rephrasing? For example:\n"
                    "• 'I want to travel to Goa next week'\n"
                    "• 'Show me eco-friendly hotels in Kerala'\n"
                    "• 'What is the carbon footprint of a train to Manali?'"
                )
            )

        return []


# =============================================================
# FORM VALIDATION: Trip Planning Form
# =============================================================

class ValidateTripPlanningForm(FormValidationAction):

    def name(self) -> Text:
        return "validate_trip_planning_form"

    def validate_destination(
        self,
        slot_value: Any,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: DomainDict
    ) -> Dict[Text, Any]:
        if slot_value and len(str(slot_value)) > 2:
            dispatcher.utter_message(
                text=f"✅ Great! Planning trip to "
                     f"**{str(slot_value).title()}**."
            )
            return {"destination": slot_value}
        dispatcher.utter_message(
            text="Please provide a valid destination city."
        )
        return {"destination": None}

    def validate_budget(
        self,
        slot_value: Any,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: DomainDict
    ) -> Dict[Text, Any]:
        try:
            budget = float(str(slot_value).replace(",", ""))
            if budget > 0:
                dispatcher.utter_message(
                    text=f"✅ Budget set to ₹{budget:.0f}."
                )
                return {"budget": budget}
            dispatcher.utter_message(
                text="Please enter a budget greater than 0."
            )
            return {"budget": None}
        except (ValueError, TypeError):
            dispatcher.utter_message(
                text="Please enter a valid number (e.g. 5000)."
            )
            return {"budget": None}

    def validate_sustainability_level(
        self,
        slot_value: Any,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: DomainDict
    ) -> Dict[Text, Any]:
        valid = ["high", "medium", "low"]
        if str(slot_value).lower() in valid:
            dispatcher.utter_message(
                text=f"✅ Sustainability set to "
                     f"**{str(slot_value).title()}**."
            )
            return {"sustainability_level": str(slot_value).lower()}
        dispatcher.utter_message(
            text="Please choose: **high**, **medium**, or **low**."
        )
        return {"sustainability_level": None}

    def validate_transport_mode(
        self,
        slot_value: Any,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: DomainDict
    ) -> Dict[Text, Any]:
        valid     = ["flight", "train", "bus", "car"]
        emoji_map = {
            "flight": "✈️",
            "train":  "🚂",
            "bus":    "🚌",
            "car":    "🚗"
        }
        if str(slot_value).lower() in valid:
            dispatcher.utter_message(
                text=f"✅ Transport set to "
                     f"{emoji_map.get(str(slot_value).lower())} "
                     f"**{str(slot_value).title()}**."
            )
            return {"transport_mode": str(slot_value).lower()}
        dispatcher.utter_message(
            text="Please choose: **flight**, **train**, "
                 "**bus**, or **car**."
        )
        return {"transport_mode": None}

    def validate_travel_dates(
        self,
        slot_value: Any,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: DomainDict
    ) -> Dict[Text, Any]:
        if slot_value and len(str(slot_value)) > 2:
            dispatcher.utter_message(
                text=f"✅ Travel dates set to **{slot_value}**."
            )
            return {"travel_dates": slot_value}
        dispatcher.utter_message(
            text="Please provide valid travel dates "
                 "(e.g. next weekend, July 10-15)."
        )
        return {"travel_dates": None}