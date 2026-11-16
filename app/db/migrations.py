
from sqlalchemy import inspect, text

from app.db.session import engine


def migrate_database() -> None:
    """
    Migrasi struktur tabel Users secara otomatis.
    Aman dijalankan berulang kali dan tidak menghapus data.
    """

    inspector = inspect(engine)

    if not inspector.has_table("Users"):
        raise RuntimeError(
            "Tabel Users belum tersedia."
        )

    existing_columns = {
        column["name"]
        for column in inspector.get_columns("Users")
    }

    migrations = {
        "Tempat_Tgl_Lahir": "VARCHAR(150) NULL",
        "Golongan_darah": "VARCHAR(2) NULL",
        "Email": "VARCHAR(255) NULL",
    }

    with engine.begin() as connection:

        # Tambahkan kolom baru jika belum tersedia
        for column_name, definition in migrations.items():
            if column_name not in existing_columns:
                connection.execute(
                    text(
                        f"ALTER TABLE `Users` "
                        f"ADD COLUMN `{column_name}` {definition}"
                    )
                )
                print(f"[DATABASE] Kolom {column_name} ditambahkan.")
            else:
                print(f"[DATABASE] Kolom {column_name} sudah tersedia.")

        # Kolom lama Tgl_lahir dibuat nullable
        if "Tgl_lahir" in existing_columns:
            connection.execute(
                text(
                    "ALTER TABLE `Users` "
                    "MODIFY COLUMN `Tgl_lahir` DATE NULL"
                )
            )
            print("[DATABASE] Kolom Tgl_lahir sekarang nullable.")

    print("[DATABASE] Migrasi selesai.")
