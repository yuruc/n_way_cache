# -*- coding: utf-8 -*-
"""

Implementation of N-way Set-associative cache

author: Yu-Ju Chang

This module serves as a in-memory  N-way Set-associative cache which user could \
use to store items(key and value pairs) and quickly access them. The type of \
the keys and values could be any type but all the keys and all the values \
should be the same type. 

Set-associative cache is used in hardware implementation, yet here the module \
provides a software simulation of it. For details of Set-associative cache, \
see here: 

https://en.wikipedia.org/wiki/Cache_Placement_Policies#Set_Associative_Cache



Input values:
Several values are needed for using this cache module. 
They are cache_size, n_way, b, key_type, value_type. 

cache_size (int): `cache_size` is the size of the cache we can use to save items. \
	if cache size == n, it means we can store at most n items. \
	cache size should be larger than n_ways * number of sets \
	* offset size.

n_way(int): `n_way` is used to specify how many ways/lines in a \
	cache set. 

b(int): `b` is used to calculate offset size. offset size is 2^b.

key_type and value_type could be any type but all keys should \
	be the same type and so do all values.  

Following values are optional. Users are free to use. 

replacement(:obj:`ReplacementPolicy`, optional): `replacement` is to set the cache \
	replacement policy. User could either to pass a subclass of \
	`ReplacementPolicy` or pass a string to specify the `LRU` or `MRU` policy. \
	Default setting is `LRU`.

	For details about LRU, see here: 

	https://en.wikipedia.org/wiki/Cache_replacement_policies#LRU

	For details about MRU, see here:

	https://en.wikipedia.org/wiki/Cache_replacement_policies#Most_recently_used_(MRU)

hash(:func:, optional): `hash` is to provide the hash function that used to hash keys \
	of the items. Default setting is to use python's built-in hash function. 

thread_safe_mode(bool, optional): when `thread_safe_mode` == True, means the \
        class is thread safe, One thing must be noted is that thread safe mode will \
        have worse performance regrading of time since lock is costly. Default \
        setting is True (enable thread safe mode).

Operations:
The cache module provide three operations. 

1. set_value(key, value): users could put items(key and value pairs) into the cache. 

	The key will be hash with the provided hash function, and then get set \
	number, offset index and tag from the hashed result. First need to check \
	if all of the lines of the set is full and if any line has the same tag.	 
		a. if the one line has the same tag, replace/put the item into \
                correspond offset directly	 
		b. if full, choose one line to evict based on evict policy
		c. if not full, place it into a new line and update the new line
	If there is any collision of key, then the old item will be replaced \
	directly.
	Replacement policy object should be updated under all of the situations. 

2. get_value(key): users could get items(key and value pairs) from the cache.
	The key will be hash with the provided hash function, and then get set \
	number, offset index and tag from the hashed result. First need to check \
	if it is valid(tag matches means it is valid), if it's valid, we then check \
	the offset index.
            a. if it is not in the cache, throw an exception 
            b. if in the cache, return the object and adjust current replacement \
            policy object.
	Replacement policy object should be updated under all of the situations. 

3. delete(key, value): users could delete items(key and value pairs) \
	from the cache.
	Similiar to get_value and set_value, the key will be hash with the \
	provided hash function, and then get set number, offset index and tag \
	from the hashed result. if tag matches: 
                a. if the item not in the cache, do nothing 
                b. if in the cache, delete the object and adjust current replacement \
                policy object. 	 
	Replacement policy object should be updated under all of the situations. 

Test: Please see cache_test.py to see the unit test code. 

Usage:
	To use the module, start with following lines::

		import cache 
		cache_size, n_way, b = 16, 2, 2 
		key_type, value_type = int, int
		#initialize the cache with your own setting
		test_cache = cache.Cache(cache_size, n_way, b, key_type, value_type)
		test_cache.set(1, 3) 
		value = test_cache.get(1) 
		test_cache.delete(1, 3)

Example use case:
	An in-memory cache could be used on an application server to store data \
	associated with user id, so we could avoid to get data from database \
	for every request.  



"""
import sys
import math
import unittest
import threading
import logging


logging.basicConfig(filename='cache_debug_log.log',level=logging.DEBUG)

