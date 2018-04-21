#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#ORM全称“Object Relational Mapping”，即对象-关系映射，就是把关系数据库的一行映射为一个对象，
#也就是一个类对应一个表，这样，写代码更简单，不用直接操作SQL语句。
import asyncio, logging

import aiomysql

def log(sql, args=()):
	logging.info('SQL:%s' % sql)
#创建连接池,调用异步IO来创建__pool

async def create_pool(loop, **kw):#**kw是关键字参数，用于字典
	logging.info('create database connection pool...')
	global __pool #定义全局变量__pool
	__pool = await aiomysql.create_pool(
		host = kw.get('host', 'localhost'),#get()函数，两个参数（查找的键，不存在返回的值）
		port = kw.get('port', 3306),
		user = kw['user'],
		password = kw['password'],
		db = kw['db'],
		charset = kw.get('charset', 'utf8'),
		autocommit = kw.get('autocommit', True),#默认自动提交事物
		maxsize = kw.get('maxsize', 10),
		minsize = kw.get('minsize', 1),
		loop = loop
		)

async def select(sql, args, size=None):
	log(sql, args)
	global __pool
	async with __pool.get() as conn:
		async with conn.cursor(aiomysql.DictCursor) as cur:#游标返回结果作为dict
			await cur.execute(sql.replace('?', '%s'), args or ())
			if size:
				rs = await cur.fetchmany(size)#如果传入size参数，就通过fetchmany()获取最多指定数量的记录
			else:
				rs = await cur.fetchall()#否则，通过fetchall()获取所有记录。
		logging.info('rows returned: %s' % len(rs))
		return rs#返回查询结构，元素是tuple的list

#通用的execute()函数，用于执行INSERT、UPDATE、DELETE语句
async def execute(sql, args, autocommit=True):
	log(sql)
	async with __pool.get() as conn:
		if not autocommit:
			await conn.begin()
		try:
			async with conn.cursor(aiomysql.DictCursor) as cur:
				await cur.execute(sql.replace('?', '%s'), args)
				affected = cur.rowcount
			if not autocommit:
				await conn.commit()
		except BaseException as e:
			if not autocommit:
				await conn.rollback()
			raise
		return affected
# 这个函数主要是把查询字段计数 替换成sql识别的?  
# 比如说：insert into  `User` (`password`, `email`, `name`, `id`) values (?,?,?,?)  看到了么 后面这四个问号  
def create_args_string(num):
	L = []
	for n in range(num):
		L.append('?')
	return (', '.join(L))
# 定义Field类，负责保存(数据库)表的字段名和字段类型			
class Field(object):

	def __init__(self, name, column_type, primary_key, default):
		self.name = name
		self.column_type = column_type
		self.primary_key = primary_key#主键
		self.default = default

	def __str__(self):
		 # 返回 表名字 字段名 和字段类型
		return '<%s, %s:%s>' % (self.__class__.__name__, self.column_type, self.name)
# 定义数据库中五个存储类型  
class StringField(Field):
	"""docstring for StringField"""
	def __init__(self, name=None, primary_key=False, default=None, ddl='varchar(100)'):
		super().__init__(name, ddl, primary_key, default)#引入super()的目的是保证相同的基类只初始化一次
# 布尔类型不可以作为主键		
class BooleanField(Field):

	def __init__(self, name=None, default=False):
		super().__init__(name, 'boolean',False, default)

class IntegerField(Field):

	def __init__(self, name=None, primary_key=False, default=0):
		super().__init__(name, 'bigint', primary_key, default)

class FloatField(Field):

	def __init__(self, name=None, primary_key=False, default=0.0):
		super().__init__(name,'real',primary_key, default)

class TextField(Field):

	def __init__(self, name=None, default=None):
		super().__init__(name,'text', False, default)
		
# -*-定义Model的元类  
# 所有的元类都继承自type  
# ModelMetaclass元类定义了所有Model基类(继承ModelMetaclass)的子类实现的操作  
   
# -*-ModelMetaclass的工作主要是为一个数据库表映射成一个封装的类做准备：  
# ***读取具体子类(user)的映射信息  
# 创造类的时候，排除对Model类的修改  
# 在当前类中查找所有的类属性(attrs)，如果找到Field属性，就将其保存到__mappings__的dict中，同时从类属性中删除Field(防止实例属性遮住类的同名属性)  
# 将数据库表名保存到__table__中  
   
