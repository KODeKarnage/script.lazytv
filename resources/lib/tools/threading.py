
import Queue
import threading

def thread_actuator(thread_queue, func, log):
    """ This is the target function used in the thread creation by the func_threader.
		func = {'method as a string': {'named_arguments': na, ... }}
		method = True for  """

    log("thread created, running {}".format(func))

    # keep running while there are items in the queue
    while True:

        try:
            # grabs the item from the queue
            # q_item = thread_queue.pop() # alternative implementation
            # the get BLOCKS and waits 1 second before throwing a Queue Empty error
            q_item = thread_queue.get(True, 1)

            # split the func into the desired method and arguments
            o = q_item.get("object", False)
            a = q_item.get("args", False)

            if o:
                # call the function on each item (instance)
                getattr(o, func)(**a)

            thread_queue.task_done()

        except Queue.Empty:

            log("Queue.Empty error")

            break

    log("thread exiting, function: {}".format(func))


def func_threader(items, func, log, threadcount=3, join=True):
    """ func is the string of the method name.
		items is a list of dicts: {'object': x, 'args': y}
		object can be either self or the instance of another class
		args must be a dict of named arguments """

    log("func_threader reached")

    # create the threading_queue
    # thread_queue = collections.deque()
    thread_queue = Queue.Queue()

    # spawn some workers
    for i in range(threadcount):

        t = threading.Thread(target=thread_actuator, args=(thread_queue, func, log))
        t.start()

    # adds each item from the items list to the queue
    # thread_queue.extendleft(items)
    [thread_queue.put(item) for item in items]
    log("{} items added to queue".format(len(items)))

    # join = True if you want to wait here until all are completed
    if join:
        thread_queue.join()

    log("func_threader complete")
