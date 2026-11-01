from pymongo import ReturnDocument, UpdateOne

from database import (
    files_col,
    files_col2,
    files_col3
)


def get_all_databases():

    databases = {
        "db1": files_col,
        "db2": files_col2,
        "db3": files_col3
    }

    return {
        name: collection
        for name, collection in databases.items()
        if collection is not None
    }


def get_target_collections(target="db1"):

    databases = get_all_databases()

    target = target.lower()

    if target == "all":
        return list(databases.values())

    if target not in databases:
        return []

    return [databases[target]]


async def is_duplicate(file_unique_id):

    databases = get_all_databases()

    for collection in databases.values():

        found = await collection.find_one(
            {
                "file_unique_id": file_unique_id
            },
            {
                "_id": 1
            }
        )

        if found:
            return True

    return False


async def get_next_round_robin_database():

    databases = get_all_databases()

    order = ["db1", "db2", "db3"]

    available = [
        name
        for name in order
        if name in databases
    ]

    if not available:
        return None

    # DB1 is used to store the persistent counter.
    if files_col is None:
        return None

    state = await files_col.find_one_and_update(
        {
            "_id": "__index_round_robin_state__"
        },
        {
            "$inc": {
                "counter": 1
            }
        },
        upsert=True,
        return_document=ReturnDocument.AFTER
    )

    counter = state.get("counter", 1)

    index = (counter - 1) % len(available)

    selected_name = available[index]

    return databases[selected_name]


async def save_file_to_databases(file_data, target="db1"):

    target = target.lower()

    databases = get_all_databases()

    if not databases:
        return 0

    # Check every database before saving.
    duplicate = await is_duplicate(
        file_data["file_unique_id"]
    )

    if duplicate:
        return 0

    # All DBs: distribute new files using round-robin.
    if target == "all":

        collection = await get_next_round_robin_database()

        if collection is None:
            return 0

    else:

        if target not in databases:
            return 0

        collection = databases[target]

    # Save only in the selected database.
    await collection.update_one(
        {
            "file_unique_id": file_data["file_unique_id"]
        },
        {
            "$set": file_data
        },
        upsert=True
    )

    return 1


# =====================================
# BULK FILE SAVE
# =====================================

async def save_files_to_databases(file_data_list, target="db1"):

    target = target.lower()

    databases = get_all_databases()

    if not databases or not file_data_list:
        return 0, len(file_data_list)

    # Collect unique IDs
    unique_ids = list({
        item["file_unique_id"]
        for item in file_data_list
        if item.get("file_unique_id")
    })

    if not unique_ids:
        return 0, len(file_data_list)

    # Check duplicates in all databases
    existing_ids = set()

    for collection in databases.values():

        cursor = collection.find(
            {
                "file_unique_id": {
                    "$in": unique_ids
                }
            },
            {
                "file_unique_id": 1,
                "_id": 0
            }
        )

        async for document in cursor:

            existing_ids.add(
                document["file_unique_id"]
            )

    # Remove duplicates
    new_files = []
    seen_ids = set()

    for item in file_data_list:

        uid = item.get("file_unique_id")

        if not uid:
            continue

        if uid in existing_ids or uid in seen_ids:
            continue

        seen_ids.add(uid)
        new_files.append(item)

    if not new_files:
        return 0, len(file_data_list)

    # Prepare database distribution
    operations = {}

    if target == "all":

        for item in new_files:

            collection = await get_next_round_robin_database()

            if collection is None:
                continue

            operations.setdefault(
                collection,
                []
            ).append(item)

    else:

        if target not in databases:
            return 0, len(file_data_list)

        operations[databases[target]] = new_files

    # Bulk write
    saved = 0

    for collection, items in operations.items():

        bulk_operations = [
            UpdateOne(
                {
                    "file_unique_id": item["file_unique_id"]
                },
                {
                    "$set": item
                },
                upsert=True
            )
            for item in items
        ]

        if bulk_operations:

            result = await collection.bulk_write(
                bulk_operations,
                ordered=False
            )

            saved += (
                result.upserted_count
                + result.modified_count
            )

    return saved, len(file_data_list) - saved
