# XBMC Modules
import xbmc

# Standard Modules
import json
import Queue
import select
import socket
import threading
import traceback


class LazyComms(threading.Thread):
	''' Waits for connections from the GUI, adds the requests to the queue. '''

	def __init__(self, to_Parent_queue, from_Parent_queue, log):

		threading.Thread.__init__(self)

		self.wait_evt = threading.Event()

		# queues to handles passing items to and recieving from the service
		self.to_Parent_queue   = to_Parent_queue
		self.from_Parent_queue = from_Parent_queue

		# old yeller
		self.log = log

		self.daemon = True

		# create the listening socket, it creates new connections when connected to
		self.address = ('localhost', 16458)
		self.sock    = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

		# allows the address to be reused (helpful with testing)
		self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
		self.sock.bind(self.address)
		self.sock.listen(1)
		
		self.stopped = False


	def stop(self):
		''' Orderly shutdown of the socket, sends message to run loop to exit. '''

		try:

			self.log('LazyComms stopping')

			self.stopped = True
				
			sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
			sock.connect(self.address)
			sock.send('exit')
			sock.close()
			self.sock.close()
				
			self.log('LazyComms stopped')

		except Exception, e:

			self.log('LazyComms error trying to stop: {}'.format(e))


	def run(self):

		self.log('LazyComms started')

		while not xbmc.abortRequested and not self.stopped:

			self.log('LazyComms waiting for connection')
			
			# wait here for a connection
			conn, addr = self.sock.accept()

			self.log('Connection! conn = %s addr = %s' % (conn, addr))

			# turn off blocking for this temporary connection
			# this will allow the loop to collect all parts of the message
			conn.setblocking(0)

			# holds the message parts
			message = []

			# recv will throw a 'resource temporarily unavailable' error 
			# if there is no more data

			# ready ensures there is data available before trying to recv
			# timeout is set to 3 seconds
			ready = select.select([conn], [], [], 3)

			while ready[0]:
				
				try:

					data_part = conn.recv(8192)
					self.log('data recv')
					if not data_part:
						self.log('no data in recv')
						break

				except Exception, e:
					self.log('LazyComms data reception error: %s, %s' % (Exception.__class__.__name__, e))
					break

				# add the partial message to the holding list
				message.append(data_part)

			data = ''.join(message)

			self.log('this is for testing only: %s' % data)

			# if the message is to stop, then kill the loop
			if data == 'exit':
				self.stopped = True
				conn.close()
				continue

			if not data:
				self.log('No data received')
				conn.close()
				continue

			# this sleep is to make sure nothing else is using data, hopefully to avoid an EoFError
			xbmc.sleep(50)

			# deserialise dict that was recieved
			deserial_data = json.loads(data)

			self.log('All data received by LazyComms: %s' % deserial_data)

			# send the data to Main for it to process
			self.to_Parent_queue.put(deserial_data)

			# wait 1 second for a response from Main
			# @@@@@@@@@@ maybe always place something in the from_Parent_queue to speed up turn-around?
			try:
				self.log('LazyComms waiting for data from Main')
				response = self.from_Parent_queue.get(True, 1)
				self.log('Response: %s' % response)

				# serialise dict for transfer back over the connection
				serial_response = json.dumps(response)

				# send the response back
				conn.send(serial_response)

				self.log('LazyComms sent response: ' + str(serial_response)[:50])

			except Queue.Empty:
				# if the queue is empty, then send back a response saying so
				self.log('Main took too long to respond.')
				conn.send('Service Timeout')

			except :
				self.log('Unknown error receiving lazycomms: \n%s' % traceback.format_exc())

			# close the connection
			conn.close()
			del conn

