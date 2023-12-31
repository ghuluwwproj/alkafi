from multiprocessing import Pool
from os import path
from collections import defaultdict
import os
from typing import List, Tuple
import pickle
import matplotlib.pyplot as plt
import pandas as pd
from scipy.stats import mannwhitneyu
# from VD_A import VD_A
from cliffs_delta import cliffs_delta
from tqdm import tqdm

from utils import read_commented_plain_text, get_yes_no, IsnadSet

DB_URL = 'sqlite:///data/isnads-kafi.sqlite'
ACCUSED_IDs_IBN_QADAERI = read_commented_plain_text('data/accused-ibn-qadairi.txt', int)
ACCUSED_IDs_REST = read_commented_plain_text('data/accused-others.txt', int)
ACCUSED_IDs = ACCUSED_IDs_IBN_QADAERI + ACCUSED_IDs_REST

isnadsets_full = IsnadSet.get_full_isnadset(DB_URL).get_curated()
print('Full IsnadSet:', isnadsets_full)

ABLATION = False
if ABLATION:
    print('*** NOTE: ABLATION  STUDY ***')
full_hid_books_dict = isnadsets_full.get_hadith_books_dict()

N_PROCESSES = 10

def f(self, isnadsets_full, ys_all, i, W):
    ys_hi = self.get_hist_by_hadith(isnadsets_full, i, W)
    stat, p = mannwhitneyu(ys_hi, ys_all)        
    if p < .05:
        d, res = cliffs_delta(ys_hi, ys_all)
        #if res == 'large':
        if d >= 0.474:
        #ds.append(d)
            hid = isnadsets_full.hadiths_list[i]
            return (hid,d,res,p,stat,ys_hi)
    return None

