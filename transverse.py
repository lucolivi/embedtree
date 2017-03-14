"""
Algorithm to compute required articles applying the pagerank algorithm to a graph generated by 
tranversing the target article by a few levels.
"""



"""
                                            ---NOTES---

- Tests showed that in_degree_centrality is better than pagerank to elect the most relevant nodes
- Clusters would be good to take the most variate areas of the knowledge but is hard to choose a 
algorithm and fitness function that can extract these areas

- The more deeper we dive in the graph to compute in_degree votes, more vast areas we get, so we need
an algorithm to avoid that some page like a "list of things in an area" tend to increase votes to something 
in common in that area. We need to valorize the votes of diveristy things in one. So we use something
similar to page rank to spread the votes the deeper we go.

"""



#think how to construct things by this


import sys #Lib to interact with the system

import py2neo #Libs to connect to neo4j

import networkx as nx #Lib to create and manipulate graphs

from tabulate import tabulate #Lib to format data as tables before print

import matplotlib.pyplot as plt #Lib to plot info graphics

VERBOSE = True #Flag to signalize whether to print process info or not

#neo4jGraph = None #Connection to neo4j graph


def connectDb():
    """Function to connect to neo4j database."""

    printLog("Initing db...")
    py2neo.authenticate("localhost:7474", "neo4j", "lucas")
    dbConnection = py2neo.Graph("http://localhost:7474/db/data/")

    return dbConnection

def get_direct_graph(article_title, transversal_level, db_connection):
    """Function"""

    #Create a directed graph
    graph = nx.DiGraph()

    #Query all nodes id related to the seed node
    db_query = " ".join([
        'MATCH (n1:Article {name:"ARTICLE-TITLE"})-[l1:RefersTo*TRANSVERSAL-LEVEL]->(n2:Article)',
        'RETURN l1'
    ]).replace("ARTICLE-TITLE", article_title).replace("TRANSVERSAL-LEVEL", transversal_level)

    #Execute query and compute ids
    for result in db_connection.run(db_query):
        edge_arr = result['l1']
        for edge in edge_arr:
            graph.add_edge(edge.start_node()['name'], edge.end_node()['name'])

    return graph

def getGraph(articleTitle, transversalLevel, dbConnection):
    """Function to get a graph data from db and create a networkx graph."""

    #global neo4jGraph

    # if neo4jGraph == None:
    #     raise "Neo4j not connected."

    #Create a directed graph
    G = nx.DiGraph()

    #All directions query based on forward nodes

    #Query all nodes id related to the seed node
    dbQuery = " ".join([
        'MATCH (n1:Article {name:"ARTICLE-TITLE"})-[l1:RefersTo*TRANSVERSAL-LEVEL]->(n2:Article)',
        'RETURN collect(DISTINCT ID(n1)) + collect(DISTINCT ID(n2)) as ids'
    ]).replace("ARTICLE-TITLE", articleTitle).replace("TRANSVERSAL-LEVEL", transversalLevel)

    nodeIds = [] #Array to keep node ids

    printLog("Querying ids...")

    #Execute query and compute ids
    for r in dbConnection.run(dbQuery):
        nodeIds += r['ids']

    #Now query all connectTo relations between these nodes
    dbQuery = " ".join([
        'MATCH (n1:Article)-[l1:RefersTo]-(n2:Article)',
        'WHERE (ID(n1) IN NODE-IDS AND ID(n2) IN NODE-IDS)',
        'RETURN l1 as edges'
    ]).replace("NODE-IDS", str(nodeIds))

    #QUery edges and create the graph with them
    printLog("Querying edges and create graph...")

    for val in dbConnection.run(dbQuery):
        e = val[0]
        G.add_edge(e.start_node()['name'], e.end_node()['name'])

    return G


