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
def init(loop):
	app = web.Application(loop=loop)
	app.router.add_route('GET', '/', index)
	srv = yield from loop.create_server(app.make_handler(), '127.0.0.1', 9000)
	logging.info('server started at http://127.0.0.1:9000...')
	return srv
#获取EventLoop：
loop = asyncio.get_event_loop()
#执行coroutine
loop.run_until_complete(init(loop))
loop.run_forever()