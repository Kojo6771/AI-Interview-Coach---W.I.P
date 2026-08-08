from app.database import SessionLocal
from app.models.target_role import TargetRole


TARGET_ROLES = [
    {
        "name": "Software Engineer",
        "description": "Designs, develops, tests, and maintains software applications and systems."
    },
    {
        "name": "Frontend Developer",
        "description": "Builds user-facing web applications using technologies such as HTML, CSS, JavaScript, and React."
    },
    {
        "name": "Backend Developer",
        "description": "Develops server-side applications, APIs, databases, and business logic."
    },
    {
        "name": "Full Stack Developer",
        "description": "Works across both frontend and backend development to build complete web applications."
    },
    {
        "name": "Data Analyst",
        "description": "Analyses datasets to identify trends, generate insights, and support business decisions."
    },
    {
        "name": "Data Scientist",
        "description": "Uses statistics, machine learning, and programming to extract insights and build predictive models."
    },
    {
        "name": "Machine Learning Engineer",
        "description": "Develops, trains, deploys, and maintains machine learning models and systems."
    },
    {
        "name": "AI Engineer",
        "description": "Builds applications and systems that use artificial intelligence and machine learning technologies."
    },
    {
        "name": "DevOps Engineer",
        "description": "Automates software delivery, infrastructure management, deployment, and monitoring processes."
    },
    {
        "name": "Cloud Engineer",
        "description": "Designs, deploys, and manages cloud infrastructure and cloud-based applications."
    },
    {
        "name": "Cybersecurity Analyst",
        "description": "Monitors, identifies, investigates, and helps protect systems from cybersecurity threats."
    },
    {
        "name": "QA Engineer",
        "description": "Tests software systems to identify defects and ensure applications meet quality requirements."
    },
    {
        "name": "Mobile App Developer",
        "description": "Develops applications for mobile platforms such as Android and iOS."
    },
    {
        "name": "Database Administrator",
        "description": "Manages, maintains, secures, and optimises database systems."
    },
    {
        "name": "Business Analyst",
        "description": "Analyses business requirements and helps translate organisational needs into technical solutions."
    },
    {
        "name": "Product Manager",
        "description": "Defines product requirements, priorities, and strategy while coordinating product development."
    }
]


def seed_target_roles():
    db = SessionLocal()

    try:
        for role_data in TARGET_ROLES:

            existing_role = (
                db.query(TargetRole)
                .filter(TargetRole.name == role_data["name"])
                .first()
            )

            if existing_role:
                print(
                    f"Skipping {role_data['name']} - already exists"
                )
                continue

            role = TargetRole(
                name=role_data["name"],
                description=role_data["description"]
            )

            db.add(role)

        db.commit()

        print("Target roles seeded successfully.")

    except Exception as error:
        db.rollback()

        print(f"Error seeding target roles: {error}")

    finally:
        db.close()


if __name__ == "__main__":
    seed_target_roles()