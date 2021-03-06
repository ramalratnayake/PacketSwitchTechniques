import os;
import threading
import signal
import time
import random
import sys
 
def sigint_handler(signum, frame):
	global finish_flag
	finish_flag = True
	exit()
 
signal.signal(signal.SIGINT, sigint_handler)

iNQs = 10
oNQs = 10

TTL  = 0
Port = 1

class state:
	IDLE 		 = 0
	ARRIVAL      = 1
	SCHED_1_PROP = 2
	SCHED_1_EVAL = 3
	DEPART  	 = 4
	SCHED_2 	 = 5
	NUM_STATES 	 = 6

	@staticmethod
	def to_string(num):
		return {
	        state.IDLE  		: "IDLE",
	        state.ARRIVAL 		: "ARRIVAL",
	        state.SCHED_1_PROP 	: "SCHED_1_PROP",
	        state.SCHED_1_EVAL 	: "SCHED_1_EVAL",
	        state.DEPART 		: "DEPART",
	        state.SCHED_2 		: "SCHED_2",
	        state.NUM_STATES 	: "NUM_STATES"
	    }[num]

curr_state = state.IDLE

		
taken 		= threading.Lock()
var_lock 	= threading.Lock()
cnt_lock 	= threading.Lock()
q_lock 		= threading.Lock()

def thread_print(the_string):
	global taken
	taken.acquire()
	print (str(threading.current_thread().getName()) + "\t" + " ----> " + str(the_string))
	taken.release()

def print_state(state):
	global curr_state
	thread_print (state.to_string(curr_state))

def get_prop_port(cell):
	global prop_ports
	# thread_print (cell[Port]
	return prop_ports[cell[Port]]

def is_state(is_it_this):
	global curr_state
	return (curr_state == is_it_this)

def hasnt_reached(this_state):
	global curr_state
	return not(curr_state == this_state)

def reset_cntrs():
	global state_cntrs
	global iNQs

	state_cntrs = [iNQs for i in xrange(0, state.NUM_STATES)]

def dec_cnt(the_state):
	global state_cntrs	
	global cnt_lock

	cnt_lock.acquire()
	state_cntrs[the_state] -= 1
	cnt_lock.release()

def input_Q_thread(id):
	global input_ports
	global input_Qs
	global output_Qs
	global finish_flag
	global prop_ports
	global curr_state
	global num_not_matched
	global var_lock
	global prop_locks

	while not(finish_flag):
		############################################ PHASE 1.0 ############################################
		if(is_state(state.ARRIVAL)):
			# If a new packet arrived at this port 
			if (input_ports[id] != None):
				new_cell = input_ports[id]

				# Calculate output cushion
				index = 0
				for cell in output_Qs[new_cell[Port]]:
					index += 1
					if(cell[TTL] > new_cell[TTL]):
						break

				# Insert into the input queue at index OC
				input_Qs[id].insert(index, new_cell)

			# thread_print (input_Qs[id])
			thread_print("done arrive")
			dec_cnt(state.ARRIVAL)

			input_ports[id] = None

			# Wait for state change 
			while is_state(state.ARRIVAL):
				if finish_flag:
					return
				pass			

		############################################ PHASE 2.0 ############################################
		elif(is_state(state.SCHED_1_PROP)):
			is_matched 		= False
			now_trying 		= 0
			considered_cell = None

			# Keep doing the stuff below until a stable matching is made
			while is_state(state.SCHED_1_PROP):
				thread_print ("matched = " + str(is_matched))
				thread_print ("iQ len = " + str(len(input_Qs[id])))	
				if(not(is_matched) and len(input_Qs[id]) != 0):
					thread_print ("nt" + str(now_trying))
					if(now_trying < len(input_Qs[id])):
						# Go thru input Queue 
						considered_cell = input_Qs[id][now_trying]
						thread_print ("try cell " + str(considered_cell))
						# Make a proposal to the appropriate output port 
						prop_locks[considered_cell[Port]].acquire()
						prop_ports[considered_cell[Port]].append(considered_cell)
						prop_locks[considered_cell[Port]].release()
						# Go to the next cell 
						now_trying += 1
					else:
						# We've gone off the queue so we don't make this matching 
						considered_cell = None

				# thread_print (considered_cell)

				dec_cnt(state.SCHED_1_PROP)

				# thread_print(state())

				# Wait until state change
				while hasnt_reached(state.SCHED_1_EVAL):
					if finish_flag:
						return
					pass

				############################################ PHASE 2.1 ############################################
				if(considered_cell is not None):
					# Wait until output port has made a decision 
					while len(get_prop_port(considered_cell)) is not 1:
						pass

					thread_print("!matched is " + str(num_not_matched))
					thread_print("chk cell " + str(considered_cell))
					# Check if we were lucky
					if (len(get_prop_port(considered_cell)) != 0 and get_prop_port(considered_cell)[0] is considered_cell):
						thread_print ("a")
						# Only decrement if this is the first time we get matched
						if(not(is_matched)):
							var_lock.acquire()
							num_not_matched -= 1
							var_lock.release()
							thread_print("1 !matched is " + str(num_not_matched))
						is_matched = True
					else:
						thread_print ("b")
						# If we were matched before then we need to signal that we 
						# arent matched anymore
						if(is_matched):
							var_lock.acquire()
							num_not_matched += 1
							var_lock.release()
							thread_print("2 !matched is " + str(num_not_matched))

						is_matched = False

					# Signal the scheduler that we are done here 
				else:
					# We aren't proposing anything so just signal that we've matched
					# Need to make sure that we dont keep decrementing after we do it once
					if(not(is_matched)):
						var_lock.acquire()
						num_not_matched -= 1
						var_lock.release()
						thread_print("nm now " + str(num_not_matched))
					is_matched = True

				dec_cnt(state.SCHED_1_EVAL)			

				thread_print("nnm " + str(num_not_matched))

				# Wait until state change
				while is_state(state.SCHED_1_EVAL):
					if finish_flag:
						return
					pass

			thread_print("b4 rem" + str(input_Qs[id]) + " -- " + str(considered_cell))
			# Remove the item from the input queue as it is now in an output queue
			if(considered_cell != None):
				input_Qs[id].remove(considered_cell)
			# input_Qs[id] = [i for i in input_Qs[id] if i != considered_cell]
			thread_print("aft rem" + str(input_Qs[id]))

		else:
			state_now = curr_state
			while is_state(state_now):
				if(finish_flag):	
					return				
				pass