def getGraphClusters(G, clusterAllocMethod, clusterRankMethod):

    #Delete main node if it is needed
    # if deleteMainNode:
    #     if verbose:
    #         print "Deleting main node..."
    #     G.remove_node(articleTitle)

    printLog("Generating clusters...")

    #Get the connected nodes of G according to choose method
    if clusterAllocMethod == 'weak':
        clusters_nodes = nx.weakly_connected_components(G)
    elif clusterAllocMethod == 'strong':
        clusters_nodes = nx.strongly_connected_components(G)

    printLog("Getting clusters graphs...")

    clusters_subgraphs = [G.subgraph(nlist) for nlist in clusters_nodes]

    #Array to keep the clusters
    clusters = []

    #Iterate thru the clusters subgraphs
    for cluster_sg in clusters_subgraphs:

        #Calculate the rank for each node in the cluster
        if clusterRankMethod == 'pagerank':
            cluster_node_ranks = nx.pagerank(cluster_sg).items() #Pagerank
        elif clusterRankMethod == 'in_degree':
            cluster_node_ranks = nx.in_degree_centrality(cluster_sg).items() #Incomming edges sum

        #Order cluster in decreasing order
        cluster_node_ranks = sorted(cluster_node_ranks, key=lambda a: a[1], reverse=False) 

        #Append the cluster to the clusters array with its length
        clusters.append((cluster_node_ranks, len(cluster_node_ranks)))

    #Order clusters in decreasing order
    clusters = sorted(clusters, key=lambda a: a[1], reverse=True) 

    return clusters


def getCentralNodes(G):
    """Function to get the central nodes of graph G based on incomming degree of the nodes."""

    centralNodes = nx.in_degree_centrality(G)
    sortedNodes = sorted(centralNodes.items(), key=lambda a: a[1], reverse=False)
    return sortedNodes

def printLog(msg):
    """Function to print data in case verbose flag is up."""
    if VERBOSE:
        print msg



def main(args):
    """Main function used for tests."""

    dbConnection = connectDb()
    G = getGraph(args[1], args[2], dbConnection)
    #clusters = getGraphClusters(G, "weak", "in_degree")

    centralNodes = reversed(getCentralNodes(G))

    for n in centralNodes:
        centralNode = n[0]
        break

    #print centralNode
    print ""

    #keep working on creating the space with node datas
    

    targetNodes = []
    for edge in G.edges():
        if edge[1] == centralNode:
            targetNodes.append(edge[0])

    for d in map(lambda a: [a], targetNodes):
        print d


    # print ""
    # print(tabulate(map(lambda a: [a], centralNodes), headers=['centralNodes']))


def seedrank(graph, seed_node):
    """Function that computes the seed rank of a graph with a seed node."""

    rank_start_dict = dict()

    for node in graph.nodes():
        if node == seed_node:
            rank_start_dict[node] = 1
        else:
            rank_start_dict[node] = 0

    rank = nx.pagerank(graph, nstart=rank_start_dict)

    return rank


def print_graph(graph):
    """Function to print networkx graph."""

    nx.draw(graph)
    plt.show()


def benchmark_central_nodes(graph, article_title):
    """ Function to benchmark central nodes """

    #Compute seedrank
    graph_seedrank = seedrank(graph, article_title)

    #Compute in_degree
    graph_in_degree = nx.in_degree_centrality(graph)

    #Compute pagerank
    graph_pagerank = nx.pagerank(graph)

    #Sort data
    sorted_sr = sorted(graph_seedrank.items(), key=lambda a: a[1], reverse=False)
    sorted_id = sorted(graph_in_degree.items(), key=lambda a: a[1], reverse=False)
    sorted_pr = sorted(graph_pagerank.items(), key=lambda a: a[1], reverse=False)

    #Concatenate
    dict_size = len(sorted_sr)
    print_data = list()
    for i in xrange(dict_size):
        #Convert data to list to be editable
        sorted_sr[i] = list(sorted_sr[i])
        sorted_id[i] = list(sorted_id[i])
        sorted_pr[i] = list(sorted_pr[i])

        #Truncate too long string
        sorted_sr[i][0] = sorted_sr[i][0][:40]
        sorted_id[i][0] = sorted_id[i][0][:40]
        sorted_pr[i][0] = sorted_pr[i][0][:40]

        #Round decimal values to fit on screen
        sorted_sr[i][1] = round(sorted_sr[i][1]*100, 2)
        sorted_id[i][1] = round(sorted_id[i][1]*100, 2)
        sorted_pr[i][1] = round(sorted_pr[i][1]*100, 2)

        print_data.append([str(sorted_sr[i]), str(sorted_pr[i]), str(sorted_id[i])])

    #Print only the last 10
    return_index = len(print_data) - 10
    if return_index < 0:
        return_index = 0

    #Print
    print "\n" + tabulate(print_data[return_index:], headers=['seedrank', 'pagerank', 'in_degree'])


