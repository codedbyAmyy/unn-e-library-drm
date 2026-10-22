
"""Run one batch of pending CAS email jobs."""

from app.database import SessionLocal
from app.services.email_worker import process_email_queue


def main():
    with SessionLocal() as db:
        processed = process_email_queue(
            db,
            batch_size=20,
        )

    print(f"Email jobs processed: {processed}")


if __name__ == "__main__":
    main()
