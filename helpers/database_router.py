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
