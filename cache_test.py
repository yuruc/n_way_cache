#cache_test.py
#test N-associative cache
#author: Yu-Ju Chang

import cache
import unittest


class TestCacheLine(unittest.TestCase):

	def test_tag(self):
		line = cache.CacheLine(10)
		line.set_tag(89109)
		self.assertEqual(line.get_tag(), 89109)
		self.assertTrue(line.match_tag(89109))
		self.assertFalse(line.match_tag(89101))
	def test_set_get(self):
		line = cache.CacheLine(10)
		line.set_tag(39380)
		line.set(1, 1009)
		self.assertEqual(line.get(1), 1009)
		#line.get(100)
		#self.assertRaises(IndexError, line.set, 11, 29)
		#self.assertRaises(IndexError, line.get, 100)
		#self.assertRaises(ValueError, line.get, 0)
	def test_delete(self):
		line = cache.CacheLine(10)
		self.assertFalse(line.delete(0, 0))
		line.set_tag(23)
		line.set(1, 1008)
		self.assertTrue(line.delete(1, 1008))
	def test_clearline(self):
		line = cache.CacheLine(10)
		line.set_tag(103)
		line.set(9, 1993)
		self.assertRaises(IndexError, line.set, 13, 440)

		self.assertEqual(line.valid_count, 1)
		self.assertEqual(line.valid[9], 1)
		line.clearline()
		for i in range(len(line.offset)):
			self.assertEqual(line.offset[i], None)
			self.assertEqual(line.valid[i], 0)


class TestDoublyLinkedList(unittest.TestCase):
	def test_insert(self):
		linkedlist = cache.DoublyLinkedList()
		a = cache.Node(18983, 0)
		b = cache.Node(78349, 1)
		linkedlist.insert(a)
		linkedlist.insert(b)
		self.assertEqual(linkedlist.get_tail(), b)
		self.assertEqual(linkedlist.get_head(), a)
		c = cache.Node(92849, 4)
		linkedlist.insert(c)
		self.assertEqual(linkedlist.get_tail(), c)
		self.assertEqual(linkedlist.get_tail().get_next(), None)
		self.assertEqual(linkedlist.get_head().get_prev(), None)
		self.assertEqual(linkedlist.get_head().get_next(), b)
		self.assertEqual(linkedlist.get_head().get_next().get_next(), c)

	def test_remove(self):
		linkedlist = cache.DoublyLinkedList()
		a = cache.Node(18983, 0)
		b = cache.Node(78349, 1)
		c = cache.Node(89289, 2)
		linkedlist.insert(a)
		self.assertEqual(linkedlist.get_head(), a)
		self.assertEqual(linkedlist.get_tail(), a)
		linkedlist.remove(a)
		self.assertEqual(linkedlist.get_tail(), None)
		self.assertEqual(linkedlist.get_head(), None)
		linkedlist.insert(a)
		linkedlist.insert(b)
		linkedlist.remove(a)
		self.assertEqual(linkedlist.get_tail(), b)
		self.assertEqual(linkedlist.get_head(), b)
		linkedlist.insert(c)
		linkedlist.insert(a)
		linkedlist.remove(c)
		self.assertEqual(linkedlist.get_head().get_next(), a)
		self.assertEqual(linkedlist.get_head(), b)
		self.assertEqual(linkedlist.get_tail(), a)
		self.assertEqual(linkedlist.get_tail().get_prev(), b)


class TestLRU_MRU(unittest.TestCase):
	def test_insert_victim(self):
		lru = cache.LRU_MRU() #LRU
		lru.insert(21938, 0)
		lru.insert(43895, 1)
		self.assertEqual(lru.victim(), (21938, 0))
		self.assertEqual(lru.get_size(), 1)
		lru.insert(43895, 1)
		lru.insert(29902, 2)
		lru.insert(92494, 3)
		lru.insert(43895, 1)
		self.assertEqual(lru.victim(), (29902, 2))
		self.assertEqual(lru.victim(), (92494, 3))
		self.assertEqual(lru.victim(), (43895, 1))
		self.assertEqual(lru.victim(), None)

		mru = cache.LRU_MRU('MRU') #MRU
		mru.insert(21938, 0)
		mru.insert(43895, 1)
		self.assertEqual(mru.victim(), (43895, 1))
		self.assertEqual(mru.get_size(), 1)
		mru.insert(43895, 1)
		mru.insert(29902, 2)
		mru.insert(92494, 3)
		mru.insert(43895, 1)
		self.assertEqual(mru.victim(), (43895, 1))
		self.assertEqual(mru.victim(), (92494, 3))
		self.assertEqual(mru.victim(), (29902, 2))
		self.assertEqual(mru.victim(), (21938, 0))
		self.assertEqual(mru.victim(), None)

	def test_delete(self):
		lru = cache.LRU_MRU() #LRU
		lru.insert(90390, 1)
		lru.insert(84992, 2)
		lru.insert(39243, 3)
		lru.delete(90390, None)
		self.assertEqual(lru.victim(), (84992, 2))
		lru.delete(39243, True)
		self.assertEqual(lru.victim(), (90390, 1))


