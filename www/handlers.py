#!/usr/bin/env python3
# -*- coding: utf-8 -*-
' url handlers '
from coroweb import get, post

import asyncio, base64, hashlib, logging, json, time, re

from models import User, Blog, Comment, next_id
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