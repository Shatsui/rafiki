import struct
import zlib
import os
import fnmatch
import re

class RafFile():
	def __init__(self, dat_file_location):
		self.dat_file_location = dat_file_location

	def extract(self):
		with open(self.dat_file_location, 'rb') as fd:
			fd.seek(self.data_offset)
			raw_data = fd.read(self.data_size)
			try:
				data = zlib.decompress(raw_data)
			except:
				self.uncompressed = True
				data = raw_data
		return data


class RafArchive():
	def __init__(self, path):
		self.files = list()
		self.paths = list()
		self.index = dict()
		self.path = path

		with open(path, "rb") as f:
			self.magic_number = f.read(4)
			self.version = struct.unpack("<I", f.read(4))[0]
			self.manager_index = struct.unpack("<I", f.read(4))[0]
			self.file_list_offset = struct.unpack("<I", f.read(4))[0]
			self.path_list_offset = struct.unpack("<I", f.read(4))[0]

			assert self.file_list_offset == f.tell()
			
			self.file_entries_count = struct.unpack("<I", f.read(4))[0]
			for i in range(self.file_entries_count):
				raf = RafFile(path + ".dat")
				raf.hash = struct.unpack("<I", f.read(4))[0]
				raf.data_offset = struct.unpack("<I", f.read(4))[0]
				raf.data_size = struct.unpack("<I", f.read(4))[0]
				raf.path_list_index = struct.unpack("<I", f.read(4))[0]
				self.files.append(raf)

			assert self.path_list_offset == f.tell()

			self.path_list_size = struct.unpack("<I", f.read(4))[0]
			self.path_list_count = struct.unpack("<I", f.read(4))[0]
			path_list_start_offset = f.tell()

			for i in range(self.path_list_count):
				f.seek(path_list_start_offset + (i)*8)
				path_offset = struct.unpack("<I", f.read(4))[0]
				path_length = struct.unpack("<I", f.read(4))[0]
				f.seek(self.path_list_offset + path_offset)
				path = f.read(path_length)
				path = path.strip('\x00')
				self.paths.append(path)

			for raffile in self.files:
				raffile.path = self.paths[raffile.path_list_index]
				self.index[raffile.path] = raffile

	def save(self, path):
		with open(path, "wb") as f:
			# HEADER
			f.write(self.magic_number)
			f.write(struct.pack("<I", self.version))
			f.write(struct.pack("<I", self.manager_index))
			f.write(struct.pack("<I", self.file_list_offset))
			f.write(struct.pack("<I", self.path_list_offset))

			assert self.file_list_offset == f.tell()

			#FILE LIST
			f.write(struct.pack("<I", self.file_entries_count))
			for raf_file in self.files:
				f.write(struct.pack("<I", raf_file.hash))
				f.write(struct.pack("<I", raf_file.data_offset))
				f.write(struct.pack("<I", raf_file.data_size))
				f.write(struct.pack("<I", raf_file.path_list_index))

			assert self.path_list_offset == f.tell()

			#PATH LIST
			f.write(struct.pack("<I", self.path_list_size))
			f.write(struct.pack("<I", self.path_list_count))

			assert len(self.paths) == self.path_list_count

			# path list offset + 8 bytes for path_list_size adn
			# path_list count + 8 bytes for each path_data entry
			path_offset = self.path_list_offset + 8 + len(self.paths)*8

			paths_data = list()
			for path in self.paths: 
				path = path + "\x00"
				paths_data.append({
					"path_offset": path_offset - self.path_list_offset,
					"path_length": len(path)
				})
				path_offset = path_offset + len(path)

			for path_data in paths_data:
				f.write(struct.pack("<I", path_data['path_offset']))
				f.write(struct.pack("<I", path_data['path_length']))

			for i in range(len(self.paths)):
				assert self.path_list_offset + paths_data[i]['path_offset'] == f.tell()
				f.write(self.paths[i] + "\x00")


class RafCollection():
	def __init__(self, path):
		self.index = dict()
		items = os.listdir(path)
		for item in items:
			for filename in os.listdir(os.path.join(path, item)):
				if fnmatch.fnmatch(filename, '*.raf'):
					self.index[item] = RafArchive(os.path.join(path, item, filename))

	def search(self, text):
		matching_archives = list()
		for item,raf in self.index.iteritems():
			for path,archive in raf.index.iteritems():
				if(re.search(text, path, re.IGNORECASE)):
					matching_archives.append(archive)
		return matching_archives



					

 