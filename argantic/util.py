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


async def identity_coro(x):
    return x


def update_all(list_data: list, replace_data: dict, override=True):
    for item in list_data:
        if type(item) != dict:
            continue
        if override:
            item.update(replace_data)
        else:
            for key in replace_data.keys():
                item[key] = item.get(key, replace_data[key])