def output_Q_thread(id):
	global out_ports
	global output_Qs
	global finish_flag
	global prop_ports
	global curr_state
	global transmitted_packets
	global prop_locks

	while not(finish_flag):
		if(is_state(state.ARRIVAL)):
			prop_locks[id].acquire()
			if(len(prop_ports[id]) is not 0):
				# Insert packet from matching into the queue
				output_Qs[id].append(prop_ports[id].pop(0))
			prop_locks[id].release()
							
		elif(is_state(state.SCHED_1_EVAL)):
			# Check if anyone has made a proposal
			prop_locks[id].acquire()

			if(len(prop_ports[id]) is not 0):
				# Sort the buffer from low to high
				prop_ports[id].sort(key=lambda tup: tup[TTL])

				# Pick the one with the lowest TTL and drop the rest
				prop_ports[id] = [prop_ports[id][0]]

				thread_print("props " + str(prop_ports[id]))

			prop_locks[id].release()


		elif(is_state(state.DEPART)):
			prop_locks[id].acquire()
			if(len(prop_ports[id]) is not 0):
				# Insert packet from matching into the queue
				output_Qs[id].append(prop_ports[id].pop(0))

			thread_print ("oQ: " + str(output_Qs[id]))
			prop_locks[id].release()
			# KICK THE THING OFF
			
			# Send the earliest packet out 
			# if(len(output_Qs[id]) != 0):
			# 	transmitted_packets.append(output_Qs[id].pop(0))

			dec_cnt(state.DEPART)

		# Wait till state change
		state_now = curr_state
		while is_state(state_now):
			if(finish_flag):	
				return				
			pass

def send_packets_out():
	global out_ports
	global transmitted_packets
	global timer_tick
	global finish_flag
	global late_lock
	global late_count
	global output_Qs

	# Send out (pop) the earliest packet from all the output queues
	late_lock.acquire()
	for i in output_Qs:
		if(len(i) != 0):
			i.sort(key=lambda tup: tup[TTL])
			to_send = i.pop(0)
			if(to_send[TTL] < timer_tick):
				# finish_flag = True
				thread_print("LATE! : " + str(to_send) + " ------ " + str(timer_tick))
				late_count += 1
				# exit()
			transmitted_packets.append(to_send)

	timer_tick += 1
	late_lock.release()

timer_tick = 0

late_count = 0
late_lock = threading.Lock()

finish_flag = False

input_ports = [None for i in xrange(0, iNQs)]
out_ports 	= [None for i in xrange(0, oNQs)]
prop_ports  = [[]   for i in xrange(0, oNQs)]
prop_locks  = [threading.Lock() for i in xrange(0, oNQs)]
input_Qs 	= [[]   for i in xrange(0, iNQs)]
output_Qs 	= [[]   for i in xrange(0, oNQs)]