def benchmark_seedrank(args):

    article_title = args[1]
    tranversal_level = args[2]

    db_connection = connectDb()

    graph = getGraph(article_title, tranversal_level, db_connection)

    #Compute seedrank
    graph_seedrank = seedrank(graph, article_title)

    #Compute in_degree
    graph_in_degree = nx.in_degree_centrality(graph)

    #Compute pagerank
    graph_pagerank = nx.pagerank(graph)

    #Sort data
    sorted_sr = sorted(graph_seedrank.items(), key=lambda a: a[1], reverse=False)
    sorted_id = sorted(graph_in_degree.items(), key=lambda a: a[1], reverse=False)
    sorted_pr = sorted(graph_pagerank.items(), key=lambda a: a[1], reverse=False)

    #Concatenate
    dict_size = len(sorted_sr)
    print_data = list()
    for i in xrange(dict_size):
        #Convert data to list to be editable
        sorted_sr[i] = list(sorted_sr[i])
        sorted_id[i] = list(sorted_id[i])
        sorted_pr[i] = list(sorted_pr[i])

        #Truncate too long string
        sorted_sr[i][0] = sorted_sr[i][0][:40]
        sorted_id[i][0] = sorted_id[i][0][:40]
        sorted_pr[i][0] = sorted_pr[i][0][:40]

        #Round decimal values to fit on screen
        sorted_sr[i][1] = round(sorted_sr[i][1], 2)
        sorted_id[i][1] = round(sorted_id[i][1], 2)
        sorted_pr[i][1] = round(sorted_pr[i][1], 2)

        print_data.append([str(sorted_sr[i]), str(sorted_pr[i]), str(sorted_id[i])])

    #Print only the last 10
    return_index = len(print_data) - 10
    if return_index < 0:
        return_index = 0

    #Print
    print "\n" + tabulate(print_data[return_index:], headers=['seedrank', 'pagerank', 'in_degree'])
    # nx.draw(graph)
    # plt.show()
    

def path(args):
    """Function to get good path to some article."""

    article_title = args[1]

    db_connection = connectDb()

    graph = getGraph(article_title, "1..3", db_connection)

    central_nodes = reversed(getCentralNodes(graph))

    for node in central_nodes:
        central_node = node[0]
        break

    

    #Check if there is a direct connection between seed node and the central node
    for edge in graph.edges():
        if edge[0] == article_title and edge[1] == central_node:
            pass
    

    print central_node

def get_central_nodes(args):
    """Function that prints node central nodes."""

    article_title = args[1]

    db_connection = connectDb()
    graph = getGraph(article_title, args[2], db_connection)

    #Delete main node if it is needed
    #graph.remove_node(article_title)

    central_nodes = getCentralNodes(graph)

    return_index = len(central_nodes) - 5
    if return_index < 0:
        return_index = 0

    print ""
    print tabulate(map(lambda a: [a], central_nodes[return_index:]), headers=['centralNodes'])


def multiply_distributions(args):
    """Function that get the multiplication of all distributions of node in_degrees.
        NOT USE, IT DOES NOT WORK
    """

    article_title = args[1]

    db_connection = connectDb()

    printLog("Getting distribution 1...")
    graph1 = getGraph(article_title, "1..1", db_connection)
    dist1 = nx.in_degree_centrality(graph1)

    printLog("Getting distribution 2...")
    graph2 = getGraph(article_title, "1..2", db_connection)
    dist2 = nx.in_degree_centrality(graph2)

    printLog("Getting distribution 3...")
    graph3 = getGraph(article_title, "1..3", db_connection)
    dist3 = nx.in_degree_centrality(graph3)

    join_dist_dict = dict()

    printLog("Computing dist 1...")
    for key, value in dist1.iteritems():
        if not join_dist_dict.has_key(key):
            join_dist_dict[key] = 1

        join_dist_dict[key] = join_dist_dict[key] * value

    printLog("Computing dist 2...")
    for key, value in dist2.iteritems():
        if not join_dist_dict.has_key(key):
            join_dist_dict[key] = 1

        join_dist_dict[key] = join_dist_dict[key] * value

    printLog("Computing dist 3...")
    for key, value in dist3.iteritems():
        if not join_dist_dict.has_key(key):
            join_dist_dict[key] = 1

        join_dist_dict[key] = join_dist_dict[key] * value


    sorted_data = sorted(join_dist_dict.items(), key=lambda a: a[1], reverse=False)

    print tabulate(map(lambda a: [a], sorted_data), headers=['multiplied dist'])


