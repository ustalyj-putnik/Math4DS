import sys
import time
import requests
import pickle
from concurrent.futures import ThreadPoolExecutor
from settings import token, my_id, api_v, deep, max_workers, delay
def force(f, delay=delay):
	"""При неудачном запросе сделать паузу и попробовать снова"""
	def tmp(*args, **kwargs):
		while True:
			try:
				res = f(*args, **kwargs)
				break
			except KeyError:
				time.sleep(delay)
		return res
	return tmp

class VkException(Exception):
	def __init__(self, message):
		self.message = message

	def __str__(self):
		return self.message


class VkFriends():
	"""
	Находит друзей, находит общих друзей
	"""
	parts = lambda lst, n=25: (lst[i:i + n] for i in iter(range(0, len(lst), n)))
	make_targets = lambda lst: ",".join(str(id) for id in lst)

	def __init__(self, *pargs):
		try:
			self.token, self.my_id, self.api_v, self.max_workers = pargs
			self.my_name, self.my_last_name = self.base_info([self.my_id])
			self.all_friends, self.count_friends = self.friends(self.my_id)
		except VkException as error:
			sys.exit(error)

	def request_url(self, method_name, parameters, access_token=False):
		"""read https://vk.com/dev/api_requests"""

		req_url = 'https://api.vk.com/method/{method_name}?{parameters}&v={api_v}'.format(
			method_name=method_name, api_v=self.api_v, parameters=parameters)

		if access_token:
			req_url = '{}&access_token={token}'.format(req_url, token=self.token)

		return req_url

	def base_info(self, ids):
		"""read https://vk.com/dev/users.get"""
		r = requests.get(self.request_url('users.get', 'user_ids=%s' % (','.join(map(str, ids))), access_token=True)).json()
		if 'error' in r.keys():
			raise VkException('Error message: %s Error code: %s' % (r['error']['error_msg'], r['error']['error_code']))
		r = r['response'][0]
		# Проверяем, если id из settings.py не деактивирован
		if 'deactivated' in r.keys():
			raise VkException("User deactivated")
		return r['first_name'], r['last_name']

	def friends(self, id):
		"""
		read https://vk.com/dev/friends.get
		Принимает идентификатор пользователя
		"""
		# TODO: слишком много полей для всего сразу, город и страна не нужны для нахождения общих друзей
		r = requests.get(self.request_url('friends.get',
				'user_id=%s&fields=uid,first_name,last_name,photo,country,city,sex,bdate' % id, True)).json()['response']
		#r = list(filter((lambda x: 'deactivated' not in x.keys()), r['items']))
		return {item['id']: item for item in r['items']}, r['count']

	def deep_friends(self, deep):
		"""
		Возвращает словарь с id пользователей, которые являются друзьями, или друзьями-друзей (и т.д. в зависимсти от
		deep - глубины поиска) указаннного пользователя
		"""
		result = {}

		@force
		def worker(i):	    
			r = requests.get(self.request_url('execute.deepFriends', 'targets=%s' % VkFriends.make_targets(i), access_token=True)).json()['response']
			for x, id in enumerate(i):
				result[id] = tuple(r[x]["items"]) if r[x] else None

		def fill_result(friends):
			with ThreadPoolExecutor(max_workers=self.max_workers) as pool:
				[pool.submit(worker, i) for i in VkFriends.parts(friends)]

		for i in range(deep):
			if result:
				# те айди, которых нет в ключах + не берем id:None
				fill_result(list(set([item for sublist in result.values() if sublist for item in sublist]) - set(result.keys())))
			else:
				fill_result(requests.get(self.request_url('friends.get', 'user_id=%s' % self.my_id, access_token=True)).json()['response']["items"])

		return result


	@staticmethod
	def save_load_deep_friends(myfile, sv, smth=None):
		if sv and smth:
			pickle.dump(smth, open(myfile, "wb"))
		else:
			return pickle.load(open(myfile, "rb"))

if __name__ == '__main__':
	a = VkFriends(token, my_id, api_v, max_workers)
	people = ['181400458',
			  '136004593',
			  '151143124',
			  '248826936',
			  '172224066',
			  '356135268',
			  '118466021',
			  '625131977',
			  '206240342',
			  '196085241']

	#print(a.friends('51100527')[1])
	#print(a.my_id, a.my_name)
	#print(a.common_friends())
	df = a.deep_friends(deep)
	df_1 = {k: v for k, v in df.items() if v != None}
	#print(df_1)
	VkFriends.save_load_deep_friends('deep_friends_dct', True, df_1)
	#print(pickle.load( open('deep_friends_dct', "rb" )))
	#print(a.from_where_gender())
