import os;
import threading
import signal
import time
import random
import sys
 
def sigint_handler(signum, frame):
	global die_bitches
	die_bitches = True
	exit()
 
signal.signal(signal.SIGINT, sigint_handler)

iNQs = 10
oNQs = 10

TTL   = 0
OPort = 1
IPort = 2

# 
# 
# 
# POSSIBLE CLOCK SYNC, WAIT ON EVENTS AT EACH STAGE AND HAVE A TIMER INTERRUPT RESET THOSE EVENTS
# 
# 
# 
# WHAT HAPPENS IF IT FAILS TO FIND STABLE MATCHING 
# USE IRWING'S ALGO?????????????????
# 
# 
# 
# 

class state:
	IDLE 		 = 0
	ARRIVAL      = 1
	SCHED_1_PROP = 2
	SCHED_1_EVAL = 3
	SCHED_1_MID  = 4
	DEPART  	 = 5
	SCHED_2 	 = 6
	NUM_STATES 	 = 7

	@staticmethod
	def to_string(num):
		return {
	        state.IDLE  		: "IDLE",
	        state.ARRIVAL 		: "ARRIVAL",
	        state.SCHED_1_PROP 	: "SCHED_1_PROP",
	        state.SCHED_1_MID 	: "SCHED_1_MID",
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
	# thread_print (cell[OPort]
	return prop_ports[cell[OPort]]

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
	global die_bitches
	global prop_ports
	global curr_state
	global num_not_matched
	global var_lock
	global prop_locks

	while not(die_bitches):
		############################################ PHASE 1.0 ############################################
		if(is_state(state.ARRIVAL)):
			# If a new packet arrived at this port 
			if (input_ports[id] != None):
				new_cell = input_ports[id]
				# Insert into the input queue 
				input_Qs[id].append(new_cell)

			# thread_print (input_Qs[id])
			dec_cnt(state.ARRIVAL)
			thread_print("done arrive")

			input_ports[id] = None

			# Wait for state change 
			while is_state(state.ARRIVAL):
				if die_bitches:
					return
				pass			

		############################################ PHASE 2.0 ############################################
		elif(is_state(state.SCHED_1_PROP)):
			# Keep doing the stuff below until a stable matching is made
			# while is_state(state.SCHED_1_PROP):
			thread_print ("iQ len = " + str(len(input_Qs[id])))	
			for considered_cell in input_Qs[id]:
				# Make a proposal to the appropriate output port 
				# thread_print(prop_locks[considered_cell[OPort]].locked())
				prop_locks[considered_cell[OPort]].acquire()
				thread_print ("try cell " + str(considered_cell))
				prop_ports[considered_cell[OPort]].append(considered_cell)
				prop_locks[considered_cell[OPort]].release()

			dec_cnt(state.SCHED_1_PROP)
			# thread_print("11111111111111111111111")

			# Wait until state change
			while hasnt_reached(state.SCHED_1_EVAL):
				if die_bitches:
					return
				pass

			############################################ PHASE 2.1 ############################################


			if(len(grant_ports[id]) > 0):

				the_grant = None
				# Sorting according to their TTLs
				grant_ports[id].sort(key=lambda tup: tup[TTL])
				# Take the one with the shortest TTL 
				the_grant = grant_ports[id][0]

				if(the_grant != None):
					grant_ports[id] = [the_grant]
				else:
					grant_ports[id] = []

				i_RR_ptrs[id] = (i_RR_ptrs[id] + 1) % iNQs

				thread_print("gp: " + str(grant_ports[id]))

			var_lock.acquire()
			num_not_matched -= 1
			var_lock.release()
			# dec_cnt(state.SCHED_1_EVAL)			


			# Wait until state change
			while is_state(state.SCHED_1_EVAL):
				if die_bitches:
					return
				pass

			old_len = len(input_Qs[id])
			# Remove the item from the input queue as it is now in an output queue
			if(len(grant_ports[id]) > 0):
				# thread_print("b4 rem" + str(input_Qs[id]) + " -- " + str(grant_ports[id][0]))
				input_Qs[id].remove(grant_ports[id].pop(0))
				thread_print("changed from " + str(old_len) + " to " + str(len(input_Qs[id])))
			# input_Qs[id] = [i for i in input_Qs[id] if i != considered_cell]
			# thread_print("aft rem" + str(input_Qs[id]))

		else:
			state_now = curr_state
			while is_state(state_now):
				if(die_bitches):	
					return				
				pass

def output_Q_thread(id):
	global out_ports
	global output_Qs
	global die_bitches
	global prop_ports
	global curr_state
	global transmitted_packets
	global prop_locks

	while not(die_bitches):
		# if(is_state(state.ARRIVAL)):
			# prop_locks[id].acquire()
			# if(len(prop_ports[id]) is not 0):
			# 	# Insert packet from matching into the queue
			# 	output_Qs[id].append(prop_ports[id].pop(0))
			# prop_locks[id].release()
							
		if(is_state(state.SCHED_1_MID)):
			# Check if anyone has made a proposal
			prop_locks[id].acquire()

			if(len(prop_ports[id]) is not 0):
				# Pick from random 

				the_grant = None
				longest_len_seen = float(-1)

				# Finding the longest queue 
				for ps in prop_ports[id]: 
					if(float(float(len(input_Qs[ps[IPort]]) / 100)/float(ps[TTL])) > longest_len_seen):
					# if(ps[TTL] < longest_len_seen):
						the_grant = ps
						longest_len_seen = float(float(len(input_Qs[ps[IPort]]))/float(ps[TTL]))

				if(the_grant != None):
					prop_ports[id] = [the_grant]
				else:
					prop_ports[id] = []

				thread_print("props " + str(prop_ports[id]))

				# prop_locks[id].release()

				if(len(prop_ports[id]) is not 0):
					granted = (prop_ports[id].pop(0))
					grant_locks[granted[IPort]].acquire()
					grant_ports[granted[IPort]].append(granted)
					grant_locks[granted[IPort]].release()

			prop_locks[id].release()
			dec_cnt(state.SCHED_1_MID)


		elif(is_state(state.SCHED_1_EVAL)):
			wait_more = True
			while wait_more:
				wait_more = False
				for i in xrange(0, iNQs):
					grant_locks[i].acquire()
					if(len(grant_ports[i]) > 1):
						wait_more = True
						grant_locks[i].release()
						break;
					grant_locks[i].release()

			for i in xrange(0, iNQs):
				grant_locks[i].acquire()
				if(len(grant_ports[i]) > 0 and grant_ports[i][0][OPort] == id):
					output_Qs[id].append(grant_ports[i].pop(0))
					# Only increment the RR ptr if the input has chosen your grant
					o_RR_ptrs[id] = (o_RR_ptrs[id] + 1) % oNQs
					grant_locks[i].release()
					break;
				grant_locks[i].release()

			dec_cnt(state.SCHED_1_EVAL)

		elif(is_state(state.DEPART)):
			dec_cnt(state.DEPART)

		# Wait till state change
		state_now = curr_state
		while is_state(state_now):
			if(die_bitches):	
				return				
			pass

def send_packets_out():
	global out_ports
	global transmitted_packets
	global timer_tick
	global die_bitches
	global late_lock
	global late_count
	global output_Qs

	# Send out (pop) the earliest packet from all the output queues
	late_lock.acquire()
	for i in output_Qs:
		if(len(i) != 0):
			i.sort(key=lambda tup: tup[TTL])
			for j in i:
				if(j[TTL] < timer_tick):
					# die_bitches = True
					thread_print("LATE! : " + str(j) + " ------ " + str(timer_tick))
					late_count += 1
					# exit()
				transmitted_packets.append(j)
				i.remove(j)

	# for i in input_Qs:
	# 	if(len(i) != 0):
	# 		for j in i:
	# 			if(j[TTL] < timer_tick):
	# 				# die_bitches = True
	# 				thread_print("LATE! : " + str(j) + " ------ " + str(timer_tick))
	# 				late_count += 1
	# 				# exit()
	# 			transmitted_packets.append(j)
	# 			i.remove(j)

	timer_tick += 1
	late_lock.release()

timer_tick = 0

late_count = 0
late_lock = threading.Lock()

die_bitches = False

input_ports = [None for i in xrange(0, iNQs)]
grant_ports = [[]   for i in xrange(0, iNQs)]
grant_locks = [threading.Lock() for i in xrange(0, iNQs)]
out_ports 	= [None for i in xrange(0, oNQs)]
prop_ports  = [[]   for i in xrange(0, oNQs)]
prop_locks  = [threading.Lock() for i in xrange(0, oNQs)]
input_Qs 	= [[]   for i in xrange(0, iNQs)]
output_Qs 	= [[]   for i in xrange(0, oNQs)]
o_RR_ptrs 	= [0    for i in xrange(0, oNQs)]
i_RR_ptrs 	= [0    for i in xrange(0, oNQs)]

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
num_packets = 100
x = 0
tick_counter = 0
base = 10
while len(transmitted_packets) < (num_packets * iNQs):
	#############################################################################
	thread_print ("\n\n======== state is ARRIVAL at " + str((x, the_seed)) + " ========\n")
	# input_ports[0] = (3, 1)
	# input_ports[1] = (2, 1)
	# input_ports[2] = (1, 1)
	# input_ports[3] = (50, 1)

	thread_print("tp: " + str(len(transmitted_packets)))
	
	if(x < num_packets):
			for y in xrange(0, iNQs):
				if(not(random.random() < (0.2 * y))):
					continue
				cell_new = None
				is_there = True
				# while is_there:
				is_there = False
				
				cell_new = (random.randint(timer_tick + base, timer_tick + base + 20), random.randint(0, oNQs - 1), y)
				thread_print("got one")
				if(cell_new in all_inputs):
					is_there = True
				all_inputs.add(cell_new)
				# print all_inputs
				input_ports[y] = (cell_new)
				thread_print("added")
	x += 1

	# input_ports[1] = (random.randint(0, 10), random.randint(0, iNQs))
	# input_ports[2] = (random.randint(0, 10), random.randint(0, iNQs))
	# input_ports[3] = (random.randint(0, 10), random.randint(0, iNQs))

	curr_state = state.ARRIVAL
	thread_print("fin packet gen")
	# Wait till everyone finished with the first stage
	while (state_cntrs[state.ARRIVAL] is not(0)):
			pass

	# Keep trying while packets havent been matched
	# while num_not_matched != 0:
	# time.sleep(1)
	#############################################################################
	thread_print ("\n\n======== state is PROP " + str((x, the_seed)) + " ========\n")
	curr_state = state.SCHED_1_PROP

	while (state_cntrs[state.SCHED_1_PROP] is not(0)):
		pass

	reset_cntrs()

	#############################################################################
	thread_print ("\n\n======== state is MID " + str((x, the_seed)) + " ========\n")
	curr_state = state.SCHED_1_MID

	while (state_cntrs[state.SCHED_1_MID] is not(0)):
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
	reset_cntrs()

	#############################################################################

	
# thread_print(all_inputs)
# thread_print(transmitted_packets)

# thread_print("Input Qs")
# j = 0
# for inq in input_Qs:
# 	thread_print(str(j) + ": " + str(inq))

# thread_print("\nOutput Qs")
# j = 0
# for outq in output_Qs:
# 	thread_print(str(j) + ": " + str(outq))

thread_print("Is: :" + str(len(all_inputs)) + ", Os: " + str(len(transmitted_packets)))

thread_print("took " + str(tick_counter) + " ticks to finish")

die_bitches = True
thread_print("There were " + str((num_packets * iNQs) - late_count) + "/" + str((num_packets * iNQs)) + " packets transmitted")
thread_print("Base was " + str(base))