def forward_position(args):
    """Function"""

    article_title = args[1]

    db_connection = connectDb()

    printLog("Getting distribution 1...")
    graph1 = getGraph(article_title, "1..1", db_connection)
    dist1 = nx.in_degree_centrality(graph1)

    printLog("Getting distribution 2...")
    graph2 = getGraph(article_title, "1..2", db_connection)
    dist2 = nx.in_degree_centrality(graph2)

    # printLog("Getting distribution 3...")
    # graph3 = getGraph(article_title, "1..3", db_connection)
    # dist3 = nx.in_degree_centrality(graph3)

    position_dict = dict()

    for key, value in dist1.iteritems():
        position_dict[key] = dist2[key]# + dist3[key]

    sorted_data = sorted(position_dict.items(), key=lambda a: a[1], reverse=False)

    print tabulate(map(lambda a: [a], sorted_data), headers=['forward_position'])


    #check if the seedrank algorithm may be used
    #create something fast, even if not so good


def test_direct_graph(args):
    """Testing get_direct_graph"""

    article_title = args[1]
    transversal_level = args[2]

    db_connection = connectDb()

    graph = get_direct_graph(article_title, transversal_level, db_connection)

    benchmark_central_nodes(graph, article_title)

    #print_graph(graph)

def test_graph(args):
    """Testing getGraph"""

    article_title = args[1]
    transversal_level = args[2]

    db_connection = connectDb()

    graph = getGraph(article_title, transversal_level, db_connection)

    benchmark_central_nodes(graph, article_title)

def benchmark_direct_nondirect(args):
    """benchmark_direct_nondirect"""

    article_title = args[1]
    transversal_level = args[2]

    db_connection = connectDb()

    nondirgraph = getGraph(article_title, transversal_level, db_connection)
    dirgraph = get_direct_graph(article_title, transversal_level, db_connection)

    print "\nALL DIRECTIONS GRAPH"
    benchmark_central_nodes(nondirgraph, article_title)
    print "\nDIRECTED GRAPH"
    benchmark_central_nodes(dirgraph, article_title)


if __name__ == "__main__":
    #main(sys.argv)
    #path(sys.argv)
    get_central_nodes(sys.argv)
    #NOT WORKmultiply_distributions(sys.argv)
    #forward_position(sys.argv)
    #benchmark_seedrank(sys.argv)

    # test_graph(sys.argv)
    # test_direct_graph(sys.argv)

    #benchmark_direct_nondirect(sys.argv)

# will use the 5 first items to compute the required items (501st)
# later we improve acuracy