class CacheLine(object):
	'''CacheLine class serves as a cache line in the cache.'''
	def __init__(self, offset_size, tag = None, thread_safe_mode = True):
		"""The __init__ method of a cache is used to initialize a cache line.

		Args:
			offset_size(int): `offset_size` is used to set the offset size in \
				a cache line. 

			tag(int, optional): `tag` is the tag of a line. When the line is \
				empty, it is set to be None. Default value is None. 

			thread_safe_mode(bool, optional): when `thread_safe_mode` == True, \
				means the class is thread safe, One thing must be noted is that \
				thread safe mode will have worse performance regrading of time \
				since lock is costly. Default setting is True (enable thread \
				safe mode).

		"""
		super(CacheLine, self).__init__()

		if thread_safe_mode:
			self.lock = threading.Lock()
		else:
			self.lock = None
		self.tag = tag
		self.offset = [ None ] * offset_size
		#valid list is to mark if user put in items (it is possible that user 
		#put None into cache too, 
		#so we need to keep track if it's valid. 1 means user put in something
		# into cache, otherwise 0. 
		self.valid = [0] * offset_size 
		#valid_count is to keep track of the number of valid items in the 
		#cache line. 
		self.valid_count = 0
		self.offset_size = offset_size

	def get_tag(self):
		"""get_tag is a function to get the tag of the current cache line. 

		Returns:
			return the tag of the current cache line .

		"""
		return self.tag

	def match_tag(self, tag):
		"""match_tag is a function to see if a tag is the same as the tag of the \
		current cache line. 

		Args:
			tag(int): `tag` is the tag of a line.

		Returns:
			return True if a tag is the same as the tag of the current cache line. \
			False Otherwise. 

		"""
		return self.tag == tag

	def set_tag(self, tag):
		"""set_tag is a function to set tag of the current cache line. 

		Args:
			tag(int): `tag` is the tag of a line.

		"""
		self.tag = tag

	def set(self, offset_index, value):

		"""set is to put an item(a key and value pair) into the cache line.

		Args:
			offset_index(int): `offset_index` is the index of the cache line offset \
				where the item will be put into.

			value(value_type): `value` is the value of the item

		"""

		logging.debug("cacheline set acquire a lock")
		out_of_bound = False 
		if self.lock != None:
			self.lock.acquire()
		try:
			self.valid[offset_index] = 1
			self.offset[offset_index] = value
			self.valid_count += 1 
		except: #could be out of bound 
			out_of_bound = True
		logging.debug("cacheline set release a lock") 
		if self.lock != None:
			self.lock.release()
		if out_of_bound:
			raise IndexError("Out of bound", sys.exc_info()[0]) 


	def get(self, offset_index):
		"""get is to get an item(a key and value pair) from the cache line.

		Args:
			offset_index(int): `offset_index` is the index of the cache line \
				offset where the item will be get from.

		Returns:
			if the value exist, return the value of the key. Otherwise raise \
			 an error.
		"""
		logging.debug("cacheline get acquire a lock") 
		if self.lock != None:
			self.lock.acquire()
		try:
			if self.valid[offset_index] == 1:
				logging.debug("cacheline get release a lock")
				self.lock.release() 
				return self.offset[offset_index]
			else: 
				raise ValueError("Access unintialized offset")
		except:
			logging.debug("Unexpected error:", sys.exc_info()[0])
		logging.debug("cacheline get release a lock") 
		if self.lock != None:
			self.lock.release() 



	def delete(self, offset_index, value):

		"""delete is to delete the item which in the offset index and match the \
		 value.

		Args:
			offset_index(int): `offset_index` is the index of the cache line \
				offset where the item shoule be located at.

			value(value_type): `value` is the value of the item which is going to be \
				deleted.

		Returns:
			if the value exist and be successfully deleted, and if the line \
			become an empty line, then it also will needed remove from the LRU \
			replacer, so return the tag of it; if the line isn't empty, then \
			return None. if not successfully deleted, return False.
		"""

		logging.debug("cacheline delete acquire a lock") 
		if self.lock != None:
			self.lock.acquire() 
		if self.valid[offset_index] == 1 and self.offset[offset_index] == value:
			self.offset[offset_index] = None
			self.valid[offset_index] = 0
			self.valid_count -= 1

			if self.valid_count == 0:
				#need to also deal with LRU replacer & clear the tag
				tag_to_delete = self.tag
				self.tag = None
				if self.lock != None:
					self.lock.release()
				logging.debug("cacheline delete release a lock") 
				return tag_to_delete
			else:
				logging.debug("cacheline delete release a lock") 
				if self.lock != None:
					self.lock.release() 

		else:
			logging.debug("cacheline delete release a lock") 
			if self.lock != None:
				self.lock.release() 
			return False # fails to delete

	def clearline(self):
		"""clearline is a function to clear the whole line. \
		It is handy when the whole line is needed to be evicted. 
		"""

		self.set_tag(None)
		logging.debug("cacheline clearline acquire a lock") 
		if self.lock != None:
			self.lock.acquire() 

		for i in range(self.offset_size):
			self.valid[i] = 0
			self.offset[i] = None
		self.valid_count = 0
		logging.debug("cacheline clearline release a lock") 
		if self.lock != None:
			self.lock.release() 

