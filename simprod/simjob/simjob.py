#!/usr/bin/python
# -*- coding: utf-8 -*-

## Author: Matthieu Marinangeli
## Mail: matthieu.marinangeli@cern.ch
## Description: simulation job class

from random import shuffle
from .scripts import *
import os
import time
from random import randint
from .setup import DoProd
import warnings
import glob
import json


class JobCollection(object):
	"""
	Simulation job collection.
	"""
	
	def __init__(self, **kwargs):
		self._jobs     = {}	
		self._jsondict = {}	
		
		simprod = os.getenv("SIMPRODPATH")+"/simprod"		
		self._jobsdir   = "{0}/._simjobs_".format(simprod)
		self._collection_file = "{0}/collection.json".format(self._jobsdir)

		if os.path.isfile( self._collection_file ):
			_collectedjobs = json.load(open(self._collection_file))
			self._jsondict = _collectedjobs
			
			for cj in _collectedjobs.keys():
				if not os.path.isfile(_collectedjobs[cj]):
					continue
				self._jobs[cj]     = SimulationJob().from_file(_collectedjobs[cj])
				self._jsondict[cj] = _collectedjobs[cj]
				
		self.__update()
								
	def _keys(self):
		_keys = [int(k) for k in self._jobs.keys()]
		return sorted(_keys, key=int)
			
	def __str__(self):
		self.__update()
		
		toprint  = "{0} jobs\n".format(len(self._jobs))
		
		h_job     = "    #job "
		h_status  = "       status "
		h_evttype = "       evttype "
		h_year    = "   year "
		h_nevents = "  #events "
		h_subjobs = "  #subjobs "
		
		header = "{0}|{1}|{2}|{3}|{4}|{5}|\n".format( 
					h_job, 
					h_status, 
					h_evttype, 
					h_year, 
					h_nevents, 
					h_subjobs)
					
		line = "-"*(len(header) - 2) + "\n"
				
		toprint += line
		toprint += header
	
		for i in self._keys():
			
			toprint += line
			
			job     = self._jobs[str(i)]
			status  = job.status
			evttype = str(job.evttype)
			year    = str(job.year)
			nevents = str(job.nevents)
			subjobs = str(job.nsubjobs)
			
			if status == "submitted":
				color = cyan
			elif status == "new":
				color = cdefault
			elif status == "submitting":
				color = magenta
			elif status == "running":
				color = green
			elif status == "completed":
				color = blue
			elif status == "failed":
				color = red
					
			p_job     = " "*(len(h_job) - len(str(i)) - 1) + str(i) + " "
			
			p_status  = " "*(len(h_status) - len(status) - 1) + status + " "
			
			p_evttype = " "*(len(h_evttype) - len(evttype) - 1) + evttype + " "
			
			p_year    = " "*(len(h_year) - len(year) - 1) + year + " "
			
			p_nevents = " "*(len(h_nevents) - len(nevents) - 1) + nevents + " "
			
			p_subjobs = " "*(len(h_subjobs) - len(subjobs) - 1) + subjobs + " "
						
			toprint += color("{0}|{1}|{2}|{3}|{4}|{5}|\n".format( 
						p_job, 
						p_status, 
						p_evttype, 
						p_year, 
						p_nevents, 
						p_subjobs))
	
		return toprint
		
	def _repr_pretty_(self, p, cycle):
		if cycle:
			p.text('job collection...')
			return
		p.text(self.__str__())
		
	def __getitem__(self, i):
		self.__update()
		if i not in self._keys():
			raise ValueError("jobs({0}) not found!".format(i))
		else:
			return self._jobs[str(i)]
			
	def __update(self):
		jsonfiles = glob.glob("{0}/*_*_*_*_*.json".format(self._jobsdir))
		
		for k in self._jsondict.keys():
			_file = self._jsondict[k]
			if not os.path.isfile(_file):
				self._jsondict.pop(k, None)
				self._jobs.pop(k, None)
								
			elif self._jobs[str(k)].status == "new":
				self._jobs[str(k)] = SimulationJob().from_file(_file)
				
		for js in jsonfiles:
			if js not in self._jsondict.values():
				if len(self._jsondict) < 1:
					index = 0
				else:
					maxindex = max(self._keys())
					index    = str(maxindex + 1) 
				self._jobs[str(index)] = SimulationJob().from_file(js) 
				self._jsondict[str(index)] = js
				
		self._store_collection()
							
	def _store_collection(self):
				
		if not os.path.isdir(self._jobsdir):
			os.system("mkdir -p {0}".format(self._jobsdir))
								
		jsondict = json.dumps(self._jsondict)
		f = open(self._collection_file, "w")
		f.write(jsondict)
		f.close()				
				
