from database import (
    files_col,
    files_col2,
    files_col3
)


def get_target_collections(target="db1"):

    databases = {
        "db1": files_col,
        "db2": files_col2,
        "db3": files_col3
    }

    target = target.lower()

    if target == "all":
        return [
            collection
            for collection in databases.values()
            if collection is not None
        ]

    if target not in databases:
        return []

    collection = databases[target]

    if collection is None:
        return []

    return [collection]


async def save_file_to_databases(file_data, target="db1"):

    collections = get_target_collections(target)

    if not collections:
        return 0

    saved_count = 0

    for collection in collections:

        await collection.update_one(
            {"file_unique_id": file_data["file_unique_id"]},
            {"$set": file_data},
            upsert=True
        )

        saved_count += 1

    return saved_count
