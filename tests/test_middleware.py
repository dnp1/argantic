import random
from typing import Dict, List, Any, Tuple
from unittest.mock import patch, Mock, call

from aiohttp import web
from aiohttp.test_utils import AioHTTPTestCase, unittest_run_loop
from multidict import MultiDictProxy
from pydantic import BaseModel

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


class Model(BaseModel):
    given_name: str
    family_name: str
    age: int
    preferences: List[str]


class TestMiddleware(AioHTTPTestCase):
    async def get_application(self):
        self.argantic = Argantic()
        self.app = web.Application(middlewares=[
            self.argantic.middleware(),
        ])
        self.app.router.add_post("/resource", TestMiddleware.post_handler)
        self.app.router.add_post("/resource-dict", TestMiddleware.post_handler_with_dict_argument)
        self.app.router.add_post("/resource-dict-tp", TestMiddleware.post_handler_with_dict_typing_argument)
        self.app.router.add_post("/resource-not-annotated", TestMiddleware.post_handler_without_annotation_argument)
        self.app.router.add_post("/resource-any", TestMiddleware.post_handler_with_any_argument)
        self.app.router.add_post("/resource-pydantic", TestMiddleware.post_handler_with_pydantic_model)

        self.app.router.add_get("/resource", TestMiddleware.get_handler)
        self.app.router.add_get("/resource/{id}/v2/{id_}", TestMiddleware.get_handler)
        return self.app

    @staticmethod
    async def post_handler(request: web.Request) -> web.Response:
        body = await request.json()
        return web.json_response(data=body)

    @staticmethod
    async def get_handler(request: web.Request) -> web.Response:
        params = request.query

        return web.json_response(data=multi_dict_to_dict_of_lists(params))

    @staticmethod
    async def post_handler_without_annotation_argument(request: web.Request, data):
        return web.json_response(data=data)

    @staticmethod
    async def post_handler_with_any_argument(request: web.Request, data: Any):
        return web.json_response(data=data)

    @staticmethod
    async def post_handler_with_dict_argument(request: web.Request, data: dict) -> web.Response:
        return web.json_response(data=data)

    @staticmethod
    async def post_handler_with_dict_typing_argument(request: web.Request, data: Dict) -> web.Response:
        return web.json_response(data=data)

    @staticmethod
    async def post_handler_with_pydantic_model(request: web.Request, data: Model ):
        return web.json_response(body=data.json())

    @unittest_run_loop
    async def test_ordinary_handler_works_handler(self):
        input_data = {'name': 'test_post', 'value': 'banana'}
        response = await self.client.post('/resource', json=input_data, params={'a': 1, 'b': 2})
        self.assertEqual(await response.json(), input_data)

    @unittest_run_loop
    async def test_handlers_are_created_once_per_resource(self):
        input_data = {'name': 'test_post', 'value': 'banana'}
        input_params = [('1', 'A'), ('1', 'a'), ('2', 'b')]
        with patch.object(self.argantic, '_create_handler',
                          side_effect=self.argantic._create_handler) as patched_create_handler:
            patched_create_handler: Mock = patched_create_handler
            for i in range(5, random.randint(10, 100)):
                response = await self.client.post('/resource', json=input_data)
                self.assertEqual(input_data, await response.json())
                response = await self.client.get('/resource', params=input_params)
                self.assertEqual(list_of_pairs_to_dict_of_lists(input_params), await response.json())
                response = await self.client.get(f'/resource/{i}/v2/{i**2}', params=input_params)
                self.assertEqual(list_of_pairs_to_dict_of_lists(input_params), await response.json())
                self.assertEqual(3, patched_create_handler.call_count)


    @unittest_run_loop
    async def test_handler_with_dict_argument_are_automatically(self):
        input_data = {'name': 'test_post', 'value': 'banana', 'vid': 1, 'URV': 1.001, 'BRL': 18.23345}
        response = await self.client.post('/resource-dict', json=input_data)
        self.assertEqual(await response.json(), input_data)

        response = await self.client.post('/resource-dict-tp', json=input_data)
        self.assertEqual(await response.json(), input_data)

        response = await self.client.post('/resource-not-annotated', json=input_data)
        self.assertEqual(await response.json(), input_data)

        response = await self.client.post('/resource-any', json=input_data)
        self.assertEqual(await response.json(), input_data)

    @unittest_run_loop
    async def test_handler_with_pydantic_model_are_properly_parsed(self):
        input_data = {'given_name': 'sardinha', 'family_name': 'pereira', 'age': 123, 'preferences': []}
        response = await self.client.post('/resource-pydantic', json=input_data)
        self.assertEqual(await response.json(), input_data)