transmitted_packets = [];

num_not_matched = iNQs

# Keep track of threads that have completed a state
state_cntrs = [iNQs for i in xrange(0, state.NUM_STATES)]
	
for x in xrange(0, iNQs):
	recv_thread = threading.Thread(target = input_Q_thread, args = ([x]));
	recv_thread.setName("Input Port " + str(x))
	recv_thread.start();

for x in xrange(0, oNQs):
	recv_thread = threading.Thread(target = output_Q_thread, args = ([x]));
	recv_thread.setName("Output Port " + str(x))
	recv_thread.start();


all_inputs = set()

the_seed = random.randrange(sys.maxsize)
# the_seed = 2549190221342468845L
random.seed(the_seed)
# for x in xrange(1,50):
num_packets = 500
x = 0
tick_counter = 0
while len(transmitted_packets) < (num_packets * iNQs):
	#############################################################################
	thread_print ("\n\n======== state is ARRIVAL at " + str((x, the_seed)) + " ========\n")
	# input_ports[0] = (3, 1)
	# input_ports[1] = (2, 1)
	# input_ports[2] = (1, 1)
	# input_ports[3] = (50, 1)

	
	if(x < num_packets):
		for y in xrange(0, iNQs):
			cell_new = None
			is_there = True
			# while is_there:
			is_there = False
			base = 10
			cell_new = (random.randint(timer_tick + base, timer_tick + base + 20), random.randint(0, oNQs - 1))
			if(cell_new in all_inputs):
				is_there = True
			all_inputs.add(cell_new)
			# print all_inputs
			input_ports[y] = (cell_new)
	x += 1

	# input_ports[1] = (random.randint(0, 10), random.randint(0, iNQs))
	# input_ports[2] = (random.randint(0, 10), random.randint(0, iNQs))
	# input_ports[3] = (random.randint(0, 10), random.randint(0, iNQs))

	curr_state = state.ARRIVAL

	# Wait till everyone finished with the first stage
	while (state_cntrs[state.ARRIVAL] is not(0)):
			pass

	# Keep trying while packets havent been matched
	while num_not_matched != 0:
		# time.sleep(1)
		#############################################################################
		thread_print ("\n\n======== state is PROP " + str((x, the_seed)) + " ========\n")
		curr_state = state.SCHED_1_PROP

		while (state_cntrs[state.SCHED_1_PROP] is not(0)):
			pass

		reset_cntrs()

		#############################################################################
		thread_print ("\n\n======== state is EVAL " + str((x, the_seed)) + " ========\n")
		curr_state = state.SCHED_1_EVAL

		while (state_cntrs[state.SCHED_1_EVAL] is not(0)):
			pass

		reset_cntrs()

	#############################################################################
	num_not_matched = iNQs

	thread_print ("\n\n======== state is DEPART " + str((x, the_seed)) + " ========\n")
	curr_state = state.DEPART

	while (state_cntrs[state.DEPART] is not(0)):
		pass

	send_packets_out()

	#############################################################################

	# Commence second matching 
	while num_not_matched != 0:
		#############################################################################
		thread_print ("\n\n======== state is PROP " + str((x, the_seed)) + " ========\n")
		curr_state = state.SCHED_1_PROP

		while (state_cntrs[state.SCHED_1_PROP] is not(0)):
			pass

		reset_cntrs()

		#############################################################################
		thread_print ("\n\n======== state is EVAL " + str((x, the_seed)) + " ========\n")
		curr_state = state.SCHED_1_EVAL

		while (state_cntrs[state.SCHED_1_EVAL] is not(0)):
			pass

		reset_cntrs()

	#############################################################################
	num_not_matched = iNQs
	thread_print("AIs : " + str(all_inputs))
 
	thread_print("Is: :" + str(len(all_inputs)) + ", Os: " + str(len(transmitted_packets)))
	
	tick_counter += 1

thread_print(all_inputs)
thread_print(transmitted_packets)

thread_print("Input Qs")
j = 0
for inq in input_Qs:
	thread_print(str(j) + ": " + str(inq))

thread_print("\nOutput Qs")
j = 0
for outq in output_Qs:
	thread_print(str(j) + ": " + str(outq))

thread_print("Is: :" + str(len(all_inputs)) + ", Os: " + str(len(transmitted_packets)))

thread_print("took " + str(tick_counter) + " ticks to finish")

finish_flag = True
thread_print("There were " + str((num_packets * iNQs) - late_count) + "/" + str((num_packets * iNQs)) + " packets transmitted")

