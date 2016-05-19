'''
ARCHES - a program developed to inventory and manage immovable cultural heritage.
Copyright (C) 2013 J. Paul Getty Trust and World Monuments Fund

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as
published by the Free Software Foundation, either version 3 of the
License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with this program. If not, see <http://www.gnu.org/licenses/>.
'''

from django.conf import settings as app_settings
from django.db import transaction
from django.shortcuts import render
from django.db.models import Q
from django.utils.translation import ugettext as _
from django.http import HttpResponseNotFound, QueryDict
from arches.app.utils.decorators import group_required
from arches.app.utils.betterJSONSerializer import JSONSerializer, JSONDeserializer
from arches.app.utils.JSONResponse import JSONResponse
from arches.app.models.graph import Graph
from arches.app.models import models
from arches.app.models.ontology import Ontology


@group_required('edit')
def manager(request, graphid):
    graphs = models.Graph.objects.all()
    if graphid is None or graphid == '':
        return render(request, 'graph-list.htm', {
            'main_script': 'graph-list',
            'graphs': JSONSerializer().serialize(graphs)
        })

    graph = Graph(graphid)
    validations = models.Validation.objects.all()
    metadata_records = JSONSerializer().serializeToPython(models.Graph.objects.all())
    branch_nodes = models.Node.objects.filter(~Q(graph=None), istopnode=True)
    branches = []
    for metadata_record in metadata_records:
       try:
           rootnode = branch_nodes.get(graph_id=metadata_record['graphid'])
           metadata_record['graph'] = Graph(rootnode)
           metadata_record['relates_via'] = ['P1', 'P2', 'P3']
           branches.append(metadata_record)
       except models.Node.DoesNotExist:
           pass
    datatypes = models.DDataType.objects.all()
    return render(request, 'graph-manager.htm', {
        'main_script': 'graph-manager',
        'graphid': graphid,
        'graphs': JSONSerializer().serialize(graphs),
        'graph': JSONSerializer().serialize(graph),
        'validations': JSONSerializer().serialize(validations),
        'branches': JSONSerializer().serialize(branches),
        'datatypes': JSONSerializer().serialize(datatypes),
        'node_list': {
            'title': _('Node List'),
            'search_placeholder': _('Find a node in the graph')
        },
        'permissions_list': {
            'title': _('Permissions'),
            'search_placeholder': _('Find a group or user account')
        },
        'branch_list': {
            'title': _('Branch Library'),
            'search_placeholder': _('Find a graph branch')
        },
        'metadata': graph.root.graph
    })


@group_required('edit')
def settings(request, graphid):
    node = models.Node.objects.get(graph_id=graphid, istopnode=True)
    graph = node.graph
    if request.method == 'POST':
        data = JSONDeserializer().deserialize(request.body)
        for key, value in data.get('metadata').iteritems():
            setattr(graph, key, value)
        graph.save()
        node.set_relatable_resources(data.get('relatable_resource_ids'))
        return JSONResponse({
            'success': True,
            'metadata': graph,
            'relatable_resource_ids': [res.nodeid for res in node.get_relatable_resources()]
        })
    icons = models.Icon.objects.order_by('name')
    resource_graphs = models.Graph.objects.filter(Q(isresource=True), ~Q(graphid=graphid))
    resource_data = []
    relatable_resources = node.get_relatable_resources()
    for res in resource_graphs:
        if models.Node.objects.filter(graph=res, istopnode=True).count() > 0:
            node = models.Node.objects.get(graph=res, istopnode=True)
            resource_data.append({
                'id': node.nodeid,
                'metadata': res,
                'is_relatable': (node in relatable_resources)
            })
    graphs = models.Graph.objects.all()
    return render(request, 'graph-settings.htm', {
        'main_script': 'graph-settings',
        'icons': JSONSerializer().serialize(icons),
        'metadata_json': JSONSerializer().serialize(graph),
        'graphs': JSONSerializer().serialize(graphs),
        'graphid': graphid,
        'metadata': graph,
        'resource_data': JSONSerializer().serialize(resource_data)
    })


@group_required('edit')
def node(request, nodeid):
    if request.method == 'POST':
        data = JSONDeserializer().deserialize(request.body)
        if data:
            node = models.Node.objects.get(nodeid=nodeid)
            with transaction.atomic():
                node.name = data.get('name', '')
                node.description = data.get('description', '')
                node.istopnode = data.get('istopnode', '')
                node.crmclass = data.get('crmclass', '')
                node.datatype = data.get('datatype', '')
                node.status = data.get('status', '')
                node.validations.set(data.get('validations', []))
                new_nodegroup_id = data.get('nodegroup_id', None)
                old_nodegroup_id = unicode(node.nodegroup_id) if node.nodegroup_id is not None else None
                if old_nodegroup_id != new_nodegroup_id:
                    for model in node.toggle_is_collector():
                        model.save()
                if node.nodegroup_id is not None:
                    cardinality = data.get('cardinality', 'n')
                    node.nodegroup.cardinality = cardinality
                    node.nodegroup.save()
                    group_nodes = node.nodegroup.node_set.all()
                else:
                    child_nodes, child_edges = node.get_child_nodes_and_edges()
                    group_nodes = [child_node for child_node in child_nodes if child_node.nodegroup is None]
                node.save()
                return JSONResponse({'node': node, 'group_nodes': group_nodes, 'nodegroup': node.nodegroup})

    if request.method == 'DELETE':
        node = models.Node.objects.get(nodeid=nodeid)
        nodes, edges = node.get_child_nodes_and_edges()
        if not node.istopnode:
            edges.append(models.Edge.objects.get(rangenode=node))
        nodes.append(node)
        with transaction.atomic():
            [edge.delete() for edge in edges]
            [node.delete() for node in nodes]
            return JSONResponse({})

    return HttpResponseNotFound()

@group_required('edit')
def append_branch(request, graphid):
    if request.method == 'POST':
        data = JSONDeserializer().deserialize(request.body)
        graph = Graph(graphid)
        new_branch = graph.append_branch(data['property'], nodeid=data['nodeid'], graphid=data['graphid'])
        graph.save()
        return JSONResponse(new_branch)

    return HttpResponseNotFound()

@group_required('edit')
def move_node(request, graphid):
    if request.method == 'POST':
        data = JSONDeserializer().deserialize(request.body)
        graph = Graph(graphid)
        updated_nodes_and_edges = graph.move_node(data['nodeid'], data['property'], data['newparentnodeid'])
        graph.save()
        return JSONResponse(updated_nodes_and_edges)

    return HttpResponseNotFound()

@group_required('edit')
def clone(request, graphid):
    if request.method == 'POST':
        data = JSONDeserializer().deserialize(request.body)
        graph = Graph(graphid).copy()
        if 'isresource' in data:
            graph.metadata.isresource = data['isresource']

        if 'name' in data:
            name = data['name']
        else:
            name = _('New Resource') if graph.metadata.isresource else _('New Graph')
        graph.root.name = name
        graph.metadata.name = name

        graph.populate_null_nodegroups()
        graph.save()
        return JSONResponse(graph)

    return HttpResponseNotFound()

def get_related_nodes(request):
    ret = {
        'properties': [],
        'classes': []
    }
    lang = request.GET.get('lang', app_settings.LANGUAGE_CODE)
    data = JSONDeserializer().deserialize(request.body)
    related_properties = Ontology().get_valid_ontology_concepts(data['parentnode'], child_properties=data['childedges'], lang=lang)
    return JSONResponse(related_properties, indent=4)
