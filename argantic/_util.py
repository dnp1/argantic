from typing import Dict, Any, List, Union

from multidict import MultiMapping


def multi_dict_to_dict(md: MultiMapping) -> Dict[Any, Union[Any, List[Any]]]:
    """
    This functions convert multi dict to dict. When a key has more than one value, it is treated as a list
    :param md:
    :return: dict

    """
    d: dict = {}
    for key in md.keys():
        value = md.getall(key)
        if len(value) > 1:
            d[key] = list(value)
        else:
            d[key] = value[0]
    return d
