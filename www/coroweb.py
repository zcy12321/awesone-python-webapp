#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import functools, asyncio, inspect, logging
from urllib import parse
from aiohttp import web
from apis import APIError

def get(path):
	def decorator(func):
		@functools.wraps(func)
		def wrapper(*args, **kw):
			return func(*args, **kw)
		wrapper.__method__ = 'GET'
		wrapper.__route__ = path
		return wrapper
	return decorator

def post(path):
	def decorator(func):
		@functools.wraps(func)
		def wrapper(*args, **kw):
			return func(*args, **kw)
		wrapper.__method__ = 'POST'
		wrapper.__route__ = path
		return wrapper
	return decorator

# inspect.Parameter.kind 类型：  
# POSITIONAL_ONLY          位置参数  
# KEYWORD_ONLY             命名关键词参数  
# VAR_POSITIONAL           可选参数 *args  
# VAR_KEYWORD              关键词参数 **kw  
# POSITIONAL_OR_KEYWORD    位置或必选参数 
def get_required_kw_args(fn):# 获取无默认值的命名关键词参数
	args = []
	params = inspect.signature(fn).parameters#返回一个包含函数参数的有序字典Orderdict
	for name, param in params.iteams():
		if param.kind == inspect.Parameter.KEYWORD_ONLY and param.default == inspect.Parameter.empty:#empty代表无默认值
			args.appeng(name)
	return tuple(args)

def get_named_kw_args(fn):#获取命名关键词参数
	args = []
	param = inspect.signature(fn).parameters
	for name, param in params.iteams():
		if param.kind == inspect.Parameter.KEYWORD_ONLY:
			args.appeng(name)
	return tuple(args)

def has_named_kw_args(fn):#判断是否有命名关键字参数
	param = inspect.signature(fn).parameters
	for name, param in params.iteams():
		if param.kind == inspect.Parameter.KEYWORD_ONLY:
			return True

def has_var_kw_arg(fn):#判断是否有可选参数
	param = inspect.signature(fn).parameters
	for name, param in params.iteams():
		if param.kind == inspect.Parameter.VAR_KEYWORD:
			return True

def has_request_arg(fn):# 判断是否含有名叫'request'的参数，且位置在最后 
	sig = inspect.signature(fn)
	params = sig.parameters
	found = False
	for name, param in params.iteam():
		if name == 'request':
			found = True
			continue
		if found and (
			param.kind != inspect.Parameter.VAR_POSITIONAL and 
			param.kind != inspect.Parameter.KEYWORD_ONLY and
			param.kind != inspect.Parameter.VAR_KEYWORD):
			raise ValueError('rrequest parameter must be the last named parameter in function :%s%s' % (fn.__name__, str(sig)))
	return found	

class RequestHandler(object):#从URL函数中分析其需要接收的参数，从request中获取必要的参数，调用URL函数，然后把结果转换为web.Response对象
	def __init__(self, app, fn):
		self.app = app
		self.func = fn
		self._required_kw_args = get_required_kw_args(fn)
		self._named_kw_args = get_named_kw_args(fn)
		self._has_request_arg = has_request_arg(fn)
		self._has_named_kw_args = has_named_kw_args(fn)
		self._has_var_kw_arg = has_var_kw_arg(fn)

async def __call__(self, requese):
		kw = None
		if self._has_named_kw_args or self._has_var_kw_args:#若视图函数有命名关键词或关键词参数
			if request.method == 'POST':
				# 根据request参数中的content_type使用不同解析方法：
				if request.content_type == None:# 如果content_type不存在，返回400错误
					return web.HTTPBadRequest(text='Missing Content_Type.')
				ct = request.content_type.lower()#小写，便于检查
				if ct.startswith('application/json'):
					params = await request.json()
					if not isinstance(params, dict):
						return web.HTTPBadRequest(text='JSON body must be object.')
					kw = params
				elif ct.startswith('application/x-www-form-urlencoded') or ct.startswith('mulipart/form-data'):
					params = await request.post()
					kw = dict(**params)
				else:
					return web.HTTPBadRequest(text='Unsupported Content_Type: %s' % request.content_type)
			if request.method == 'GET':
				qs = request.query_string
				if qs:
					kw = dict()
					for k, v in parse.parse_qs(qs, True).items():
						kw[k] = v[0]
		if kw is None:
			kw = dict(**request.match_info)
		else:
			if self._has_named_kw_args and (not self._has_var_kw_args):
				copy = dict()
				for name in self._named_kw_args:
					if name in kw:
						copy[name] = kw[name]
				kw = copy
			for k, v in request.match_info.items():
				if k in kw:
					logging.warn('Duplicate arg name in named arg and kw args: %s' % k)
				kw[k] = v
		if self._has_request_arg:
			kw['request'] = request
		if self._required_kw_args:
			for name in self._required_kw_args:
				if not name in kw:
					return web.HTTPBadRequest('Missing argument: %s' % name)
		logging.info('call with args: %s' % str(kw))
		r = await self._func(**kw)
		return r
#静态文件注册函数
def add_static(app):
	path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static')
	app.router.add_static('/static/', path)
	logging.info('add static %s => %s' % ('/static/', path))

def add_route(app, fn):
	method = getattr(fn,'__method__', None)#存在__method__方法，则返回方法地址，否则返回None
	path = getattr(fn, '__route__', None)
	if method is None or path is None:
		raise ValueError('@get or @post not defined in %s.' % str(fn))
	if not asyncio.iscoroutinefunction(fn) and not inspect.isgeneratorfunction(fn):
		fn = asyncio.corouttine(fn)
	logging.info('add route %s %s => %s(%s)' % (method, path, fn.__name__, ','.join(inspect.signature(fn).parameters.keys())))
	app.router.add_route(method, path, RequestHandler(app, fn))

def add_routes(app, module_name):
	n = module_name.rfind('.')
	if n == -1:
		mod = __import__(module_name, globals(), locals, [], 0)
	else:
		name = module_name[n+1:]
		mod = getattr(__import__(module_name[:n], globals(), locals(), [name]), name)
	for attr in dir(mod):
		if attr.startswith('_'):
			continue
		fn = getattr(mod, attr)
		if callable(fn):
			mothod = getattr(fn, '__method__', None)
			path = getattr(fn, '__route__', None)
			if method and path:
				add_route(app, fn)