class TestCacheSet(unittest.TestCase):
	def test_cacheset_set_get_value(self):
		sets = cache.CacheSet(2, 2) #2way 2offset
		sets.set(101, 24384, 0)
		sets.set(102, 24384, 1)
		sets.set(103, 24384, 0) #replace the one in the orginal location 
		self.assertEqual(sets.get_value(24384, 0), 103 )
		self.assertEqual(sets.get_value(37485, 1), None)
		sets.set(104, 37884, 0)
		sets.set(105, 38984, 0)
		self.assertEqual(sets.get_value(37884, 0), 104)
		self.assertEqual(sets.get_value(24384, 1), None)

	def test_cacheset_getline(self):
		sets = cache.CacheSet(2, 2) #2way 2offset
		sets.set(101, 24384, 0)
		sets.set(102, 24384, 1)
		sets.set(103, 24384, 0) #replace the one in the orginal location
		self.assertEqual(sets.get_line(24384),  sets.lines[0])
		sets.set(104, 24956, 0)
		self.assertEqual(sets.get_line(24956), sets.lines[1])

	def test_cacheset_deletevalue(self):
		sets = cache.CacheSet(2, 2)
		sets.set(101, 38944, 0)
		sets.set(102, 38944, 1) #index: 0
		sets.delete_value(38944, 0, 101)
		self.assertEqual(sets.get_line(38944), sets.lines[0])
		sets.set(103, 34788, 1) #index: 1
		sets.delete_value(38944, 1, 102)
		sets.set(104, 44788, 1) #index: 0
		self.assertEqual(sets.get_line(38944), None)
		sets.set(105, 34788, 0) 
		sets.set(106, 44788, 0)
		sets.delete_value(34788, 0, 105)
		sets.set(107, 10755, 0)
		self.assertEqual(sets.get_line(38944), None)
		self.assertEqual(sets.get_line(10755), sets.lines[0])
		self.assertEqual(sets.get_line(44788), None)
		self.assertEqual(sets.get_line(34788), sets.lines[1])

