define([
    'jquery',
    'arches',
    'knockout',
    'models/graph',
    'viewmodels/card',
    'viewmodels/provisional-tile'
], function($, arches, ko, GraphModel, CardViewModel, ProvisionalTileViewModel) {
    function viewModel(params) {
        var self = this;
        var url = arches.urls.api_card + params.graphid;

        this.card = ko.observable();
        this.tile = ko.observable();
        this.loading = ko.observable();

        $.getJSON(url, function(data) {
            var handlers = {
                'after-update': [],
                'tile-reset': []
            };
            var displayname = ko.observable(data.displayname);
            var resourceId = ko.observable(data.resourceid);
            var createLookup = function(list, idKey) {
                return _.reduce(list, function(lookup, item) {
                    lookup[item[idKey]] = item;
                    return lookup;
                }, {});
            };

            self.reviewer = data.userisreviewer;
            self.provisionalTileViewModel = new ProvisionalTileViewModel({tile: self.tile, reviewer: data.userisreviewer});

            var graphModel = new GraphModel({
                data: {nodes: data.nodes, nodegroups: data.nodegroups, edges: []},
                datatypes: data.datatypes
            });

            var topCards = _.filter(data.cards, function(card) {
                var nodegroup = _.find(data.nodegroups, function(group) {
                    return group.nodegroupid === card.nodegroup_id;
                });
                return !nodegroup || !nodegroup.parentnodegroup_id;
            }).map(function(card) {
                return new CardViewModel({
                    card: card,
                    graphModel: graphModel,
                    tile: null,
                    resourceId: resourceId,
                    displayname: displayname,
                    handlers: handlers,
                    cards: data.cards,
                    tiles: data.tiles,
                    provisionalTileViewModel: self.provisionalTileViewModel,
                    cardwidgets: data.cardwidgets,
                    userisreviewer: data.userisreviewer,
                    loading: self.loading
                });
            });

            topCards.forEach(function(topCard) {
                topCard.topCards = topCards;
            });

            self.widgetLookup = createLookup(data.widgets, 'widgetid');
            self.cardComponentLookup = createLookup(data['card_components'], 'componentid');
            self.nodeLookup = createLookup(graphModel.get('nodes')(), 'nodeid');
            self.on = function(eventName, handler) {
                if (handlers[eventName]) {
                    handlers[eventName].push(handler);
                }
            };

            // set self.tile and self.card....
            self.card(topCards[0]);
            self.tile(self.card().getNewTile());
        });

        self.saveTile = function(tile, callback) {
            tile.save(function(response) {
                // handle failure...
                console.log(response);
            }, callback);
        };
    }
    ko.components.register('new-tile-step', {
        viewModel: viewModel,
        template: {
            require: 'text!templates/views/components/workflows/new-tile-step.htm'
        }
    });
    return viewModel;
});
