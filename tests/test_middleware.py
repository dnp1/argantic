import random
from typing import Dict, List, Any, Tuple
from unittest.mock import patch, Mock, call

from aiohttp import web
from aiohttp.test_utils import AioHTTPTestCase, unittest_run_loop
from multidict import MultiDictProxy

from argantic import Argantic


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


class TestMiddleware(AioHTTPTestCase):
    async def get_application(self):
        self.argantic = Argantic()
        self.app = web.Application(middlewares=[
            self.argantic.middleware(),
        ])
        self.app.router.add_post("/resource", TestMiddleware.post_handler)
        self.app.router.add_get("/resource", TestMiddleware.get_handler)
        return self.app

    @staticmethod
    async def post_handler(request) -> web.Response:
        body = await request.json()
        return web.json_response(data=body)

    @staticmethod
    async def get_handler(request) -> web.Response:
        params = request.query

        return web.json_response(data=multi_dict_to_dict_of_lists(params))

    @unittest_run_loop
    async def test_ordinary_handler_works_handler(self):
        input_data = {'name': 'test_post', 'value': 'banana'}
        response = await self.client.post('/resource', json=input_data, params={'a': 1, 'b': 2})
        self.assertEqual(await response.json(), input_data)

    @unittest_run_loop
    async def test_handlers_are_created_once_per_endpoint(self):
        input_data = {'name': 'test_post', 'value': 'banana'}
        input_params = [('1', 'A'), ('1', 'a'), ('2', 'b')]
        with patch.object(self.argantic, '_create_handler',
                          side_effect=self.argantic._create_handler) as patched_create_handler:
            patched_create_handler: Mock = patched_create_handler
            for i in range(1, random.randint(10, 100)):
                response = await self.client.post('/resource', json=input_data)
                self.assertEqual(input_data, await response.json())
                response = await self.client.get('/resource', params=input_params)
                self.assertEqual(list_of_pairs_to_dict_of_lists(input_params), await response.json())
                self.assertEqual(2, patched_create_handler.call_count)
