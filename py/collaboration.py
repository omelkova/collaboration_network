#!usr/bin/python3


import numpy as np
from pandas import DataFrame
from rdflib import Graph, Namespace, RDF
import operator
from collections import Counter


def parse_graph(path, frmt):
    g = Graph()
    g.parse(path, format=frmt)  # "../graph/experiment_graph.ttl", format="turtle")
    ns = dict(api_network=Namespace("http://deepweb.ut.ee/ontologies/api-network#"),
              cat=Namespace("http://www.programmableweb.com/category/"),
              rdf=RDF, gr=Namespace("http://purl.org/goodrelations/v1#"),
              pw_api=Namespace("http://www.programmableweb.com/api/"),
              xsd=Namespace("http://www.w3.org/2001/XMLSchema#"),
              skos=Namespace("http://www.w3.org/2004/02/skos/core#"),
              foaf=Namespace("http://xmlns.com/foaf/0.1/"),
              sioc=Namespace("http://rdfs.org/sioc/ns#"))
    return (g, ns)


def two_layer_recommendation(used_items, user_item, item_user):
    user_resource = np.zeros(len(user_item), dtype="float")
    item_resource = np.zeros(len(item_user), dtype="float")
    # initial allocation
    item_resource[used_items] = 1
    # print(item_resource)
    # first round
    for key, i in enumerate(item_resource):
        if i > 0:
            if item_user[key]:
                user_resource[item_user[key]] += float(i) / float(len(item_user[key]))
    # second round
    item_resource = np.zeros(len(item_user), dtype="float")
    for key, i in enumerate(user_resource):
        if i > 0:
            # print(key, i)
            item_resource[user_item[key]] += i / len(user_item[key])
    result = [(k, i) for k, i in enumerate(item_resource) if k not in used_items and i != 0]  # delete weights for items used by user
    return sorted(result, key=lambda x: x[1], reverse=True)


def three_layer_recommendation(user_id, e1_e_dict, e_e1_dict, e2_e_dict, e_e2_dict):
    recom1 = two_layer_recommendation(e1_e_dict[user_id], e1_e_dict, e_e1_dict)
    recom2 = two_layer_recommendation(e1_e_dict[user_id], e2_e_dict, e_e2_dict)
    merged = Counter(dict(recom1))
    merged.update(dict(recom2))
    return sorted(list(merged.items()), key=operator.itemgetter(1), reverse=True)


def create_relatiobships_df(g, ns, entity1, entity2, relationship):
    rows = g.query("""SELECT ?m ?s WHERE {
                ?s ?p %s .
                ?m ?p %s .
                ?m %s ?s .
                }""" % (entity2, entity1, relationship), initNs=ns)
    df = DataFrame()
    df[entity1] = [t["?m"].toPython() for t in rows.bindings]  # .split(':', 1)[-1]
    df[entity2] = [t["?s"].toPython() for t in rows.bindings]
    return df


def create_legend_and_reversed_legend(entity, df):
    entity_legend = list(enumerate(df[entity].unique()))
    reversed_entity_legend_dict = {}
    for i in entity_legend:
        reversed_entity_legend_dict[i[1]] = i[0]
    return (entity_legend, reversed_entity_legend_dict)


def create_legend_and_reversed_legend_from_graph(entity, g, ns):
    rows = g.query(""" SELECT DISTINCT ?e WHERE{
        ?e rdf:type %s .
        }""" % entity, initNs=ns)
    entity_legend = list(enumerate([t["?e"].toPython() for t in rows.bindings]))
    entity_rev_dict = {}
    for i in entity_legend:
        entity_rev_dict[i[1]] = i[0]
    return (entity_legend, entity_rev_dict)


def create_relationship_dictionary(entity1, entity2, e1_legend, reversed_e2_legend, df):
    e1_e2 = {}
    for e1 in e1_legend:
        entities2 = df[df[entity1] == e1[1]][entity2]
        # print(apis)
        a = []
        for e2 in entities2:
            a = a + [reversed_e2_legend[e2]]
        e1_e2[e1[0]] = a
    return e1_e2


def create_bipartite_graph(g, ns, df=None, entity1="api_network:Mashup", entity2="api_network:API", relationship="gr:include"):
    if df is None:
        relationships_df = create_relatiobships_df(g, ns, entity1, entity2, relationship)
    else:
        relationships_df = df
    # entity1, entity2 = [i.split(':', 1)[-1] for i in [entity1, entity2]]  # Delete prefixes
    e1_legend, reversed_e1_legend = create_legend_and_reversed_legend(entity1, relationships_df)
    e2_legend, reversed_e2_legend = create_legend_and_reversed_legend(entity2, relationships_df)
    e1_e2 = create_relationship_dictionary(entity1, entity2, e1_legend, reversed_e2_legend, relationships_df)
    e2_e1 = create_relationship_dictionary(entity2, entity1, e2_legend, reversed_e1_legend, relationships_df)
    return (e1_e2, e2_e1, e1_legend, e2_legend)
