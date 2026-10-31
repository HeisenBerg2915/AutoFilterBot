import io

from pyrogram import Client, filters
from config import ADMINS
from database import missing_col


@Client.on_message(
    filters.command("missing") & filters.private
)
async def missing_command(client, message):

    if not message.from_user or message.from_user.id not in ADMINS:
        return

    movies = await missing_col.find(
        {},
        {"_id": 0, "movie_name": 1}
    ).sort(
        "movie_name", 1
    ).to_list(length=None)

    if not movies:
        await message.reply_text(
            "✅ No Missing Movies Found!"
        )
        return

    movie_names = [
        movie["movie_name"]
        for movie in movies
        if movie.get("movie_name")
    ]

    report = (
        "MISSING MOVIES REPORT\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        + "\n".join(
            f"{i}. {name}"
            for i, name in enumerate(movie_names, 1)
        )
        + "\n\n━━━━━━━━━━━━━━━━━━\n"
        + f"Total Movies: {len(movie_names)}"
    )

    file = io.BytesIO(report.encode("utf-8"))
    file.name = "missing_movies.txt"

    await client.send_document(
        chat_id=message.chat.id,
        document=file,
        caption="📄 Missing Movies Report"
    )
