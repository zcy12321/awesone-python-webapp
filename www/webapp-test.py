#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# from orm import Model, StringField, IntegerField
# import orm
# from models import User, Blog, Comment
# import asyncio
# loop = asyncio.get_event_loop()
# async def test():
# 	await orm.create_pool(loop=loop, host='127.0.0.1', port=3306, user='root', password='password', db='awesome')
# 	u = User(name='New_Test', email='750570753@qq.com', passwd='1234321', image='about:black',id='3')
# 	a = await u.findAll() #这个要打印才显示出来
# 	print(a)
# 	await u.save()


# loop.run_until_complete(test())
# orm.__pool.close()
# loop.run_until_complete(orm.__pool.wait_closed())
# loop.close()
from coroweb import get
import asyncio
from app import init_jinja2
@get('/')
async def index(request):
	return '<h1>Awesome</h1>'

@get('/hello')
async def hello(request):
	return '<h1>hello!</h1>'

if __name__=='__main__':
	async def init(loop):
		app = web.Application(loop=loop, middlewares=[logger_factory, response_factory])
		init_jinja2(app, filters=dict(datetime = datetime_filter))
		add_routes(app, 'test_view')
		add_static(app)
		srv = await loop.create_serve(app.make_handler(), 'localhost', 9000)
		logging.info('serve started at http://127.0.0.1:9000...')
		return srv

	loop = get_event_loop()
	loop.run_until_complete(init())
	loop.run_forever()


