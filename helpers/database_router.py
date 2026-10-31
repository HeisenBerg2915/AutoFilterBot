from pymongo import ReturnDocument

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
