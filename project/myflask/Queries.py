from SPARQLWrapper import SPARQLWrapper, JSON
import re
from collections import defaultdict
# ./fuseki-server --mem /ds

sparql = SPARQLWrapper("http://localhost:3030/ds/query")


prefixes ="""
        prefix foaf: <http://xmlns.com/foaf/0.1/> 
        prefix myns: <http://inf558.org/chemcosmetic/> 
        prefix ns1: <http://www.w3.org/2002/07/owl#> 
        prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> 
        prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> 
        prefix schema: <https://schema.org/> 
        prefix xml: <http://www.w3.org/XML/1998/namespace> 
        prefix xsd: <http://www.w3.org/2001/XMLSchema#> 
        
        """

def ResultFormat_basic(results):
    ans = dict()
    rr = results['results']['bindings']
    if rr:
        ans['product_id'] = rr[0]['product']['value'].split('/')[-1]
        ans['product_name'] = rr[0]['product_name']['value']
        ans['url'] = rr[0]['url']['value']
        ans['brand'] = rr[0]['brand']['value']
        ans['category'] = rr[0]['category']['value']
        ans['subcategory'] = rr[0]['subcategory']['value']
        ans['minicategory'] = rr[0]['minicategory']['value']
        ans['size'] = float(rr[0]['minsize']['value'])
        ans['price'] = float(rr[0]['minPrice']['value'])
        ing_list = [] # a list of ingredient for each product
        iid_list = [] # multiple functions for each ingredient
        for r in rr:
            if r['ingredient_id']['value'] not in iid_list:
                ing_dict=defaultdict(list)
                ing_dict['ingredient_id'] = r['ingredient_id']['value'].split('/')[-1]
                ing_dict['name'] = r['name']['value']
                if 'acne' in r.keys(): ing_dict['acne'] = r['acne']['value'] 
                if 'irritant' in r.keys(): ing_dict['irritant'] = r['irritant']['value']
                if 'safety' in r.keys(): ing_dict['safety'] = r['safety']['value']
                if 'function' in r.keys(): ing_dict['function']= [r['function']['value']]
                ing_list.append(ing_dict)
                iid_list.append(r['ingredient_id']['value'])
            else:
                if r['name']['value']==ing_list[-1]['name']:
                    ing_list[-1]['function'].append(r['function']['value'])
                else:
                    print('sth wrong',r['name']['value'])
        ans['ingredients'] = ing_list
    return ans

def ResultFormat_Advance(results):
    ans_list = list()
    if results['results']['bindings']:
        print(results['results']['bindings'])
        for r in results['results']['bindings']:
            ans = dict()
            ans['product_id'] = r['pid']['value']
            ans['product_name'] = r['name']['value']
            ans['url'] = r['url']['value']
            ans['brand'] = r['brand']['value']
            ans['minicategory'] = r['minicategory']['value']
            ans_list.append(ans)
        return ans_list
    else:
        return None

def ResultFormat_Ingredient(results):
    # only one result
    ans = defaultdict(list)
    if results['results']['bindings']:
        ans['ingredient_id'] = results['results']['bindings'][0]['ingredient_id']['value'].split('/')[-1]
        ans['name'] = results['results']['bindings'][0]['name']['value']
        
        urls = set([i['url']['value'] for i in results['results']['bindings']])
        for url in urls:
            if 'cosdna' in url: ans['coslink'] = url
            elif 'pubchem' in url: ans['publink'] = url
        # if 'cosdna' in results['results']['bindings'][0]['url']['value']:
        #     ans['coslink'] = results['results']['bindings'][0]['url']['value']
        
        if 'forumula' in results['results']['bindings'][0].keys(): ans['forumula'] = results['results']['bindings'][0]['forumula']['value']
        if 'safety' in results['results']['bindings'][0].keys(): ans['safety'] = results['results']['bindings'][0]['safety']['value']
        if 'acne' in results['results']['bindings'][0].keys(): ans['acne'] = results['results']['bindings'][0]['acne']['value']
        if 'irritant' in results['results']['bindings'][0].keys(): ans['safety'] = results['results']['bindings'][0]['irritant']['value']
        for rr in results['results']['bindings']: # multiple results
            if 'function' in rr.keys() and rr['function']['value'] not in ans['function']:
                ans['function'].append(rr['function']['value']) 
            if 'attribute' in rr.keys() and rr['attribute']['value'] not in ans['attribute']:
                ans['attribute'].append(rr['attribute']['value'])
    else:
        return None   
    return ans

