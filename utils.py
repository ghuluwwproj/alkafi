from typing import Dict, List, Tuple, Type
import pandas as pd
from collections import Counter, defaultdict
import networkx as nx

#verbose = True
verbose = False

def read_commented_plain_text(fn: str, data_type: Type=str) -> list:
    ret = []
    with open(fn, encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line.startswith('#'): continue
            if '#' in line:
                data, _ = line.split('#')
            else:
                data = line
            data = data_type(data.strip())
            ret.append(data)
    return ret

def get_yes_no(msg: str) -> bool:
    """ Get a yes/no answer from input."""
    while True:
        inp = input(msg).lower()
        if inp == 'y' or input == 'yes': return True
        elif inp == 'n' or input == 'no': return False

class Isnad:
    def __init__(self, sid: int, hid: int, edges_list: List[Tuple[int,int]]):
        """
        Args:
            sid: isnad id
            hid: hadith id
            edges_list: a list of transmitter pairs, ex: [(t1-id, t2-id), ...]
        """
        assert len(edges_list) != 0
        self.sid = int(sid)
        self.hid = int(hid)
        self.edges_list = edges_list
        el = []
        for u,v in edges_list:
            if u not in el: el.append(u)
            if v not in el: el.append(v)
        self.nodes_list = el
        
    def __str__(self):
        return "Isnad (sid=%d, hid=%d, edges_list=%s)" % (self.sid, self.hid, self.edges_list)


class IsnadSet:
    """ A collection of isnads with metadata stored in a SQL database. """
    def __init__(self, isnads_list: List[Isnad], db_url: str):
        self.isnads_list = isnads_list # list of insnad
        self.isnads_dict = {isn.sid: isn for isn in isnads_list} # a dictionary of isnads keyed with isnad ids
        self.hadiths_list = [] # list of corresponding hadith ids
        self.hadiths_dict = defaultdict(list) # a dictionary of isnads keyed with hadith ids 
        for isn in self.isnads_list:
            self.hadiths_dict[isn.hid].append(isn)
            if isn.hid not in self.hadiths_list:
                self.hadiths_list.append(isn.hid)
        self.db_url = db_url

    @staticmethod
    def get_full_isnadset(db_url: str) -> 'IsnadSet':
        """ Get all isnads in the database as an IsnadSet. """
        isnads_df = pd.read_sql_table('Isnad', db_url, 
                                       index_col='ID', columns=['HadithID', 'TransmitterIDs'])   
        ret = []
        for sid,hid,transmitter_ids in isnads_df.itertuples():
            # each row is like: 5717,412,660,1190,1496,5633,5485
            nodes = list(map(int, [tid for tid in transmitter_ids.split(',') if tid != '']))
            edges = list(zip(nodes, nodes[1:]))
            if len(edges) == 0:
                if verbose:
                    print(f'*** error in sid: {sid}')
                continue
            ret.append(Isnad(sid, hid, edges))
        
        return IsnadSet(ret, db_url)

    def get_curated(self, gens_dict: Dict[int,int]=None) -> 'IsnadSet':
        """ Return a curated version of self. 
        
        Steps:
            - remove diachronic edges (gens_dict can be provided as dictionary; otherwise constructed using isnad chains)
            - remove edges involving indefinite or Imam nodes

        Arguments:
            gens_dict: a dictionary of relative generation number of transmitters keyed by transmitter ids
        """
        if gens_dict is None:
            gens_dict = self.get_gens_dict()
        ret = []
        node_names = self.get_node_names_dict()
        for sid, isnad in self.isnads_dict.items():
            ne, nne = [], [] # new edges and newest edges
            
            # only keep non-anachronic edges from isnad.edges_list in ne
            for u,v in isnad.edges_list:
                if u in gens_dict and v in gens_dict and abs(gens_dict[u]-gens_dict[v]) <= 2:
                    ne.append((u,v))
            
            # only keep edges whose both ends are definite, non-Imam nodes
            for u,v in ne:
                un, vn = node_names[u], node_names[v]
                if not(un.startswith('غير ') or un.startswith('غير-') or un.startswith('بعض ') or
                    vn.startswith('غير ') or vn.startswith('غير-') or vn.startswith('بعض ') or
                    un.endswith(' ع') or vn.endswith(' ع')):
                    nne.append((u,v))
                    
            if len(nne) == 0:
                if verbose:
                    print('*** error in sid:', sid)
                continue
            ni = Isnad(sid, isnad.hid, nne)
            ret.append(ni)
        return IsnadSet(ret, self.db_url)
        
    def get_by_range(self, a: int, b: int) -> 'IsnadSet':
        """ Get isnads indexed at [a,b) as an IsnadSet. """
        if a < 0: a = 0
        return IsnadSet(self.isnads_list[a:b], self.db_url)
        
    def get_by_range_hadith(self, a: int, b: int) -> 'IsnadSet':
        """ Get isnads whose associated hadiths are indexed at [a,b) as an IsnadSet. """
        ret = []
        if a < 0: a = 0
        for hid in self.hadiths_list[a:b]:
            ret.extend(self.hadiths_dict[hid])
        return IsnadSet(ret, self.db_url)
    
    def get_node_names_dict(self) -> Dict[int, str]:
        transmitters_df = pd.read_sql_table('Transmitter', self.db_url, index_col='ID', columns=['Name'])
        return transmitters_df.to_dict()['Name']
    
    def get_hadith_books_dict(self) -> Dict[int, str]:
        """ Get a dictionary of hadith ids to book names. """
        hadiths_df = pd.read_sql_table('Hadith', self.db_url, 
                                       index_col='ID', columns=['BookName'])   
        return hadiths_df.to_dict()['BookName']
        
    def get_edges_sids_dict(self) -> Dict[Tuple[int,int],int]:
        """ Get a dictionary of isnads keyed by edges in the isnad. """
        ret = defaultdict(list)
        for isnad in self.isnads_list:
            for e in isnad.edges_list:
                ret[e].append(isnad.sid)
        ret2 = dict()
        for k,v in ret.items():
            ret2[k] = list(set(v))
        return ret2
                
    def get_nodes_sids_dict(self) -> Dict[int,int]:
        """ Get a dictionary of isnads keyed by nodes in the isnad. """
        assert len(self.isnads_list) != 0
        ret = defaultdict(list)        
        for isnad in self.isnads_list:
            for u in isnad.nodes_list:
                ret[u].append(isnad.sid)
        ret2 = dict()
        for k,v in ret.items():
            ret2[k] = list(set(v))
        return ret2
        
    def get_gens_dict(self) -> Dict[int,int]:
        """ Get an approximation relative generation number for each node. """
        aret = defaultdict(list)
        for isnad in self.isnads_list:
            for ui,u in enumerate(isnad.nodes_list):
                aret[u].append(ui)
                
        return {u: Counter(aret[u]).most_common()[0][0] for u in aret}
        
    def get_nx_graph(self) -> nx.digraph:
        """ Get isnad set as a weighted networkx DiGraph. """
        G = nx.DiGraph()
        all_es = []
        for (u,v),sids in self.get_edges_sids_dict().items():
            all_es.append((u,v,len(sids)))
        
        G.add_weighted_edges_from(all_es)
        return G
        
    def __sub__(self, other: 'IsnadSet') -> 'IsnadSet':
        """ Subtract two isnad lists. """
        assert self.db_url == other.db_url
        ret = []
        for isn in self.isnads_list:
            if isn.sid not in other.isnads_dict:
                ret.append(isn)
        return IsnadSet(ret, self.db_url)
    
    def __str__(self) -> str:
        return "IsnadSet (containing %d isnads)" % len(self.isnads_dict)