class Node(object):
	'''Node class is a node used in implementation of doubly linked list.'''
	def __init__(self, tag, index):
		'''The __init__ method of a Node is used to initialize a Node. \
			Here, a node represent a cache line and used to decide the evict \
			order of cache lines. 

			tag(int): the tag of the cache line the node represents.

			index(int): the index of the cache line in the cache set.

			prev(node): the previous node of the current node. 

			next(node): the next node of the current node. '''
		super(Node, self).__init__()
		self.tag = tag
		self.index = index
		self.prev = None
		self.next = None
	def set_prev(self, prev):
		"""set_prev is a function to set the previous node of the current node.

		Args:
			prev(:obj:`Node`): `prev` is the node that will be the previous node of \
			the current node.

		"""
		self.prev = prev
	def get_prev(self):
		"""get_prev is a function to get the previous node of the current node. 

		Returns:
			return a node which is the previous node of the current node.

		"""
		return self.prev
	def set_next(self, next):
		"""set_next is a function to set the next node of the current node. 

		Args:
			next(:obj:`Node`): `next` is the node that will be the next node of the \
			current node.

		"""
		self.next = next
	def get_next(self):
		"""get_next is a function to get the next node of the current node. 

		Returns:
			return a node which is the next node of the current node.

		"""
		return self.next
	def get_index(self):
		"""get_index is a function to get the cache line index of the current \
		node. 

		Returns:
			return a cache line index of the current node.

		"""
		return self.index 
	def get_tag(self):
		"""get_tag is a function to get the cache line tag of the current node.

		Returns:
			return a cache line tag of the current node.

		"""
		return self.tag



class DoublyLinkedList(object):
	'''DoublyLinkedList class is a doubly linkedlist used in implementation \
	of LRU/MRU policy.'''

	def __init__(self, thread_safe_mode = True):
		"""The __init__ method of a DoublyLinkedList is used to initialize a \
		doubly linked list.

		Args:
			thread_safe_mode(bool, optional): when `thread_safe_mode` == True, \
				means the class is thread safe, One thing must be noted is that \
				thread safe mode will have worse performance regrading of time \
				since lock is costly. Default setting is True (enable thread \
				safe mode).


		"""
		super(DoublyLinkedList, self).__init__()
		if thread_safe_mode:
			self.lock = threading.Lock()
		else:
			self.lock = None
		self.head = None 
		self.tail = None

	def insert(self, node):
		"""insert is a function to insert a node into the tail of the \
		doubly linked list. 

		Args:
			node(:obj:`Node`): `node` is the node that will be inserted into the list.

		"""
		logging.debug("DoublyLinkedList insert acquire a lock") 
		if self.lock != None:
			self.lock.acquire() 
		if self.head == None: #if the list is empty
			self.head = self.tail = node
		else: #new node will be insert in the tail 
			node.set_prev(self.tail) 
			node.set_next(None)
			self.tail.set_next(node)
			self.tail = node
		logging.debug("DoublyLinkedList insert release a lock") 
		if self.lock != None:
			self.lock.release() 


	def remove(self, node): #should i check if the node in the list? 
		"""remove is a function to remove a node from the list. 

		Args:
			node(:obj:`Node`):`node` is the node that will be removed from the list.

		Returns:
			return True when operation is done as expected, False otherwise. 

		"""
		logging.debug("DoublyLinkedList remove acquire a lock") 
		if self.lock != None:
			self.lock.acquire() 

		prev = node.get_prev()
		next = node.get_next()

		#if the node is the only node
		if node == self.head == self.tail:
			self.head = None
			self.tail = None
		#if the node is head
		elif node == self.head:
			self.head = node.next 
		#if the node is tail 
		elif node == self.tail:
			new_tail = node.get_prev()
			new_tail.set_next(None)
			self.tail = new_tail

		#if the node is not head/tail of the current list, 
		#but it doesn't have prev or next value, there 
		#should be something wrong such as the node isn't in 
		#current list
		elif prev == None or next == None:
			if self.lock != None:
				self.lock.release() 
			return False

		#if the node in the middle 
		else:
			prev.set_next(next)
			next.set_prev(prev)
		logging.debug("DoublyLinkedList remove release a lock") 

		if self.lock != None:
			self.lock.release() 
		return True

	def get_head(self):
		"""get_head is a function to get the head of the linked list.

		Returns:
			an node which is head of the linked list.
		"""
		return self.head

	def get_tail(self):
		"""get_tail is a function to get the tail of the linked list.

		Returns:
			an node which is tail of the linked list.
		"""
		return self.tail