def ResultFormat_ingredient_synonym(results):
    synonyms = list()
    if results['results']['bindings']:
        for rr in results['results']['bindings']:
            synonyms.append(rr['synonym']['value'])
    return synonyms

def queryByIngredient(iid):
    results = queryByIngredient_others(iid)
    syns = queryByIngredient_synonym(iid)
    if syns:
        results['synonym'] = syns[:min(len(syns),10)]
    return results

def queryByIngredient_others(iid):
    query ="""
        SELECT DISTINCT * 
        WHERE{{
            VALUES ?ingredient_id {{
            {}
            }}
            ?ingredient_id a myns:Compound;
                        foaf:name ?name;
            OPTIONAL{{?ingredient_id myns:formula ?forumula ;}}
            OPTIONAL{{?ingredient_id ns1:sameAs ?url ;}}         	  
            OPTIONAL{{?ingredient_id myns:hasFunction [rdfs:label ?function]}}
            OPTIONAL{{?ingredient_id myns:hasAttribute [rdfs:label ?attribute]}}
            OPTIONAL{{?ingredient_id myns:safety ?safety;}}
            OPTIONAL {{?ingredient_id myns:acne ?acne;}}
            OPTIONAL {{?ingredient_id myns:irritant ?irritant;}}
        }}
    """
    sparql.setQuery(prefixes + query.format('myns:'+iid))
    sparql.setReturnFormat(JSON)
    results = sparql.query().convert()
    return ResultFormat_Ingredient(results)

def queryByIngredient_synonym(iid):
    query ="""
        SELECT DISTINCT * 
        WHERE{{
            {} a myns:Compound;
                        myns:synonym ?synonym.
        }}
    """
    sparql.setQuery(prefixes + query.format('myns:'+iid))
    sparql.setReturnFormat(JSON)
    results = sparql.query().convert()
    return ResultFormat_ingredient_synonym(results)


def queryByName(pid):
    query ="""
        SELECT DISTINCT ?product ?product_name ?url ?category ?subcategory ?minicategory ?ingredient_id ?brand ?love ?name ?function ?safety ?acne ?irritant (MIN(?price) AS ?minPrice) (MIN(?size) AS ?minsize)
        WHERE{{
            ?product a myns:skincare_product;
                myns:product_id {} ;
                myns:product_url ?url;
                myns:category [rdfs:label ?category];
                myns:subcategory [rdfs:label ?subcategory];
                myns:minicategory [rdfs:label ?minicategory];
                myns:product_name ?product_name;
                myns:brand [rdfs:label ?brand];
                myns:numOfLoves ?love;
                myns:size_price_pair ?spp;
                myns:hasIngredient ?ingredient_id.
            ?ingredient_id a myns:Compound ;
                foaf:name ?name;
                OPTIONAL{{?ingredient_id myns:hasFunction [rdfs:label ?function]}}
                OPTIONAL{{?ingredient_id myns:safety ?safety;}}
                OPTIONAL{{?ingredient_id myns:acne ?acne;}}
                OPTIONAL{{?ingredient_id myns:irritant ?irritant;}}
            ?minspp myns:fromProduct ?product;
                myns:hasPrice ?price;
                myns:hasSize ?size.    
        
    }}GROUP BY ?product ?product_name ?url ?category ?subcategory ?minicategory ?ingredient_id ?brand ?love ?name ?function ?safety ?acne ?irritant       
    ORDER BY ?name
    """
    sparql.setQuery(prefixes + query.format(pid))
    sparql.setReturnFormat(JSON)
    results = sparql.query().convert()
    return ResultFormat_basic(results)