class SimulationJob(object):
	"""
	Simulation job
	"""
	
	def __init__(self, **kwargs):			
		self._subjobs = {}
		self._options = {}
					
		self._nevents    = kwargs.get('nevents', None)
		self._neventsjob = kwargs.get('neventsjob', 50)
		self._year       = kwargs.get('year', None)
		self._polarity   = kwargs.get('polarity', None)
		self._simcond    = kwargs.get('simcond', "Sim09c")
		self._stripping  = kwargs.get('stripping', None)
		self._turbo      = kwargs.get('turbo', False)
		self._mudst      = kwargs.get('mudst', False)
		self._runnumber  = kwargs.get('runnumber', baserunnumber())
		self._decfiles   = kwargs.get('decfiles', 'v30r5')
		
		self._evttype = kwargs.get('evttype', None)	
		if self._evttype:
			self.__setoptfile()
		
		_basedir = os.getenv("SIMOUTPUT")
		if not _basedir:
			_basedir = os.getenv("HOME")+"/SimulationJobs"

		self._options["basedir"] = kwargs.get('basedir', _basedir)
		
		self._options["time"]  = kwargs.get('time', None)
																			
		if IsSlurm():
			default_options    = DefaultSlurmOptions( )
			
			self._options["lsf"]      = False
			self._lsf                 = self._options["lsf"]
			self._options["slurm"]    = True	
			self._slurm               = self._options["slurm"]
			self._options["subtime"]  = kwargs.get('subtime', None)
						
			self._options["default_options"] = []
							
			def addvars(var):
				
				def make_get_set(var):
					def getter(self):
						return self._options["var"]
					def setter(self, value):
						if isinstance(value, (int, float) ):
							self._options[var] = int( value )
							if var in self._options["default_options"]:
								self._options["default_options"].remove(var)
						else:
							raise TypeError(var + " must be a int!")
					return getter, setter
				
				get_set = make_get_set(var)
				self.__add_var(var, get_set)
			
			self._options["nsimjobs"]     = kwargs.get('nsimjobs', None)
			if not self._options["nsimjobs"]:
				self._options["nsimjobs"]             = default_options['nsimjobs']
				self._options["default_options"]     += ["nsimjobs"]
				
			addvars("nsimjobs")
													
			self._options["nsimuserjobs"] = kwargs.get('nsimuserjobs', None)
			if not self._options["nsimuserjobs"]:
				self._options["nsimuserjobs"]         = default_options['nsimuserjobs']
				self._options["default_options"]     += ["nsimuserjobs"]
				
			addvars("nsimuserjobs")
								
			self._options["nuserjobs"]    = kwargs.get('nuserjobs', None)
			if not self._options["nuserjobs"]:
				self._options["nuserjobs"]            = default_options['nuserjobs']
				self._options["default_options"]     += ["nuserjobs"]
				
			addvars("nuserjobs")
								
			self._options["npendingjobs"]  = kwargs.get('npendingjobs', None)
			if not self._options["npendingjobs"]:
				self._options["npendingjobs"]         = default_options['npendingjobs']
				self._options["default_options"]     += ["npendingjobs"]
				
			addvars("npendingjobs")
								
			self._options["nfreenodes"]    = kwargs.get('nfreenodes', None)
			if not self._options["nfreenodes"]:
				self._options["nfreenodes"]           = default_options['nfreenodes']
				self._options["default_options"]     += ["nfreenodes"]
				
			addvars("nfreenodes")
								
			self._options["cpu"]  = kwargs.get('cpu', None)
			if not self._options["cpu"]:
				self._options["cpu"]                  = default_options['cpu']
				self._options["default_options"]     += ["cpu"]
				
			addvars("npendingjobs")
								
		elif IsLSF():
			default_options    = DefaultLSFOptions()
			self._options["default_options"] = []
			self._options["toeos"]    = kwargs.get('toeos', False)
			
			if self._options["toeos"]:				
				self._options["eosdir"]  = kwargs.get('_eosdir', None)
				self._options["eosproddir"] = kwargs.get('_eosproddir',  None)
				
			self._options["lsf"]      = True
			self._lsf                 = self._options["lsf"]
			self._options["slurm"]    = False	
			self._slurm               = self._options["slurm"]
			
			self._options["cpu"]  = kwargs.get('cpu', None)
			if not self._options["cpu"]:
				self._options["cpu"]                  = default_options['cpu']
				self._options["default_options"]     += ["cpu"]
				
		self._proddir            = kwargs.get('_proddir',  None)
		self._destdir            = kwargs.get('_destdir', None)
		self._nsubjobs           = kwargs.get('_nsubjobs',  None)
		self._neventsjobs        = kwargs.get('_neventsjob',  None)
		self._options["subdir"]  = kwargs.get('subdir',  None)
							
	@property
	def nevents( self):
		return self._nevents
		
	@nevents.setter
	def nevents( self, value):
		if isinstance(value, (int, float) ):
			self._nevents = int( value )
		else:
			raise TypeError("nevents must be a int!")
				
	@property
	def neventsjob( self):
		return self._neventsjob
		
	@neventsjob.setter
	def neventsjob( self, value):
		if isinstance(value, (int, float) ):
			self._neventsjob = int( value )
		else:
			raise TypeError("nevents must be a int!")
		
	@property
	def nsubjobs( self):
		return self._nsubjobs
		
	@property
	def evttype( self):
		return self._evttype
		
	@evttype.setter
	def evttype( self, value ):
		self._evttype = value		
		self._setoptfile()
		
	@property	
	def simcond( self):
		return self._simcond
		
	@simcond.setter	
	def simcond( self, value):
		if not isinstance(value, str):
			raise TypeError("simcond must be a str!")
		if not value in ["Sim09b", "Sim09c"]:
			raise ValueError("simcond must be Sim09b or Sim09c!")
		self._simcond = value
		
	@property	
	def stripping( self):
		return self._stripping
		
	@stripping.setter	
	def stripping( self, value):
		if not isinstance(value, str):
			raise TypeError("simcond must be a str!")
		if not value in ["21", "24", "28", "24r1", "24r1p1", "28r1", "28r1p1"]:
			raise ValueError("stripping must be '21, '24', '28', '24r1', '24r1p1', '28r1', or '28r1p1'!")
		self._simcond = value
		
	@property	
	def year( self):
		return self._year
		
	@year.setter
	def year( self, value):
		if not isinstance(value, int):
			raise TypeError("nevents must be a int!")
		if not value in [2011,2012,2015,2016,2017]:
			raise ValueError("year must be 2011, 2012, 2015, 2016 or 2017!")
		self._year = value
					
	@property	
	def options( self):
		return self._options
		
	@property	
	def proddir( self):
		return self._proddir
		
	@proddir.setter	
	def proddir( self, directory):
		if not os.path.isdir(directory):
			os.system("mkdir -p {0}".format(directory))
		self._proddir = directory
		
	@property	
	def destdir( self):
		return self._destdir
		
	@property	
	def optfile( self):
		return self._optfile
		
	@property	
	def turbo( self):
		return self._turbo
		
	@turbo.setter	
	def turbo( self, value):
		if isinstance(value, bool):
			self._turbo = value
		else:
			raise TypeError("turbo must be set to True/False!")
	
	@property	
	def mudst( self):
		return self._mudst
		
	@mudst.setter	
	def mudst( self, value):
		if isinstance(value, bool):
			self._mudst = value
		else:
			raise TypeError("mudst must be set to True/False!")
			
	@property	
	def toeos( self):
		return self._options["toeos"]
		
	@toeos.setter	
	def toeos( self, value):
		if isinstance(value, bool):
			self._options["toeos"] = value			
		else:
			raise TypeError("toeos must be set to True/False!")
			
	def subjobs( self ):			
		return self._subjobs.values()
			
	def __getitem__(self, job_number):
		if not isinstance(job_number, int):
			raise TypeError("Job number must be a 'int'. Got a '{0}' instead!".format(job_number.__class__.__name__))
		return self._subjobs[str(job_number)]
			
	def __runnumber( self, job_number = None ):
		if job_number != None and not isinstance(job_number, int):
			raise TypeError("Job number must be a 'int'. Got a '{0}' instead!".format(job_number.__class__.__name__))
		
		if job_number == None:
			return self._runnumber
		else:
			return self._runnumber + job_number
		
	@property
	def status( self):
		nrunning   = 0
		ncompleted = 0 
		nfailed    = 0
		nsubmitted = 0
		
		for j in self.subjobs():
			status = j.status
			if status == "submitted":
				nsubmitted += 1
			elif status == "running":
				nrunning   += 1
				nsubmitted += 1
			elif status == "completed":
				ncompleted += 1
				nsubmitted += 1
			elif status == "failed":
				nfailed    += 1
				nsubmitted += 1
				
		if nsubmitted == 0:
			return "new"	
		elif nsubmitted < self.nsubjobs and nsubmitted > 0:
			return "submitting"
		elif nsubmitted == self.nsubjobs and nrunning == 0 and nfailed == 0:
			return "submitted"
		elif nsubmitted == self.nsubjobs and nrunning > 0:
			return "running"
		elif nsubmitted == self.nsubjobs and nrunning == 0 and ncompleted == self.nsubjobs and nfailed == 0:
			return "completed"
		elif nsubmitted == self.nsubjobs and nrunning == 0 and ncompleted < self.nsubjobs and nfailed > 0:
			return "failed"
																		
	def prepare( self, job_number = None, **kwargs ):
		
		if len(self._subjobs) < 1:
				
			if not self._evttype:
				raise NotImplementedError('Evttype not defined!')
				
			if not self._nevents:
				raise NotImplementedError('nevents not defined!')
				
			if not self._neventsjob:
				raise NotImplementedError('neventsjob not defined!')
				
			if not self._year:
				raise NotImplementedError('year not defined!')
				
			if not self._simcond:
				raise NotImplementedError('simcond not defined!')
				
			self.__checksiminputs()
			
			if not self._nsubjobs:
				#Number of jobs
				self._nsubjobs = int( self._nevents/ self._neventsjob )
				
				if  self._nsubjobs  == 0:
					warnings.warn( red(" WARNING: no jobs are being sent (make sure that neventsjob is smaller than nevents)! "), stacklevel = 2 )
			
			if not isinstance(self._polarity, list) or len(self._polarity) < self.nsubjobs:
				
				if not self._polarity:
					polarity = ["MagUp" for i in range(0,int(self.nsubjobs / 2))]
					polarity += ["MagDown" for i in range(int(self.nsubjobs / 2), self.nsubjobs)]
					shuffle(polarity)
					self._polarity = polarity
				else:
					self._polarity = [self._polarity for i in range(0, self.nsubjobs)]
				
			if not self._options.get("subdir", None):
				subdir = "simProd_{0}_{1}".format( self._evttype, self._simcond)
				if self._turbo:
					subdir += "_Turbo"
				if self._mudst:
					subdir += "_muDST"
				
				self._options["subdir"] = subdir
				
			if not self._proddir:
				self._proddir  = "{0}/{1}".format( self.options["basedir"], self.options["subdir"])
			
			if self._options.get("toeos", False):
				if not self._options["eosdir"]:			
					_eos = os.getenv("EOS_SIMOUTPUT")
										
					if _eos is None:
						self._options["eosdir"] = "/eos/lhcb/user/{0}/{1}/".format( user[0], user )
					else:
						self._options["eosdir"] = _eos
						
				if not self._options["eosproddir"]:	
					self._options["eosproddir"]  = "{0}/{1}".format( self.options["eosdir"], self.options["subdir"])
				
			if not self._destdir:
				self._destdir = "{0}/{1}/{2}/{3}".format( self.__destination(), self._evttype, self._year, self._simcond)
				
		self._store_job()
		
		infiles = kwargs.get('infiles', [])

		for n in range(self.nsubjobs):
			if job_number != None and job_number != n:
				continue
				
			if self._subjobs.get(str(n), None):
				continue
			
			polarity  = self._polarity[n]
			runnumber = self.__runnumber(n)
			self._subjobs[str(n)] = SimulationSubJob( parent=self, polarity=polarity, runnumber=runnumber, infiles=infiles, jobnumber=n )
			
		
			
	def cancelpreparation( self, job_number = None, **kwargs ):
		
		for n in range(self.nsubjobs):
			if job_number != None and job_number != n:
				continue
				
			if self._subjobs.get(str(n), None):
				del self._subjobs[str(n)]
						
	def __cansubmit( self):
		if self._slurm:
			#update default options
			default_options  = DefaultSlurmOptions( )
			for opt in self.options["default_options"]:
				self.options[opt] = default_options[opt]
			return SubCondition( self.options )
		else:
			return True
				
	def send( self, job_number = None ):
		for n in range(self.nsubjobs):
			if job_number != None and job_number != n:
				continue
		
			SUBMIT = False
			while SUBMIT == False:
				SUBMIT = self.__cansubmit()
				if not SUBMIT:
					print(self.__str__())
					print("")
					time.sleep( randint(0,30) * 60 )
			
			if self[n]._submitted:
				continue
					
			self[n].send
			
	def __checksiminputs( self ):
		
		def StrippingVersion( *args ):
			args = list(args)
			with warnings.catch_warnings():
				warnings.simplefilter("always")	
				if self._stripping == None:
					self._stripping = args[0]
					if len(args) > 1:
						warnings.warn( red("Default stripping verion {0} used. {1} versions are available.".format( 
										self._stripping, 
									   	args)), 
									   	stacklevel = 2)
				elif self._stripping not in args:
					raise NotImplementedError( "Stripping version {0} is not available for {1} {2}! Only {3}!".format( 
									   	self._stripping, 
									   	self._year, 
									   	self._simcond, 
									   	args) )	
						
		if self._simcond == "Sim09b" and ( self._year == 2011 or self._year == 2017 ):
			raise NotImplementedError( "{0} setup is not (yet) implemented for {1}!".format(
										self._year, 
										self._simcond) )
			
		elif self._simcond == "Sim09c" and self._year == 2017:
			raise NotImplementedError( "{0} setup is not (yet) implemented for {1}!".format(
										self._year, 
										self._simcond) )
		
		if self._year == 2012:
			if self._simcond == "Sim09b":
				StrippingVersion("21")
			elif self._simcond == "Sim09c":
				StrippingVersion("21")
			
		elif self._year == 2015:
			if self._simcond == "Sim09b":
				StrippingVersion("24")
			if self._simcond == "Sim09c":
				StrippingVersion("24r1", "24r1p1")
			
		elif self._year == 2016:
			if self._simcond == "Sim09b":
				StrippingVersion("28")
			if self._simcond == "Sim09c":
				StrippingVersion("28r1", "28r1p1")	
								
		if self._mudst and ( self._year == 2012 or self._year == 2011 ):
			raise NotImplementedError( "No micro DST output for {0}!".format(self._year) )
				
		if self._turbo and ( self._year == 2012 or self._year == 2011 ):
			raise NotImplementedError( "Turbo is not implemented for {0}!".format(self._year) )
			
	def __setoptfile( self ):
		moddir = os.getenv("SIMPRODPATH")
		self._optfile = "{0}/EvtTypes/{1}/{1}.py".format( moddir, self._evttype )
	
		if not os.path.isfile( self._optfile ):
			GetEvtType.get( evttype = self._evttype, decfiles = self._decfiles )
			
	def __add_var(self, var, get_set):
		setattr(SimulationJob, var, property(*get_set))
		self.__dict__[var] = getattr(SimulationJob, var)
		
	def _store_job(self):
		simprod = os.getenv("SIMPRODPATH")+"/simprod"
		jobsdir = "{0}/._simjobs_".format(simprod)
		
		if not os.path.isdir(jobsdir):
			os.system("mkdir -p {0}".format(jobsdir))
				
		jobfile = "{0}/{1}_{2}_{3}_{4}_{5}.json".format(
					jobsdir,
					self.evttype,
					self.year,
					self.nevents,
					self.neventsjob,
					self._runnumber,
					)
					
		outdict = {"evttype":     self.evttype,
				   "year"   :	  self.year,
				   "nevents":     self.nevents,
				   "neventsjob":  self.neventsjob,
				   "_nsubjobs":   self.nsubjobs,
				   "simcond":     self.simcond,
				   "stripping":   self.stripping,
				   "basedir":     self.options["basedir"],
				   "subdir":      self.options["subdir"],
				   "_proddir" :   self.proddir,
				   "_destdir":    self.destdir,
				   "runnumber":   self._runnumber,
				   "slurm":       self.options["slurm"],
				   "lsf":         self.options["lsf"],
				   "toeos":		  self.options["toeos"],
				   "mudst":       self.mudst,
				   "turbo":       self.turbo,
				   "jobs":        {}
				   } 
				
		if self._options["toeos"]:
			outdict["_eosdir"] = self.options["eosdir"]
			outdict["_eosproddir"] = self.options["eosproddir"]
			
		jsondict = json.dumps(outdict)
		f = open(jobfile, "w")
		f.write(jsondict)
		f.close()
				
		self._options["jobfile"] = jobfile
		
	def remove( self ):
				
		if self.status == "running":
			raise NotImplementedError("Cannot remove running jobs!")

		if os.path.isfile(self.options["jobfile"]):
			os.remove(self.options["jobfile"])
			
		for i in range(self.nsubjobs):
			job = self[i]
			job.kill()
								
	@classmethod
	def from_file(cls, file):
		data = json.load(open(file))
		simcollection = cls( **data )
		simcollection.options["jobfile"] = file
		### prepare like 
				
		jobs = data["jobs"]
				
		for n in jobs.keys():
			simcollection._subjobs[n] = SimulationSubJob(parent = simcollection, jobnumber=n, **jobs[n])
															
		return simcollection
		
	def __str__(self):
		
		if len(self._subjobs) > 0:
			toprint  = "evttype: {0}; year: {1}; #events {2}; stripping {3}; simcond {4}; {5} jobs\n".format( 
						self.evttype,
						self.year,
						self.nevents,
						self.stripping,
						self.simcond,
						self.nsubjobs )
			
			h_job        = "    #job "
			h_jobID      = "    job ID "
			h_status     = "       status "
			h_runnumber  = "      runnumber "
			h_polarity   = "   polarity "
			h_nevents    = "  #events "
			
			header = "{0}|{1}|{2}|{3}|{4}|{5}|\n".format( 
						h_job,
						h_jobID, 
						h_status, 
						h_runnumber, 
						h_polarity, 
						h_nevents)
						
			line = "-"*(len(header) - 2) + "\n"	
			toprint += line
			toprint += header
			
			for i in range(self.nsubjobs):
				
				job = self[i]
				
				toprint += line
				
				status    = job.status
				jobID     = str(job.jobid)
				runnumber = str(job.runnumber)
				polarity  = job.polarity
				nevents   = str(self.neventsjob)
				
				if status == "submitted":
					color = cyan
				elif status == "new":
					color = cdefault
				elif status == "running":
					color = green
				elif status == "completed":
					color = blue
				elif status == "failed":
					color = red
				
				p_job       = " "*(len(h_job) - len(str(i)) - 1) + str(i) + " "
				
				p_jobID     = " "*(len(h_jobID) - len(jobID) - 1) + jobID + " "
				
				p_status    = " "*(len(h_status) - len(status) - 1) + status + " "
				
				p_runnumber = " "*(len(h_runnumber) - len(runnumber) - 1) + runnumber + " "
				
				p_polarity  = " "*(len(h_polarity) - len(polarity) - 1) + polarity + " "
				
				p_nevents   = " "*(len(h_nevents) - len(nevents) - 1) + nevents + " "
										
				toprint += color("{0}|{1}|{2}|{3}|{4}|{5}|\n".format( 
							p_job, 
							p_jobID,
							p_status, 
							p_runnumber, 
							p_polarity, 
							p_nevents))						
		else:
			toprint = self.__repr__()
		
		return toprint
		
	def _repr_pretty_(self, p, cycle):
		if cycle:
			p.text('simulation job...')
			return
		p.text(self.__str__())
		
	def __destination(self):

		if self.toeos:
			return self.options["eosdir"]
		else:
			return self.options["basedir"]
		
					