class ReplacementPolicy(object):
	'''ReplacementPolicy class is an interface to allow user to \
	inherit and implement their own replacement policy.'''
	''' the self-defined class need to have following functiions '''

	def insert(self, tag, cache_line_index):
		"""insert is a function to call when one item is accessed by user. \
		When an item is accessed by users, we need to update the order of \
		cahce lines (put it into the end of the linked list). If the \
		item/cache line is not accessed before, we need to both update \
		the list and the hash table. 

		Args:
			tag(int): `tag` is the tag of the line.

			cache_line_index(int): `cache_line_index` is the index of the line. \
				i.e. the index of the line in the cache set.\
				It will be used to find the line faster when we need to \
				evict/update the line.

		"""
		raise NotImplementedError
	def victim(self):
		"""victim is a function to choose the victim cache line to evict \
		based on current replacement policy. 

		Returns:
			Return a tag and index i of the victim cache line. \
			If there is no item in the linked list/hash table, return None. 
		"""
		raise NotImplementedError
	def get_size(self):
		"""get_size is a function to get the number of the items/cache \
		lines in this object.

		Returns:
			an int value of the size of the linked list and the hash table.
		"""
		raise NotImplementedError
	def delete(self, tag, delete_result):
		"""delete is a function to update the replacement policy object \
		after a value is ask to be deleted from a cache line. delete \
		counts as an access, so the replacement policy needed to be \
		updated too. If the line doesn't become empty, we update the \
		order; if the line is empty then delete the whole line from \
		replacement policy.

		Args:
			tag(int): `tag` is the tag of the cache line.

			delete_result(bool): `delete_result` is value we got after delete a \
				value from the cache line. None means the line is non-empty \
				after delete, True means the line became an empty line. 

		"""
		raise NotImplementedError