class RQ:
    """Base class of all Research Questions"""
    def __init__(self, tag):
        self.name = type(self).__name__
        self.tag = tag
        
    def get_p(self, isnadset: IsnadSet, base_hid: int) -> float:
        """ Return a property (hence, 'p') of a hadith windows."""
        raise NotImplementedError('RQ::get_p is an abstract (pure virtual) method.')
        
    def get_hist_all(self, isnadset: IsnadSet, W: int) -> List[float]:
        """ Get the distribution of `get_p' properties of all (sliding) hadith windows in an isnadset.
        
        Note: The property is defined by get_p method in the subclasses of RQ.
        """
        NUM_H = len(isnadset.hadiths_list)
        ys = []
        for hi in range(NUM_H-W):
            Wi_isnadset = isnadset.get_by_range_hadith(hi, hi+W)
            ys.append(self.get_p(Wi_isnadset))
        return ys
    
    def get_hist_by_hadith(self, isnadset: IsnadSet, hi: int, W: int) -> List[float]:
        """ Get the distribution of `get_p' properties of all hadith windows overlapping with hadith index `hi'. 
            
        Notes:
            - `hi' is a hadith index (from 0), not a hadith_id (hid)
            - The property is defined by `get_p' method in the subclasses of `RQ'.
        """
        ys = []
        for i in range(W):
            #print(hi, ' - ', i)
            Wi_isnadset = isnadset.get_by_range_hadith(hi+i-W+1, hi+i+1)
            #print(len(Wi_isnadset.hadiths_list), hi+i-W+1, hi+i+1)
            hid = isnadsets_full.hadiths_list[hi]
            ys.append(self.get_p(Wi_isnadset, hid))
        return ys
        
    def load_hists(self, W: int) -> List[Tuple[int,float,str,float,float,List[float]]]:
        """ Return hids that the distribution of get_p property of their windows are significantly higher than that of al-Kafi.
        
        More explanation:
            ret = [hid for hid in all_hids
                if [get_p(w) for w in get_overlapping_windows(hid)] > [get_p(w) for w in get_all_windows(hid)]]

        Returns:
            A list of tuples (hid,cliff-delta-d,cliff-delta-res,MW-p,MW-stat,hist-of-hid)
        """
        NUM_H = len(isnadsets_full.hadiths_list)
        
        pickle_fn = 'pickles/hists-%s-%s.pickle' % (self.name, W)
        
        ans = False
        if path.exists(pickle_fn):
            ans = get_yes_no('Old pickle file (%s) found. Use it? [y/n] ' % pickle_fn)
            if not ans:
                ans = get_yes_no('Are you kidding? [y/n] ')
        
        ys_all = None
        
        if not ans:
            hists = []
            ys_all = self.get_hist_all(isnadsets_full, W)
                
            with Pool(processes=N_PROCESSES) as pool:
                args = [(self, isnadsets_full, ys_all, i, W) for i in range(NUM_H)]
                hists = pool.starmap(f, args)
                # hists = list(tqdm(pool.imap(f, range(0,NUM_H)), total=NUM_H))
            # Sort hists by cliff-d
            hists = [h for h in hists if h is not None]
            hists = sorted(hists, key=lambda e: e[1], reverse=True)
            os.makedirs('pickles', exist_ok=True)
            pickle.dump(hists, open(pickle_fn, 'wb'))
        
        return pickle.load(open(pickle_fn, 'rb'))
        
    def draw_books_hist(self, all_hists: List, aslice: slice, W: int, color: str):
        """ Plot the distribution of elements of a hists (as returned by load_hists) over al-Kafi chapters.
        
        Note: values in each chapter are normalized by chapter's length, so technically this is not a histogram. 
        """
        hists = all_hists[aslice]
        D = self.get_books_bars(hists)
        plt.figure()
        plt.bar(range(len(D)), list(D.values()), align='center', color=color)
        plt.xticks(range(len(D)), list(D.keys()), rotation=90)
        plt.xlabel('Book name')
        plt.ylabel('Normalized frequency')
        plt.title(f'Chapters of top-{aslice.stop} {self.tag} hadiths (W={W})')
        plt.tight_layout()

    def get_books_bars(self, hists):
        hid_books_dict = isnadsets_full.get_hadith_books_dict()
        book_lens = defaultdict(int)
        # bhdis_dict_debug = defaultdict(list)
        for hid,book_name in hid_books_dict.items():
            book_lens[book_name] += 1
        # book_counter holds distribution of above-average hids (i.e., each hid that the distribution of get_p of windows is 
        # larger than that of the whole al-Kafi) over al-Kafi books.
        book_counter = defaultdict(int)
        for hist in hists:
            hid = hist[0]
            book_counter[hid_books_dict[hid]] += 1
        
        book_counter_norm = {k: v/book_lens[k] for k,v in book_counter.items() if v>0}
        book_counter_norm = {k: v for k,v in 
                             sorted(book_counter_norm.items(), key=lambda e: e[1], reverse=True)}
        
        df = pd.read_csv('data/book-names-to-en.csv')
        en_names = pd.Series(df['en-name'].values,index=df['ar-name']).to_dict()
        D = {en_names[k]:book_counter_norm[k] for k in book_counter_norm.keys()}
        return D

    def draw_time_series_plot(self, Ws: List[int], colors: List[str]):
        plt.figure()
        for W, color in zip(Ws, colors):
            ys = self.get_hist_all(isnadsets_full, W)
            plt.plot(range(1, len(ys)+1), ys, label=f'W={W}', color=color)
        plt.xlabel('Windows number')
        plt.ylabel('Percent')
        plt.title(f'Percent of {self.tag} hadiths over whole al-Kafi')
        plt.legend()
        
    def run(self, Ws: List[int]):
        """Run an RQ and generate its plots by calling plot_books_hist.
        
        Args:
            Ws: A list of window sizes.
        """
        colors = ['blue', 'red', 'green']
        for Wi, W in enumerate(Ws):
            print(f'W={W}')
            hists = self.load_hists(W)
            self.draw_books_hist(hists, slice(0, 1000), W, colors[Wi])
            self.draw_books_hist(hists, slice(0, 2000), W, colors[Wi])
            self.draw_books_hist(hists, slice(0, 3000), W, colors[Wi])

        self.draw_time_series_plot(Ws, colors)
        plt.show()    

class RQ1(RQ):
    """ Is there a window of hadiths in whose transmission ghalis were influential (see the paper)? """
    def __init__(self):
        super().__init__('ghali-influenced')

    def get_p(self, isnadset, base_hid=None):
        """ Get the proportion of hadiths in whose transmission ghalis were influential. """
        num = 0
        for hid, isnads in isnadset.hadiths_dict.items():
            for isn in isnads:
                nl = isn.nodes_list
                if (ABLATION and 
                    base_hid is not None and
                    full_hid_books_dict[base_hid] == 'کتاب الدواجن'):
                        nl = [-1]*5
                if all([v not in ACCUSED_IDs for v in nl]):
                    break
            else:
                num += 1
        return num/len(isnadset.hadiths_dict)

class RQ2(RQ):
    """ Is there a window of hadiths with more pronounced ghali-to-ghali transmission?"""
    def __init__(self):
        super().__init__('ghali-to-ghali transmitted')
    def get_p(self, isnadset, base_hid=None):
        """ Get the proportion of ghali-to-ghali links in a window. """
        es = isnadset.get_edges_sids_dict()
        mes = [(x,y) for x,y in es if x in ACCUSED_IDs and y in ACCUSED_IDs]
        return len(mes)/len(es)
    
if __name__ == '__main__':
    rq1 = RQ1()
    rq1.run([20, 40, 60])
                    
    rq2 = RQ2()
    rq2.run([20, 40, 60])