#Function to get the article cluster
def getArticleClusters(articleTitle, transversalLevel, deleteMainNode, clusterAllocMethod, clusterRankMethod, neo4jGraph, verbose):

    def sortConcatAndPrint(dict1, dict2):

        #Sort
        sortedDict1 = sorted(dict1.items(), key=lambda a: a[1], reverse=False)
        sortedDict2 = sorted(dict2.items(), key=lambda a: a[1], reverse=False)

        #Concatenate
        dictSize = len(sortedDict1)
        printData = list()
        for i in xrange(dictSize):
            #Convert data to list to be editable
            sortedDict1[i] = list(sortedDict1[i])
            sortedDict2[i] = list(sortedDict2[i])

            #Truncate too long string
            sortedDict1[i][0] = sortedDict1[i][0][:40]
            sortedDict2[i][0] = sortedDict2[i][0][:40]

            #Round decimal values to fit on screen
            sortedDict1[i][1] = round(sortedDict1[i][1], 2)
            sortedDict2[i][1] = round(sortedDict2[i][1], 2)

            printData.append([str(sortedDict1[i]), str(sortedDict2[i])])

        #Print
        print(tabulate(printData, headers=['PageRank', 'InCentrality']))



    def sortAndPrint(items):
        sortedItems = sorted(items.items(), key=lambda a: a[1], reverse=False)
        for d in sortedItems:
            print d.encode('ascii', 'ignore')
    

    sortConcatAndPrint(pagerank, centrality)

    #print ""
    #sortAndPrint(centrality)

    #print ""
    #sortAndPrint(pagerank)

    sys.exit()



    if verbose:
        print "Generating clusters..."

    #Get the connected nodes of G according to choose method
    if clusterAllocMethod == 'weak':
        clusters_nodes = nx.weakly_connected_components(G)
    elif clusterAllocMethod == 'strong':
        clusters_nodes = nx.strongly_connected_components(G)

    if verbose:
        print "Getting clusters graphs..."

    clusters_subgraphs = [G.subgraph(nlist) for nlist in clusters_nodes]

    #Array to keep the clusters
    clusters = []

    #Iterate thru the clusters subgraphs
    for cluster_sg in clusters_subgraphs:

        #Calculate the rank for each node in the cluster
        if clusterRankMethod == 'pagerank':
            cluster_node_ranks = nx.pagerank(cluster_sg).items() #Pagerank
        elif clusterRankMethod == 'sum':
            cluster_node_ranks = in_degree_centrality(cluster_sg).items() #Incomming edges

        #Order cluster in decreasing order
        cluster_node_ranks = sorted(cluster_node_ranks, key=lambda a: a[1], reverse=True) 

        #Append the cluster to the clusters array with its length
        clusters.append((cluster_node_ranks, len(cluster_node_ranks)))

    #Order clusters in decreasing order
    clusters = sorted(clusters, key=lambda a: a[1], reverse=True) 

    return clusters





#--------------main()-----------------
# if __name__ == "__main__":
#     main(sys.argv)
    # print "Initing db..."

    # #Load database
    # py2neo.authenticate("localhost:7474", "neo4j", "lucas")
    # neo4jGraph = Graph("http://localhost:7474/db/data/")

    # #Default Configuration
    # articleTitle = "MQTT" #Article to generate graph from
    # transversalLevel = "1..3" #Graph transversal level 
    # deleteMainNode = True #Exclude the main node in the cluster computation
    # clusterAllocMethod = "weak" # 'weak' for weakly-connnected-components and 'strong' for strongly-connected-components
    # clusterRankMethod = "sum" #'sum' to simply sum incomming nodes and 'pagerank' to compute nodes pageranks
    # #betweenNodesConnections #TO BE IMPLEMENTED Whether to get connections between graph nodes or only their forward connections

    # #Replace configs
    # try: 
    #     articleTitle = sys.argv[1]
    # except: 
    #     pass

    # try:
    #     transversalLevel = sys.argv[2]
    # except: 
    #     pass

    # try:
    #     clusterAllocMethod = sys.argv[3]
    # except: 
    #     pass

    # try:
    #     clusterRankMethod = sys.argv[4]
    # except: 
    #     pass


    # clusters = getArticleClusters(articleTitle, transversalLevel, True, clusterAllocMethod, clusterRankMethod, neo4jGraph, True)


    # #String to store the result of the process
    # resultLog = ""

    # #Iterate thru clusters
    # for c in clusters:
    #     resultLog += "Cluster nodes: " + str(c[1]) + "\n\r"
    #     for node in c[0]:
    #         resultLog += str(node) + "\n\r"
    #     resultLog += "\n\r"

    # #Save result log with its properties
    # fileName = "-".join([articleTitle, transversalLevel, str(deleteMainNode), clusterAllocMethod, clusterRankMethod]) + ".txt"
    # with open("results/" + fileName, "w") as f:
    #     f.write(resultLog)
    # f.close()

    # print ""
    # print resultLog

    # # nx.draw(G)
    # # plt.show()