class LRU_MRU(ReplacementPolicy):
	'''LRU_MRU class keep the accessed order and quick get the cache lines for \
	the needs of LRU/MRU policy.'''
	def __init__(self, policy = 'LRU', thread_safe_mode = True):
		"""The __init__ method of a LRU/MRU replacement policy is used to \
		initialize a LRU/MRU object. Default policy is LRU. 

		Args:
			policy(string, optional): `policy` is to set the replacement policy. \
				User could pass a string to specify the `LRU` or `MRU` policy \
				will be used. Default setting is `LRU`.

			thread_safe_mode(bool, optional): when `thread_safe_mode` == True, \
				means the class is thread safe, One thing must be noted is that \
				thread safe mode will have worse performance regrading of time \
				since lock is costly. Default setting is True (enable thread \
				safe mode).
		"""
		super(LRU_MRU, self).__init__()
		if thread_safe_mode:
			self.lock = threading.Lock()
		else:
			self.lock = None
		self.size = 0
		#need a hash table to quickly access the items
		self.table = dict()
		#need a linkedlist to keep the accessed order 
		self.list = DoublyLinkedList(thread_safe_mode)
		self.policy = policy

	def insert(self, tag, i = 0): 
		"""insert is a function to call when one item is accessed by user. \
		When an item is accessed by users, we need to update the order of \
		cahce lines (put it into the end of the linked list).\
		If the item/cache line is not accessed before, we need to both update \
		the list and the hash table. 

		Args:
			tag(int): `tag` is the tag of the line.

			i(int, optional): `i` the index of the line. i.e. the index of \
				the line in the cache set. It will be used to find the line \
				faster when we need to evict/update the line.

		"""
		logging.debug("LRU_MRU insert acquire a lock")
		if self.lock != None:
			self.lock.acquire() 

		if tag in self.table:
			curr_node = self.table[tag] #get the node by tag
			#update the order in the linked list 
			self.list.remove(curr_node) 
			self.list.insert(curr_node)
		else:
			self.table[tag] = Node(tag, i)
			self.list.insert(self.table[tag])
			self.size += 1
		logging.debug("LRU_MRU insert release a lock") 
		if self.lock != None:
			self.lock.release() 


	def victim(self):
		"""victim is a function to choose the victim cache line to evict \
		based on current replacement policy. 

		Returns:
			Return a tag and index i of the victim cache line. \
			If there is no item in the linked list/hash table, return None. 
		"""
		if self.list.get_head() == None:
			return
		logging.debug("LRU_MRU victim acquire a lock") 
		if self.lock != None:
			self.lock.acquire() 

		if self.policy == 'LRU': 
			#LRU -> remove the oldest node, which is the head
			tag = self.list.get_head().get_tag()
			i = self.list.get_head().get_index()
		else:
			#MRU -> remove the most recent node, which is the tail 
			tag = self.list.get_tail().get_tag()
			i = self.list.get_tail().get_index()

		victim_node = self.table.pop(tag)
		self.list.remove(victim_node)
		self.size -= 1
		logging.debug("LRU_MRU victim release a lock") 
		if self.lock != None:
			self.lock.release() 

		return (tag, i)

	def get_size(self):
		"""get_size is a function to get the number of the items/cache lines \
		in this object.

		Returns:
			an int value of the size of the linked list and the hash table.
		"""
		return self.size

	def delete(self, tag, delete_result):
		"""delete is a function to update the replacement policy object after \
		a value is ask to be deleted from a cache line. delete counts as an \
		access, so the replacement policy needed to be update too. If the \
		line doesn't become empty, we update the order; if the line is \
		empty then delete the whole line from replacement policy.

		Args:
			tag(int): `tag` is the tag of the cache line.

			delete_result(bool): `delete_result` is value we got after \
				delete a value from the cache line. None means the line \
				is non-empty after delete, True means the line became an \
				empty line. 

		"""
		if delete_result == None:
			#the line still exist, index in the set stays the same
			#only need to update the order 
			self.insert(tag)
			return
		logging.debug("LRU_MRU delete acquire a lock") 
		if self.lock != None:
			self.lock.acquire() 

		if tag in self.table:
			#the whole line is invalid now
			#need to remove the line from LRU/MRU
			deleted_node = self.table.pop(tag)
			self.list.remove(deleted_node)
		logging.debug("LRU_MRU delete release a lock") 
		if self.lock != None:
			self.lock.release() 
		return 


