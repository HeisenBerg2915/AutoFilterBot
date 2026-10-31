import asyncio
from database import files_col, files_col2, files_col3


async def clear_all_files():

    collections = [
        ("DB1", files_col),
        ("DB2", files_col2),
        ("DB3", files_col3)
    ]

    print("Starting database cleanup...")

    for db_name, collection in collections:

        if collection is None:
            print(f"{db_name}: Not connected. Skipped.")
            continue

        # Count before deletion
        total = await collection.count_documents({})

        # Delete all file records
        result = await collection.delete_many({
            "_id": {
                "$ne": "__index_round_robin_state__"
            }
        })

        print(
            f"{db_name}: "
            f"{result.deleted_count} files deleted."
        )

    print("Database cleanup completed!")


if __name__ == "__main__":
    asyncio.run(clear_all_files())
