from typing import Any, Dict, List, Tuple

from multidict import MultiDictProxy


def multi_dict_to_dict_of_lists(md: MultiDictProxy) -> Dict[Any, List[Any]]:
    d: Dict[List[Any]] = {}
    for k, v in md.items():
        d[k] = d.get(k, [])
        d[k].append(v)
    return d


def list_of_pairs_to_dict_of_lists(lt: List[Tuple[Any, Any]]) -> Dict[Any, List[Any]]:
    d: Dict[List[Any]] = {}
    for k, v in lt:
        d[k] = d.get(k, [])
        d[k].append(v)
    return d
