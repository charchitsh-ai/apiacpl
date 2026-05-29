import asyncio
import logging
from sqlalchemy import select
from app.db.session import SessionLocal
from app.models.user import User
from app.models.symptom import Symptom
from app.models.speciality import Speciality
from app.core import security

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("AYKACare.Seeder")

# Initial specialized medical specialities list
SPECIALITIES_SEED = [
    {
        "name": "General Physician",
        "slug": "general-physician",
        "description": "Primary healthcare provider for general illnesses, common cold, and chronic disease management.",
    },
    {
        "name": "Cardiologist",
        "slug": "cardiologist",
        "description": "Specialists managing heart health, cardiovascular conditions, chest pain, and hypertension.",
    },
    {
        "name": "Dermatologist",
        "slug": "dermatologist",
        "description": "Skin, hair, nail disorder specialists, acne treatment, and dermatology procedures.",
    },
    {
        "name": "Pediatrician",
        "slug": "pediatrician",
        "description": "Medical care for infants, children, and adolescents.",
    },
    {
        "name": "Gynecologist",
        "slug": "gynecologist",
        "description": "Women's reproductive health, pregnancy, maternity care, and fertility treatment.",
    },
]

# Initial common symptoms list
SYMPTOMS_SEED = [
    {"name": "Fever", "slug": "fever", "description": "High body temperature often indicating infection."},
    {"name": "Chest Pain", "slug": "chest-pain", "description": "Discomfort or pain in the chest area, requiring cardiac attention."},
    {"name": "Acne", "slug": "acne", "description": "Skin condition causing pimples, blackheads, or skin inflammation."},
    {"name": "Cough", "slug": "cough", "description": "Reflex action to clear airways, common in respiratory tract infections."},
    {"name": "Abdominal Pain", "slug": "abdominal-pain", "description": "Pain or cramps in the stomach area."},
]

# Mapping symptoms to primary specialty recommendation
MAPPING_SEED = {
    "fever": ["general-physician", "pediatrician"],
    "chest-pain": ["cardiologist", "general-physician"],
    "acne": ["dermatologist"],
    "cough": ["general-physician", "pediatrician"],
    "abdominal-pain": ["general-physician", "gynecologist"],
}


async def seed_db():
    logger.info("Starting database seeding...")
    async with SessionLocal() as db:
        # 1. Seed Specialities
        specialities_map = {}
        for spec_data in SPECIALITIES_SEED:
            stmt = select(Speciality).filter(Speciality.slug == spec_data["slug"])
            res = await db.execute(stmt)
            spec = res.scalars().first()
            if not spec:
                spec = Speciality(**spec_data)
                db.add(spec)
                logger.info(f"Added Speciality: {spec_data['name']}")
            specialities_map[spec_data["slug"]] = spec

        # 2. Seed Symptoms & Symptom-Speciality Maps
        for sym_data in SYMPTOMS_SEED:
            stmt = select(Symptom).filter(Symptom.slug == sym_data["slug"])
            res = await db.execute(stmt)
            symptom = res.scalars().first()
            if not symptom:
                symptom = Symptom(**sym_data)
                db.add(symptom)
                logger.info(f"Added Symptom: {sym_data['name']}")

            # Connect mapping
            related_slugs = MAPPING_SEED.get(sym_data["slug"], [])
            for r_slug in related_slugs:
                target_spec = specialities_map.get(r_slug)
                if target_spec and target_spec not in symptom.specialities:
                    symptom.specialities.append(target_spec)
                    logger.info(f"Mapped Symptom '{symptom.name}' to Speciality '{target_spec.name}'")

        # 3. Seed default Admin/Doctor login
        admin_phone = "+919999999999"
        stmt = select(User).filter(User.phone == admin_phone)
        res = await db.execute(stmt)
        admin = res.scalars().first()
        if not admin:
            admin_data = {
                "full_name": "AYKA Administrator",
                "email": "admin@ayka.care",
                "phone": admin_phone,
                "hashed_password": security.hash_password("AykaCare@2026"),
                "is_active": True,
                "is_verified": True,
            }
            admin = User(**admin_data)
            db.add(admin)
            logger.info(f"Created default admin user with phone: {admin_phone} (Password: AykaCare@2026)")

        await db.commit()
    logger.info("Database seeding completed successfully.")


if __name__ == "__main__":
    asyncio.run(seed_db())