class TestCache(unittest.TestCase):

	def test_get_set_num(self): #how to test same object in different fcuntiosn?
		cache_size = 1024 #
		n_way = 2
		b = 3 #2^3 = 8 slots 
		#sets = 1024/8 = 2^7 /2 = 2^6 => 6 bits 
		key_type = int
		value_type = int
		test_cache = cache.Cache(cache_size, n_way, b, key_type, value_type)
		self.assertEqual(test_cache.get_set_num(10), 1)
		self.assertEqual(test_cache.get_set_num(18), 2)
		self.assertEqual(test_cache.get_set_num(839), 40)
		self.assertEqual(test_cache.get_set_num(39), 4)
		self.assertEqual(test_cache.get_set_num(1), 0)

		cache_size = 8 #
		n_way = 1
		b = 3 #2^3 = 8 slots 
		key_type = int
		value_type = int
		test_cache = cache.Cache(cache_size, n_way, b, key_type, value_type)
		self.assertEqual(test_cache.get_set_num(10), 0)
		self.assertEqual(test_cache.get_set_num(18), 0)
		self.assertEqual(test_cache.get_set_num(839), 0)
		self.assertEqual(test_cache.get_set_num(39), 0)
		self.assertEqual(test_cache.get_set_num(1), 0)

	def test_get_offset_index(self):
		cache_size = 1024 #
		n_way = 2
		b = 3 #2^3 = 8 slots 
		key_type = int
		value_type = int
		test_cache = cache.Cache(cache_size, n_way, b, key_type, value_type)
		#replacement = 'LRU', hash = hash
		hash_result = test_cache.hash(7)
		self.assertEqual(test_cache.get_offset_index(hash_result), 7)
		self.assertEqual(test_cache.get_offset_index(1), 1)
		self.assertEqual(test_cache.get_offset_index(2), 2)
		self.assertEqual(test_cache.get_offset_index(19), 3)
		self.assertEqual(test_cache.get_offset_index(8), 0)

	def test_get_tag_num(self):
		cache_size = 1024 #
		n_way = 2
		b = 3 #2^3 = 8 slots 
		key_type = int
		value_type = int
		test_cache = cache.Cache(cache_size, n_way, b, key_type, value_type)
		#replacement = 'LRU', hash = hash
		self.assertEqual(test_cache.get_tag_num(3287), int(bin(3287).replace('0b', '0000000000')[:-9] , 2)) 
		self.assertEqual(test_cache.get_tag_num(1), int(bin(1).replace('0b', '0000000000')[:-9] , 2) )
		self.assertEqual(test_cache.get_tag_num(10), int(bin(10).replace('0b', '0000000000')[:-9] , 2) )
		self.assertEqual(test_cache.get_tag_num(7), int(bin(7).replace('0b', '0000000000')[:-9] , 2) )

	def test_set_get_value(self):

		#LRU
		cache_size = 16 #
		n_way = 2
		b = 2 #2^2 = 4 slots 
		#sets => 8 / 4 / 2=  2
		key_type = int
		value_type = int
		test_cache = cache.Cache(cache_size, n_way, b, key_type, value_type)

		#tag: 0 - 3 => set 0 , 4 - 7 => set 1, 8 - 10 => set 0  
		test_cache.set_value(1, 1) #set 0 tag 0
		self.assertEqual(test_cache.get_value(1), 1)
		test_cache.set_value(2, 2) #set0 tag 0
		self.assertEqual(test_cache.get_value(2), 2)
		test_cache.set_value(1, 1) 
		test_cache.set_value(2, 2)
		test_cache.set_value(3, 3)  #set0 tag 0
		test_cache.set_value(4, -1) #set1
		self.assertEqual(test_cache.get_value(4), -1)
		test_cache.set_value(4, 4)
		self.assertEqual(test_cache.get_value(4), 4)
		test_cache.set_value(0, 0) #set0 tag 0
		test_cache.set_value(5, 5) #set1
		test_cache.set_value(6, 6) #set1
		test_cache.set_value(7, 7) #set1 
		test_cache.set_value(8, 8) #set0 tag 1
		test_cache.set_value(9, 9) #set0 tag 1
		test_cache.set_value(10, 10) #set0 tag 1
		test_cache.set_value(11, 11) #set0 tag 1
		#self.assertEqual(test_cache.get_value(0), 0)
		test_cache.set_value(16, 16) #set0 tag 10
		self.assertEqual(test_cache.get_value(0), None)
		test_cache.set_value(17, 17) #set0 tag 10
		test_cache.set_value(18, 18) #set0 tag 10
		test_cache.set_value(19, 19) #set0 tag 10



		self.assertEqual(test_cache.get_value(0), None)
		self.assertEqual(test_cache.get_value(1), None)
		self.assertEqual(test_cache.get_value(2), None)
		self.assertEqual(test_cache.get_value(3), None)

		self.assertEqual(test_cache.get_value(4), 4)

		self.assertEqual(test_cache.get_value(5), 5)
		self.assertEqual(test_cache.get_value(6), 6)
		self.assertEqual(test_cache.get_value(7), 7)
		self.assertEqual(test_cache.get_value(8), 8)
		self.assertEqual(test_cache.get_value(9), 9)
		self.assertEqual(test_cache.get_value(10), 10)
		self.assertEqual(test_cache.get_value(11), 11)
		self.assertEqual(test_cache.get_value(16), 16)
		self.assertEqual(test_cache.get_value(17), 17)
		self.assertEqual(test_cache.get_value(18), 18)
		self.assertEqual(test_cache.get_value(19), 19)


		test_cache.set_value(0, 0) #set0 tag 0
		test_cache.set_value(16, 16) #set0 tag 10
		test_cache.get_value(0) #set0 tag 1
		test_cache.set_value(10, 10) #set0 tag 1
		self.assertEqual(test_cache.get_value(16), None)

		#MRU
		cache_size = 16 #
		n_way = 2
		b = 2 #2^2 = 4 slots 
		#sets => 8 / 4 / 2=  2
		key_type = int
		value_type = int
		test_cache = cache.Cache(cache_size, n_way, b, key_type, value_type, replacement= "MRU")

		#tag: 0 - 3 => set 0 tag 0, 4 - 7 => set 1, 8 - 11 => set 0 tag 1, 16 - 19 => set 0 tag 10

		test_cache.set_value(0, 0) #set0 tag 0
		test_cache.set_value(8, 8) #set0 tag 1
		test_cache.set_value(16, 16) #set0 tag 10
		self.assertEqual(test_cache.get_value(8), None)





	def test_delete(self):
		cache_size = 1024 #
		n_way = 2
		b = 3 #2^3 = 8 slots 
		key_type = int
		value_type = int
		test_cache = cache.Cache(cache_size, n_way, b, key_type, value_type)
		test_cache.set_value(0, 0) #set0 tag 0
		test_cache.set_value(8, 8) #set0 tag 1
		self.assertEqual(test_cache.get_value(0), 0)

		test_cache.delete(0 , 0)
		self.assertEqual(test_cache.get_value(0), None)


		#tag: 0 - 3 => set 0 tag 0, 4 - 7 => set 1, 8 - 11 => set 0 tag 1, 16 - 19 => set 0 tag 10


unittest.main()	
