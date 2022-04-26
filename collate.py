#!/usr/bin/env python3
"""A simple utility to collate dumpvdl2 messages

"""

import collections
import dateutil.parser
import flask
import sys
import threading
import time
import re

hex_to_messages = None  # will be written later
app = flask.Flask(__name__)


class HexToMessages:
  def __init__(self):
    self.map = collections.defaultdict(lambda: [])
    self.num_messages = 0

  def add_message(self, message):
    valid_message = False
    if message.from_hex:
      self.map[message.from_hex].append(message)
      valid_message = True
    if message.to_hex:
      self.map[message.to_hex].append(message)
      valid_message = True
    if valid_message:
      self.num_messages += 1


class Message:
  def __init__(self, raw):
    self.raw = raw
    self._parse_acquisition()
    self._parse_endpoints()

  def __repr__(self):
    return "%s (%s) -> %s (%s)" % (self.from_hex, self.from_type, self.to_hex, self.to_type)

  def __str__(self):
    return "\n".join(raw)

  def _parse_acquisition(self):
    self.timestamp = None
    for line in self.raw:
      matched = re.fullmatch(r"\[([0-9 :A-Z-]*)\] \[([0-9.]*)\] \[.*\] \[([0-9.]*) dB\].*", line)
      if matched:
        self.timestamp = dateutil.parser.parse(matched.group(1))
        self.freq = float(matched.group(2))
        self.dB = float(matched.group(3))

  def _parse_endpoints(self):
    self.from_hex = None
    self.from_type = None
    self.to_hex = None
    self.to_type = None
    for line in self.raw:
      matched = re.fullmatch(r"([A-F0-9]+) \(([^,]*).*\) -> ([A-F0-9]+) \(([^,]*).*\): (.*)", line)
      if matched:
        self.from_hex = matched.group(1)
        self.from_type = matched.group(2)
        self.to_hex = matched.group(3)
        self.to_type = matched.group(4)


class Reader:

  def __init__(self, log_filename, hex_to_messages):
    self.log_filename = log_filename
    self.hex_to_messages = hex_to_messages
 
  def start_thread(self):
    self.reader_thread = threading.Thread(target=self._data_reader_thread)
    self.reader_thread.daemon = True
    self.reader_thread.start()

  def _data_reader_thread(self):
    with open(self.log_filename, "r") as f:
      for message in self._tail_messages(f):
        self.hex_to_messages.add_message(message)

  def _tail_lines(self, f):
    lastpos = 0
    while True:
      line = f.readline()
      newpos = f.tell()
      if lastpos != newpos:
        yield line
      else:
        time.sleep(0.1)
      lastpos = newpos

  def _tail_messages(self, f):
    message_buffer = []
    for line in self._tail_lines(f):
      if line == "\n":
        if message_buffer:
          yield Message(message_buffer)
          message_buffer = []
      else:
        message_buffer.append(line.rstrip("\n"))


@app.route("/")
def root():
  return "number of messages: %d" % hex_to_messages.num_messages

if __name__ == "__main__":
  if len(sys.argv) != 2:
    print("Please pass the log file")
    sys.exit(1)
  log_file = sys.argv[1]

  hex_to_messages = HexToMessages()
  reader = Reader(log_file, hex_to_messages)
  reader.start_thread()
  # Starts the web server
  app.run(host="0.0.0.0")