class SimulationSubJob(object):
	"""
	Simulation subjob.
	"""
	
	def __init__(self, parent, polarity, runnumber, jobnumber, **kwargs):
		self._parent       = parent
		self._polarity     = polarity
		self._runnumber    = runnumber
		self._jobnumber    = jobnumber
		self._jobid        = kwargs.get("jobid", None)	
		self._send_options = self._parent.options.copy()
						
		self._infiles = kwargs.get('infiles', [])
		if not isinstance(self._infiles, list) and " " in self._infiles:
			self._infiles = self._infiles.split(" ")
		elif not isinstance(self._infiles, list):
			self._infiles = [self._infiles]
		
		self._jobname = "{0}_{1}_{2}evts_s{3}_{4}".format( 
							self._parent.year, 
							self._polarity, 
							self._parent.neventsjob, 
							self._parent.stripping, 
							self._runnumber )
							
		_subdir = "{0}_{1}_{2}evts_s{3}_{4}".format( 
							self._parent.year, 
							self._polarity, 
							self._parent.neventsjob, 
							self._parent.stripping, 
							self._runnumber)
							
		self._ext = "dst"	
		if self._parent.mudst:
			self._ext = "mdst"
			
		self._jobdir = kwargs.get("_jobdir", None)
		if not self._jobdir:					
			self._jobdir = "{0}/{1}".format(
							self._parent.proddir,
							_subdir)		
		
		self._prodfile = kwargs.get("_prodfile", None)
		if not self._prodfile:		
			self._prodfile = "{0}/{1}_events.{2}".format( 
							self._jobdir,
							self._parent.neventsjob, 
							self._ext )
							
		if self._send_options["toeos"]:
			
			self._eosjobdir = kwargs.get("_eosjobdir", None)
			if not self._eosjobdir:
				self._eosjobdir = "{0}/{1}".format(
								self._send_options["eosproddir"],
								_subdir)	
			
			self._eosprodfile = kwargs.get("_eosprodfile", None)
			if not self._eosprodfile:
				self._eosprodfile = "{0}/{1}_events.{2}".format( 
								self._eosjobdir,
								self._parent.neventsjob, 
								self._ext )
								
			def eos_get_set(attribute):
				def getter(self):
					return attribute
				def setter(self, directory):
					return attribute
				return getter, setter
				
			setattr(SimulationSubJob, "eosjobdir", property(*eos_get_set(self._eosjobdir)))
			self.__dict__["eosjobdir"] = getattr(SimulationSubJob, "eosjobdir")
				
			setattr(SimulationSubJob, "eosprodfile", property(*eos_get_set(self._eosprodfile)))
			self.__dict__["eosprodfile"] = getattr(SimulationSubJob, "eosprodfile")
			
		self._destfile = kwargs.get("_destfile", None)															
		if not self._destfile:
							
			self._destfile = "{0}/{1}/{2}evts_s{3}_{4}.{5}".format( 
									self._parent.destdir, 
									self._polarity, 
									self._parent.neventsjob, 
									self._parent.stripping, 
									self.runnumber, 
									self._ext )
		
		self._send_options["jobname"] = self._jobname
		self._send_options["infiles"] = self._infiles
		self._send_options["command"] = self._command()
		
		self._submitted = kwargs.get("_submitted", False)
		self._running   = kwargs.get("_running", False)
		self._finished  = kwargs.get("_finished", False)
		self._completed = kwargs.get("_completed", False)
		self._failed    = kwargs.get("_failed", False)
		self._store_subjob()
		
	@property
	def jobdir( self):
		return self._jobdir
				
	@property
	def prodfile( self):
		return self._prodfile
		
	@property
	def destfile( self):
		return self._destfile
				
	@property	
	def send( self):
		if not self._submitted or self._failed:
			send_options = self._send_options
			self._jobid = submit( **send_options )
			self._submitted = True
			self._running   = False
			self._finished  = False
			self._completed = False
			self._failed    = False
			self._store_subjob()
						
			time.sleep(0.07)
			print( blue( "{0}/{1} jobs submitted!".format( int(self._jobnumber) + 1, self._parent.nsubjobs ) ) )
			time.sleep(0.07)
			
			
	@property
	def jobid( self):
		return self._jobid
		
	@property
	def polarity( self):
		return self._polarity
		
	@property
	def runnumber( self):
		return self._runnumber
					
	@property
	def status( self):
		if not self._finished and self._submitted:
			self.__updatestatus()
		if not self._submitted:
			self._status = "new"
		elif self._submitted and not self._running and not self._finished:
			self._status = "submitted"
		elif self._submitted and self._running and not self._finished:
			self._status = "running"
		elif self._submitted and not self._running and self._finished:
			if self._completed:
				self._status = "completed"
				if not self.output == self.destfile:
					self.__move_jobs()
			elif self._failed:
				self._status = "failed"
				self.__empty_proddir(keep_log = True)
				
		return self._status
				
	@property
	def step( self):
		raise NotImplementedError
		
	@property
	def application( self):
		raise NotImplementedError
				
	@property
	def out( self):
		raise NotImplementedError
		
	@property
	def err( self):
		raise NotImplementedError
		
	@property
	def output( self):
		if os.path.isfile( self._prodfile):
			return self._prodfile
		elif os.path.isfile( self._destfile):
			return self._destfile
		elif self._send_options["toeos"] and os.path.isfile(self._eosprodfile):
			return self._eosprodfile		
		else:
			return ""
			
	def _command( self ):
		doprod  = DoProd( self._parent.simcond, self._parent.year)
		
		command  = doprod
		command += ' {0}'.format( self._parent.optfile)
		command += ' {0}'.format( self._parent.neventsjob)
		command += ' {0}'.format( self._polarity)
		command += ' {0}'.format( self._runnumber)
		command += ' {0}'.format( self._parent.turbo)
		command += ' {0}'.format( self._parent.mudst)
		command += ' {0}'.format( self._parent.stripping)
			
		return command
					
	def __updatestatus( self):
		if self._send_options["slurm"]:
			status = GetSlurmStatus( self.jobid )								
		elif self._send_options["lsf"]:
			status = GetLSFStatus( self.jobid )
						
		if status == "running" and not self._running:
			self._running = True
			
		if status == "completed" or status == "canceled" or status == "failed" or status == "notfound":
			self._running  = False
			self._finished = True
						
			if self.output != "" and os.path.isfile( self.output ):							
				if os.path.isfile( self.output ) and os.path.getsize( self.output ) > 1000000:
					self._completed = True
				elif os.path.isfile( self.output ) and os.path.getsize( self.output ) < 1000000:
					self._failed = True	
			elif self.output == "":
				self._failed = True
				
	def kill( self ):
		if self._running and not self._finished:
			if self._send_options["slurm"]:
				KillSlurm( self.jobid )
			elif self._send_options["lsf"]:
				KillLSF( self.jobid )
				
			self._failed = True
			self._running = False
			self._completed = False
			self._finished  = True
			self._store_subjob()
			self.__empty_proddir()
			
	def __empty_proddir( self, keep_log = False ):
		if os.path.isdir(self._jobdir):
			if keep_log:
				files = glob.glob(self._jobdir + "/*")
				for f in files:
					if "out" in f or "err" in f:
						continue
					else:
						os.remove(f) 
			else:
				print "EMPTY JOB {0} DIR".format(self._jobnumber)
				os.system("rm -rf {0}".format(self._jobdir))
		if self._send_options["toeos"] and os.path.isdir(self._eosjobdir):
			print "EMPTY EOS JOB {0} DIR".format(self._jobnumber)
			os.system("rm -rf {0}".format(self._eosjobdir))
			
	def __move_jobs( self ):
		print "MOVING JOB {0}".format(self._jobnumber)
		if self._send_options["toeos"]:
			dst_prodfile = self.eosprodfile
			mover = Move
		else:
			dst_prodfile = self.prodfile
			mover = EosMove
			
		xml_prodfile = os.path.dirname(dst_prodfile) + "/GeneratorLog.xml"	
		dst_destfile = self.destfile
		xml_destfile = os.path.dirname(self.destfile) + "/xml/{0}.xml".format(self.runnumber)

		mover( dst_prodfile, dst_destfile )
		mover( xml_prodfile, xml_destfile )
		
		self.__empty_proddir()
		
	def _store_subjob(self):
		
		_jobfile = self._parent.options["jobfile"]
		_dict = json.load(open(_jobfile))	
		
		_subjob = _dict["jobs"]
		
		_subjob[str(self._jobnumber)] = {
			       "runnumber":   self.runnumber,
			       "polarity":    self.polarity,
			       "jobid":       self.jobid,
				   "_prodfile":   self.prodfile,
			       "_jobdir":     self.jobdir,
				   "_destfile":   self.destfile,
				   "_submitted":  self._submitted,
				   "_running":    self._running,
				   "_finished":   self._finished,
				   "_completed":  self._completed,
				   "_failed":     self._failed
					  }
		if self._send_options["toeos"]:
			_subjob[str(self._jobnumber)]["_eosprodfile"] = self.eosprodfile
			_subjob[str(self._jobnumber)]["_eosjobdir"] = self.eosjobdir
						
		jsondict = json.dumps(_dict)
		f = open(_jobfile, "w")
		f.write(jsondict)
		f.close()		

