#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import logging; logging.basicConfig(level=logging.INFO)
#一行中书写多条句必须使用分号分隔每个语句，否则Python无法识别语句之间的间隔
import asyncio, os, json, time
from datetime import datetime

from aiohttp import web

def index(request):
	return web.Response(text='<h1>你好！妳好（繁體字）</h1>', content_type='text/html',charset='utf-8')
#GB2312是中国规定的汉字编码，简体中文的字符集编码，
#GBK是GB2312的扩展 ,兼容GB2312、显示繁体中文、日文的假名
#UTF-8是全世界通用的

@asyncio.coroutine
def logger_factory(app, handler):
	@asyncio.coroutine
	def logger(request):
		#记录日志
		logging.info('Request: %s %s' % (request.method, request.path))
		#继续处理请求
		return (yield from handler(request))
	return logger

@asyncio.coroutine
def response_factory(app, handler):
	@asyncio.coroutine
	def response(request):
		#结果
		r = yield from handler(request)
		if isinstance(r, web.StreamResponse):
			return r
		if isinstance(r, bytes):
			resp = web.Response(body=r)
			resp.content_type = 'application/octet=stream'
			return resp
		if isinstance(r, str):
			if r.startswith('redirect:'):
				return web.HTTPFound(r[9:])
			resp = web.Response(body=r.encode('utf-8'))
			resp.content_type = 'text/html;charset=utf-8'
			return resp
		if isinstance(r, dict):
			template = r.get('__template__')
			if template is None:
				resp = web.Response(body=json.dumps(r, ensure_ascii=False, default=lambda o: o.__dict__).encode('utf-8'))
				resp.content_type = 'application/json;charset=utf-8'
				return resp 
			else:
				resp = web.Response(body=app['__template__'].get_template(template).render(**r).encode('utf-8'))
				resp.content_type = 'text/html;charset=utf-8'
				return resp
		if isinstance(r, int) and r >= 100 and r < 60:
			return web.Response(r)
		if isinstance(r, tuple) and len(r) == 2:
			t, m = r
			if isinstance(t, int) and t >= 100 and t < 600:
				return web.Response(t, str(m))
		#default
		resp = web.Response(body=str(r).encode('utf-8'))
		resp.content_type = 'text/plain;charset=utf-8'
		return resp
	return response



@asyncio.coroutine
def init(loop):
	app = web.Application(loop=loop, middlewares=[logger_factory, response_factory])
	init_jinja2(app, filters=dict(datetime=datetime_filter))
	add_routes(app, 'handlers')
	add_static(app)
	app.router.add_route('GET', '/', index)
	srv = yield from loop.create_server(app.make_handler(), '127.0.0.1', 9000)
	logging.info('server started at http://127.0.0.1:9000...')
	return srv
#获取EventLoop：
loop = asyncio.get_event_loop()
#执行coroutine
loop.run_until_complete(init(loop))
loop.run_forever()