# 完成这些工作就可以在Model中定义各种数据库的操作方法  
# metaclass是类的模板，所以必须从`type`类型派生： 
class ModelMetaclass(type):#元类

	def __new__(cls, name, bases, attrs):
		#排除model本身,因为要排除对model类的修改
		if name == 'Model':
			return type.__new__(cls, name, bases, attrs)
		#获取table名称
		tableName = attrs.get('__table__', None) or name #如果存在表名，则返回表名，否则返回 name  
		logging.info('found model: %s (table: %s)' % (name, tableName))
		#获取所有的Field和主键名
		mappings = dict()
		fields = [] #field保存的是除主键外的属性名 
		primaryKey = None
		for k, v in attrs.items():
			if isinstance(v, Field):
				logging.info('found mapping: %s ==> %s' % (k, v))
				mappings[k] = v
				if v.primary_key:
					#找到主键,这里很有意思 当第一次主键存在primaryKey被赋值 后来如果再出现主键的话就会引发错误 
					if primaryKey:
						raise RuntimeError('Duplicate primary key for field: %s' % k)#一个表只能有一个主键，当再出现一个主键的时候就报错  
					primaryKey = k# 也就是说主键只能被设置一次 
				else:
					fields.append(k)
		if not primaryKey:#一个表必须有一个主键,否则报错  
			raise StandardError('Primary key not found')
		# 下面位字段从类属性中删除Field 属性 	
		for k in mappings.keys():
			attrs.pop(k)
		escaped_fields = list(map(lambda f: ' `%s` ' % f, fields))
		attrs['__mappings__'] = mappings #保存属性和列的映射关系
		attrs['__table__'] = tableName# 保存表名  
		attrs['__primary_key__'] = primaryKey#主键属性名
		attrs['__fields__'] = fields#除主键外的属性名
		# 构造默认的SELECT, INSERT, UPDATE和DELETE语句:
		attrs['__select__'] = 'select `%s`, %s from `%s`' % (primaryKey, ', '.join(escaped_fields), tableName)
		attrs['__insert__'] = 'insert into `%s` (%s, `%s`) values (%s)' % (tableName, ', '.join(escaped_fields), primaryKey, create_args_string(len(escaped_fields)+1))
		attrs['__update__'] = 'update `%s` set %s where `%s`=?' % (tableName, ', '.join(map(lambda f: '`%s` = ?' % (mappings.get(f).name or f), fields)), primaryKey)
		attrs['__delete__'] = 'delete from `%s` where `%s`=?' % (tableName, primaryKey)
		return type.__new__(cls, name, bases, attrs)
# 定义ORM所有映射的基类：Model  
# Model类的任意子类可以映射一个数据库表  
# Model类可以看作是对所有数据库表操作的基本定义的映射  
    
# 基于字典查询形式  
# Model从dict继承，拥有字典的所有功能，同时实现特殊方法__getattr__和__setattr__，能够实现属性操作  
# 实现数据库操作的所有方法，定义为class方法，所有继承自Model都具有数据库操作方法 
class Model(dict, metaclass=ModelMetaclass):
	def __init__(self, **kw):
		super(Model, self).__init__(**kw)

	def __getattr__(self, key):
		try:
			return self[key]
		except KeyError:
			raise AttributeError(r"'Model' object has no attribute '%s'" % key)
	def __setattr__(self, key, value):
		self[key] = value

	def getValue(self, key):
		return getattr(self, key, None)

	def getValueOrDefault(self, key):
		value = getattr(self, key, None)
		if value is None:
			field = self.__mappings__[key]
			if field.default is not None:
				value = field.default() if callable(field.default) else field.default
				logging.debug('using default value for %s: %s' % (key, str(value)))
				getattr(self, key, value)
		return value

	@classmethod
	async def findAll(cls, where=None, args=None, **kw):
		' find objects by where clause. '
		sql = [cls.__select__]
		if where:
			sql.append('where')
			sql.append(where)
		if args is None:
			args = []
		orderBy = kw.get('orderBy', None)
		if orderBy:
			sql.append('order by')
			sql.append(orderBy)
		limit = kw.get('limit', None)
		if limit is not None:
			sql.append('limit')
			if isinstance(limit, int):
				sql.append('?')
				args.append(limit)
			elif isinstance(limit, tuple) and len(limit) == 2:
				sql.append('?, ?')
				args.extend(limit)
			else:
				raise ValueError('Invalid limit value: %s' % str(limit))
		rs = await select(' '.join(sql), args)
		return [cls(**r) for r in rs]

	@classmethod
	@asyncio.coroutine
	def findNumber(cls, selectField, where=None, args=None):
		' find number by select and where. '
		sql = ['select %s _num_ from `%s`' % (selectField, cls.__table__)]
		if where:
			sql.append('where')
			sql.append(where)
		rs = yield from select(' '.join(sql), args, 1)
		if len(rs) == 0:
			return None
		return rs[0]['_num_']
	@classmethod
	@asyncio.coroutine
	def find(cls, pk):
		'find object by primary key.'
		rs = yield from select('%s where %s =?' % (cls.__select__, cls.__primary_key__), [pk], 1)
		if len(rs) == 0:
			return None
		return cls(**rs[0])

	@asyncio.coroutine
	def save(self):
		args = list(map(self.getValueOrDefault, self.__fields__))
		args.append(self.getValueOrDefault(self.__primary_key__))
		rows = yield from execute(self.__insert__, args)
		if rows != 1:
			logging.warn('field to insert record: affected rows:%s' % rows)
	@asyncio.coroutine
	def update(self):
		args = list(map(self.getValue, self.__fields__))
		args.append(self.getValue(self.__primary_key__))
		rows = yield from execute(self.__update__, args)
		if rows != 1:
			logging.warn('failed to update by primary key: affected rows: %s' % rows)
	@asyncio.coroutine
	def remove(self):
		args = [self.getValue(self.__primary_key__)]
		rows = yield from execute(self.__delete__, args)
		if rows != 1:
			logging.warn('failed to remove by primary key: affected rows: %s' % rows)



