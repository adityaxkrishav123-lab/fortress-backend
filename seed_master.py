import asyncio
import uuid
import hashlib
from datetime import datetime
from google.cloud import firestore

# --- Configuration ---
# Ensure service-account.json is in the same directory
db = firestore.AsyncClient.from_service_account_json("service-account.json")

def hash_pin(pin: str) -> str:
    """Simulates the backend PIN hashing (SHA-256)."""
    return hashlib.sha256(pin.encode()).hexdigest()

async def seed_data():
    print("Starting Master Seeding for Fortress Demo with UNIQUE PINS...")

    # Collections to seed
    users_ref = db.collection("users")
    ngos_ref = db.collection("ngos")
    inv_ref = db.collection("ngo_inventory")
    pins_ref = db.collection("user_pins")

    # 1. Citizen Account (The Requester)
    citizen_uid = "CITIZEN-001"
    citizen_pin = "121212"
    await users_ref.document(citizen_uid).set({
        "uid": citizen_uid,
        "name": "Sam Citizen",
        "email": "sam.citizen@fortress.org",
        "phone": "+919000000001",
        "role": "CITIZEN",
        "region": "Sector-12, North District",
        "is_verified": True,
        "created_at": datetime.utcnow().isoformat()
    })
    await pins_ref.document(citizen_uid).set({"pin_hash": hash_pin(citizen_pin)})
    print(f"Seeded Citizen: Sam Citizen (PIN: {citizen_pin})")

    # 2. Volunteer Accounts (The Responders)
    volunteers = [
        {"uid": "VOL-001", "name": "John Rescuer", "phone": "+919000000002", "prof": "Rescue Specialist", "pin": "101010"},
        {"uid": "VOL-002", "name": "Sarah Medic", "phone": "+919000000003", "prof": "Paramedic", "pin": "202020"},
    ]
    for v in volunteers:
        await users_ref.document(v["uid"]).set({
            "uid": v["uid"],
            "name": v["name"],
            "email": f"{v['name'].lower().replace(' ', '.')}@fortress.org",
            "phone": v["phone"],
            "role": "VOLUNTEER",
            "region": "Sector-12, North District",
            "profession": v["prof"],
            "is_verified": True,
            "created_at": datetime.utcnow().isoformat()
        })
        await pins_ref.document(v["uid"]).set({"pin_hash": hash_pin(v["pin"])})
        print(f"Seeded Volunteer: {v['name']} (PIN: {v['pin']})")

    # 3. NGO Accounts (The Powerhouses)
    ngos = [
        {
            "uid": "NGO-001", "pin": "111111",
            "name": "Fortress Alpha Relief", 
            "phone": "+919111111111", 
            "type": "Medical Relief", 
            "tags": ["Medicines", "First Aid", "Oxygen"],
            "region": "North District",
            "inventory": [("Medicines", 500), ("First Aid", 100)]
        },
        {
            "uid": "NGO-002", "pin": "222222",
            "name": "Unity Disaster Response", 
            "phone": "+919222222222", 
            "type": "Disaster Response", 
            "tags": ["Rescue", "Tents", "Shelter"],
            "region": "North District",
            "inventory": [("Tents", 50), ("Blankets", 200)]
        },
        {
            "uid": "NGO-003", "pin": "333333",
            "name": "Global Food Guard", 
            "phone": "+919333333333", 
            "type": "Food Security", 
            "tags": ["Dry Ration", "Cooked Food", "Water"],
            "region": "South District",
            "inventory": [("Dry Ration", 1000), ("Water", 2000)]
        },
        {
            "uid": "NGO-004", "pin": "444444",
            "name": "Red Cross Fortress", 
            "phone": "+919444444444", 
            "type": "Medical Relief", 
            "tags": ["Blood", "Oxygen", "Ambulance"],
            "region": "South District",
            "inventory": [("Oxygen", 40), ("Blood", 100)]
        },
        {
            "uid": "NGO-005", "pin": "555555",
            "name": "Hope Community Support", 
            "phone": "+919555555555", 
            "type": "Social Support", 
            "tags": ["Clothing", "Shelter", "Social Work"],
            "region": "West District",
            "inventory": [("Clothing", 300)]
        },
    ]

    for n in ngos:
        ngo_id = f"ORG-{uuid.uuid4().hex[:6].upper()}"
        # Create User Doc
        await users_ref.document(n["uid"]).set({
            "uid": n["uid"],
            "name": f"{n['name']} Admin",
            "email": f"admin@{n['name'].lower().replace(' ', '')}.org",
            "phone": n["phone"],
            "role": "NGO_ADMIN",
            "region": n["region"],
            "ngo_id": ngo_id,
            "is_verified": True,
            "created_at": datetime.utcnow().isoformat()
        })
        await pins_ref.document(n["uid"]).set({"pin_hash": hash_pin(n["pin"])})
        
        # Create NGO Doc
        await ngos_ref.document(ngo_id).set({
            "ngo_id": ngo_id,
            "name": n["name"],
            "admin_uid": n["uid"],
            "ngo_type": n["type"],
            "ngo_tags": n["tags"],
            "region": n["region"],
            "ngo_contact": n["phone"],
            "is_verified": True,
            "created_at": datetime.utcnow().isoformat()
        })

        # Create Inventory Docs
        for item, qty in n["inventory"]:
            await inv_ref.add({
                "ngo_id": ngo_id,
                "admin_uid": n["uid"],
                "item_name": item,
                "quantity": qty,
                "available": True,
                "region": n["region"],
                "last_updated": datetime.utcnow().isoformat()
            })
        
        print(f"Seeded NGO: {n['name']} (PIN: {n['pin']})")

    print("\nSeeding Complete! All 8 Master Accounts are live in Firestore with UNIQUE PINS.")

if __name__ == "__main__":
    asyncio.run(seed_data())