class CacheSet(object):
	'''CacheSet class serves as a cache set in a cache to store cache \
	lines, and each cache line will store items (a key & value pair).\
	A cache might have more than one cache sets.'''

	def __init__(self, n_way, offset_size, replacement = 'LRU', thread_safe_mode = True):
		"""The __init__ method of a cache is used to initialize a 
		cache set.

		Args:
			n_way(int): `n_way` is used to specified how many ways(lines) \
				 in a cache set. 

			offset_size(int): `offset_size` is used to set offset size. 

			replacement(:obj:`ReplacementPolicy`, optional): `replacement` \
				is to set the cache replacement policy. User could either \
				to pass a subclass of `ReplacementPolicy` or pass a string \
				to specify the `LRU` or`MRU` policy. Default setting is `LRU`.

			thread_safe_mode(bool, optional): when `thread_safe_mode` == True, \
				means the class is thread safe, One thing must be noted is that \
				thread safe mode will have worse performance regrading of time \
				since lock is costly. Default setting is True (enable thread \
				safe mode).


		"""
		super(CacheSet, self).__init__()
		if thread_safe_mode:
			self.lock = threading.Lock()
		else:
			self.lock = None
		self.n_way = n_way
		self.offset_size = offset_size

		#initalize cache lines
		self.lines = [CacheLine(offset_size, thread_safe_mode = thread_safe_mode) for i in range(n_way)]

		#replacement policy
		if replacement == 'MRU' or replacement == 'LRU':
			self.replacement = LRU_MRU(replacement, thread_safe_mode = thread_safe_mode)
		elif isinstance(replacement, ReplacementPolicy):
			self.replacement = replacement
		else:
			raise ValueError("Invalid Input Values")

	def set(self, value, tag, offset):

		"""set is a function to put an item(a key and value pair) into the \
		cache line in a cache set. items in replacement policy will be \
		updated accordingly. The hashed key is transferred to tag and \
		offset to be used to find the item in the cache line. set will \
		first go to find if there is any tag matches the tag of the key of \
		item we are going to put into, if so, we will directly find the \
		offset and put the item (cache hit);if there is no matching tag, \
		then we will either fill the value into an empty cache line or evict \
		a cache line if there is no empty cache line(cache miss). Note, when\
		 we evict a cache line, the whole line will be cleared and the tag \
		 will be replace with the new tag of the item we are goint to put \
		 into it. 

		Args:
			value(value_type): `key` is the key of the item.

			tag(int): `tag` is the tag of the hashed item key.

			offset(int): `offset` is the offset of the hashed item.

		Returns:
			True if successful, None otherwise.
		"""

		candiate_linenum = None
		logging.debug("CacheSet set acquire a lock")
		if self.lock != None:
			self.lock.acquire() 

		for i in range(self.n_way):
			if self.lines[i].match_tag(tag):
				#found the one matches the tag so be able to set the value
				self.lines[i].set(offset, value)
				#call LRU/MRU or other replacement policy to update 
				#replacement order 
				self.replacement.insert(tag, i)
				logging.debug("CacheSet set release a lock")

				if self.lock != None:
					self.lock.release()

				return True #success to set the value 
			if candiate_linenum == None and self.lines[i].get_tag() == None:
				#found an empty line which could be a candiate to put the 
				#value, if we don't find anyone matches the tag
				candiate_linenum = i

		#there is no same tag 
		if candiate_linenum == None:
			#if we found there isn't an empty line, choose a victim cache 
			#line to evict.
			victim_value = self.replacement.victim() 

			if victim_value == None: 
				#we can't find an empty line and also no any line could be the
				#victim
				#based on our replacement policy 
				raise ValueError("Ran out of space")

			_ , candiate_linenum = victim_value

			self.lines[candiate_linenum].clearline()

		#put the value into the candidate cache line (an empty or victim line)
		self.lines[candiate_linenum].set_tag(tag)
		self.lines[candiate_linenum].set(offset, value)
		#update replacement policy
		self.replacement.insert(tag, candiate_linenum)

		logging.debug("CacheSet set release a lock") 

		if self.lock != None:
			self.lock.release() 
		return True

	def get_value(self, tag, offset):

		"""get_value is a function to get an item(a key and value pair) from \
		the cache by a key(trasferred to tag and offset).

		Args:
			tag(int): `tag` is the tag of the hashed item key.

			offset(int): `offset` is the offset of the hashed item (in a cache \
				 line).

		Returns:
			if the value exist, return the value of the key. Otherwise \
			return None.
		"""

		logging.debug("CacheSet get_value acquire a lock") 
		if self.lock != None:
			self.lock.acquire() 
		for i in range(self.n_way):
			if self.lines[i].match_tag(tag):
				self.replacement.insert(tag, i) 
				#if there isn't that offset, it still counts as one access.
				logging.debug("CacheSet get_value release a lock") 
				if self.lock != None:
					self.lock.release() 
				return self.lines[i].get(offset)
		logging.debug("CacheSet get_value release a lock") 
		if self.lock != None:
			self.lock.release() 


	def get_line(self, tag):

		"""get_line is a function to get a cache line which has the same tag. \
			By design, each tag is unique in one cache set 

		Args:
			tag(int): `tag` is the tag of the targeted cache line.

		Returns:
			if the line exist, return the line. Otherwise return None.
		"""

		logging.debug("CacheSet get_line acquire a lock") 
		if self.lock != None:
			self.lock.acquire() 
		for i in range(self.n_way):
			if self.lines[i].match_tag(tag):
				logging.debug("CacheSet get_line release a lock") 
				if self.lock != None:
					self.lock.release() 
				return self.lines[i]

		logging.debug("CacheSet get_line release a lock")
		if self.lock != None:
			self.lock.release() 


	def delete_value(self, tag, offset, value):

		"""delete_value is a function to delete the item in a cahce line which \
		has the inputed key(trasferred to tag and offset) and value.

		Args:
			tag(int): `tag` is the tag of the hashed item key.

			offset(int): `offset` is the offset of the hashed item \
				(in a cache line).

			value(value_type): `value` is the value of the item which is going to \
				be deleted.

		Returns:
			if the value exist and be successfully deleted, return True; 
			if not successfully deleted, return False; otherwise return None.
		"""


		logging.debug("CacheSet delete_value acquire a lock")
		if self.lock != None:
			self.lock.acquire() 
		found_delete = None 

		for i in range(self.n_way):
			if self.lines[i].match_tag(tag):
				#get the targeted line
				found_delete = self.lines[i]
				break

		if found_delete != None: 
		#found the cache line which contains the item we want to delete
			delete_result = found_delete.delete(offset, value)
			if delete_result != False:
				self.replacement.delete(tag, delete_result) 
				#delete or update the line in replacement policy object 
				#if needed
				#delete also counts as an access, so if the line doesn't 
				#become empty, we update the order; if the line is empty 
				#then delete the whole line from replacement policy 
				logging.debug("CacheSet delete_value release a lock")
				if self.lock != None:
					self.lock.release() 

				return True
			else:
				logging.debug("CacheSet delete_value release a lock")
				#fails to delete 
				if self.lock != None:
					self.lock.release()


				return False

		logging.debug("CacheSet delete_value release a lock")
		if self.lock != None:
			self.lock.release() 
		return None


