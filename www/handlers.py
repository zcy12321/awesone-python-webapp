#!/usr/bin/env python3
# -*- coding: utf-8 -*-
' url handlers '
from coroweb import get, post

import asyncio, base64, hashlib, logging, json, time, re

from models import User, Blog, Comment, next_id
@get('/')
async def index(request):
	users = await User.findAll()
	return {
		'__template__': 'test.html',
		'users': users
	}
#eturn web.Response(text='<h1>你好！妳好（繁體字）</h1>', content_type='text/html',charset='utf-8')
#GB2312是中国规定的汉字编码，简体中文的字符集编码，
#GBK是GB2312的扩展 ,兼容GB2312、显示繁体中文、日文的假名
#UTF-8是全世界通用的