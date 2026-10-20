
from app.config import settings
from supabase import create_client


def main():
    supabase = create_client(
        settings.SUPABASE_URL,
        settings.SUPABASE_KEY,
    )

    buckets = supabase.storage.list_buckets()
    bucket_names = [bucket.name for bucket in buckets]

    print("Supabase connection successful.")

    if "library-resources" in bucket_names:
        print("library-resources bucket found.")
    else:
        print("Bucket not found. Check the bucket name in Supabase.")


if __name__ == "__main__":
    main()
