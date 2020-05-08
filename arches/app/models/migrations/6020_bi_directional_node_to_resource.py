# Generated by Django 2.2.9 on 2020-04-30 17:16

import os
import uuid
import datetime
from django.db.models import Q
from django.db import migrations, models
from arches.app.search.search_engine_factory import SearchEngineFactory


def setup(apps):
    nodes = apps.get_model("models", "Node")
    tiles = apps.get_model("models", "Tile")
    relations = apps.get_model("models", "ResourceXResource")
    resource = apps.get_model("models", "Resource")
    resource_instance_nodes = {
        str(node["nodeid"]): node["datatype"]
        for node in nodes.objects.filter(Q(datatype="resource-instance") | Q(datatype="resource-instance-list")).values(
            "nodeid", "datatype"
        )
    }
    resource_instance_tiles = tiles.objects.filter(
        Q(nodegroup_id__node__datatype="resource-instance") | Q(nodegroup_id__node__datatype="resource-instance-list")
    ).distinct()
    root_ontology_classes = {
        str(node["graph_id"]): node["ontologyclass"] for node in nodes.objects.filter(istopnode=True).values("graph_id", "ontologyclass")
    }

    return resource, relations, resource_instance_nodes, resource_instance_tiles, root_ontology_classes


def create_relation(relations, resource, resourceinstanceid_from, resourceinstanceid_to, tileid, nodeid, root_ontology_classes):
    relationid = uuid.uuid4()
    relations.objects.create(
        resourcexid=relationid,
        resourceinstanceidfrom_id=resourceinstanceid_from,
        resourceinstanceidto_id=resourceinstanceid_to,
        tileid_id=tileid,
        nodeid_id=nodeid,
        modified=datetime.datetime.now(),
        created=datetime.datetime.now(),
    )

    ontologyClass = ""
    resourceName = ""
    try:
        resTo = resource.objects.get(pk=resourceinstanceid_to)
        ontologyClass = root_ontology_classes[str(resTo.graph_id)]
        se = SearchEngineFactory().create()
        resource_document = se.search(index="resources", id=resourceinstanceid_to)
        resourceName = resource_document["docs"][0]["_source"]["displayname"]
    except:
        pass

    ret = {
        "resourceId": resourceinstanceid_to,
        "ontologyProperty": "",
        "inverseOntologyProperty": "",
        "resourceName": resourceName,
        "ontologyClass": ontologyClass,
        "resourceXresourceId": str(relationid),
    }
    return ret


def create_resource_instance_tiledata(relations, tile, nodeid, datatype):
    if tile.data[nodeid] is None:
        return None
    else:
        new_tile_data = []
        for resourceRelationItem in tile.data[nodeid]:
            relation = relations.objects.get(resourcexid=resourceRelationItem["resourceXresourceId"])
            relation.delete()
            new_tile_data.append(str(resourceRelationItem["resourceId"]))

        if datatype == "resource-instance-list":
            return new_tile_data
        else:
            return new_tile_data[0]


def forward_migrate(apps, schema_editor, with_create_permissions=True):
    resource, relations, resource_instance_nodes, resource_instance_tiles, root_ontology_classes = setup(apps)
    # iterate over resource-instance tiles and identify resource-instance nodes
    for tile in resource_instance_tiles:
        for nodeid in tile.data.keys():
            if nodeid in resource_instance_nodes and tile.data[nodeid] is not None:
                # check if data is a list or string then replace resourceinstanceids with relationids
                new_tile_resource_data = []
                if isinstance(tile.data[nodeid], list):
                    for resourceinstanceidto in tile.data[nodeid]:
                        new_tile_resource_data.append(
                            create_relation(
                                relations,
                                resource,
                                tile.resourceinstance_id,
                                resourceinstanceidto,
                                tile.tileid,
                                nodeid,
                                root_ontology_classes,
                            )
                        )
                else:
                    new_tile_resource_data.append(
                        create_relation(
                            relations, resource, tile.resourceinstance_id, tile.data[nodeid], tile.tileid, nodeid, root_ontology_classes
                        )
                    )

                tile.data[nodeid] = new_tile_resource_data
                tile.save()


def reverse_migrate(apps, schema_editor, with_create_permissions=True):
    resource, relations, resource_instance_nodes, resource_instance_tiles, root_ontology_classes = setup(apps)
    for tile in resource_instance_tiles:
        for nodeid in tile.data.keys():
            if nodeid in resource_instance_nodes.keys() and tile.data[nodeid] is not None:
                tile.data[nodeid] = create_resource_instance_tiledata(relations, tile, nodeid, resource_instance_nodes[nodeid])
                tile.save()


class Migration(migrations.Migration):

    dependencies = [
        ("models", "6019_node_config_for_resource_instance"),
    ]

    operations = [
        migrations.RunPython(forward_migrate, reverse_migrate),
    ]
