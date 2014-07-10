from django.conf import settings
from django.db import connections

class ComputeNode:
	def __init__(self,vcpus,memory_mb,vcpus_used,memory_mb_used,hypervisor_hostname,running_vms):
		self.vcpus=vcpus
                self.memory_mb=memory_mb
		self.vcpus_used=vcpus_used
		self.memory_mb_used=memory_mb_used
		self.hypervisor_hostname=hypervisor_hostname
		self.running_vms=running_vms
		self.rest_vcpus=vcpus*4-vcpus_used
		self.rest_memory_mb=memory_mb-memory_mb_used
	def __str__(self):
		return "--host:%s,rest_vcpus:%s,rest_mem:%s-- " % (self.hypervisor_hostname,self.rest_vcpus,self.rest_memory_mb)

        def __repr__(self):
                return "--host:%s,rest_vcpus:%s,rest_mem:%s-- " % (self.hypervisor_hostname,self.rest_vcpus,self.rest_memory_mb)

	def availability(self,cpu,mem):
		return self.rest_vcpus>cpu and self.rest_memory_mb>mem

GET_PHYSICAL="SELECT vcpus,memory_mb,vcpus_used,memory_mb_used,hypervisor_hostname,running_vms FROM compute_nodes WHERE deleted=0 AND host_ip=%s"

GET_ALL_PHYSICAL="SELECT vcpus,memory_mb,vcpus_used,memory_mb_used,hypervisor_hostname,running_vms FROM compute_nodes WHERE deleted=0"

GET_FILTER_PHYSICAL="SELECT vcpus,memory_mb,vcpus_used,memory_mb_used,hypervisor_hostname,running_vms FROM compute_nodes WHERE deleted=0 AND hypervisor_hostname IN (%s)"

class ComputeNodeMana:

    def getComputeNodeByIp(self,ip,db):
	cursor=db.cursor()
	cursor.execute(GET_PHYSICAL,ip)
	result=cursor.fetchone()
	cursor.close()
	if not result:
		print "Can't find physical machine by ip(%s)" % ip
		return None
	vcpus=result[0]
	memory_mb=result[1]
	vcpus_used=result[2]
	memory_mb_used=result[3]
	hypervisor_hostname=result[4]	
	running_vms=result[5]
	computeNode=ComputeNode(vcpus,memory_mb,vcpus_used,memory_mb_used,hypervisor_hostname,running_vms)
	return computeNode

    def getComputeNodes(self,db):
	cursor=db.cursor()
	cursor.execute(GET_ALL_PHYSICAL)
	results=cursor.fetchall()
	nodes=[]
	for line in results:
		vcpus=line[0]
		memory_mb=line[1]
		vcpus_used=line[2]
		memory_mb_used=line[3]
		hypervisor_hostname=line[4]	
		running_vms=line[5]
		nodes.append(ComputeNode(vcpus,memory_mb,vcpus_used,memory_mb_used,hypervisor_hostname,running_vms))
	cursor.close()
	return nodes

    def getFilterComputeNodes(self,db,filters):
	cursor=db.cursor()
	cursor.execute(GET_FILTER_PHYSICAL,filters)
	results=cursor.fetchall()
	nodes=[]
	for line in results:
		vcpus=line[0]
		memory_mb=line[1]
		vcpus_used=line[2]
		memory_mb_used=line[3]
		hypervisor_hostname=line[4]	
		running_vms=line[5]
		nodes.append(ComputeNode(vcpus,memory_mb,vcpus_used,memory_mb_used,hypervisor_hostname,running_vms))
	cursor.close()
	return nodes



VIR_PORT="SELECT port_id FROM ipallocations WHERE ip_address=%s"

VIR_UUID="SELECT device_id FROM ports WHERE id=%s"

GET_INSTANCE="SELECT uuid,memory_mb,vcpus,vm_state,host,user_id,project_id,hostname,id FROM instances WHERE uuid=%s"

PHY_CHILDS="SELECT uuid,memory_mb,vcpus,vm_state,host,user_id,project_id,hostname,id FROM instances WHERE `host`=%s AND vm_state <> 'deleted'"

class InstanceBean:
	def __init__(self,uuid,memory_mb,vcpus,vm_state,host,user_id,project_id,hostname,id_):
		self.uuid=uuid
		self.memory_mb=memory_mb
		self.vcpus=vcpus
		self.vm_state=vm_state
		self.host=host
		self.user_id=user_id,
		self.project_id=project_id
		self.hostname=hostname
		self.id=id_

        def __repr__(self):
                return "--uuid:%s,hostname:%s,vcpus:%s,mem:%s-- " % (self.uuid,self.hostname,self.vcpus,self.memory_mb)

