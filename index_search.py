import math

from index_builder import IndexBuilder
from string_group import StringGroup, get_levenshtein_distance
from unicode_converter import decompose_kor_unicode, reverse_kor_eng

def evaluate_token(token: str, index: list[dict[str,StringGroup|str]]) -> dict[str,float]:
  '''Evaluate how suitable a given token is for each markdown.'''
  score_table = {}
  match_list = []
  for sub_index in index:
    string_set = sub_index['string_set']
    min_distance = math.inf
    min_group = None
    # Evaluate token based on levenshtein distance for each string group
    for str_grp in string_set:
      avg_distance = get_levenshtein_distance(StringGroup(token), str_grp) / len(token)
      if avg_distance < min_distance:
        min_distance = avg_distance
        min_group = str_grp

    # Evaluate every markdowns based on the most appropriate group
    score =  (2 ** (-15*min_distance)) * math.log1p(len(min_group.group))
    score_table[sub_index['path']] = score
    match_list.append((score, min_group.centroid))

  match = sorted(match_list)[-1]
  return score_table, match

def evaluate_query(query: str, index: list[dict[str,StringGroup|str]], beta: float) -> dict[str, float]:
  '''Evaluate how suitable a given query is for each markdown.'''
  # initialize score table
  score_table = {}
  match_list = []
  for sub_index in index:
    score_table[sub_index['path']] = 0

  # Tokenize queries based on whitespace
  tokens = query.split()
  for token in tokens:
    token = ''.join(list(map(decompose_kor_unicode, token))) # convert kor unicode to each characters
    token = token.lower()
    token_score_table, match = evaluate_token(token, index)
    if match[0] < beta: # consider korean/english toggle key
      tkn_scr_tbl, mch = evaluate_token(reverse_kor_eng(token), index)
      if mch[0] > match[0]:
        match = mch
        token_score_table = tkn_scr_tbl

    for path, score in token_score_table.items():
      score_table[path] += score
    match_list.append(match)

  return score_table, match_list

def search(query: str,
           root: str,
           index_file: str='index/index.json',
           skip_indexing: list[str]=[],
           alpha: float=0.2,
           beta: float=0.005):
  '''Search function that searches the markdown that best matches the query using a given index file.
  Returns a list of eligible markdowns, each tokens used in the search, and its scores.
  Markdown with fitness below beta is omitted.
  If there is no index file in the given path, create a new one.'''
  index = IndexBuilder.load_index(index_file)
  if index == []:
    IndexBuilder.build_index(root, index_file, skip_indexing, alpha)
    index = IndexBuilder.load_index(index_file)

  score_table, match_list = evaluate_query(query, index, beta)
  filtered_table = {key: value for key, value in score_table.items() if value >= beta}
  result = sorted(filtered_table, key=lambda k: filtered_table[k], reverse=True)
  return result, match_list