#!/usr/bin/env python3
# -*- coding: utf-8 -*-
' url handlers '
from coroweb import get, post

import asyncio, base64, hashlib, logging, json, time, re

from aiohttp import web

from apis import APIError, APIValueError

from models import User, Blog, Comment, next_id
from config import configs
@get('/')
def index(request):
	summary = 'Lorem ipsum dolor sit amet, consectrtur adipisicing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.'
	blogs = [Blog(id='1', name='Test Blog', summary=summary, created_at=time.time()-120),
			 Blog(id='2', name='Something New', summary=summary, created_at=time.time()-3600),
			 Blog(id='3', name='Learn Swift', summary=summary, created_at=time.time()-7200),
			 ]
#	users = await User.findAll()
	return {
		'__template__': 'blogs.html',
		'blogs': blogs
	}

@get('/register')
def register():
	return{
		'__template__': 'register.html'
	}

@get('/signin')
def signin():
	return{
		'__template__': 'signin.html'
	}

@get('/api/users')
async def api_get_users(request):
	users = await User.findAll(orderBy='created_at desc')
	for u in users:
		u.passwd = '******'
	return dict(users=users)

	# page_index = get_page_index(page)
	# num = yield from User.findNumber('count(id')
	# p = Page(num, page_index)
	# if num == 0:
	# 	return dict(page=p, user=())
	# users = yield from User.findAll(orderBy='created_at desc', limit=(p.offset, p.limit))
	# for u in users:
	# 	u.passwd = '******'
	# return dict(page=p, users=users)
	# pass
#eturn web.Response(text='<h1>你好！妳好（繁體字）</h1>', content_type='text/html',charset='utf-8')
#GB2312是中国规定的汉字编码，简体中文的字符集编码，
#GBK是GB2312的扩展 ,兼容GB2312、显示繁体中文、日文的假名
#UTF-8是全世界通用的
async def auth_factory(app, handler):
	async def auth(request):
		logging.info('check user: %s %s' % (request.method, request.path))
		request.__user__ = None
		cookie_str = request.cookie.get(COOKIE_NAME)
		if cookie_str:
			user = await cookie2user(cookie_str)
			if user:
				logging.info('set current user: %s') % user.email
				request.__user__ = user
		return (await handler(request))
	return auth

#解密cookie
async def cookie2user(cookie_str):

	if not cookie_str:
		return None
	try:
		L = cookie_str.split('-')
		if len(L) != 3:
			return None
		uid, expires, sha1 = L
		if int(expires) < time.time():
			return None
		user = await User.find(uid)
		if user is None:
			return None
		s = '%s-%s-%s-%s' % (uid, user.passwd, expires, __COOKIE_KEY)
		if sha1 != hashlib.sha1(s.encode('utf-8')).hexdigest():
			logging.info('Invalid sha1')
			return None
		ueer.passwd = '******'
		return user
	except Exception as e:
		logging.exception(e)
		return None

COOKIE_NAME = 'awesession'
__COOKIE_KEY = configs.session.secret
def user2cookie(user, max_age):
	...
	#Generate cookie str by user.
	...
	expires = str(int(time.time() + max_age))
	s = '%s-%s-%s-%s' % (user.id, user.passwd, expires, __COOKIE_KEY)
	L = [user.id, expires, hashlib.sha1(s.encode('utf-8')).hexdigest()]
	return '-'.join(L)

@post('/api/authenticate')
async def authenticate(*, email, passwd):
	if not email:
		raise APIValueError('email', 'Invalid email.')
	if not passwd:
		raise APIValueError('passwd', 'Invalid passwd')
	users = await User.findAll('email=?', [email])
	if len(users) == 0:
		raise APIValueError('email', 'Email not exist.')
	user = users[0]
	sha1 = hashlib.sha1()
	sha1.update(user.id.encode('utf-8'))
	sha1.update(b':')
	sha1.update(passwd.encode('utf-8'))
	if user.passwd != sha1.hexdigest():	
		raise APIValueError('passwd', 'Invalid password.')
	r = web.Response()
	r.set_cookie(COOKIE_NAME, user2cookie(user, 86400), max_age=86400, httponly=True)
	user.passwd = '******'
	r.content_type = 'application/json'
	r.body = json.dumps(user, ensure_ascii=False).encode('utf-8')
	return r

@get('/signout')
def signout(request):
	referer = request.headers.get('Referer')
	r = web.HTTPFounf(referer or '/')
	r.set_cookie(COOKIE_NAME, '-deleted-', max_age=0, httponly=True)
	logging.info('user signed out')
	return r

_RE_EMAIL =  re.compile(r'^[a-z0-9\.\-\_]+\@[a-z0-9\-\_]+(\.[a-z0-9\-\_]+){1,4}$')
_RE_SHA1 = re.compile(r'^[0-9a-f]{40}$')

@post('/api/users')
async def api_register_user(*, email, name, passwd):
	if not name or not name.strip():#strip() 方法用于移除字符串头尾指定的字符
		raise APIValueError('name')
	if not email or not _RE_EMAIL.match(email):#起始位置匹配正则表达式，否则返回None
		raise APIValueError('email')
	if not passwd or not _RE_SHA1.match(passwd):
		raise APIValueError('passwd')
	users = await User.findAll('email=?', [email])
	if len(users) > 0:
		raise APIError('register:failed', 'email', 'Email is already in use.')
	uid = next_id()
	sha1_passwd = '%s:%s' % (uid, passwd)
	user = User(id=uid, name=name.strip(), email=email, passwd=hashlib.sha1(sha1_passwd.encode('utf-8')).hexdigest(), image='http://www.gravatar.com/avatar/%s?d=mm&s=120' % hashlib.md5(email.encode('utf-8')).hexdigest())
	await user.save()
	r = web.Response()
	r.set_cookie(COOKIE_NAME, user2cookie(user, 86400), max_age=86400, httponly=True)
	user.passwd = '******'	
	r.content_type='application/json'
	r.body = json.dumps(user, ensure_ascii=False).encode('utf-8')
	return r