class InstanceManager:
	def findInstanceIdByIp(self,neutron_db,nova_db,ip):
		cursor=neutron_db.cursor()
		cursor.execute(VIR_PORT,ip)
		result=cursor.fetchone()
		
		size=0 if not result else len(result)
		if size>0:
		    print "GET PORT_ID %s" % result[0]
		    cursor.execute(VIR_UUID,result[0])
		    result=cursor.fetchone()
		    size=0 if not result else len(result)
		else:
		    print "Can't find port_id by ip(%s),break!" % ip
		cursor.close()
		if size==0:
		    print "Can't find device_id by ip(%s),break!" % ip
		    return None
		uuid=result[0]
		print "GET UUID %s" % uuid
		cur=nova_db.cursor()
		cur.execute(GET_INSTANCE,uuid)
		result=cur.fetchone()
		cur.close()
		if not result:
			print "Can't find instance by device_id(%s),break!" % uuid
			return None
		uuid=result[0]
		memory_mb=result[1]
		vcpus=result[2]
		vm_state=result[3]
		host=result[4]
		user_id=result[5]
		project_id=result[6]
		hostname=result[7]
		id_=result[8]
	        instanceBean=InstanceBean(uuid,memory_mb,vcpus,vm_state,host,user_id,project_id,hostname,id_)
		return instanceBean

	def getChildrens(self,nova_db,ip):
		node=ComputeNodeMana().getComputeNodeByIp(ip,nova_db)
		if not node:
			return None
		host=node.hypervisor_hostname
		cursor=nova_db.cursor()
		cursor.execute(PHY_CHILDS,host)
		childs=[]
		results=cursor.fetchall()
		for result in results:
			uuid=result[0]
			memory_mb=result[1]
			vcpus=result[2]
			vm_state=result[3]
			host=result[4]
			user_id=result[5]
			project_id=result[6]
			hostname=result[7]
			id_=result[8]
	        	instanceBean=InstanceBean(uuid,memory_mb,vcpus,vm_state,host,user_id,project_id,hostname,id_)
			childs.append(instanceBean)
		cursor.close()
		return childs
		

GET_SERVICE_URL='SELECT url FROM endpoint WHERE interface="public" AND region=%s AND service_id =(SELECT id FROM service WHERE type=%s)'
		


class KeyStoneManager:
    def getServiceUrl(self,service_name,region):
	print region
	print service_name
	db_region=connections["KEYSTONE"]
	cursor=db_region.cursor()
	cursor.execute(GET_SERVICE_URL,(region,service_name))
	result=cursor.fetchone()
	cursor.close()
	return None if not result else result[0] % settings.SYS_C2


GET_FREE_IP='SELECT networks.`name`,networks.`status`,subnets.id,ipavailabilityranges.first_ip,ipavailabilityranges.last_ip,networks.id,subnets.`name` as "subnet_name" FROM ipavailabilityranges,ipallocationpools,subnets,networks WHERE ipavailabilityranges.allocation_pool_id=ipallocationpools.id AND ipallocationpools.subnet_id=subnets.id AND subnets.network_id=networks.id ORDER BY networks.`name`,subnets.`name`'


class NetWork:
	def __init__(self,id_,name,status,subnet,subnet_id,first_ip,last_ip):
		self.name=name
		self.status=status
		self.subnet=subnet
		self.subnet_id=subnet_id
		self.first_ip=first_ip
		self.last_ip=last_ip
		self.id=id_
		self.freeNumber=self.freeNum()

	def freeNum(self):
		index=self.first_ip.rindex(".")+1
		first_num=int(self.first_ip[index:])
		index=self.last_ip.rindex(".")+1
		last_num=int(self.last_ip[index:])
		return last_num-first_num+1

class NetWorkManager:

    def getFreeIp(self,db):
	cursor=db.cursor()
	cursor.execute(GET_FREE_IP)
	results=cursor.fetchall()
	cursor.close()
	nodes=[]
	for line in results:
		name=line[0]
		status=line[1]
		subnet_id=line[2]
		first_ip=line[3]
		last_ip=line[4]	
		id_=line[5]
		subnet=line[6]
		nodes.append(NetWork(id_,name,status,subnet,subnet_id,first_ip,last_ip))
	return nodes

    def getTotalNum(self,nodes):
	display={}
	for node in nodes:
	    if display.has_key(node.name):
		total=display.get(node.name)
		total+=node.freeNum()
		display[node.name]=total
	    else:
		display[node.name]=node.freeNum()
	return display




		

		

		