def queryByAttributes_old_slow(param):
    print(param)
    query = """
    SELECT DISTINCT ?product ?pid ?name ?url
    WHERE{{
        ?product a myns:skincare_product;
            myns:product_id ?pid;
            myns:product_url ?url;
            myns:product_name ?name;
            myns:numOfLoves ?love;
            myns:size_price_pair ?spp.
        ?spp myns:fromProduct ?product;
            myns:hasPrice ?price;
            myns:hasSize ?size.
  		FILTER (?price>={price[0]} && ?price<={price[1]})
    """  
    query = prefixes + query
    if param['minicategory']: 
        query +="""
        ?product myns:minicategory [rdfs:label ?minicategory];
        FILTER (?minicategory IN ({minicategory}))"""
    if param['brand']: 
        query += """
        ?product myns:brand [rdfs:label ?brand];
        FILTER (?brand = "{brand}" )"""
    if param['function']: 
        query +="""
        ?product myns:hasIngredient [ myns:hasFunction [rdfs:label ?function]]
        FILTER (?function IN ({function}))"""
    if param['Preservative']: 
        query += """MINUS{{?product myns:hasIngredient [myns:hasAttribute myns:Preservatives].}}"""
        query += """MINUS{{?product myns:hasIngredient [myns:hasFunction myns:Preservative].}}"""
    if param['Fragrance']: 
        query += """MINUS{{?product myns:hasIngredient [myns:hasAttribute myns:Fragrance].}}"""
    if param['Alcohol']: 
        query += """MINUS{{?product myns:hasIngredient [myns:groupOf myns:Alcoholic].}}"""
    if param['acne']: 
        query +="""OPTIONAL{{?product myns:hasIngredient [ myns:acne ?acne_index].}}
  		FILTER (?acne_index<={acne} || !BOUND(?acne_index))"""
    if param['irrative']:
        query +="""OPTIONAL{{?product myns:hasIngredient [ myns:acne ?irrative_index].}}
  		FILTER (?irrative_index<={irrative} || !BOUND(?irrative_index))"""
    # if param['safety']: 
    #     query +="""OPTIONAL{{?product myns:hasIngredient [ myns:safety ?safety_index].}}
  	# 	FILTER (?safety_index<={safety} || !BOUND(?safety_index))"""
   
    query += """}}ORDER BY DESC(?love)"""
    # print('--------------------')
    print(query.format(**param))
    # print('--------------------')
    sparql.setQuery(prefixes + query.format(**param))
    sparql.setReturnFormat(JSON)
    results = sparql.query().convert()
    #print(len(results['results']['bindings']))
    return ResultFormat_Advance(results)

def queryByAttributes(param):
    inner_query = """
    SELECT DISTINCT ?product ?pid ?name ?url ?brand ?minicategory
    WHERE{{
        ?product a myns:skincare_product;
            myns:product_id ?pid;
            myns:product_url ?url;
            myns:product_name ?name;
            myns:brand [rdfs:label ?brand];
            myns:minicategory [rdfs:label ?minicategory];
            myns:numOfLoves ?love;
            myns:size_price_pair ?spp.
        ?spp myns:fromProduct ?product;
            myns:hasPrice ?price;
            myns:hasSize ?size.
  		FILTER (?price>={price[0]} && ?price<={price[1]})  
    """
    if param['minicategory']: 
        inner_query +="""
        FILTER (?minicategory IN ({minicategory}))"""
    if param['brand']: 
        inner_query += """
        FILTER (?brand = "{brand}" )"""
    if any([param['function'],param['Preservative'],param['Fragrance'],param['Alcohol'],param['acne'],param['irrative']]):
        query = """
        SELECT DISTINCT ?product ?pid ?name ?url ?brand ?minicategory
        WHERE{{
            ?product a myns:skincare_product.
        """
        if param['function']: 
            query +="""
            ?product myns:hasIngredient [ myns:hasFunction [rdfs:label ?function]]
            FILTER (?function IN ({function}))"""
        if param['Preservative']: 
            query += """MINUS{{?product myns:hasIngredient [myns:hasAttribute myns:Preservatives].}}"""
            query += """MINUS{{?product myns:hasIngredient [myns:hasFunction myns:Preservative].}}"""
        if param['Fragrance']: 
            query += """MINUS{{?product myns:hasIngredient [myns:hasAttribute myns:Fragrance].}}"""
        if param['Alcohol']: 
            query += """MINUS{{?product myns:hasIngredient [myns:groupOf myns:Alcoholic].}}"""
        if param['acne']: 
            query +="""OPTIONAL{{?product myns:hasIngredient [ myns:acne ?acne_index].}}
            FILTER (?acne_index<={acne} || !BOUND(?acne_index))"""
        if param['irrative']:
            query +="""OPTIONAL{{?product myns:hasIngredient [ myns:acne ?irrative_index].}}
            FILTER (?irrative_index<={irrative} || !BOUND(?irrative_index))"""

        # ending = """
        #     {{
        #         {}
        #     }}
        #         }}		
        #     }}
        #     }}ORDER BY DESC(?love)
        # """
        # query = query + ending.format(inner_query)
        query = query + "{{" + inner_query +"}}\n" + "}}\n" + "}}ORDER BY DESC(?love)"
    else:
        query = inner_query + """}}ORDER BY DESC(?love)"""
    
    #print(query.format(**param))
    # print('--------------------')
    sparql.setQuery(prefixes + query.format(**param))
    sparql.setReturnFormat(JSON)
    results = sparql.query().convert()
    print('advanced result: ',len(results['results']['bindings']))
    return ResultFormat_Advance(results)
    

