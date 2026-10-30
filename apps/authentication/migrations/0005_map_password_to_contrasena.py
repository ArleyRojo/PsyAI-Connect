from django.db import migrations, models


def align_register_columns(apps, schema_editor):
    Register = apps.get_model("authentication", "Register")
    connection = schema_editor.connection
    table_name = Register._meta.db_table

    with connection.cursor() as cursor:
        tables = {
            name.casefold(): name
            for name in connection.introspection.table_names(cursor)
        }
        actual_table_name = tables.get(table_name.casefold())
        if actual_table_name is None:
            raise RuntimeError(f"Expected authentication table {table_name!r}")

        columns = {
            column.name
            for column in connection.introspection.get_table_description(
                cursor, actual_table_name
            )
        }
    had_contrasena_column = "contrasena" in columns

    for field_name in ("last_login", "email_verificado"):
        if field_name not in columns:
            schema_editor.add_field(Register, Register._meta.get_field(field_name))

    with connection.cursor() as cursor:
        columns = {
            column.name
            for column in connection.introspection.get_table_description(
                cursor, actual_table_name
            )
        }

    password_field = Register._meta.get_field("password")
    if "password" in columns and "contrasena" in columns:
        if not had_contrasena_column:
            quote = connection.ops.quote_name
            schema_editor.execute(
                f"UPDATE {quote(actual_table_name)} "
                f"SET {quote('contrasena')} = {quote('password')}"
            )
        schema_editor.remove_field(Register, password_field)
    elif "password" in columns:
        quote = connection.ops.quote_name
        if connection.vendor == "mysql":
            column_type = password_field.db_type(connection)
            schema_editor.execute(
                f"ALTER TABLE {quote(actual_table_name)} "
                f"CHANGE COLUMN {quote('password')} {quote('contrasena')} "
                f"{column_type} NOT NULL"
            )
        else:
            schema_editor.execute(
                f"ALTER TABLE {quote(actual_table_name)} "
                f"RENAME COLUMN {quote('password')} TO {quote('contrasena')}"
            )
    elif "contrasena" not in columns:
        raise RuntimeError(
            f"Expected a password column in authentication table {table_name!r}"
        )


class Migration(migrations.Migration):
    dependencies = [
        ("authentication", "0004_migrate_contrasena_to_argon2"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunPython(
                    align_register_columns
                ),
            ],
            state_operations=[
                migrations.RemoveField(
                    model_name="register",
                    name="contrasena",
                ),
                migrations.AlterField(
                    model_name="register",
                    name="password",
                    field=models.CharField(
                        db_column="contrasena",
                        max_length=255,
                        verbose_name="contrasena",
                    ),
                ),
            ],
        ),
    ]
