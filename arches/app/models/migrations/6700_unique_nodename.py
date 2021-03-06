# Generated by Django 2.2.13 on 2020-10-09 19:09

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("models", "6492_add_date_datatype_configs"),
    ]

    operations = [
        migrations.RunSQL(
            """
                UPDATE nodes AS n1
                SET name = n1.name || '_' || nodeid
                WHERE EXISTS (
                    SELECT n1.nodeid
                    FROM nodes AS n2
                    WHERE n1.nodeid <> n2.nodeid
                    AND n1.name = n2.name
                    AND n1.nodegroupid = n2.nodegroupid
                );
            """,
        ),
        migrations.AddConstraint(
            model_name="node", constraint=models.UniqueConstraint(fields=("name", "nodegroup"), name="unique_nodename_nodegroup"),
        ),
    ]