def queryIfProductsConflicted(products):
    # check if a new product is conflict with the existing products
    query = """
        SELECT DISTINCT * WHERE{
  	  ?product1 a myns:skincare_product;
               myns:hasIngredient [myns:groupOf ?g1];
               myns:product_id 2058402  .
  
      ?product2 a myns:skincare_product;
  			   myns:hasIngredient [myns:groupOf ?g2];
  				myns:product_id 2311439 .
     FILTER EXISTS{?g1 myns:conflictWith ?g2} # with result = conflict
    	}"""
    # if result : conflict
    
def queryFindConflictedGroup(collections):
    # find conflicted group for the collections
    query = """
    SELECT DISTINCT ?conflictedGroup WHERE{{
        ?product_list myns:product_id ?product_ids;
   			          myns:hasIngredient ?ingredient.
     ?ingredient myns:groupOf [myns:conflictWith ?conflictedGroup].
	FILTER (?product_ids IN ({}))
    	}}
    """
    query = prefixes + query
    sparql.setQuery(prefixes + query.format(collections))
    sparql.setReturnFormat(JSON)
    results = sparql.query().convert()
    results = results['results']['bindings']
    return ['myns:'+r['conflictedGroup']['value'].split('/')[-1] for r in results]
    
def queryFindFitProduct(pids,conflictedgroup):
    # find products qualified for conflicted group and pid
    query="""
    SELECT DISTINCT ?product ?pid ?name ?url ?minicategory ?brand ?love
    WHERE{{
        ?product a myns:skincare_product;
            myns:product_id ?pid;
            myns:product_url ?url;
            myns:minicategory [rdfs:label ?minicategory];
            myns:product_name ?name;
            myns:brand [rdfs:label ?brand];
            myns:numOfLoves ?love.
            #myns:size_price_pair ?spp.
        #?spp myns:fromProduct ?product;
        #    myns:hasPrice ?price;
        #    myns:hasSize ?size.
      FILTER (?pid IN ({}))
    """.format(pids)
    for c in conflictedgroup:
        query += """MINUS {{?product myns:hasIngredient [myns:groupOf {}]}}\n""".format(c)
    query += "}"
    # print('-----------------------')
    # print(query)
    # print('-----------------------')
    sparql.setQuery(prefixes + query)
    sparql.setReturnFormat(JSON)
    results = sparql.query().convert()
    print(len(results['results']['bindings']))
    return ResultFormat_Advance(results)


'''
import pandas as pd
products=pd.read_json('./sephora/output/sephora_skincare_product_ingredient_list.jl',lines=True)
ingredients=pd.read_json('./sephora/output/ingredients.jl',lines=True)

products.prices
tmp = temp[temp.map(lambda d: len(d)) > 0]
tmp.map(foo)
def foo(x):
    coll = list()
    for string in x:
        match=re.search(r'\$([0-9\.]+)',string)
        if match:
            coll.append(float(match.group(1)))
    return max(coll)
with open('./output/query_result.json') as json_file:
    results = json.load(json_file)
import pandas as pd


results = pd.read_json('./sephora/output/query_result.json') # dataframe
df =results.applymap(lambda x:x['value'])

temp = df[df['product']=='http://inf558.org/chemcosmetic/p_1014554']
df.groupby(['product','ingredient'])


'''