class Cache(object):
	'''Cache class serves as a cache to store cache sets, each cache 
	set will have cache lines to store items (a key & value pair).'''


	def __init__(self, cache_size, n_way, b, key_type, value_type, replacement = None, hash = hash, thread_safe_mode = True):
		"""The __init__ method of a cache is used to initialize a cache.

		Args:
			cache_size (int): `cache_size` is the cache size we can use to save \
				items. if cache size == n, it means we can store at most n items. \
				cache size should be larger than n_ways * number of sets * \
				* offset size.

			n_way(int): `n_way` is used to specify how many ways/lines in a \
				cache set. 

			b(int): `b` is used to calculate offset size. offset size is 2^b.

			key_type(key_type): `key_type` is used to specifiy the key type of \
				the item.

			value_type(value_type): `value_type` is used to specifiy the key type \
				of the item. 

			replacement(:obj:`ReplacementPolicy`, optional): `replacement` is to \
				set the cache replacement policy. User could either to pass a \
				subclass of `ReplacementPolicy` or pass a string to specify \
				the `LRU` or `MRU` policy. Default setting is `LRU`.

			hash(:func:, optional): `hash` is to provide the hash function that \
				used to hash keys of the items. Default setting is to use \
				python's built-in hash function. 

			thread_safe_mode(bool, optional): when `thread_safe_mode` == True, \
				means the class is thread safe, One thing must be noted is that \
				thread safe mode will have worse performance regrading of time \
				since lock is costly. Default setting is True (enable thread safe \
				mode).


		"""

		super(Cache, self).__init__()


		if thread_safe_mode:
			self.lock = threading.Lock()
		else:
			self.lock = None

		if replacement == None or replacement == 'LRU':
			self.replacement = 'LRU'
		elif replacement == 'MRU':
			self.replacement = 'MRU'
		elif isinstance(replacement, ReplacementPolicy):
			self.replacement = replacement
		else:
			raise ValueError("Invalid Input Values")

		self.cache_size = cache_size
		self.n_way = n_way

		self.key_type = key_type
		self.value_type = value_type 

		self.offset_size = 2**b
		self.offset_bits = b 
		self.total_sets = int(math.floor(cache_size / (2**b) / n_way))
		self.set_bits =  int(math.log(self.total_sets, 2))

		#check values
		if self.is_valid_input(cache_size, n_way, self.total_sets, self.offset_size, b) == False:
			raise ValueError("Invalid Input Values")

		#initalize cache sets
		self.sets = [CacheSet(n_way, self.offset_size, replacement = self.replacement, thread_safe_mode = thread_safe_mode) for i in range(self.total_sets)]
		self.replacement = replacement
		self.hash = hash


	def is_valid_input(self, cache_size, n_way, total_sets, offset_size, b):
		"""is_valid_input is to check if the values are valid.

		Args:
			cache_size (int): `cache_size` is the cache size we can use to save \
				items. if cache size == n, it means we can store at most n items. \
				cache size should be larger than n_ways * number of sets \
				* offset size.

			n_way(int): `n_way` is used to specify how many ways/lines in a \
				cache set. 

			total_sets(int): `total_sets` is how many sets we should have. 

			offset_size(int): `offset_size` is how large the offset should be \
				according to `b`.

			b(int): `b` is used to calculate offset size. offset size is 2^b.
 
		Returns:
			True if the inputs are valid, False otherwise.

		"""
		if cache_size <= 0 or n_way <= 0 or b <= 0:
			return False
		if cache_size < (n_way * offset_size * total_sets):
			return False
		return True

	def get_set_num(self, hash_result):

		"""get_set_num is to get the set number (which set) based on the hash \
		result.

		Args:
			hash_result(int): `hash_result` is the result of hash the key of \
				the item.

		Returns:
			an int to indicate which set the item should be in.
		"""

		mask_out = -1 << self.offset_bits   
		mask_in = -1 << (self.set_bits + self.offset_bits) 
		return ((mask_out ^ mask_in) & hash_result) >> self.offset_bits

	def get_offset_index(self, hash_result):

		"""get_offset_index is to get the index offset (which slot in offset) \
		based on the hash result.

		Args:
			hash_result(int): `hash_result` is the result of hash the key of \
                        the item.

		Returns:
			an int to indicate which index in the offset the item should be in.
		"""

		mask = ~(-1 << self.offset_bits)
		return hash_result & mask

	def get_tag_num(self, hash_result):

		"""get_tag_num is to get the tag number based on the hash result.

		Args:
			hash_result(int): `hash_result` is the result of hash the key of \
                        the item.

		Returns:
			an int to indicate the tag of the item.
		"""

		mask = -1 << (self.set_bits + self.offset_bits)
		return (hash_result & mask) >> (self.set_bits + self.offset_bits)


	def set_value(self, key, value):

		"""set_value is to put an item(a key and value pair) into the cache.

		Args:
			key(key_type): `key` is the key of the item.

			value(value_type): `value` is the value of the item

		Returns:
			True if successful, None otherwise.
		"""

		if not isinstance(key, self.key_type) or not isinstance(value, self.value_type):
			raise ValueError("Invalid key type or value type")

		if self.lock != None:
			self.lock.acquire() 
		hash_result = self.hash(key)
		set_num = self.get_set_num(hash_result)
		offset_index = self.get_offset_index(hash_result)
		tag = self.get_tag_num(hash_result)
		is_success = self.sets[set_num].set(value, tag, offset_index)
		if self.lock != None:
			self.lock.release()
		return is_success 


	def get_value(self, key):


		"""get_value is to get an item(a key and value pair) from the cache by \
		a key.

		Args:
			key(key_type): `key` is the key of the item.

		Returns:
			if the value exist, return the value of the key. Otherwise \
			return None.
		"""
		if not isinstance(key, self.key_type):
			raise ValueError("Invalid key type or value type")


		if self.lock != None:
			self.lock.acquire() 
		hash_result = self.hash(key)
		set_num = self.get_set_num(hash_result)
		offset_index = self.get_offset_index(hash_result)
		tag = self.get_tag_num(hash_result)
		if self.lock != None:
			self.lock.release() 
		return self.sets[set_num].get_value(tag, offset_index)

	def delete(self, key, value):

		"""delete is to delete the item which has the inputed key and value.

		Args:
			key(key_type): `key` is the key of the item which is going to \
				be deleted. 

			value(value_type): `value` is the value of the item which \
				is going to be deleted.

		Returns:
			if the value exist and be successfully deleted, return True; 
			if not successfully deleted, return False; otherwise return None.
		"""

		if not isinstance(key, self.key_type) or not isinstance(value, self.value_type):
			raise ValueError("Invalid key type or value type")

		if self.lock != None:
			self.lock.acquire() 
		hash_result = self.hash(key)
		set_num = self.get_set_num(hash_result)
		offset_index = self.get_offset_index(hash_result)
		tag = self.get_tag_num(hash_result)
		if self.lock != None:
			self.lock.release() 
		return self.sets[set_num].delete_value(tag, offset_index, value)



